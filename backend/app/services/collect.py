"""Optional pulls from public anime feeds.

Failures stay in the response. The curated catalog does not depend on them.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SourceDoc, Title

ANN_RSS = "https://www.animenewsnetwork.com/news/rss.xml"
ANILIST_URL = "https://graphql.anilist.co"
ANILIST_QUERY = """
query ($page: Int) {
  Page(page: $page, perPage: 8) {
    media(type: ANIME, status: RELEASING, sort: TRENDING_DESC) {
      id
      title { romaji english }
      nextAiringEpisode { airingAt episode }
      siteUrl
    }
  }
}
"""


def _match_title(db: Session, text: str) -> Title | None:
    lowered = text.lower()
    titles = list(db.scalars(select(Title)))
    # Longer names first so "Chainsaw Man" wins over a shorter fragment.
    titles.sort(key=lambda title: len(title.name), reverse=True)
    for title in titles:
        if title.name.lower() in lowered:
            return title
    return None


def _store(db: Session, *, story: str, publisher: str, medium: str, headline: str, body: str, external: str) -> bool:
    exists = db.scalar(select(SourceDoc).where(SourceDoc.story_key == story))
    if exists:
        return False
    matched = _match_title(db, f"{headline} {body}")
    db.add(
        SourceDoc(
            title_id=matched.id if matched else None,
            person_id=None,
            story_key=story,
            publisher=publisher,
            medium=medium,
            headline=headline[:240],
            body=body[:2000],
            published_at=datetime.now(timezone.utc),
            processed=False,
            rejected=False,
            reject_reason="",
            external_name="" if matched else external[:160],
        )
    )
    return True


def pull_public_sources(db: Session) -> dict:
    fetched = 0
    errors: list[str] = []
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            response = client.get(ANN_RSS, headers={"User-Agent": "AniPulseDemo/1.0"})
            response.raise_for_status()
            root = ET.fromstring(response.text)
            items = root.findall("./channel/item")[:8]
            for item in items:
                title = (item.findtext("title") or "").strip()
                description = (item.findtext("description") or "").strip()
                link = (item.findtext("link") or title)
                if not title:
                    continue
                story = "ann-" + hashlib.sha1(link.encode()).hexdigest()[:12]
                if _store(
                    db,
                    story=story,
                    publisher="Anime News Network",
                    medium="news",
                    headline=title,
                    body=f"{title}. {description}",
                    external=title,
                ):
                    fetched += 1
    except Exception as exc:  # noqa: BLE001 — surface the failure to the UI
        errors.append(f"News feed unavailable: {exc.__class__.__name__}")

    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.post(ANILIST_URL, json={"query": ANILIST_QUERY, "variables": {"page": 1}})
            response.raise_for_status()
            media = response.json()["data"]["Page"]["media"]
            for row in media:
                names = row.get("title") or {}
                name = names.get("english") or names.get("romaji") or "Untitled"
                nxt = row.get("nextAiringEpisode") or {}
                episode = nxt.get("episode")
                airing = nxt.get("airingAt")
                if not episode or not airing:
                    continue
                when = datetime.fromtimestamp(airing, tz=timezone.utc)
                months = [
                    "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December",
                ]
                body = (
                    f"{name} episode {episode} releases "
                    f"{months[when.month - 1]} {when.day}, {when.year} "
                    "according to the episode database."
                )
                story = f"anilist-{row.get('id')}-{episode}"
                if _store(
                    db,
                    story=story,
                    publisher="AniList",
                    medium="episode_database",
                    headline=f"{name} episode {episode}",
                    body=body,
                    external=name,
                ):
                    fetched += 1
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Episode database unavailable: {exc.__class__.__name__}")

    db.flush()
    return {"fetched": fetched, "errors": errors}
