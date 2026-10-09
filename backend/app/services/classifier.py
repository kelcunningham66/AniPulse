"""Small text classifiers that separate real announcements from fan noise.

Both models are fit in-process on a fixed labeled set. They are deliberately
small: the point is a reproducible decision, not a hosted LLM call.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Labeled examples stay close to the wording the collector actually sees.
_SAMPLES: list[tuple[str, str]] = [
    ("official trailer released for the new season", "trailer"),
    ("the production committee released a new trailer", "trailer"),
    ("new movie trailer released ahead of the theatrical date", "trailer"),
    ("a january premiere window was announced by the committee", "premiere"),
    ("theatrical release date announced for the movie", "premiere"),
    ("season premiere set for a dated opening on a platform", "premiere"),
    ("the movie opens in theaters on a published date", "premiere"),
    ("episode releases this week on the streaming service", "premiere"),
    ("chapter releases in the weekly magazine on a set date", "premiere"),
    ("crunchyroll confirmed it will stream the new season", "streaming"),
    ("the platform confirmed streaming after the theatrical run", "streaming"),
    ("now available on netflix in the united states", "streaming"),
    ("netflix added the series to the us catalog", "streaming"),
    ("streaming has not been announced for the movie", "streaming"),
    ("episode has been delayed and the schedule was updated", "schedule"),
    ("the air date changed to later in the week", "schedule"),
    ("episode will skip a week and the schedule was updated", "schedule"),
    ("english dub episode arrives on the published schedule", "dub"),
    ("spanish dub episode is dated for later this month", "dub"),
    ("voice actor returns for the english dub", "cast"),
    ("the cast confirmed for the upcoming dub episode", "cast"),
    ("new key visual revealed for the movie", "visual"),
    ("a new key art was published by the studio", "visual"),
    ("the production update included no season announcement", "production"),
    ("anime announced for next year and a season has not been named", "production"),
    ("studio announcement confirms the new season is in production", "production"),
    ("a recap post describes a major character death and a return in a later episode", "production"),
    ("coverage mentions a character death in a future episode", "production"),
    ("ultimate amv fan edit set to a nightcore track not an official release", "noise"),
    ("new amv fan edit using a phonk track not an official announcement", "noise"),
    ("fan edit of the opening synced to a pop song", "noise"),
    ("tier list of characters in a meme bracket posted by a fan account", "noise"),
    ("which character would win a meme poll on a fan account", "noise"),
    ("cosplay photos from a fan meetup this weekend", "noise"),
    ("fan theory thread with no studio statement attached", "noise"),
    ("unofficial discord screenshot of a rumor with no source", "noise"),
    ("reddit meme about the opening theme and a dance trend", "noise"),
    ("fan account ranking the best outfits in the series", "noise"),
    ("playlist of fan songs inspired by the show", "noise"),
    ("cosplay tutorial with fabric from a craft store", "noise"),
]


@lru_cache(maxsize=1)
def _models() -> dict:
    texts = [row[0] for row in _SAMPLES]
    labels = [row[1] for row in _SAMPLES]
    binary = ["noise" if label == "noise" else "signal" for label in labels]
    vector = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    matrix = vector.fit_transform(texts)
    signal = LogisticRegression(max_iter=500, random_state=7)
    signal.fit(matrix, binary)
    typed_text = [text for text, label in _SAMPLES if label != "noise"]
    typed_y = [label for label in labels if label != "noise"]
    type_vector = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    type_matrix = type_vector.fit_transform(typed_text)
    typer = LogisticRegression(max_iter=500, random_state=7)
    typer.fit(type_matrix, typed_y)
    return {"vector": vector, "signal": signal, "type_vector": type_vector, "typer": typer}


def score_text(text: str) -> dict:
    models = _models()
    cleaned = " ".join(text.lower().split()) or "empty"
    signal_row = models["vector"].transform([cleaned])
    signal_probs = models["signal"].predict_proba(signal_row)[0]
    signal_labels = list(models["signal"].classes_)
    signal_map = {label: float(prob) for label, prob in zip(signal_labels, signal_probs, strict=True)}
    type_row = models["type_vector"].transform([cleaned])
    type_probs = models["typer"].predict_proba(type_row)[0]
    best = int(np.argmax(type_probs))
    predicted = str(models["typer"].classes_[best])
    return {
        "signal_probability": round(signal_map.get("signal", 0.0), 4),
        "noise_probability": round(signal_map.get("noise", 0.0), 4),
        "predicted_type": predicted,
        "type_probability": round(float(type_probs[best]), 4),
    }


def confidence_label(confidence: float, sources: int) -> str:
    score = confidence
    if sources >= 3:
        score += 0.12
    elif sources == 2:
        score += 0.05
    score = min(score, 0.99)
    if score >= 0.72:
        return "High"
    if score >= 0.48:
        return "Medium"
    return "Low"
