from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class AssigneeStats(BaseModel):
    assignee: Optional[str] = None
    todo_count: int
    in_progress_count: int
    done_count: int


class DashboardMetrics(BaseModel):
    total_items: int
    completion_rate: float
    overdue_count: int
    assignee_stats: List[AssigneeStats]

    # allow model population from attribute objects if needed
    model_config = ConfigDict(from_attributes=True)
