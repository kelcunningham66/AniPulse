# AniPulse AI

AniPulse is a personal show tracker. You follow something once. The app keeps the next episode, the dub, the platform, and the announcements that actually changed something — in one place.

Fans usually piece that together themselves: a post on X, a line on Crunchyroll, a note on the official site, a thread on Reddit. AniPulse collects those sources, throws out the noise, and answers the question.

## Credits

**Kel** conceived AniPulse. The product idea, the problem (fragmented show news), and the feature set — the watchlist, the release calendar, release-date estimates, sub versus dub tracking, streaming availability, spoiler-safe updates, “what did I miss?”, and watchlist recommendations — are Kel's.

Working in Cursor, Kel and Cursor built this application: the React interface, the FastAPI service, the collection pipeline, and the scikit-learn models that decide whether a source is a real update and which season an undated announcement probably belongs to.

## What you can do

- **Watchlist.** Each show you follow has one card: the latest episode, the next date, the dub, the season status, and a warning when the schedule moved.
- **Feed.** Sources about the same story are merged. You see what changed, how confident the merge is, and which outlets agreed. Fan edits and meme posts are discarded.
- **Calendar.** Filter sub releases, dub releases, movies, season premieres, and manga chapters. Reminders are scheduled in-app for a lead time you pick (30 minutes by default).
- **Dub mode.** “I only watch the English dub” (or Spanish) rewrites the watchlist around that version and says how far behind the Japanese release it is.
- **Streaming.** Availability by region, with a marker when a service was just added.
- **Spoiler protection.** Set your progress. Coverage that talks past that episode is hidden, not rewritten into a fake recap.
- **Catch up.** A short list of what changed since you last checked, or over 7, 30, or 60 days.
- **Recommendations.** A cosine match on the themes of shows you follow, with the titles that drove the score named in the reason.
- **Release estimate.** When a studio has only said a year, a random forest trained on a sample premiere history suggests a season. Official dates are never replaced by that guess. The number on screen is the model's probability.
- **Pulse lab.** Paste a note and see the score, or scan waiting sources. A public pull can read an Anime News Network RSS feed and AniList's airing schedule when those hosts are reachable.

The catalog is **sample data for October 2026**, so the product runs without broadcaster credentials. It is not a live listing. Public pulls are labeled separately and can fail closed if a host is unreachable.

## How the pipeline works

```text
Internet sources
  official sites, streamers, studios, news, social, episode databases
        │
        ▼
Data collection
        │
        ▼
AI classification          meaningful update, or noise?
        │
        ▼
Information extraction     trailer, date, dub, streamer, delay
        │
        ▼
PostgreSQL
        │
        ├── recommendation engine
        ▼
User dashboard and in-app reminders
```

Classification is a TF–IDF logistic regression fit on a fixed labeled set. Extraction is deterministic wording (dates, platforms, delays, dubs). Stories that share a key are merged, and confidence steps up when more than one publisher agrees. The season model is a random forest over studio, announcement quarter, trailer, and how specific the official wording is. Recommendations are cosine similarity on theme tags.

Spoiler protection compares episode numbers (and unmarked plot-leak wording) with your saved progress. It will miss a spoiler that never names an episode or uses those words.

Email and Firebase push are stubbed. The API tells you they stay off until credentials exist. In-app reminders are real and computed from the calendar plus your lead time.

Celery is wired (`app/worker.py`) for the same scan the API runs inline. Redis is optional for local use.

## Run it locally

You need Python 3.12, Node 22, and PostgreSQL.

```bash
# Database, once
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER anipulse WITH PASSWORD 'anipulse';"
sudo -u postgres psql -c "CREATE DATABASE anipulse OWNER anipulse;"
```

```bash
# API
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 43118
```

```bash
# Web
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:43117](http://127.0.0.1:43117). The dev server proxies `/api` to port 43118. Interactive docs are at [http://127.0.0.1:43118/docs](http://127.0.0.1:43118/docs).

Copy `.env.example` if you want a different database URL. The default is the local `anipulse` role above.

Tests:

```bash
cd backend
.venv/bin/pytest
```

## Docker

```bash
docker compose up --build
```

That starts PostgreSQL, Redis, the API, a Celery worker, and the web app on port 43117.

## Stack

React, TypeScript, Tailwind, FastAPI, PostgreSQL, scikit-learn, and an optional Celery/Redis worker. The interface uses Radix primitives for dialogs and switches.
