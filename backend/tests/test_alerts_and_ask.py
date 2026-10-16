"""Alerts send once, and Ask cites saved updates."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

NOW = "2026-10-16T15:00:00+00:00"
MOMENT = datetime(2026, 10, 16, 15, tzinfo=timezone.utc)


def client() -> TestClient:
    return TestClient(app)


def test_alerts_cover_each_kind_and_do_not_repeat():
    with client() as api:
        first = api.get("/api/notifications", params={"now": NOW}).json()
        categories = {item["category"] for item in first["alerts"]}
        assert {"episode", "dub", "delay", "renewal", "streaming"} <= categories
        assert first["duplicates_skipped"] == 0
        email = next(delivery for alert in first["alerts"] for delivery in alert["deliveries"] if delivery["channel"] == "email")
        assert email["status"] == "recorded"
        second = api.get("/api/notifications", params={"now": NOW}).json()
        assert [item["id"] for item in second["alerts"]] == [item["id"] for item in first["alerts"]]
        assert second["duplicates_skipped"] == len(first["alerts"])


def test_held_email_sends_once_credentials_exist(monkeypatch):
    with client() as api:
        first = api.get("/api/notifications", params={"now": NOW}).json()
        assert all(
            delivery["status"] == "recorded"
            for alert in first["alerts"]
            for delivery in alert["deliveries"]
            if delivery["channel"] == "email"
        )
        calls = {"n": 0}

        def fake_email(user, alert, now):
            calls["n"] += 1
            from app.models import Delivery

            return Delivery(
                alert_id=alert.id,
                channel="email",
                status="sent",
                destination=user.email_address,
                detail="Sent.",
                created_at=now,
            )

        monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
        monkeypatch.setenv("SMTP_FROM", "pulse@example.test")
        monkeypatch.setattr("app.services.notify._email", fake_email)
        api.patch("/api/me", json={"email_address": "kel@example.test"})
        second = api.get("/api/notifications", params={"now": NOW}).json()
        emailed = [
            delivery
            for alert in second["alerts"]
            for delivery in alert["deliveries"]
            if delivery["channel"] == "email"
        ]
        assert emailed
        assert all(delivery["status"] == "sent" for delivery in emailed)
        assert calls["n"] == len(emailed)
        calls["n"] = 0
        api.get("/api/notifications", params={"now": NOW})
        assert calls["n"] == 0


def test_turning_off_dubs_hides_them_and_does_not_create_new_ones():
    with client() as api:
        api.patch("/api/me", json={"notify_dubs": False})
        payload = api.get("/api/notifications", params={"now": NOW}).json()
        assert all(item["category"] != "dub" for item in payload["alerts"])


def test_solo_leveling_renewal_is_not_invented():
    with client() as api:
        payload = api.post("/api/ask", params={"now": NOW}, json={"question": "Did Solo Leveling get renewed?"}).json()
        assert payload["unannounced"] is True
        assert "has not been announced" in payload["answer"].lower() or "not been announced" in payload["answer"].lower() or "no saved update" in payload["answer"].lower()
        assert "renewed" not in payload["answer"].lower() or "no saved update" in payload["answer"].lower()
        cited = " ".join(item["headline"].lower() for item in payload["citations"])
        assert "renew" not in cited


def test_weekend_and_dubs_and_the_past_month_cite_saved_records():
    with client() as api:
        weekend = api.post("/api/ask", params={"now": NOW}, json={"question": "What's dropping this weekend?"}).json()
        assert "One Piece" in weekend["answer"]
        assert weekend["citations"]
        dubs = api.post("/api/ask", params={"now": NOW}, json={"question": "Which of my shows have new English dubs?"}).json()
        assert "Solo Leveling" in dubs["answer"]
        assert any(item["publisher"] for item in dubs["citations"])
        missed = api.post("/api/ask", params={"now": NOW}, json={"question": "What have I missed in the past month?"}).json()
        assert missed["citations"]
        assert "One Piece" in missed["answer"] or "Jujutsu Kaisen" in missed["answer"]


def test_a_window_is_not_called_a_release_date():
    with client() as api:
        payload = api.post(
            "/api/ask",
            params={"now": NOW},
            json={"question": "When is the Jujutsu Kaisen release date?"},
        ).json()
        assert payload["unannounced"] is True
        assert "has not been announced" in payload["answer"]
        assert "not an official date" in payload["answer"]
        assert payload["citations"]
