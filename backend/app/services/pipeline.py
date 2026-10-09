"""Turn raw source documents into one update per story."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SourceDoc, Title, UpdateEvent
from app.services.classifier import confidence_label, score_text
from app.services.extract import KICKERS, extract_facts, lead_type, ordered_facts

MEDIUMS = {
    "official_site": "Official site",
    "streaming": "Streaming platform",
    "studio": "Studio announcement",
    "news": "News article",
    "social": "Social media",
    "episode_database": "Episode database",
}


def medium_label(medium: str) -> str:
    return MEDIUMS.get(medium, medium.replace("_", " ").title())


def _headline(title_name: str, season_label: str, primary: str, facts: list[dict]) -> str:
    if primary == "streaming" and len(facts) == 1 and facts[0]["text"].startswith("Now available on "):
        platform = facts[0]["text"].replace("Now available on ", "")
        return f"{title_name} is now available on {platform}"
    if primary in {"premiere", "production", "trailer", "visual"} and season_label:
        return f"{title_name} {season_label}".strip()
    return title_name


def _story_key(doc: SourceDoc) -> str:
    if doc.story_key:
        return doc.story_key
    day = doc.published_at.date().toordinal() // 10
    return f"loose-{doc.title_id or doc.external_name}-{day}"


def process_pending(db: Session, commit: bool = True) -> dict:
    docs = list(db.scalars(select(SourceDoc).where(SourceDoc.processed.is_(False))))
    groups: dict[str, list[SourceDoc]] = defaultdict(list)
    scored: dict[int, dict] = {}
    extracted: dict[int, list[dict]] = {}
    for doc in docs:
        groups[_story_key(doc)].append(doc)
        extracted[doc.id] = extract_facts(doc.body)
        scored[doc.id] = score_text(doc.body)

    created: list[dict] = []
    discarded: list[dict] = []

    for key, group in groups.items():
        contributors: list[SourceDoc] = []
        facts: list[dict] = []
        seen: set[str] = set()
        for doc in group:
            doc_facts = extracted[doc.id]
            noise = scored[doc.id]["noise_probability"]
            if doc_facts and noise < 0.92:
                contributors.append(doc)
                for fact in doc_facts:
                    marker = fact["text"].lower()
                    if marker not in seen:
                        seen.add(marker)
                        facts.append(fact)
        if not facts:
            for doc in group:
                doc.processed = True
                doc.rejected = True
                doc.reject_reason = "Not a meaningful update"
            discarded.append(
                {
                    "story_key": key,
                    "headline": group[0].headline,
                    "reason": "No real schedule, release, or availability change in this item.",
                }
            )
            continue

        facts = ordered_facts(facts)
        primary = lead_type(facts)
        title = db.get(Title, contributors[0].title_id) if contributors[0].title_id else None
        title_name = title.name if title else (contributors[0].external_name or contributors[0].headline)
        season = title.season_label if title else ""
        signal_values = [scored[doc.id]["signal_probability"] for doc in contributors]
        confidence = sum(signal_values) / len(signal_values)
        publishers = []
        source_rows = []
        seen_publishers: set[str] = set()
        for doc in contributors:
            if doc.publisher not in seen_publishers:
                seen_publishers.add(doc.publisher)
                publishers.append(doc.publisher)
                source_rows.append({"publisher": doc.publisher, "medium": medium_label(doc.medium)})
        person_id = next((doc.person_id for doc in contributors if doc.person_id), None)
        published_at = max(doc.published_at for doc in contributors)
        event = UpdateEvent(
            title_id=title.id if title else None,
            person_id=person_id,
            story_key=key,
            headline=_headline(title_name, season, primary, facts),
            kicker=KICKERS.get(primary, "Update detected."),
            primary_type=primary,
            changes=facts,
            confidence=round(confidence, 4),
            confidence_label=confidence_label(confidence, len(publishers)),
            sources_verified=len(publishers),
            sources=source_rows,
            published_at=published_at,
            external_name="" if title else title_name,
        )
        db.add(event)
        db.flush()
        for doc in group:
            doc.processed = True
            doc.rejected = doc not in contributors
            doc.reject_reason = "" if doc in contributors else "Grouped source did not add a fact"
            doc.update_id = event.id if doc in contributors else None
        if title and any(fact["type"] == "schedule" for fact in facts):
            title.schedule_note = "Schedule updated"
        created.append(
            {
                "id": event.id,
                "headline": event.headline,
                "kicker": event.kicker,
                "changes": [fact["text"] for fact in facts],
                "confidence_label": event.confidence_label,
                "sources_verified": event.sources_verified,
            }
        )

    if commit:
        db.commit()
    else:
        db.flush()
    return {"updates": created, "discarded": discarded}
