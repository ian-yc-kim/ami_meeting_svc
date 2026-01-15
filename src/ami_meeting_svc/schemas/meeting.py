from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator


class MeetingBase(BaseModel):
    title: str
    date: datetime
    attendees: List[str]
    notes: str


class MeetingCreate(MeetingBase):
    # notes must be at least 50 characters
    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str) -> str:
        if v is None:
            raise ValueError("notes is required")
        if len(v) < 50:
            raise ValueError("notes must be at least 50 characters long")
        return v


class MeetingUpdate(BaseModel):
    title: str | None = None
    date: datetime | None = None
    attendees: List[str] | None = None
    notes: str | None = None


class MeetingResponse(MeetingBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    analysis_result: dict | None = None

    model_config = ConfigDict(from_attributes=True)
