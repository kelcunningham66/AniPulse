"""Read models into the payloads the dashboard renders."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Follow,
    Franchise,
    Person,
    Prediction,
    Release,
    SourceDoc,
    StreamingOffer,
    Studio,
    Title,
    UpdateEvent,
    User,
    WatchProgress,
    AudioTrack,
)
from app.services.recommender import centroid, cosine, explain, vector
from app.services.spoiler import guard_changes, hidden_note
from app.services.timeutil import et_day, fmt_day, fmt_time

CORE_SERVICES = ["Crunchyroll", "Netflix", "Hulu"]
LANG_NAMES = {"ja": "Japanese", "en": "English", "es": "Spanish"}


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def app_now() -> datetime:
    return datetime.now(timezone.utc)


def get_user(db: Session) -> User:
    user = db.scalar(select(User).order_by(User.id))
    if user is None:
        raise LookupError("No user is loaded")
    return user


def _follows(db: Session, user: User) -> list[Follow]:
    return list(db.scalars(select(Follow).where(Follow.user_id == user.id)))


def scopes(db: Session, user: User) -> tuple[set[int], set[int], set[int]]:
    explicit: set[int] = set()
    franchise_ids: set[int] = set()
    studio_ids: set[int] = set()
    person_ids: set[int] = set()
    for follow in _follows(db, user):
        if follow.target_type == "title":
            explicit.add(follow.target_id)
        elif follow.target_type == "franchise":
            franchise_ids.add(follow.target_id)
        elif follow.target_type == "studio":
            studio_ids.add(follow.target_id)
        elif follow.target_type == "person":
            person_ids.add(follow.target_id)
    expanded = set(explicit)
    if franchise_ids or studio_ids:
        for title in db.scalars(select(Title)):
            if title.franchise_id in franchise_ids or title.studio_id in studio_ids:
                expanded.add(title.id)
    return explicit, expanded, person_ids


def _tracks(db: Session, title_ids: set[int] | list[int]) -> dict[int, list[AudioTrack]]:
    if not title_ids:
        return {}
    rows = db.scalars(select(AudioTrack).where(AudioTrack.title_id.in_(title_ids)))
    grouped: dict[int, list[AudioTrack]] = {}
    for row in rows:
        grouped.setdefault(row.title_id, []).append(row)
    return grouped


def _offers(db: Session, title_ids: set[int] | list[int]) -> dict[int, list[StreamingOffer]]:
    if not title_ids:
        return {}
    rows = db.scalars(select(StreamingOffer).where(StreamingOffer.title_id.in_(title_ids)))
    grouped: dict[int, list[StreamingOffer]] = {}
    for row in rows:
        grouped.setdefault(row.title_id, []).append(row)
    return grouped


def _progress_map(db: Session, user: User) -> dict[int, int]:
    rows = db.scalars(select(WatchProgress).where(WatchProgress.user_id == user.id))
    return {row.title_id: row.episode for row in rows}


def streaming_line(offers: list[StreamingOffer], region: str) -> str:
    names = [offer.service for offer in offers if offer.region == region and offer.available]
    if not names:
        return "Streaming: Not announced"
    return "Streaming: " + ", ".join(names)


def _preferred_code(user: User) -> str:
    if user.audio_mode == "dub" and user.audio_language in {"en", "es"}:
        return user.audio_language
    return "ja"


def card_for(
    title: Title,
    tracks: list[AudioTrack],
    offers: list[StreamingOffer],
    user: User,
) -> dict:
    by_lang = {track.language: track for track in tracks}
    japanese = by_lang.get("ja")
    english = by_lang.get("en")
    preferred = by_lang.get(_preferred_code(user))
    lines: list[str] = []
    next_at = None
    primary = title.list_release or title.season_label or title.name

    if user.audio_mode == "dub" and title.kind == "anime" and preferred and preferred.language != "ja":
        language = LANG_NAMES.get(preferred.language, "Dub")
        if preferred.latest_episode:
            primary = f"{language} dub · Episode {preferred.latest_episode}"
        else:
            primary = f"{language} dub"
        if preferred.next_at and preferred.next_episode:
            lines.append(f"Next for you: {fmt_day(preferred.next_at)}")
            next_at = preferred.next_at
        if japanese and japanese.latest_episode and preferred.latest_episode is not None:
            gap = japanese.latest_episode - preferred.latest_episode
            if gap > 0:
                lines.append(f"Japanese is {gap} episodes ahead")
        lines.append("Sub releases stay off this list")
    elif title.kind == "movie" or title.season_label == "Movie":
        primary = f"Release: {title.list_release}"
        lines.append(streaming_line(offers, user.region))
        if title.prediction_subject and title.official_specificity < 3:
            lines.append(f"{title.prediction_subject}: {title.prediction_official}")
        release_time = _next_release_at(title, tracks)
        next_at = release_time
    elif title.status == "completed":
        primary = "Series complete"
        fresh = [offer.service for offer in offers if offer.region == user.region and offer.available and offer.is_new]
        if fresh:
            lines.append(f"Now on {fresh[0]}")
        lines.append(streaming_line(offers, user.region))
    elif title.status == "announced":
        primary = title.season_label
        lines.append("Status: Announced")
        lines.append(f"Release: {title.list_release}")
    elif title.kind == "manga":
        track = japanese or preferred
        if track and track.latest_episode:
            primary = f"Chapter {track.latest_episode} — Released"
        if track and track.next_at:
            lines.append(f"Next chapter: {fmt_day(track.next_at)}")
            next_at = track.next_at
        lines.append("Serializing")
    elif title.kind == "tv" and title.status == "upcoming":
        primary = f"{title.season_label} premiere"
        lines.append(f"Release: {title.list_release}")
        lines.append(streaming_line(offers, user.region))
    elif title.status == "airing":
        if title.schedule_note and japanese and japanese.next_at:
            primary = f"Next episode: {fmt_day(japanese.next_at)}"
            next_at = japanese.next_at
            if japanese.latest_episode:
                lines.append(f"Episode {japanese.latest_episode} — Released")
        elif japanese and japanese.latest_episode:
            primary = f"Episode {japanese.latest_episode} — Released"
            if japanese.next_at:
                lines.append(f"Next episode: {fmt_day(japanese.next_at)}")
                next_at = japanese.next_at
        if english and english.latest_episode:
            lines.append(f"Dub: Episode {english.latest_episode} available")
        lines.append("Season status: Airing")
    else:
        primary = title.season_label or title.list_release
        if title.list_release:
            lines.append(title.list_release)

    return {
        "slug": title.slug,
        "name": title.name,
        "kind": title.kind,
        "season_label": title.season_label,
        "status": title.status,
        "accent": title.accent,
        "logline": title.logline,
        "primary": primary,
        "lines": lines,
        "warning": title.schedule_note,
        "next_at": aware(next_at).isoformat() if next_at else None,
    }


def _next_release_at(title: Title, tracks: list[AudioTrack]) -> datetime | None:
    dated = [track.next_at for track in tracks if track.next_at]
    return min(dated) if dated else None


def watchlist(db: Session, user: User) -> dict:
    explicit, _, _ = scopes(db, user)
    titles = list(db.scalars(select(Title).where(Title.id.in_(explicit)))) if explicit else []
    tracks = _tracks(db, explicit)
    offers = _offers(db, explicit)
    cards = [card_for(title, tracks.get(title.id, []), offers.get(title.id, []), user) for title in titles]
    rank = {"airing": 0, "serializing": 1, "upcoming": 2, "announced": 3, "completed": 4}

    def sort_key(card: dict) -> tuple:
        warning = 0 if card["warning"] else 1
        status = rank.get(card["status"], 5)
        nxt = card["next_at"] or "9999"
        return (warning, status, nxt, card["name"])

    cards.sort(key=sort_key)
    return {"items": cards}


def _visible_update(event: UpdateEvent, progress: int, user: User) -> dict:
    changes = event.changes or []
    visible, hidden = guard_changes(changes, progress, user.spoiler_protection)
    published = aware(event.published_at)
    checked = aware(user.last_checked_at)
    return {
        "id": event.id,
        "slug": None,
        "name": event.external_name or event.headline,
        "headline": event.headline,
        "kicker": event.kicker,
        "changes": visible,
        "hidden_count": hidden,
        "hidden_note": hidden_note(hidden, progress),
        "confidence": event.confidence,
        "confidence_label": event.confidence_label,
        "sources_verified": event.sources_verified,
        "sources": event.sources or [],
        "published_at": published.isoformat() if published else None,
        "is_new": bool(published and checked and published > checked),
        "primary_type": event.primary_type,
        "title_id": event.title_id,
        "person_id": event.person_id,
    }


def _attach_names(db: Session, rows: list[dict]) -> list[dict]:
    title_ids = {row["title_id"] for row in rows if row["title_id"]}
    titles = {}
    if title_ids:
        for title in db.scalars(select(Title).where(Title.id.in_(title_ids))):
            titles[title.id] = title
    people = {}
    person_ids = {row["person_id"] for row in rows if row["person_id"]}
    if person_ids:
        for person in db.scalars(select(Person).where(Person.id.in_(person_ids))):
            people[person.id] = person
    for row in rows:
        title = titles.get(row["title_id"])
        if title:
            row["slug"] = title.slug
            row["name"] = title.name
            row["accent"] = title.accent
        else:
            row["accent"] = "#ff4d2e"
        person = people.get(row["person_id"])
        row["person_slug"] = person.slug if person else None
        row["person_name"] = person.name if person else None
        row.pop("title_id", None)
        row.pop("person_id", None)
    return rows


def feed(db: Session, user: User, kind: str | None = None) -> dict:
    _, expanded, person_ids = scopes(db, user)
    events = list(db.scalars(select(UpdateEvent).order_by(UpdateEvent.published_at.desc())))
    progress = _progress_map(db, user)
    personal = []
    public = []
    for event in events:
        if kind and event.primary_type != kind:
            continue
        row = _visible_update(event, progress.get(event.title_id or -1, 0), user)
        matched = (event.title_id in expanded) or (event.person_id in person_ids)
        if matched:
            personal.append(row)
        elif event.external_name:
            public.append(row)
    personal = _attach_names(db, personal)
    public = _attach_names(db, public)
    collected = db.scalar(select(func.count()).select_from(SourceDoc)) or 0
    discarded = db.scalar(select(func.count()).select_from(SourceDoc).where(SourceDoc.rejected.is_(True))) or 0
    pending = db.scalar(select(func.count()).select_from(SourceDoc).where(SourceDoc.processed.is_(False))) or 0
    return {
        "updates": personal,
        "public": public,
        "stats": {
            "collected": collected,
            "published": len(events),
            "discarded": discarded,
            "pending": pending,
        },
    }


def _release_allowed(user: User, kind: str) -> bool:
    if user.audio_mode != "dub":
        return True
    if kind == "sub":
        return False
    if kind == "dub_en":
        return user.audio_language == "en"
    if kind == "dub_es":
        return user.audio_language == "es"
    return True


def calendar(db: Session, user: User, start: str, end: str, kinds: list[str] | None) -> dict:
    explicit, _, _ = scopes(db, user)
    if not explicit:
        return {"releases": []}
    if kinds is not None and len(kinds) == 0:
        return {"releases": [], "start": start, "end": end}
    titles = {title.id: title for title in db.scalars(select(Title).where(Title.id.in_(explicit)))}
    rows = db.scalars(select(Release).where(Release.title_id.in_(explicit)))
    allowed = set(kinds) if kinds else None
    releases = []
    for row in rows:
        if not _release_allowed(user, row.kind):
            continue
        if allowed is not None and row.kind not in allowed:
            continue
        day = et_day(row.starts_at)
        if day < start or day > end:
            continue
        title = titles[row.title_id]
        releases.append(
            {
                "id": row.id,
                "slug": title.slug,
                "name": title.name,
                "accent": title.accent,
                "label": row.label,
                "kind": row.kind,
                "starts_at": aware(row.starts_at).isoformat(),
                "day": day,
                "time": fmt_time(row.starts_at),
                "platform": row.platform,
                "note": row.note,
            }
        )
    releases.sort(key=lambda item: item["starts_at"])
    return {"releases": releases, "start": start, "end": end}


def _prediction_payload(title: Title, row: Prediction | None) -> dict:
    if row is None:
        return {
            "subject": title.prediction_subject or title.season_label,
            "official_text": title.prediction_official or title.list_release,
            "estimated_window": None,
            "confidence": None,
            "factors": [],
            "disclaimer": "A dated release is already on the calendar. No estimate is shown over an official date.",
            "skipped": True,
        }
    return {
        "subject": row.subject,
        "official_text": row.official_text,
        "estimated_window": row.estimated_window,
        "confidence": row.confidence,
        "factors": row.factors or [],
        "disclaimer": row.disclaimer,
        "skipped": row.skipped,
    }


def _offer_payload(offers: list[StreamingOffer], region: str) -> list[dict]:
    by_service = {offer.service: offer for offer in offers if offer.region == region}
    names = list(CORE_SERVICES)
    for service in by_service:
        if service not in names:
            names.append(service)
    payload = []
    for service in names:
        offer = by_service.get(service)
        payload.append(
            {
                "service": service,
                "available": bool(offer and offer.available),
                "is_new": bool(offer and offer.is_new),
                "note": offer.note if offer else "",
            }
        )
    return payload


def title_detail(db: Session, user: User, slug: str, region: str | None) -> dict | None:
    title = db.scalar(select(Title).where(Title.slug == slug))
    if title is None:
        return None
    explicit, _, _ = scopes(db, user)
    tracks = _tracks(db, [title.id]).get(title.id, [])
    offers = _offers(db, [title.id]).get(title.id, [])
    progress = _progress_map(db, user).get(title.id, 0)
    chosen = region or user.region
    events = list(
        db.scalars(
            select(UpdateEvent).where(UpdateEvent.title_id == title.id).order_by(UpdateEvent.published_at.desc())
        )
    )
    updates = _attach_names(db, [_visible_update(event, progress, user) for event in events])
    prediction = db.scalar(select(Prediction).where(Prediction.title_id == title.id))
    studio = db.get(Studio, title.studio_id) if title.studio_id else None
    franchise = db.get(Franchise, title.franchise_id) if title.franchise_id else None
    japanese = next((track for track in tracks if track.language == "ja"), None)
    track_rows = []
    for track in sorted(tracks, key=lambda item: {"ja": 0, "en": 1, "es": 2}.get(item.language, 9)):
        gap = None
        if japanese and japanese.latest_episode is not None and track.latest_episode is not None:
            gap = japanese.latest_episode - track.latest_episode
        track_rows.append(
            {
                "language": track.language,
                "name": LANG_NAMES.get(track.language, track.language),
                "latest_episode": track.latest_episode,
                "next_episode": track.next_episode,
                "next_at": aware(track.next_at).isoformat() if track.next_at else None,
                "next_day": fmt_day(track.next_at) if track.next_at else None,
                "behind": gap,
            }
        )
    upcoming = []
    moment = app_now() - timedelta(days=1)
    for release in db.scalars(select(Release).where(Release.title_id == title.id).order_by(Release.starts_at)):
        starts = aware(release.starts_at)
        if starts is None or starts < moment:
            continue
        upcoming.append(
            {
                "label": release.label,
                "kind": release.kind,
                "day": fmt_day(release.starts_at),
                "time": fmt_time(release.starts_at),
                "platform": release.platform,
                "note": release.note,
            }
        )
        if len(upcoming) == 4:
            break
    return {
        "slug": title.slug,
        "name": title.name,
        "kind": title.kind,
        "season_label": title.season_label,
        "status": title.status,
        "logline": title.logline,
        "genres": title.genres,
        "accent": title.accent,
        "followed": title.id in explicit,
        "progress": progress,
        "warning": title.schedule_note,
        "upcoming": upcoming,
        "card": card_for(title, tracks, offers, user),
        "tracks": track_rows,
        "streaming": {"region": chosen, "offers": _offer_payload(offers, chosen)},
        "prediction": _prediction_payload(title, prediction),
        "updates": updates,
        "studio": {"slug": studio.slug, "name": studio.name, "blurb": studio.blurb} if studio else None,
        "franchise": {"slug": franchise.slug, "name": franchise.name, "blurb": franchise.blurb} if franchise else None,
    }


def resolve_since(user: User, since: str | None, now: datetime) -> datetime:
    if not since or since == "last":
        checked = aware(user.last_checked_at)
        return checked or now - timedelta(days=60)
    if since.isdigit():
        return now - timedelta(days=int(since))
    parsed = datetime.fromisoformat(since)
    return aware(parsed) or parsed


def catchup(db: Session, user: User, since: str | None, slug: str | None, now: datetime | None = None) -> dict:
    moment = now or app_now()
    start = resolve_since(user, since, moment)
    explicit, expanded, person_ids = scopes(db, user)
    if slug:
        title = db.scalar(select(Title).where(Title.slug == slug))
        allowed = {title.id} if title else set()
    else:
        allowed = expanded
    progress = _progress_map(db, user)
    events = list(db.scalars(select(UpdateEvent).order_by(UpdateEvent.published_at.asc())))
    grouped: dict[int | str, dict] = {}
    for event in events:
        published = aware(event.published_at)
        if published is None or published < start:
            continue
        if event.title_id and event.title_id in allowed:
            key: int | str = event.title_id
        elif event.person_id and event.person_id in person_ids and not slug:
            key = f"person-{event.person_id}"
        else:
            continue
        row = _visible_update(event, progress.get(event.title_id or -1, 0), user)
        bucket = grouped.setdefault(key, {"bullets": [], "hidden": 0, "seen": set()})
        for change in row["changes"]:
            if change not in bucket["seen"]:
                bucket["seen"].add(change)
                bucket["bullets"].append(change)
        bucket["hidden"] += row["hidden_count"]
    titles = {title.id: title for title in db.scalars(select(Title))}
    people = {person.id: person for person in db.scalars(select(Person))}
    groups = []
    for key, bucket in grouped.items():
        if isinstance(key, int):
            title = titles.get(key)
            if title is None:
                continue
            groups.append(
                {
                    "slug": title.slug,
                    "name": title.name,
                    "accent": title.accent,
                    "kind": "title",
                    "bullets": bucket["bullets"],
                    "hidden_count": bucket["hidden"],
                    "hidden_note": hidden_note(bucket["hidden"], progress.get(title.id, 0)),
                }
            )
        else:
            person = people.get(int(key.split("-")[1]))
            if person is None:
                continue
            groups.append(
                {
                    "slug": person.slug,
                    "name": person.name,
                    "accent": person.accent,
                    "kind": "person",
                    "bullets": bucket["bullets"],
                    "hidden_count": bucket["hidden"],
                    "hidden_note": hidden_note(bucket["hidden"], 0),
                }
            )
    groups.sort(key=lambda item: item["name"])
    checked = aware(user.last_checked_at)
    return {
        "since": start.isoformat(),
        "last_checked_at": checked.isoformat() if checked else None,
        "groups": groups,
    }


def recommendations(db: Session, user: User) -> dict:
    explicit, _, _ = scopes(db, user)
    titles = list(db.scalars(select(Title)))
    followed = [title for title in titles if title.id in explicit]
    profile = centroid([title.themes or [] for title in followed])
    followed_pairs = [(title.name, title.themes or []) for title in followed]
    results = []
    for title in titles:
        if title.id in explicit:
            continue
        score = cosine(profile, vector(title.themes or []))
        if score <= 0:
            continue
        sibling = None
        if title.franchise_id:
            for other in followed:
                if other.franchise_id == title.franchise_id:
                    sibling = other.name
                    break
        results.append(
            {
                "slug": title.slug,
                "name": title.name,
                "kind": title.kind,
                "season_label": title.season_label,
                "logline": title.logline,
                "accent": title.accent,
                "genres": title.genres,
                "match": round(score * 100),
                "reason": explain(title.themes or [], followed_pairs, profile, sibling),
                "themes": title.themes,
            }
        )
    results.sort(key=lambda item: (-item["match"], item["name"]))
    return {"items": results}


def search(db: Session, user: User, q: str) -> dict:
    needle = f"%{q.strip()}%"
    explicit, _, _ = scopes(db, user)
    follows = _follows(db, user)
    followed_keys = {(follow.target_type, follow.target_id) for follow in follows}
    results = []
    for title in db.scalars(select(Title).where(Title.name.ilike(needle))):
        results.append(
            {
                "target_type": "title",
                "slug": title.slug,
                "name": title.name,
                "detail": title.season_label or title.kind,
                "kind": title.kind,
                "accent": title.accent,
                "followed": title.id in explicit,
            }
        )
    for person in db.scalars(select(Person).where(Person.name.ilike(needle))):
        results.append(
            {
                "target_type": "person",
                "slug": person.slug,
                "name": person.name,
                "detail": person.role,
                "kind": "person",
                "accent": person.accent,
                "followed": ("person", person.id) in followed_keys,
            }
        )
    for studio in db.scalars(select(Studio).where(Studio.name.ilike(needle))):
        results.append(
            {
                "target_type": "studio",
                "slug": studio.slug,
                "name": studio.name,
                "detail": "Studio",
                "kind": "studio",
                "accent": "#ffb199",
                "followed": ("studio", studio.id) in followed_keys,
            }
        )
    for franchise in db.scalars(select(Franchise).where(Franchise.name.ilike(needle))):
        results.append(
            {
                "target_type": "franchise",
                "slug": franchise.slug,
                "name": franchise.name,
                "detail": "Franchise",
                "kind": "franchise",
                "accent": "#9ec0e0",
                "followed": ("franchise", franchise.id) in followed_keys,
            }
        )
    return {"items": results[:24]}


def notifications(db: Session, user: User, now: datetime | None = None) -> dict:
    moment = now or app_now()
    explicit, _, _ = scopes(db, user)
    if not user.notify_enabled or not explicit:
        return {
            "enabled": user.notify_enabled,
            "lead_minutes": user.notify_lead_minutes,
            "items": [],
            "channels": _channels(),
        }
    titles = {title.id: title for title in db.scalars(select(Title).where(Title.id.in_(explicit)))}
    horizon = moment + timedelta(days=21)
    items = []
    for row in db.scalars(select(Release).where(Release.title_id.in_(explicit))):
        starts = aware(row.starts_at)
        if starts is None or starts < moment or starts > horizon:
            continue
        if not _release_allowed(user, row.kind):
            continue
        title = titles[row.title_id]
        fire_at = starts - timedelta(minutes=user.notify_lead_minutes)
        items.append(
            {
                "id": row.id,
                "slug": title.slug,
                "name": title.name,
                "label": row.label,
                "kind": row.kind,
                "starts_at": starts.isoformat(),
                "day": fmt_day(starts),
                "time": fmt_time(starts),
                "fire_at": fire_at.isoformat(),
                "fire_label": f"{fmt_day(fire_at)} · {fmt_time(fire_at)}",
                "lead_minutes": user.notify_lead_minutes,
            }
        )
    items.sort(key=lambda item: item["starts_at"])
    return {
        "enabled": True,
        "lead_minutes": user.notify_lead_minutes,
        "items": items,
        "channels": _channels(),
    }


def _channels() -> dict:
    return {
        "in_app": True,
        "email": False,
        "push": False,
        "note": "In-app reminders are scheduled. Email and Firebase push stay off until credentials are added.",
    }


def library(db: Session, user: User) -> dict:
    follows = _follows(db, user)
    buckets = {"title": [], "person": [], "studio": [], "franchise": []}
    for follow in follows:
        if follow.target_type == "title":
            row = db.get(Title, follow.target_id)
            if row:
                buckets["title"].append({"slug": row.slug, "name": row.name, "detail": row.season_label, "accent": row.accent})
        elif follow.target_type == "person":
            row = db.get(Person, follow.target_id)
            if row:
                buckets["person"].append({"slug": row.slug, "name": row.name, "detail": row.role, "accent": row.accent})
        elif follow.target_type == "studio":
            row = db.get(Studio, follow.target_id)
            if row:
                buckets["studio"].append({"slug": row.slug, "name": row.name, "detail": "Studio", "accent": "#ffb199"})
        elif follow.target_type == "franchise":
            row = db.get(Franchise, follow.target_id)
            if row:
                buckets["franchise"].append({"slug": row.slug, "name": row.name, "detail": "Franchise", "accent": "#9ec0e0"})
    for items in buckets.values():
        items.sort(key=lambda item: item["name"])
    return buckets


def entity(db: Session, user: User, kind: str, slug: str) -> dict | None:
    follows = _follows(db, user)
    followed_keys = {(follow.target_type, follow.target_id) for follow in follows}
    progress = _progress_map(db, user)
    if kind == "studio":
        row = db.scalar(select(Studio).where(Studio.slug == slug))
        if row is None:
            return None
        related = list(db.scalars(select(Title).where(Title.studio_id == row.id)))
        events = []
        if related:
            ids = [title.id for title in related]
            events = list(db.scalars(select(UpdateEvent).where(UpdateEvent.title_id.in_(ids))))
        profile = {"slug": row.slug, "name": row.name, "blurb": row.blurb, "accent": "#ffb199", "role": "Studio"}
        target_id = row.id
    elif kind == "person":
        row = db.scalar(select(Person).where(Person.slug == slug))
        if row is None:
            return None
        events = list(db.scalars(select(UpdateEvent).where(UpdateEvent.person_id == row.id)))
        related_ids = {event.title_id for event in events if event.title_id}
        related = list(db.scalars(select(Title).where(Title.id.in_(related_ids)))) if related_ids else []
        profile = {"slug": row.slug, "name": row.name, "blurb": row.blurb, "accent": row.accent, "role": row.role}
        target_id = row.id
    elif kind == "franchise":
        row = db.scalar(select(Franchise).where(Franchise.slug == slug))
        if row is None:
            return None
        related = list(db.scalars(select(Title).where(Title.franchise_id == row.id)))
        events = []
        if related:
            ids = [title.id for title in related]
            events = list(db.scalars(select(UpdateEvent).where(UpdateEvent.title_id.in_(ids))))
        profile = {"slug": row.slug, "name": row.name, "blurb": row.blurb, "accent": "#9ec0e0", "role": "Franchise"}
        target_id = row.id
    else:
        return None
    updates = []
    for event in sorted(events, key=lambda item: aware(item.published_at) or app_now(), reverse=True):
        updates.append(_visible_update(event, progress.get(event.title_id or -1, 0), user))
    updates = _attach_names(db, updates)
    return {
        "kind": kind,
        "profile": profile,
        "followed": (kind, target_id) in followed_keys,
        "titles": [
            {"slug": title.slug, "name": title.name, "season_label": title.season_label, "accent": title.accent, "kind": title.kind}
            for title in related
        ],
        "updates": updates,
    }


def serialize_user(user: User) -> dict:
    checked = aware(user.last_checked_at)
    return {
        "display_name": user.display_name,
        "region": user.region,
        "audio_mode": user.audio_mode,
        "audio_language": user.audio_language,
        "spoiler_protection": user.spoiler_protection,
        "notify_enabled": user.notify_enabled,
        "notify_lead_minutes": user.notify_lead_minutes,
        "last_checked_at": checked.isoformat() if checked else None,
    }


def resolve_target(db: Session, target_type: str, slug: str):
    if target_type == "title":
        return db.scalar(select(Title).where(Title.slug == slug))
    if target_type == "person":
        return db.scalar(select(Person).where(Person.slug == slug))
    if target_type == "studio":
        return db.scalar(select(Studio).where(Studio.slug == slug))
    if target_type == "franchise":
        return db.scalar(select(Franchise).where(Franchise.slug == slug))
    return None
