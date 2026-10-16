"""Relational model for follows, releases, sources, and classified updates."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80))
    region: Mapped[str] = mapped_column(String(8), default="US")
    audio_mode: Mapped[str] = mapped_column(String(16), default="all")
    audio_language: Mapped[str] = mapped_column(String(8), default="en")
    spoiler_protection: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_lead_minutes: Mapped[int] = mapped_column(Integer, default=30)
    notify_in_app: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("TRUE"))
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("TRUE"))
    notify_push: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("FALSE"))
    notify_episodes: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("TRUE"))
    notify_dubs: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("TRUE"))
    notify_delays: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("TRUE"))
    notify_renewals: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("TRUE"))
    notify_streaming: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("TRUE"))
    email_address: Mapped[str] = mapped_column(String(160), default="", server_default="")
    push_token: Mapped[str] = mapped_column(String(512), default="", server_default="")
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Franchise(Base):
    __tablename__ = "franchises"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    blurb: Mapped[str] = mapped_column(Text, default="")


class Studio(Base):
    __tablename__ = "studios"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    blurb: Mapped[str] = mapped_column(Text, default="")


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(80), default="Voice actor")
    blurb: Mapped[str] = mapped_column(Text, default="")
    accent: Mapped[str] = mapped_column(String(16), default="#f0a06a")


class Title(Base):
    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(16))
    season_label: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(24))
    logline: Mapped[str] = mapped_column(Text, default="")
    genres: Mapped[list] = mapped_column(JSON)
    themes: Mapped[list] = mapped_column(JSON)
    accent: Mapped[str] = mapped_column(String(16), default="#ff4d2e")
    list_release: Mapped[str] = mapped_column(String(120), default="")
    schedule_note: Mapped[str | None] = mapped_column(String(160), nullable=True)
    studio_id: Mapped[int | None] = mapped_column(ForeignKey("studios.id"), nullable=True)
    franchise_id: Mapped[int | None] = mapped_column(ForeignKey("franchises.id"), nullable=True)
    official_specificity: Mapped[int] = mapped_column(Integer, default=3)
    prediction_official: Mapped[str] = mapped_column(String(120), default="")
    prediction_subject: Mapped[str] = mapped_column(String(80), default="")
    prediction_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    announce_quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_trailer: Mapped[bool] = mapped_column(Boolean, default=False)
    prediction_is_movie: Mapped[bool] = mapped_column(Boolean, default=False)


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[int] = mapped_column(Integer)


class AudioTrack(Base):
    __tablename__ = "audio_tracks"
    __table_args__ = (UniqueConstraint("title_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    language: Mapped[str] = mapped_column(String(8))
    latest_episode: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_episode: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    label: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(16))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    platform: Mapped[str | None] = mapped_column(String(80), nullable=True)
    note: Mapped[str | None] = mapped_column(String(160), nullable=True)


class StreamingOffer(Base):
    __tablename__ = "streaming_offers"
    __table_args__ = (UniqueConstraint("title_id", "service", "region"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    service: Mapped[str] = mapped_column(String(40))
    region: Mapped[str] = mapped_column(String(8))
    available: Mapped[bool] = mapped_column(Boolean, default=False)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(160), default="")


class WatchProgress(Base):
    __tablename__ = "watch_progress"
    __table_args__ = (UniqueConstraint("user_id", "title_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    episode: Mapped[int] = mapped_column(Integer, default=0)


class SourceDoc(Base):
    __tablename__ = "source_docs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int | None] = mapped_column(ForeignKey("titles.id"), nullable=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    story_key: Mapped[str] = mapped_column(String(80))
    publisher: Mapped[str] = mapped_column(String(120))
    medium: Mapped[str] = mapped_column(String(32))
    headline: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    reject_reason: Mapped[str] = mapped_column(String(160), default="")
    update_id: Mapped[int | None] = mapped_column(ForeignKey("updates.id"), nullable=True)
    external_name: Mapped[str] = mapped_column(String(160), default="")


class UpdateEvent(Base):
    __tablename__ = "updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int | None] = mapped_column(ForeignKey("titles.id"), nullable=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    story_key: Mapped[str] = mapped_column(String(80))
    headline: Mapped[str] = mapped_column(String(240))
    kicker: Mapped[str] = mapped_column(String(160))
    primary_type: Mapped[str] = mapped_column(String(32))
    changes: Mapped[list] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    confidence_label: Mapped[str] = mapped_column(String(16))
    sources_verified: Mapped[int] = mapped_column(Integer, default=1)
    sources: Mapped[list] = mapped_column(JSON)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    external_name: Mapped[str] = mapped_column(String(160), default="")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    dedupe_key: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(16))
    title_id: Mapped[int | None] = mapped_column(ForeignKey("titles.id"), nullable=True)
    headline: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("FALSE"))


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    channel: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    destination: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(String(400), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"), unique=True)
    subject: Mapped[str] = mapped_column(String(80), default="")
    official_text: Mapped[str] = mapped_column(String(160), default="")
    estimated_window: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    factors: Mapped[list] = mapped_column(JSON)
    disclaimer: Mapped[str] = mapped_column(Text, default="")
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
