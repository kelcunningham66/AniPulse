"""Personalized alerts for the shows a person follows.

Each story is stored once per user. In-app delivery is always recorded.
Email and push send when their credentials exist, and stay in the inbox
as a held copy when they do not.
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib import error, request

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Alert, Delivery, Release, StreamingOffer, Title, UpdateEvent, User, WatchProgress
from app.services.timeutil import fmt_day, fmt_time

CATEGORIES = ("episode", "dub", "delay", "renewal", "streaming")
CATEGORY_FLAG = {
    "episode": "notify_episodes",
    "dub": "notify_dubs",
    "delay": "notify_delays",
    "renewal": "notify_renewals",
    "streaming": "notify_streaming",
}
EPISODE_KINDS = {"sub", "manga", "movie", "premiere"}
DUB_KINDS = {"dub_en": "English", "dub_es": "Spanish"}


def smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"))


def push_configured() -> bool:
    return bool(os.getenv("FCM_SERVER_KEY"))


def category_enabled(user: User, category: str) -> bool:
    return bool(getattr(user, CATEGORY_FLAG[category], False))


def channel_note(user: User) -> str:
    if user.notify_email and smtp_configured() and user.email_address:
        email = f"email sends to {user.email_address}"
    elif user.notify_email:
        email = "email is held in AniPulse until an address and SMTP_HOST are set"
    else:
        email = "email is off"
    if user.notify_push and push_configured() and user.push_token:
        push = "push sends to the saved device"
    elif user.notify_push:
        push = "push is held in AniPulse until a device token and FCM_SERVER_KEY are set"
    else:
        push = "push is off"
    inbox = "In-app alerts are on" if user.notify_in_app else "In-app alerts are off"
    return f"{inbox}. {email[0].upper() + email[1:]}. {push[0].upper() + push[1:]}. Each story is sent once."


def materialize_alerts(db: Session, user: User, now: datetime) -> int:
    """Create missing alerts and deliver them. Returns how many were already sent."""
    if not user.notify_enabled:
        return 0
    from app.services.query import scopes

    explicit, expanded, _ = scopes(db, user)
    if not expanded:
        return 0
    existing = set(
        db.scalars(select(Alert.dedupe_key).where(Alert.user_id == user.id)).all()
    )
    titles = {title.id: title for title in db.scalars(select(Title).where(Title.id.in_(expanded)))}
    candidates = _candidates(db, user, expanded, titles, now)
    skipped = 0
    for candidate in candidates:
        if not category_enabled(user, candidate["category"]):
            continue
        if candidate["dedupe_key"] in existing:
            skipped += 1
            continue
        alert = Alert(
            user_id=user.id,
            dedupe_key=candidate["dedupe_key"],
            category=candidate["category"],
            title_id=candidate["title_id"],
            headline=candidate["headline"],
            body=candidate["body"],
            citations=candidate["citations"],
            created_at=now,
            read=False,
        )
        try:
            with db.begin_nested():
                db.add(alert)
                db.flush()
                _deliver(db, user, alert, now)
        except IntegrityError:
            skipped += 1
            continue
        existing.add(candidate["dedupe_key"])
    _release_held(db, user, now)
    db.commit()
    return skipped


def alert_rows(db: Session, user: User) -> list[dict]:
    alerts = list(
        db.scalars(select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc(), Alert.id.desc()))
    )
    if not alerts:
        return []
    titles = {
        title.id: title
        for title in db.scalars(select(Title).where(Title.id.in_({row.title_id for row in alerts if row.title_id})))
    }
    deliveries = list(db.scalars(select(Delivery).where(Delivery.alert_id.in_([row.id for row in alerts]))))
    by_alert: dict[int, list[Delivery]] = {}
    for delivery in deliveries:
        by_alert.setdefault(delivery.alert_id, []).append(delivery)
    visible = []
    for alert in alerts:
        if not category_enabled(user, alert.category):
            continue
        title = titles.get(alert.title_id or -1)
        visible.append(
            {
                "id": alert.id,
                "category": alert.category,
                "slug": title.slug if title else None,
                "name": title.name if title else alert.headline,
                "headline": alert.headline,
                "body": alert.body,
                "citations": alert.citations or [],
                "created_at": alert.created_at.isoformat(),
                "read": alert.read,
                "deliveries": [
                    {
                        "channel": item.channel,
                        "status": item.status,
                        "destination": item.destination,
                        "detail": item.detail,
                    }
                    for item in by_alert.get(alert.id, [])
                ],
            }
        )
    return visible


def mark_read(db: Session, user: User, alert_id: int | None) -> int:
    rows = list(db.scalars(select(Alert).where(Alert.user_id == user.id, Alert.read.is_(False))))
    changed = 0
    for row in rows:
        if alert_id is not None and row.id != alert_id:
            continue
        row.read = True
        changed += 1
    db.commit()
    return changed


def _candidates(db: Session, user: User, title_ids: set[int], titles: dict[int, Title], now: datetime) -> list[dict]:
    from app.services.query import aware

    start = now - timedelta(days=3)
    horizon = now + timedelta(days=21)
    progress = _progress(db, user)
    events = [
        event
        for event in db.scalars(select(UpdateEvent).where(UpdateEvent.title_id.in_(title_ids)))
        if event.title_id in titles
    ]
    found: list[dict] = []
    covered: set[tuple[int, str]] = set()
    for event in events:
        category = _update_category(event)
        if category is None:
            continue
        title = titles[event.title_id]
        visible = _visible_changes(event, progress.get(title.id, 0), user)
        if not visible and category != "delay":
            continue
        publishers = [source.get("publisher", "") for source in (event.sources or []) if source.get("publisher")]
        body = visible[0] if visible else event.headline
        if publishers:
            body = f"{body} Source: {', '.join(publishers)}."
        found.append(
            {
                "dedupe_key": f"update:{event.id}:{category}",
                "category": category,
                "title_id": title.id,
                "headline": _category_headline(category, title.name),
                "body": body,
                "citations": [
                    {"publisher": source.get("publisher", ""), "headline": event.headline}
                    for source in (event.sources or [])
                ],
            }
        )
        covered.add((title.id, category))

    offers = db.scalars(select(StreamingOffer).where(StreamingOffer.title_id.in_(title_ids)))
    for offer in offers:
        if not offer.is_new or not offer.available or offer.region != user.region:
            continue
        if (offer.title_id, "streaming") in covered:
            continue
        title = titles[offer.title_id]
        note = f" {offer.note}." if offer.note else ""
        found.append(
            {
                "dedupe_key": f"offer:{offer.id}",
                "category": "streaming",
                "title_id": title.id,
                "headline": f"New on {offer.service}",
                "body": f"{title.name} is newly available on {offer.service} in {offer.region}.{note}",
                "citations": [{"publisher": offer.service, "headline": offer.note or "Newly added"}],
            }
        )
        covered.add((title.id, "streaming"))

    releases = db.scalars(select(Release).where(Release.title_id.in_(title_ids)))
    for release in releases:
        starts = aware(release.starts_at)
        if starts is None or starts < start or starts > horizon:
            continue
        category = _release_category(user, release.kind)
        if category is None or (release.title_id, category) in covered:
            continue
        title = titles[release.title_id]
        fire_at = starts - timedelta(minutes=user.notify_lead_minutes)
        language = DUB_KINDS.get(release.kind)
        label = f"{language} dub {release.label}" if language else release.label
        where = f" on {release.platform}" if release.platform else ""
        found.append(
            {
                "dedupe_key": f"release:{release.id}",
                "category": category,
                "title_id": title.id,
                "headline": _category_headline(category, title.name),
                "body": (
                    f"{label}{where}, {fmt_day(starts)} at {fmt_time(starts)}. "
                    f"Reminder {user.notify_lead_minutes} minutes before, {fmt_day(fire_at)} at {fmt_time(fire_at)}."
                ),
                "citations": [{"publisher": release.platform or "Schedule", "headline": release.label}],
            }
        )
    return found


def _update_category(event: UpdateEvent) -> str | None:
    changes = event.changes or []
    text = " ".join(
        [event.headline, event.kicker, event.primary_type]
        + [item.get("text", "") for item in changes]
    ).lower()
    types = {item.get("type") for item in changes}
    if event.primary_type == "schedule" or "schedule" in types or "delayed" in text or "skip a week" in text:
        return "delay"
    if "no season" in text or "has not been named" in text or "not been announced" in text:
        renewal = False
    else:
        renewal = (
            "renew" in text
            or "another season" in text
            or "premiere window" in text
            or "season premiere" in text
        )
    if renewal:
        return "renewal"
    if "dub" in text or event.primary_type == "dub":
        return "dub"
    if event.primary_type == "streaming" or "streaming" in types or "now available" in text or "added" in text and "netflix" in text:
        return "streaming"
    return None


def _release_category(user: User, kind: str) -> str | None:
    if kind in DUB_KINDS:
        if user.audio_mode == "dub" and DUB_KINDS[kind] and not kind.endswith(user.audio_language):
            return None
        return "dub"
    if user.audio_mode == "dub":
        return None
    if kind in EPISODE_KINDS:
        return "episode"
    return None


def _visible_changes(event: UpdateEvent, progress: int, user: User) -> list[str]:
    from app.services.spoiler import guard_changes

    visible, _hidden = guard_changes(event.changes or [], progress, user.spoiler_protection)
    return visible


def _progress(db: Session, user: User) -> dict[int, int]:
    return {
        row.title_id: row.episode
        for row in db.scalars(select(WatchProgress).where(WatchProgress.user_id == user.id))
    }


def _category_headline(category: str, name: str) -> str:
    labels = {
        "episode": "New episode",
        "dub": "Dubbed release",
        "delay": "Schedule delay",
        "renewal": "Renewal",
        "streaming": "Now streaming",
    }
    return f"{labels[category]} · {name}"


def _release_held(db: Session, user: User, now: datetime) -> None:
    """Send copies that were held until an address and credentials existed."""
    held = list(
        db.scalars(
            select(Delivery)
            .join(Alert, Alert.id == Delivery.alert_id)
            .where(Alert.user_id == user.id, Delivery.status == "recorded")
        )
    )
    if not held:
        return
    alerts = {
        alert.id: alert
        for alert in db.scalars(select(Alert).where(Alert.id.in_({row.alert_id for row in held})))
    }
    for delivery in held:
        alert = alerts.get(delivery.alert_id)
        if alert is None or not category_enabled(user, alert.category):
            continue
        if delivery.channel == "email" and user.notify_email:
            replacement = _email(user, alert, now)
        elif delivery.channel == "push" and user.notify_push:
            replacement = _push(user, alert, now)
        else:
            continue
        if replacement.status == "recorded":
            continue
        delivery.status = replacement.status
        delivery.destination = replacement.destination
        delivery.detail = replacement.detail


def _deliver(db: Session, user: User, alert: Alert, now: datetime) -> None:
    if user.notify_in_app:
        db.add(_row(alert, "in_app", "sent", "In-app", "Shown in Alerts.", now))
    if user.notify_email:
        db.add(_email(user, alert, now))
    if user.notify_push:
        db.add(_push(user, alert, now))


def _row(alert: Alert, channel: str, status: str, destination: str, detail: str, now: datetime) -> Delivery:
    return Delivery(
        alert_id=alert.id,
        channel=channel,
        status=status,
        destination=destination,
        detail=detail,
        created_at=now,
    )


def _email(user: User, alert: Alert, now: datetime) -> Delivery:
    address = (user.email_address or "").strip()
    if not smtp_configured() or not address:
        return _row(
            alert,
            "email",
            "recorded",
            address or "No address yet",
            "Held in AniPulse. Add an email address and SMTP_HOST to send it.",
            now,
        )
    message = EmailMessage()
    message["Subject"] = alert.headline
    message["From"] = os.environ["SMTP_FROM"]
    message["To"] = address
    message.set_content(f"{alert.headline}\n\n{alert.body}\n")
    try:
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=10) as client:
            if os.getenv("SMTP_TLS", "1") != "0":
                client.starttls()
            username = os.getenv("SMTP_USER")
            password = os.getenv("SMTP_PASSWORD")
            if username and password:
                client.login(username, password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        return _row(alert, "email", "failed", address, f"Email could not be sent. {exc.__class__.__name__}.", now)
    return _row(alert, "email", "sent", address, "Sent.", now)


def _push(user: User, alert: Alert, now: datetime) -> Delivery:
    token = (user.push_token or "").strip()
    if not push_configured() or not token:
        return _row(
            alert,
            "push",
            "recorded",
            "This device" if token else "No device token",
            "Held in AniPulse. Add a device token and FCM_SERVER_KEY to send it.",
            now,
        )
    payload = json.dumps(
        {"to": token, "notification": {"title": alert.headline, "body": alert.body[:180]}}
    ).encode()
    call = request.Request(
        "https://fcm.googleapis.com/fcm/send",
        data=payload,
        headers={"Authorization": f"key={os.environ['FCM_SERVER_KEY']}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(call, timeout=10) as response:
            if response.status >= 400:
                return _row(alert, "push", "failed", "Device", "Push was rejected.", now)
    except (OSError, error.URLError):
        return _row(alert, "push", "failed", "Device", "Push could not be sent.", now)
    return _row(alert, "push", "sent", "Device", "Sent.", now)
