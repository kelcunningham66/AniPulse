"""Pull structured facts out of a source document.

The classifier decides whether a document is signal. This module decides
what actually changed, using the wording studios and outlets use.
"""

from __future__ import annotations

import re

MONTH = (
    r"(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)"
)
PLATFORMS = ["Crunchyroll", "Netflix", "Hulu", "HIDIVE", "Disney+", "Amazon"]


def _month(token: str) -> str:
    return token.strip().title()


def _day(token: str) -> str:
    return str(int(token))


def extract_facts(text: str) -> list[dict]:
    raw = " ".join(text.split())
    low = raw.lower()
    facts: list[dict] = []

    def add(kind: str, label: str, spoiler: bool = False) -> None:
        facts.append({"type": kind, "text": label, "spoiler": spoiler})

    is_schedule = bool(
        re.search(r"delayed|schedule was updated|schedule updated|air date changed|skip a week", low)
    )

    if "trailer" in low:
        if "movie" in low:
            add("trailer", "New movie trailer released")
        else:
            add("trailer", "New trailer released")

    if "key visual" in low or "key art" in low:
        add("visual", "New key visual revealed")

    season_gap = re.search(r"no season (\d+) announcement", low)
    if season_gap:
        add("production", f"No Season {season_gap.group(1)} announcement")

    window = re.search(rf"{MONTH}\s+(20\d\d)\s+premiere window", low)
    if window:
        add("premiere", f"{_month(window.group(1))} {window.group(2)} premiere window announced")

    if is_schedule:
        if "skip a week" in low:
            episode = re.search(r"episode\s+(\d+)", low)
            if episode:
                add("schedule", f"Schedule updated — episode {episode.group(1)} skipped a week")
            else:
                add("schedule", "Schedule updated")
        else:
            episode = re.search(r"episode\s+(\d+)", low)
            dest = re.search(rf"\bto\s+{MONTH}\s+(\d{{1,2}})", low)
            if episode and dest:
                add(
                    "schedule",
                    f"Episode {episode.group(1)} moved to {_month(dest.group(1))} {_day(dest.group(2))}",
                )
            else:
                add("schedule", "Schedule updated")

    if not is_schedule:
        if "premiere set for" in low or "release date announced" in low or re.search(r"\bopens\b", low):
            dated = re.search(rf"{MONTH}\s+(\d{{1,2}})(?:,\s*|\s+)(20\d\d)", low)
            if dated:
                label = "premiere date announced" if "premiere set for" in low else "release date announced"
                add("premiere", f"{_month(dated.group(1))} {_day(dated.group(2))} {label}")

        episode_drop = re.search(rf"episode\s+(\d+)\s+releases\s+{MONTH}\s+(\d{{1,2}})", low)
        if episode_drop:
            add(
                "premiere",
                f"Episode {episode_drop.group(1)} releases {_month(episode_drop.group(2))} {_day(episode_drop.group(3))}",
            )

        chapter = re.search(rf"chapter\s+(\d+)\s+releases\s+{MONTH}\s+(\d{{1,2}})", low)
        if chapter:
            add(
                "manga",
                f"Chapter {chapter.group(1)} releases {_month(chapter.group(2))} {_day(chapter.group(3))}",
            )

        named = re.search(r"announced for (20\d\d)", low)
        if named and "not been named" in low:
            add("production", f"Announced for {named.group(1)} without a season")

    if "english dub" in low or "spanish dub" in low:
        language = "Spanish" if "spanish dub" in low else "English"
        episode = re.search(r"episode\s+(\d+)", low)
        if episode:
            add("dub", f"{language} dub episode {episode.group(1)} on the schedule")
        else:
            add("dub", f"{language} dub update")

    if "returns for" in low:
        add("cast", "Cast confirmed for the upcoming dub")

    if "streaming has not been announced" in low or "streaming not announced" in low:
        add("streaming", "Streaming not announced")
    else:
        for platform in PLATFORMS:
            token = platform.lower()
            if token not in low:
                continue
            if "now available" in low or ("added" in low and ("catalog" in low or "available" in low)):
                add("streaming", f"Now available on {platform}")
            elif any(key in low for key in ("will stream", "confirmed", "to stream", "streaming", "premiere", "opens")):
                add("streaming", f"{platform} confirmed streaming")

    if re.search(r"\b(death|dies|killed)\b", low):
        add("coverage", raw[:280], spoiler=True)

    deduped: list[dict] = []
    seen: set[str] = set()
    for fact in facts:
        key = fact["text"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fact)
    return deduped


DISPLAY_ORDER = [
    "trailer",
    "visual",
    "premiere",
    "manga",
    "streaming",
    "schedule",
    "dub",
    "cast",
    "production",
    "coverage",
]

LEAD_PRIORITY = [
    "schedule",
    "premiere",
    "manga",
    "production",
    "trailer",
    "dub",
    "streaming",
    "visual",
    "cast",
    "coverage",
]

KICKERS = {
    "schedule": "Schedule change detected.",
    "premiere": "Official production update detected.",
    "manga": "New chapter detected.",
    "production": "Official production update detected.",
    "trailer": "New trailer detected.",
    "visual": "New artwork detected.",
    "streaming": "Streaming availability changed.",
    "dub": "Dub release detected.",
    "cast": "Cast update detected.",
    "coverage": "Coverage may contain story details.",
}


def lead_type(facts: list[dict]) -> str:
    kinds = {fact["type"] for fact in facts}
    for kind in LEAD_PRIORITY:
        if kind in kinds:
            return kind
    return "production"


def ordered_facts(facts: list[dict]) -> list[dict]:
    rank = {kind: index for index, kind in enumerate(DISPLAY_ORDER)}
    return sorted(facts, key=lambda fact: rank.get(fact["type"], 99))
