"""Answer watchlist questions from saved updates, then say what is missing.

Nothing here is invented from a model. A question is matched to followed
titles, the saved releases and verified updates are read first, and the
reply cites those records. A release date that was never announced is
called out instead of filled in.
"""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Prediction, Release, StreamingOffer, Title, UpdateEvent, User
from app.services.spoiler import guard_changes
from app.services.timeutil import fmt_day, fmt_time

_RENEWAL_YES = re.compile(
    r"renew|another season|new season|premiere window|season premiere|season \d+",
    re.IGNORECASE,
)
_RENEWAL_NO = re.compile(
    r"no season|has not been named|not been announced|not announced|no season \d+",
    re.IGNORECASE,
)
_DATE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b",
    re.IGNORECASE,
)


def ask(db: Session, user: User, question: str, now: datetime | None = None) -> dict:
    from app.services.query import app_now, aware, scopes

    moment = now or app_now()
    text = " ".join(question.split())
    low = text.lower()
    explicit, expanded, _people = scopes(db, user)
    del explicit
    titles = list(db.scalars(select(Title).where(Title.id.in_(expanded)))) if expanded else []
    mentioned = [title for title in titles if title.name.lower() in low]
    if not mentioned:
        mentioned = [title for title in _all_titles(db) if title.name.lower() in low]
    scope = mentioned or titles
    events = _events(db, {title.id for title in scope})
    intent = _intent(low)
    if intent == "missed":
        payload = _missed(db, user, titles, events, moment)
    elif intent == "weekend":
        payload = _weekend(db, user, titles, moment)
    elif intent == "dub":
        payload = _dubs(db, user, scope, events, low, moment)
    elif intent == "renewal":
        payload = _renewal(scope, events, user)
    elif intent == "streaming":
        payload = _streaming(db, user, scope, events)
    elif intent == "date":
        payload = _dates(db, user, scope, events, moment)
    else:
        payload = _general(scope, events, user)
    payload["question"] = text
    return payload


def _intent(low: str) -> str:
    if any(word in low for word in ("missed", "past month", "last month", "catch up", "catch-up")):
        return "missed"
    if any(word in low for word in ("weekend", "this week", "dropping", "coming out", "on tonight")):
        return "weekend"
    if "dub" in low:
        return "dub"
    if any(word in low for word in ("renew", "another season", "new season")):
        return "renewal"
    if any(word in low for word in ("stream", "where can i watch", "netflix", "crunchyroll", "hulu")):
        return "streaming"
    if any(word in low for word in ("when", "release date", "premiere", "what day", "air")):
        return "date"
    return "general"


def _all_titles(db: Session) -> list[Title]:
    return list(db.scalars(select(Title)))


def _events(db: Session, title_ids: set[int]) -> list[UpdateEvent]:
    if not title_ids:
        return []
    return list(db.scalars(select(UpdateEvent).where(UpdateEvent.title_id.in_(title_ids))))


def _blob(event: UpdateEvent) -> str:
    parts = [event.headline, event.kicker]
    for change in event.changes or []:
        parts.append(change.get("text", ""))
    return " ".join(parts)


def _visible(event: UpdateEvent, user: User, progress: dict[int, int]) -> list[str]:
    visible, _hidden = guard_changes(event.changes or [], progress.get(event.title_id or -1, 0), user.spoiler_protection)
    return visible


def _progress(db: Session, user: User) -> dict[int, int]:
    from app.models import WatchProgress

    return {
        row.title_id: row.episode
        for row in db.scalars(select(WatchProgress).where(WatchProgress.user_id == user.id))
    }


def _cite(event: UpdateEvent, title: Title | None) -> list[dict]:
    sources = event.sources or [{"publisher": "Saved update", "headline": event.headline}]
    return [
        {
            "publisher": source.get("publisher") or "Saved update",
            "headline": event.headline,
            "published_at": event.published_at.isoformat() if event.published_at else None,
            "slug": title.slug if title else None,
            "name": title.name if title else event.headline,
        }
        for source in sources
    ]


