from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ActionItemCreate(BaseModel):
    description: str
    assignee: Optional[str] = None
    priority: str
    deadline: Optional[datetime] = None

    @field_validator("priority")
    @classmethod
    def normalize_priority(cls, v: str) -> str:
        if v is None:
            raise ValueError("priority is required")
        normalized = v.strip().title()
        allowed = {"High", "Medium", "Low"}
        if normalized not in allowed:
            raise ValueError("priority must be one of High, Medium, Low")
        return normalized


class ActionItemResponse(BaseModel):
    id: int
    meeting_id: int
    description: str
    assignee: Optional[str] = None
    priority: str
    deadline: Optional[datetime] = None
    status: str
    is_overdue: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
