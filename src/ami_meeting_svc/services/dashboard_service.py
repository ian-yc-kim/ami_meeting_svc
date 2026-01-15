from __future__ import annotations

import logging
from typing import Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ami_meeting_svc.models import ActionItem
from ami_meeting_svc.schemas.dashboard import DashboardMetrics, AssigneeStats

logger = logging.getLogger(__name__)


def get_dashboard_metrics(db: Session) -> DashboardMetrics:
    try:
        # total items
        stmt_total = select(func.count()).select_from(ActionItem)
        total_items = int(db.execute(stmt_total).scalar_one())

        # done items
        stmt_done = select(func.count()).select_from(ActionItem).where(ActionItem.status == "Done")
        done_count = int(db.execute(stmt_done).scalar_one())

        # overdue
        stmt_overdue = select(func.count()).select_from(ActionItem).where(ActionItem.is_overdue == True)
        overdue_count = int(db.execute(stmt_overdue).scalar_one())

        # completion rate
        if total_items == 0:
            completion_rate = 0.0
        else:
            completion_rate = round((done_count / total_items) * 100.0, 1)

        # per-assignee aggregation: assignee + status
        stmt_group = (
            select(ActionItem.assignee, ActionItem.status, func.count().label("cnt"))
            .group_by(ActionItem.assignee, ActionItem.status)
        )
        rows = db.execute(stmt_group).all()

        # build mapping
        stats_map: Dict[Any, Dict[str, int]] = {}
        for assignee, status, cnt in rows:
            key = assignee  # can be None
            if key not in stats_map:
                stats_map[key] = {"To Do": 0, "In Progress": 0, "Done": 0}
            # normalize status keys to expected ones
            stats_map[key][status] = int(cnt)

        # build AssigneeStats list sorted deterministically by assignee string (None -> empty string)
        assignee_stats_list: List[AssigneeStats] = []
        for assignee_key in sorted(stats_map.keys(), key=lambda x: "" if x is None else str(x)):
            counts = stats_map[assignee_key]
            assignee_stats_list.append(
                AssigneeStats(
                    assignee=assignee_key,
                    todo_count=counts.get("To Do", 0),
                    in_progress_count=counts.get("In Progress", 0),
                    done_count=counts.get("Done", 0),
                )
            )

        return DashboardMetrics(
            total_items=total_items,
            completion_rate=completion_rate,
            overdue_count=overdue_count,
            assignee_stats=assignee_stats_list,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        # In case of DB error, raise the exception to caller to handle/log as HTTP 500
        raise
