"""Load the demo catalog once, then run it through the same pipeline as live sources."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data.catalog import (
    DOCUMENTS,
    FOLLOWS,
    FRANCHISES,
    OFFERS,
    PEOPLE,
    PROGRESS,
    RELEASES,
    STUDIOS,
    TITLES,
    TRACKS,
)
from app.models import (
    AudioTrack,
    Follow,
    Franchise,
    Person,
    Prediction,
    Release,
    SourceDoc,
    StreamingOffer,
    Studio,
    Title,
    User,
    WatchProgress,
)
from app.services.pipeline import process_pending
from app.services.predictor import estimate


def seed_if_empty(db: Session) -> None:
    existing = db.scalar(select(func.count()).select_from(User))
    if existing:
        return

    user = User(
        display_name="Kel",
        region="US",
        audio_mode="all",
        audio_language="en",
        spoiler_protection=True,
        notify_enabled=True,
        notify_lead_minutes=30,
        last_checked_at=datetime(2026, 8, 10, 15, tzinfo=timezone.utc),
    )
    db.add(user)

    studios = {row["slug"]: Studio(slug=row["slug"], name=row["name"], blurb=row["blurb"]) for row in STUDIOS}
    franchises = {
        row["slug"]: Franchise(slug=row["slug"], name=row["name"], blurb=row["blurb"]) for row in FRANCHISES
    }
    people = {
        row["slug"]: Person(
            slug=row["slug"],
            name=row["name"],
            role=row["role"],
            blurb=row["blurb"],
            accent=row["accent"],
        )
        for row in PEOPLE
    }
    db.add_all([*studios.values(), *franchises.values(), *people.values()])
    db.flush()

    titles: dict[str, Title] = {}
    for row in TITLES:
        title = Title(
            slug=row["slug"],
            name=row["name"],
            kind=row["kind"],
            season_label=row["season_label"],
            status=row["status"],
            logline=row["logline"],
            genres=row["genres"],
            themes=row["themes"],
            accent=row["accent"],
            list_release=row["list_release"],
            schedule_note=None,
            studio_id=studios[row["studio"]].id if row["studio"] else None,
            franchise_id=franchises[row["franchise"]].id if row["franchise"] else None,
            official_specificity=row["official_specificity"],
            prediction_official=row["prediction_official"],
            prediction_subject=row["prediction_subject"],
            prediction_year=row["prediction_year"],
            announce_quarter=row["announce_quarter"],
            has_trailer=row["has_trailer"],
            prediction_is_movie=row["prediction_is_movie"],
        )
        titles[row["slug"]] = title
        db.add(title)
    db.flush()

    for slug, language, latest, nxt, when in TRACKS:
        db.add(
            AudioTrack(
                title_id=titles[slug].id,
                language=language,
                latest_episode=latest,
                next_episode=nxt,
                next_at=when,
            )
        )

    for slug, label, kind, starts, platform, note in RELEASES:
        db.add(
            Release(
                title_id=titles[slug].id,
                label=label,
                kind=kind,
                starts_at=starts,
                platform=platform,
                note=note,
            )
        )

    for slug, rows in OFFERS.items():
        for service, region, available, is_new, note in rows:
            db.add(
                StreamingOffer(
                    title_id=titles[slug].id,
                    service=service,
                    region=region,
                    available=available,
                    is_new=is_new,
                    note=note,
                )
            )

    for slug, episode in PROGRESS.items():
        db.add(WatchProgress(user_id=user.id, title_id=titles[slug].id, episode=episode))

    for target_type, slug in FOLLOWS:
        if target_type == "title":
            target_id = titles[slug].id
        elif target_type == "studio":
            target_id = studios[slug].id
        elif target_type == "person":
            target_id = people[slug].id
        else:
            target_id = franchises[slug].id
        db.add(Follow(user_id=user.id, target_type=target_type, target_id=target_id))

    for row in DOCUMENTS:
        if row.get("pending"):
            continue
        db.add(
            SourceDoc(
                title_id=titles[row["slug"]].id,
                person_id=people[row["person"]].id if row.get("person") else None,
                story_key=row["story"],
                publisher=row["publisher"],
                medium=row["medium"],
                headline=row["headline"],
                body=row["body"],
                published_at=row["published"],
                processed=False,
                rejected=False,
                reject_reason="",
                external_name="",
            )
        )
    db.flush()
    process_pending(db, commit=False)

    for title in titles.values():
        studio = db.get(Studio, title.studio_id) if title.studio_id else None
        if title.official_specificity >= 3 and not title.prediction_subject:
            continue
        if not title.prediction_subject and title.official_specificity >= 3:
            continue
        # Dated shows without a separate vague subject do not get a fake window.
        if title.official_specificity >= 3:
            result = estimate(
                studio=studio.name if studio else "Unknown",
                announce_quarter=title.announce_quarter,
                has_trailer=title.has_trailer,
                is_movie=title.prediction_is_movie,
                specificity=3,
                official_text=title.prediction_official,
                year_hint=title.prediction_year,
                subject=title.prediction_subject,
            )
        else:
            result = estimate(
                studio=studio.name if studio else "Unknown",
                announce_quarter=title.announce_quarter,
                has_trailer=title.has_trailer,
                is_movie=title.prediction_is_movie,
                specificity=title.official_specificity,
                official_text=title.prediction_official,
                year_hint=title.prediction_year,
                subject=title.prediction_subject or title.season_label,
            )
        db.add(
            Prediction(
                title_id=title.id,
                subject=result["subject"],
                official_text=result["official_text"],
                estimated_window=result["estimated_window"],
                confidence=result["confidence"],
                factors=result["factors"],
                disclaimer=result["disclaimer"],
                skipped=result["skipped"],
            )
        )

    for row in DOCUMENTS:
        if not row.get("pending"):
            continue
        db.add(
            SourceDoc(
                title_id=titles[row["slug"]].id,
                person_id=None,
                story_key=row["story"],
                publisher=row["publisher"],
                medium=row["medium"],
                headline=row["headline"],
                body=row["body"],
                published_at=row["published"],
                processed=False,
                rejected=False,
                reject_reason="",
                external_name="",
            )
        )
    db.commit()
