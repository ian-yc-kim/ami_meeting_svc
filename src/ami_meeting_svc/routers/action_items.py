from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ami_meeting_svc.models import ActionItem
from ami_meeting_svc.models.base import get_db
from ami_meeting_svc.schemas.action_item import ActionItemUpdate, ActionItemResponse

logger = logging.getLogger(__name__)

action_items_router = APIRouter(tags=["action-items"])


@action_items_router.patch("/{action_item_id}", response_model=ActionItemResponse)
async def update_action_item(
    action_item_id: int, payload: ActionItemUpdate, db: Session = Depends(get_db)
) -> ActionItem:
    try:
        stmt = select(ActionItem).where(ActionItem.id == action_item_id)
        action_item = db.execute(stmt).scalar_one_or_none()
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

    if action_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found")

    # Apply updates from payload (only provided fields)
    try:
        updates: Dict = payload.model_dump(exclude_unset=True)
        for key, val in updates.items():
            setattr(action_item, key, val)

        # Recalculate overdue based on the updated values
        deadline = action_item.deadline
        status_val = action_item.status

        if deadline is None:
            action_item.is_overdue = False
        else:
            try:
                if deadline.tzinfo is None:
                    now = datetime.utcnow()
                else:
                    now = datetime.now(timezone.utc)
                action_item.is_overdue = (deadline < now) and (status_val != "Done")
            except Exception as e:
                logger.error(e, exc_info=True)
                # If comparison fails, be conservative and mark not overdue
                action_item.is_overdue = False

        # update timestamp
        action_item.updated_at = datetime.utcnow()

        db.add(action_item)
        db.commit()
        db.refresh(action_item)
        return action_item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
