"""Request bodies."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MePatch(BaseModel):
    region: Literal["US", "GB", "JP", "CA"] | None = None
    audio_mode: Literal["all", "dub"] | None = None
    audio_language: Literal["en", "es", "ja"] | None = None
    spoiler_protection: bool | None = None
    notify_enabled: bool | None = None
    notify_lead_minutes: Literal[15, 30, 60, 120] | None = None
    notify_in_app: bool | None = None
    notify_email: bool | None = None
    notify_push: bool | None = None
    notify_episodes: bool | None = None
    notify_dubs: bool | None = None
    notify_delays: bool | None = None
    notify_renewals: bool | None = None
    notify_streaming: bool | None = None
    email_address: str | None = Field(default=None, max_length=160)
    push_token: str | None = Field(default=None, max_length=512)


class ProgressIn(BaseModel):
    episode: int = Field(ge=0, le=20000)


class FollowIn(BaseModel):
    target_type: Literal["title", "person", "studio", "franchise"]
    slug: str = Field(min_length=1, max_length=80)


class ClassifyIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class ReadIn(BaseModel):
    id: int | None = None
