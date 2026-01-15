from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ami_meeting_svc.models.base import get_db
from ami_meeting_svc.models import User
from ami_meeting_svc.utils.security import get_current_user
from ami_meeting_svc.services.dashboard_service import get_dashboard_metrics
from ami_meeting_svc.schemas.dashboard import DashboardMetrics

logger = logging.getLogger(__name__)

dashboard_router = APIRouter()


@dashboard_router.get("/metrics", response_model=DashboardMetrics)
async def metrics(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DashboardMetrics:
    try:
        result = get_dashboard_metrics(db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to compute dashboard metrics")
