"""Seeded API: watchlist, feed, catch-up, and the dub switch."""

from fastapi.testclient import TestClient

from app.main import app


def client() -> TestClient:
    return TestClient(app)


def test_watchlist_matches_the_tracker_shape():
    with client() as api:
        response = api.get("/api/watchlist")
        assert response.status_code == 200
        items = {item["name"]: item for item in response.json()["items"]}
        solo = items["Solo Leveling"]
        assert solo["primary"] == "Episode 19 — Released"
        assert "Next episode: Oct 11" in solo["lines"]
        assert "Dub: Episode 17 available" in solo["lines"]
        assert "Season status: Airing" in solo["lines"]
        piece = items["One Piece"]
        assert piece["warning"] == "Schedule updated"
        assert piece["primary"] == "Next episode: Oct 11"
        jjk = items["Jujutsu Kaisen"]
        assert jjk["primary"] == "Season 3"
        assert "Release: January 2027 window" in jjk["lines"]
        chainsaw = items["Chainsaw Man"]
        assert chainsaw["primary"] == "Release: Oct 2026"
        assert "Streaming: Not announced" in chainsaw["lines"]


def test_feed_publishes_the_jjk_cluster_and_drops_fan_edits():
    with client() as api:
        response = api.get("/api/feed")
        payload = response.json()
        headlines = [item["headline"] for item in payload["updates"]]
        assert "Jujutsu Kaisen Season 3" in headlines
        jjk = next(item for item in payload["updates"] if item["headline"] == "Jujutsu Kaisen Season 3")
        assert jjk["kicker"] == "Official production update detected."
        assert jjk["changes"] == [
            "New trailer released",
            "January 2027 premiere window announced",
            "Crunchyroll confirmed streaming",
        ]
        assert jjk["confidence_label"] == "High"
        assert jjk["sources_verified"] == 3
        assert payload["stats"]["discarded"] >= 3
        assert payload["stats"]["pending"] == 2


def test_spoiler_protection_on_the_title():
    with client() as api:
        detail = api.get("/api/titles/jujutsu-kaisen").json()
        assert detail["progress"] == 13
        coverage = [item for item in detail["updates"] if item["primary_type"] == "coverage"]
        assert coverage
        assert coverage[0]["changes"] == []
        assert coverage[0]["hidden_count"] == 1
        opened = api.put("/api/titles/jujutsu-kaisen/progress", json={"episode": 24}).json()
        coverage = [item for item in opened["updates"] if item["primary_type"] == "coverage"]
        assert coverage[0]["hidden_count"] == 0
        assert "episode 24" in coverage[0]["changes"][0]


def test_catchup_demon_slayer():
    with client() as api:
        payload = api.get("/api/catchup", params={"since": "60", "slug": "demon-slayer"}).json()
        assert len(payload["groups"]) == 1
        assert payload["groups"][0]["bullets"] == [
            "New movie trailer released",
            "New key visual revealed",
            "October 16 release date announced",
            "Crunchyroll confirmed streaming",
            "No Season 5 announcement",
        ]


def test_dub_mode_hides_the_sub_as_the_lead():
    with client() as api:
        api.patch("/api/me", json={"audio_mode": "dub", "audio_language": "en"})
        solo = next(item for item in api.get("/api/watchlist").json()["items"] if item["slug"] == "solo-leveling")
        assert solo["primary"] == "English dub · Episode 17"
        assert "Next for you: Oct 18" in solo["lines"]
        assert "Japanese is 2 episodes ahead" in solo["lines"]


def test_calendar_has_saturday_dandadan():
    with client() as api:
        payload = api.get("/api/calendar", params={"start": "2026-10-01", "end": "2026-10-31"}).json()
        days = {(item["day"], item["name"], item["label"]) for item in payload["releases"]}
        assert ("2026-10-10", "Dandadan", "Ep. 9") in days
        assert ("2026-10-11", "One Piece", "Ep. 1142") in days


def test_prediction_on_demon_slayer_is_labeled_as_an_estimate():
    with client() as api:
        detail = api.get("/api/titles/demon-slayer").json()
        prediction = detail["prediction"]
        assert prediction["official_text"] == "2027"
        assert prediction["skipped"] is False
        assert prediction["estimated_window"].endswith("2027")
        assert "estimate" in prediction["disclaimer"].lower()


def test_scan_keeps_a_delay_and_drops_an_amv():
    with client() as api:
        result = api.post("/api/pulse/scan").json()
        assert any("skipped a week" in change for item in result["updates"] for change in item["changes"])
        assert result["discarded"]
        solo = next(item for item in api.get("/api/watchlist").json()["items"] if item["slug"] == "solo-leveling")
        assert solo["warning"] == "Schedule updated"


def test_classify_endpoint_rejects_fan_noise():
    with client() as api:
        noise = api.post(
            "/api/pulse/classify",
            json={"text": "Ultimate Solo Leveling AMV fan edit set to a nightcore track. This is a fan edit, not an official release."},
        ).json()
        assert noise["meaningful"] is False
        signal = api.post(
            "/api/pulse/classify",
            json={"text": "Crunchyroll confirmed it will stream Jujutsu Kaisen Season 3."},
        ).json()
        assert signal["meaningful"] is True
        assert "Crunchyroll confirmed streaming" in signal["changes"]
