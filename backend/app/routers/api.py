"""HTTP API for the watchlist, feed, calendar, and models."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Follow, WatchProgress
from app.schemas import AskIn, ClassifyIn, FollowIn, MePatch, ProgressIn, ReadIn
from app.services.ask import ask
from app.services.classifier import score_text
from app.services.notify import mark_read
from app.services.collect import pull_public_sources
from app.services.extract import KICKERS, extract_facts, lead_type, ordered_facts
from app.services.pipeline import process_pending
from app.services.query import (
    app_now,
    calendar,
    catchup,
    entity,
    feed,
    get_user,
    library,
    notifications,
    recommendations,
    resolve_target,
    search,
    serialize_user,
    title_detail,
    watchlist,
)

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"ok": True, "service": "AniPulse"}


@router.get("/me")
def me(db: Session = Depends(get_db)) -> dict:
    return serialize_user(get_user(db))


@router.patch("/me")
def patch_me(body: MePatch, db: Session = Depends(get_db)) -> dict:
    user = get_user(db)
    data = body.model_dump(exclude_none=True)
    if data.get("audio_language") == "ja":
        data["audio_mode"] = "all"
    if data.get("email_address") and "@" not in data["email_address"]:
        raise HTTPException(status_code=400, detail="Enter a full email address")
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    return serialize_user(user)


@router.post("/me/checked")
def mark_checked(db: Session = Depends(get_db)) -> dict:
    user = get_user(db)
    user.last_checked_at = app_now()
    db.commit()
    return serialize_user(user)


@router.post("/me/rewind")
def rewind(db: Session = Depends(get_db)) -> dict:
    user = get_user(db)
    user.last_checked_at = app_now() - timedelta(days=60)
    db.commit()
    return serialize_user(user)


@router.get("/watchlist")
def get_watchlist(db: Session = Depends(get_db)) -> dict:
    return watchlist(db, get_user(db))


@router.get("/feed")
def get_feed(kind: str | None = None, db: Session = Depends(get_db)) -> dict:
    return feed(db, get_user(db), kind)


@router.get("/calendar")
def get_calendar(
    start: str,
    end: str,
    kinds: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    if kinds == "none":
        selected: list[str] | None = []
    elif kinds:
        selected = [item for item in kinds.split(",") if item]
    else:
        selected = None
    return calendar(db, get_user(db), start, end, selected)


@router.get("/titles/{slug}")
def get_title(slug: str, region: str | None = None, db: Session = Depends(get_db)) -> dict:
    payload = title_detail(db, get_user(db), slug, region)
    if payload is None:
        raise HTTPException(status_code=404, detail="Title not found")
    return payload


@router.put("/titles/{slug}/progress")
def put_progress(slug: str, body: ProgressIn, db: Session = Depends(get_db)) -> dict:
    user = get_user(db)
    from app.models import Title

    title = db.scalar(select(Title).where(Title.slug == slug))
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")
    row = db.scalar(
        select(WatchProgress).where(WatchProgress.user_id == user.id, WatchProgress.title_id == title.id)
    )
    if row is None:
        row = WatchProgress(user_id=user.id, title_id=title.id, episode=body.episode)
        db.add(row)
    else:
        row.episode = body.episode
    db.commit()
    return title_detail(db, user, slug, None)


@router.get("/catchup")
def get_catchup(since: str | None = None, slug: str | None = None, db: Session = Depends(get_db)) -> dict:
    return catchup(db, get_user(db), since, slug)


@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)) -> dict:
    return recommendations(db, get_user(db))


@router.get("/search")
def get_search(q: str = "", db: Session = Depends(get_db)) -> dict:
    return search(db, get_user(db), q)


@router.get("/notifications")
def get_notifications(now: str | None = None, db: Session = Depends(get_db)) -> dict:
    moment = datetime.fromisoformat(now) if now else None
    return notifications(db, get_user(db), moment)


@router.post("/notifications/read")
def read_notifications(body: ReadIn, db: Session = Depends(get_db)) -> dict:
    changed = mark_read(db, get_user(db), body.id)
    return {"ok": True, "updated": changed}


@router.post("/ask")
def post_ask(body: AskIn, now: str | None = None, db: Session = Depends(get_db)) -> dict:
    moment = datetime.fromisoformat(now) if now else None
    return ask(db, get_user(db), body.question, moment)


@router.get("/library")
def get_library(db: Session = Depends(get_db)) -> dict:
    return library(db, get_user(db))


@router.get("/entities/{kind}/{slug}")
def get_entity(kind: str, slug: str, db: Session = Depends(get_db)) -> dict:
    payload = entity(db, get_user(db), kind, slug)
    if payload is None:
        raise HTTPException(status_code=404, detail="Not found")
    return payload


@router.post("/follows")
def post_follow(body: FollowIn, db: Session = Depends(get_db)) -> dict:
    user = get_user(db)
    target = resolve_target(db, body.target_type, body.slug)
    if target is None:
        raise HTTPException(status_code=404, detail="Nothing matches that follow")
    existing = db.scalar(
        select(Follow).where(
            Follow.user_id == user.id,
            Follow.target_type == body.target_type,
            Follow.target_id == target.id,
        )
    )
    if existing is None:
        db.add(Follow(user_id=user.id, target_type=body.target_type, target_id=target.id))
        if body.target_type == "title":
            progress = db.scalar(
                select(WatchProgress).where(WatchProgress.user_id == user.id, WatchProgress.title_id == target.id)
            )
            if progress is None:
                db.add(WatchProgress(user_id=user.id, title_id=target.id, episode=0))
        db.commit()
    return {"ok": True, "followed": True}


@router.delete("/follows/{target_type}/{slug}")
def delete_follow(target_type: str, slug: str, db: Session = Depends(get_db)) -> dict:
    user = get_user(db)
    target = resolve_target(db, target_type, slug)
    if target is None:
        raise HTTPException(status_code=404, detail="Nothing matches that follow")
    row = db.scalar(
        select(Follow).where(
            Follow.user_id == user.id,
            Follow.target_type == target_type,
            Follow.target_id == target.id,
        )
    )
    if row is not None:
        db.delete(row)
        db.commit()
    return {"ok": True, "followed": False}


@router.post("/pulse/classify")
def classify(body: ClassifyIn) -> dict:
    facts = ordered_facts(extract_facts(body.text))
    scored = score_text(body.text)
    meaningful = bool(facts) and scored["noise_probability"] < 0.92
    primary = lead_type(facts) if facts else scored["predicted_type"]
    return {
        "signal_probability": scored["signal_probability"],
        "noise_probability": scored["noise_probability"],
        "predicted_type": scored["predicted_type"],
        "type_probability": scored["type_probability"],
        "meaningful": meaningful,
        "kicker": KICKERS.get(primary, "Update detected.") if meaningful else "Left out of the feed.",
        "changes": [fact["text"] for fact in facts] if meaningful else [],
        "spoiler": any(fact["spoiler"] for fact in facts),
    }


@router.post("/pulse/scan")
def scan(db: Session = Depends(get_db)) -> dict:
    return process_pending(db)


@router.post("/pulse/pull")
def pull(db: Session = Depends(get_db)) -> dict:
    incoming = pull_public_sources(db)
    processed = process_pending(db)
    return {**incoming, **processed}