def _reply(question: str, answer: str, citations: list[dict], unannounced: bool) -> dict:
    seen: set[tuple[str, str, str | None]] = set()
    unique = []
    for citation in citations:
        key = (citation.get("publisher", ""), citation.get("headline", ""), citation.get("slug"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    return {
        "question": question,
        "answer": answer,
        "unannounced": unannounced,
        "citations": unique,
    }


def _renewal(titles: list[Title], events: list[UpdateEvent], user: User) -> dict:
    if not titles:
        return _reply("", "That show is not on your watchlist, so there is nothing saved to check.", [], True)
    lines = []
    citations: list[dict] = []
    unannounced = False
    progress = {}
    for title in titles:
        matched = [event for event in events if event.title_id == title.id]
        yes = []
        no = []
        for event in matched:
            blob = _blob(event)
            if _RENEWAL_NO.search(blob):
                no.append(event)
            elif _RENEWAL_YES.search(blob) and "no season" not in blob.lower():
                yes.append(event)
        if yes:
            facts = []
            for event in yes:
                facts.extend(_visible(event, user, progress) or [event.headline])
                citations.extend(_cite(event, title))
            lines.append(f"{title.name}: {facts[0]}")
        elif no:
            unannounced = True
            lines.append(f"No saved update says {title.name} was renewed. A saved note says a new season has not been announced.")
            for event in no:
                citations.extend(_cite(event, title))
        else:
            unannounced = True
            lines.append(f"No saved update says {title.name} was renewed. A renewal has not been announced.")
    return _reply("", " ".join(lines), citations, unannounced)


def _weekend(db: Session, user: User, titles: list[Title], moment: datetime) -> dict:
    from app.services.query import aware

    friday, sunday = _weekend_bounds(moment)
    by_id = {title.id: title for title in titles}
    if not by_id:
        return _reply("", "Your watchlist is empty, so nothing is dropping.", [], False)
    rows = []
    citations = []
    for release in db.scalars(select(Release).where(Release.title_id.in_(by_id))):
        starts = aware(release.starts_at)
        if starts is None or starts < friday or starts > sunday:
            continue
        if user.audio_mode == "dub" and not release.kind.startswith("dub"):
            continue
        title = by_id[release.title_id]
        rows.append(f"{title.name} {release.label} on {fmt_day(starts)} at {fmt_time(starts)}")
        citations.append(
            {
                "publisher": release.platform or "Schedule",
                "headline": f"{title.name} {release.label}",
                "published_at": starts.isoformat(),
                "slug": title.slug,
                "name": title.name,
            }
        )
    if not rows:
        return _reply("", "Nothing on your watchlist is dated for this weekend.", citations, False)
    return _reply("", "This weekend: " + "; ".join(rows) + ".", citations, False)


def _dubs(db: Session, user: User, titles: list[Title], events: list[UpdateEvent], low: str, moment: datetime) -> dict:
    from app.services.query import aware

    language = "es" if "spanish" in low else "en"
    language_name = "Spanish" if language == "es" else "English"
    by_id = {title.id: title for title in titles}
    lines = []
    citations: list[dict] = []
    seen: set[int] = set()
    for event in events:
        blob = _blob(event).lower()
        if language_name.lower() not in blob and f"{language_name.lower()} dub" not in blob:
            if "dub" not in blob:
                continue
            if language == "en" and "spanish" in blob:
                continue
        title = by_id.get(event.title_id or -1)
        if title is None or title.id in seen:
            continue
        facts = _visible(event, user, {})
        if not facts:
            continue
        seen.add(title.id)
        lines.append(f"{title.name}: {facts[0]}")
        citations.extend(_cite(event, title))
    horizon = moment + timedelta(days=21)
    recent = moment - timedelta(days=21)
    for release in db.scalars(select(Release).where(Release.title_id.in_(by_id))):
        if release.kind != f"dub_{language}":
            continue
        starts = aware(release.starts_at)
        title = by_id.get(release.title_id)
        if title is None or starts is None or starts < recent or starts > horizon or title.id in seen:
            continue
        seen.add(title.id)
        lines.append(f"{title.name}: {release.label} on {fmt_day(starts)}")
        citations.append(
            {
                "publisher": release.platform or "Schedule",
                "headline": f"{language_name} dub {release.label}",
                "published_at": starts.isoformat(),
                "slug": title.slug,
                "name": title.name,
            }
        )
    if not lines:
        return _reply(
            "",
            f"None of these shows have a saved {language_name} dub update.",
            [],
            True,
        )
    return _reply("", f"{language_name} dubs: " + "; ".join(lines) + ".", citations, False)


def _streaming(db: Session, user: User, titles: list[Title], events: list[UpdateEvent]) -> dict:
    lines = []
    citations: list[dict] = []
    unannounced = False
    for title in titles:
        offers = list(
            db.scalars(
                select(StreamingOffer).where(
                    StreamingOffer.title_id == title.id,
                    StreamingOffer.region == user.region,
                    StreamingOffer.available.is_(True),
                )
            )
        )
        related = [event for event in events if event.title_id == title.id]
        denied = [event for event in related if "not been announced" in _blob(event).lower() or "not announced" in _blob(event).lower()]
        if offers:
            names = ", ".join(offer.service for offer in offers)
            extra = ""
            fresh = [offer.service for offer in offers if offer.is_new]
            if fresh:
                extra = f" Newly added: {', '.join(fresh)}."
            lines.append(f"{title.name} is on {names} in {user.region}.{extra}")
            for offer in offers:
                if offer.is_new:
                    citations.append(
                        {
                            "publisher": offer.service,
                            "headline": offer.note or "Newly added",
                            "published_at": None,
                            "slug": title.slug,
                            "name": title.name,
                        }
                    )
        elif denied:
            unannounced = True
            lines.append(f"Streaming for {title.name} has not been announced.")
            for event in denied:
                citations.extend(_cite(event, title))
        else:
            unannounced = True
            lines.append(f"No saved streaming offer for {title.name} in {user.region}.")
        for event in related:
            if event.primary_type == "streaming" or "streaming" in _blob(event).lower():
                citations.extend(_cite(event, title))
    if not lines:
        return _reply("", "Nothing on your watchlist has a saved streaming offer.", [], True)
    return _reply("", " ".join(lines), citations, unannounced)


def _dates(db: Session, user: User, titles: list[Title], events: list[UpdateEvent], moment: datetime) -> dict:
    from app.services.query import aware

    if not titles:
        return _reply("", "Name a show on your watchlist and I can check the saved dates.", [], True)
    lines = []
    citations: list[dict] = []
    unannounced = False
    predictions = {
        row.title_id: row
        for row in db.scalars(select(Prediction).where(Prediction.title_id.in_([title.id for title in titles])))
    }
    for title in titles:
        related = [event for event in events if event.title_id == title.id]
        dated = [
            event
            for event in related
            if _DATE.search(_blob(event)) and "not announced" not in _blob(event).lower()
        ]
        upcoming = []
        for release in db.scalars(select(Release).where(Release.title_id == title.id)):
            starts = aware(release.starts_at)
            if starts and starts >= moment - timedelta(days=1):
                upcoming.append((starts, release))
        upcoming.sort(key=lambda item: item[0])
        if title.official_specificity >= 3 and _DATE.search(title.prediction_official or ""):
            lines.append(f"{title.name}: the saved official date is {title.prediction_official}.")
        elif dated:
            fact = _visible(dated[0], user, {})
            lines.append(f"{title.name}: {fact[0] if fact else dated[0].headline}.")
            citations.extend(_cite(dated[0], title))
        else:
            unannounced = True
            official = title.prediction_official or "nothing dated"
            lines.append(
                f"{title.name}: a specific release date has not been announced. The saved official wording is \"{official}\"."
            )
            estimate = predictions.get(title.id)
            if estimate and estimate.estimated_window and not estimate.skipped:
                lines.append(
                    f"A separate estimate says {estimate.estimated_window}. That number is not an official date."
                )
            for event in related:
                blob = _blob(event).lower()
                if any(word in blob for word in ("window", "premiere", "not announced", "not been announced")):
                    citations.extend(_cite(event, title))
        if upcoming:
            starts, release = upcoming[0]
            lines.append(f"Next dated release: {release.label} on {fmt_day(starts)}.")
            citations.append(
                {
                    "publisher": release.platform or "Schedule",
                    "headline": f"{title.name} {release.label}",
                    "published_at": starts.isoformat(),
                    "slug": title.slug,
                    "name": title.name,
                }
            )
        for event in related:
            if "no season" in _blob(event).lower():
                citations.extend(_cite(event, title))
    return _reply("", " ".join(lines), citations, unannounced)


def _missed(db: Session, user: User, titles: list[Title], events: list[UpdateEvent], moment: datetime) -> dict:
    from app.services.query import aware

    start = moment - timedelta(days=30)
    by_id = {title.id: title for title in titles}
    progress = _progress(db, user)
    lines = []
    citations: list[dict] = []
    for event in sorted(events, key=lambda item: aware(item.published_at) or moment, reverse=True):
        published = aware(event.published_at)
        if published is None or published < start:
            continue
        title = by_id.get(event.title_id or -1)
        if title is None:
            continue
        facts = _visible(event, user, progress)
        if facts:
            lines.append(f"{title.name}: {facts[0]}")
        elif user.spoiler_protection:
            lines.append(f"{title.name}: a saved update is hidden because it is past your progress.")
        citations.extend(_cite(event, title))
    if not lines:
        return _reply("", "Nothing verified was saved for your watchlist in the past month.", [], False)
    return _reply("", "In the past month: " + "; ".join(lines) + ".", citations, False)


def _general(titles: list[Title], events: list[UpdateEvent], user: User) -> dict:
    if not titles:
        return _reply("", "I can only answer from shows on your watchlist, and none of them matched.", [], True)
    lines = []
    citations: list[dict] = []
    for title in titles[:4]:
        related = [event for event in events if event.title_id == title.id]
        if not related:
            lines.append(f"No verified update is saved for {title.name}.")
            continue
        latest = max(related, key=lambda event: event.published_at)
        facts = _visible(latest, user, {})
        lines.append(f"{title.name}: {facts[0] if facts else latest.headline}.")
        citations.extend(_cite(latest, title))
    return _reply("", " ".join(lines), citations, False)


def _weekend_bounds(moment: datetime) -> tuple[datetime, datetime]:
    weekday = moment.weekday()
    if weekday <= 4:
        friday = moment.date() + timedelta(days=4 - weekday)
    else:
        friday = moment.date() - timedelta(days=weekday - 4)
    start = datetime.combine(friday, time.min, tzinfo=moment.tzinfo)
    end = datetime.combine(friday + timedelta(days=2), time.max, tzinfo=moment.tzinfo)
    return start, end
