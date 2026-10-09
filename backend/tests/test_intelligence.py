"""Facts, spoilers, and the season model."""

from app.data.catalog import DOCUMENTS
from app.services.extract import extract_facts
from app.services.predictor import estimate
from app.services.recommender import centroid, cosine, explain, vector
from app.services.spoiler import guard_changes


def _body(story: str) -> list[str]:
    return [row["body"] for row in DOCUMENTS if row["story"] == story]


def test_jjk_sources_become_one_set_of_changes():
    facts = []
    seen = set()
    for body in _body("jjk-s3"):
        for fact in extract_facts(body):
            if fact["text"] not in seen:
                seen.add(fact["text"])
                facts.append(fact["text"])
    assert "New trailer released" in facts
    assert "January 2027 premiere window announced" in facts
    assert "Crunchyroll confirmed streaming" in facts


def test_demon_slayer_catchup_facts():
    seen = []
    for body in _body("ds-movie"):
        for fact in extract_facts(body):
            if fact["text"] not in seen:
                seen.append(fact["text"])
    assert seen == [
        "New movie trailer released",
        "October 16 release date announced",
        "New key visual revealed",
        "Crunchyroll confirmed streaming",
        "No Season 5 announcement",
    ] or set(seen) == {
        "New movie trailer released",
        "October 16 release date announced",
        "New key visual revealed",
        "Crunchyroll confirmed streaming",
        "No Season 5 announcement",
    }


def test_delay_does_not_invent_a_premiere():
    facts = extract_facts(_body("op-delay")[0])
    texts = [fact["text"] for fact in facts]
    assert texts == ["Episode 1142 moved to October 11"]


def test_fan_edit_has_no_facts():
    facts = extract_facts(_body("noise-amv")[0])
    assert facts == []


def test_spoiler_hides_episode_past_progress():
    changes = [
        {
            "type": "coverage",
            "text": "A recap post describes a major character's death and a return in episode 24.",
            "spoiler": True,
        }
    ]
    hidden, count = guard_changes(changes, 13, True)
    assert hidden == []
    assert count == 1
    shown, count = guard_changes(changes, 24, True)
    assert count == 0
    assert "episode 24" in shown[0]


def test_prediction_separates_estimate_from_a_dated_release():
    dated = estimate(
        studio="A-1 Pictures",
        announce_quarter=3,
        has_trailer=True,
        is_movie=False,
        specificity=3,
        official_text="October 11, 2026",
        year_hint=2026,
        subject="Season 2",
    )
    assert dated["skipped"] is True
    assert dated["estimated_window"] is None
    assert "official date" in dated["disclaimer"]

    vague = estimate(
        studio="Ufotable",
        announce_quarter=2,
        has_trailer=False,
        is_movie=False,
        specificity=0,
        official_text="2027",
        year_hint=2027,
        subject="Season 5",
    )
    assert vague["skipped"] is False
    assert vague["estimated_window"].endswith("2027")
    assert 0 < vague["confidence"] < 1
    assert "estimate" in vague["disclaimer"].lower()


def test_recommendation_names_followed_shows():
    followed = [
        ("Solo Leveling", ["action", "dark_fantasy", "supernatural", "shonen"]),
        ("Jujutsu Kaisen", ["action", "dark_fantasy", "supernatural", "shonen"]),
    ]
    profile = centroid([themes for _, themes in followed])
    candidate = ["action", "dark_fantasy", "supernatural", "sci_fi", "shonen"]
    reason = explain(candidate, followed, profile, None)
    assert "Solo Leveling" in reason
    assert "Jujutsu Kaisen" in reason
    assert cosine(profile, vector(candidate)) > 0.5
