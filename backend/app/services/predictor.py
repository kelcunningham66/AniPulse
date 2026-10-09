"""Season-window model trained on a fixed studio history table.

Official dates stay official. The model only runs when a premiere is still
a year or a loose window, and every response carries that distinction.
"""

from __future__ import annotations

import random
from functools import lru_cache

import numpy as np
from sklearn.ensemble import RandomForestClassifier

QUARTERS = ["Winter", "Spring", "Summer", "Fall"]

_STUDIOS = [
    "Ufotable",
    "MAPPA",
    "A-1 Pictures",
    "Madhouse",
    "Wit Studio",
    "CloverWorks",
    "Science SARU",
    "Toei Animation",
    "Bones",
    "Production I.G",
]


def load_history() -> list[dict]:
    """Deterministic sample of announcement to premiere pairs."""
    rng = random.Random(11)
    rows: list[dict] = []
    for index in range(96):
        studio = _STUDIOS[index % len(_STUDIOS)]
        announce_quarter = index % 4
        has_trailer = 0 if index % 3 == 0 else 1
        is_movie = 1 if index % 11 == 0 else 0
        specificity = index % 3
        premiere = (announce_quarter + 1 + has_trailer) % 4
        if studio == "Ufotable":
            premiere = 1
        elif studio == "MAPPA":
            premiere = 0 if has_trailer else (announce_quarter + 1) % 4
        if is_movie:
            premiere = 3
        if rng.random() < 0.18:
            premiere = (premiere + rng.choice([1, 3])) % 4
        rows.append(
            {
                "studio": studio,
                "announce_quarter": announce_quarter,
                "has_trailer": has_trailer,
                "is_movie": is_movie,
                "specificity": specificity,
                "premiere_quarter": premiere,
            }
        )
    return rows


def _encode(rows: list[dict], levels: list[str]) -> np.ndarray:
    matrix = []
    for row in rows:
        studio = [1.0 if row["studio"] == level else 0.0 for level in levels]
        studio.extend(
            [
                float(row["announce_quarter"]),
                float(row["has_trailer"]),
                float(row["is_movie"]),
                float(row["specificity"]),
            ]
        )
        matrix.append(studio)
    return np.array(matrix, dtype=float)


@lru_cache(maxsize=1)
def _fitted() -> tuple[RandomForestClassifier, list[str], tuple]:
    history = load_history()
    levels = sorted({row["studio"] for row in history})
    model = RandomForestClassifier(n_estimators=80, max_depth=6, random_state=3)
    model.fit(_encode(history, levels), np.array([row["premiere_quarter"] for row in history]))
    return model, levels, tuple(history)


def _reasons(features: dict, predicted: int, history: list[dict]) -> list[str]:
    reasons: list[str] = []
    studio_rows = [row for row in history if row["studio"] == features["studio"]]
    if len(studio_rows) >= 4:
        counts: dict[int, int] = {}
        for row in studio_rows:
            counts[row["premiere_quarter"]] = counts.get(row["premiere_quarter"], 0) + 1
        mode, hits = max(counts.items(), key=lambda item: item[1])
        if mode == predicted:
            share = hits / len(studio_rows)
            reasons.append(
                f"{features['studio']} premieres in this sample most often fall in {QUARTERS[mode]} ({share:.0%} of studio rows)."
            )
    if features["has_trailer"]:
        reasons.append(
            "A trailer is already public. In this sample, trailer-backed titles usually land in the next seasonal slots."
        )
    else:
        reasons.append("No trailer is on file, so the window leans on studio history and the announcement quarter.")
    if features["specificity"] == 0:
        reasons.append("Only a year was announced, so the model is choosing a season inside that year.")
    elif features["specificity"] == 2:
        reasons.append("An official month or window is already published. This season call is a cross-check.")
    return reasons


def estimate(
    *,
    studio: str,
    announce_quarter: int | None,
    has_trailer: bool,
    is_movie: bool,
    specificity: int,
    official_text: str,
    year_hint: int | None,
    subject: str,
) -> dict:
    disclaimer = "This is an estimate, not an official release date."
    if specificity >= 3:
        return {
            "subject": subject,
            "official_text": official_text,
            "estimated_window": None,
            "confidence": None,
            "factors": [],
            "disclaimer": "A dated release is already on the calendar. No estimate is shown over an official date.",
            "skipped": True,
        }
    model, levels, history_tuple = _fitted()
    history = list(history_tuple)
    quarter = 0 if announce_quarter is None else int(announce_quarter)
    features = {
        "studio": studio or "Unknown",
        "announce_quarter": quarter,
        "has_trailer": 1 if has_trailer else 0,
        "is_movie": 1 if is_movie else 0,
        "specificity": int(specificity),
    }
    encoded = _encode([features], levels)
    predicted = int(model.predict(encoded)[0])
    probabilities = model.predict_proba(encoded)[0]
    confidence = float(probabilities[list(model.classes_).index(predicted)])
    year = year_hint or 2027
    if specificity == 2:
        disclaimer = (
            "This is an estimate, not an official release date. "
            "An official window is already published; the model is only a cross-check."
        )
    return {
        "subject": subject,
        "official_text": official_text,
        "estimated_window": f"{QUARTERS[predicted]} {year}",
        "confidence": round(confidence, 4),
        "factors": _reasons(features, predicted, history),
        "disclaimer": disclaimer,
        "skipped": False,
    }
