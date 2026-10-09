"""Content match against the shows someone already follows."""

from __future__ import annotations

import math

THEMES = [
    "action",
    "dark_fantasy",
    "supernatural",
    "adventure",
    "comedy",
    "romance",
    "mystery",
    "horror",
    "sports",
    "slice_of_life",
    "sci_fi",
    "historical",
    "thriller",
    "shonen",
    "seinen",
    "isekai",
    "military",
    "psychological",
    "fantasy",
    "drama",
]

LABELS = {
    "action": "action",
    "dark_fantasy": "dark fantasy",
    "supernatural": "supernatural",
    "adventure": "adventure",
    "comedy": "comedy",
    "romance": "romance",
    "mystery": "mystery",
    "horror": "horror",
    "sports": "sports",
    "slice_of_life": "slice-of-life",
    "sci_fi": "science fiction",
    "historical": "historical",
    "thriller": "thriller",
    "shonen": "shonen",
    "seinen": "seinen",
    "isekai": "isekai",
    "military": "military",
    "psychological": "psychological",
    "fantasy": "fantasy",
    "drama": "drama",
}


def vector(themes: list[str]) -> list[float]:
    owned = set(themes)
    return [1.0 if theme in owned else 0.0 for theme in THEMES]


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def centroid(theme_lists: list[list[str]]) -> list[float]:
    if not theme_lists:
        return [0.0 for _ in THEMES]
    rows = [vector(themes) for themes in theme_lists]
    width = len(THEMES)
    return [sum(row[index] for row in rows) / len(rows) for index in range(width)]


def _shared_phrase(candidate: list[str], followed: list[list[str]], profile: list[float]) -> str:
    if not followed:
        return "shows on your list"
    counts = {theme: 0 for theme in THEMES}
    for themes in followed:
        for theme in themes:
            if theme in counts:
                counts[theme] += 1
    total = len(followed)

    def weight(theme: str) -> float:
        return profile[THEMES.index(theme)]

    universal = [
        theme
        for theme in candidate
        if counts.get(theme, 0) / total > 0.75 and weight(theme) > 0
    ]
    distinctive = [
        theme
        for theme in candidate
        if 0 < counts.get(theme, 0) / total <= 0.75 and weight(theme) > 0
    ]
    universal.sort(key=weight, reverse=True)
    distinctive.sort(key=weight, reverse=True)
    if universal and distinctive:
        return f"{LABELS[universal[0]]}-heavy {LABELS[distinctive[0]]} anime"
    if distinctive:
        return f"{LABELS[distinctive[0]]} anime"
    if universal:
        return f"{LABELS[universal[0]]} anime"
    return "shows on your list"


def explain(
    candidate_themes: list[str],
    followed: list[tuple[str, list[str]]],
    profile: list[float],
    sibling: str | None,
) -> str:
    phrase = _shared_phrase(candidate_themes, [themes for _, themes in followed], profile)
    candidate_vector = vector(candidate_themes)
    ranked = sorted(
        followed,
        key=lambda item: cosine(candidate_vector, vector(item[1])),
        reverse=True,
    )
    names = [name for name, themes in ranked if cosine(candidate_vector, vector(themes)) > 0][:2]
    if len(names) == 2:
        sentence = f"Recommended because you follow {phrase} including {names[0]} and {names[1]}."
    elif names:
        sentence = f"Recommended because you follow {phrase}, including {names[0]}."
    else:
        sentence = f"Recommended because you follow {phrase}."
    if sibling:
        sentence += f" You already follow {sibling} in this franchise."
    return sentence
