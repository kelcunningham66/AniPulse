"""Hide story details that sit past the viewer's progress."""

from __future__ import annotations

import re

_LEAK = re.compile(r"\b(death|dies|died|killed|murder|identity|betray)\b", re.IGNORECASE)
_EPISODE = re.compile(r"episode\s+(\d+)", re.IGNORECASE)


def referenced_episodes(text: str) -> list[int]:
    return [int(match) for match in _EPISODE.findall(text)]


def is_past_progress(text: str, progress: int, marked: bool = False) -> bool:
    episodes = referenced_episodes(text)
    if episodes:
        return any(episode > progress for episode in episodes)
    if marked or _LEAK.search(text):
        return True
    return False


def guard_changes(changes: list[dict], progress: int, enabled: bool) -> tuple[list[str], int]:
    if not enabled:
        return [item["text"] for item in changes], 0
    visible: list[str] = []
    hidden = 0
    for item in changes:
        if is_past_progress(item["text"], progress, bool(item.get("spoiler"))):
            hidden += 1
            continue
        visible.append(item["text"])
    return visible, hidden


def hidden_note(hidden: int, progress: int) -> str | None:
    if hidden <= 0:
        return None
    episode = "episode" if progress == 1 else "episodes"
    if progress <= 0:
        return "Story details are hidden while spoiler protection is on."
    return f"Story details past {episode} you've reached (through episode {progress}) are hidden."
