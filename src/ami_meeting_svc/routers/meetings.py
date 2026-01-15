from __future__ import annotations

import json
import logging
from typing import List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ami_meeting_svc.models import Meeting, User, ActionItem
from ami_meeting_svc.models.base import get_db
from ami_meeting_svc.schemas.meeting import (
    MeetingCreate,
    MeetingResponse,
)
from ami_meeting_svc.schemas.action_item import ActionItemCreate, ActionItemResponse
from ami_meeting_svc.utils.security import get_current_user
from ami_meeting_svc.services.ai_service import OpenAIService

logger = logging.getLogger(__name__)

meetings_router = APIRouter(tags=["meetings"])


@meetings_router.post("/", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Meeting:
    try:
        meeting = Meeting(owner_id=current_user.id, **payload.model_dump())
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        return meeting
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@meetings_router.get("/", response_model=List[MeetingResponse])
async def list_meetings(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> List[Meeting]:
    try:
        stmt = select(Meeting).where(Meeting.owner_id == current_user.id)
        result = db.execute(stmt).scalars().all()
        return result
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@meetings_router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Meeting:
    try:
        stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == current_user.id)
        meeting = db.execute(stmt).scalar_one_or_none()
        if meeting is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        return meeting
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@meetings_router.post("/{meeting_id}/analyze", response_model=MeetingResponse)
async def analyze_meeting(
    meeting_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Meeting:
    try:
        # Fetch meeting and ensure ownership
        stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == current_user.id)
        meeting = db.execute(stmt).scalar_one_or_none()
        if meeting is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

        # Validate notes
        notes = meeting.notes or ""
        if not notes.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting notes are empty")

        # Build prompt for AI
        prompt = (
            "Analyze the following meeting notes and return a single JSON object with keys: "
            "summary (short text), key_discussion_points (array of key bullet points), "
            "decisions (array of decisions). Return only the JSON object, no explanatory text, no markdown.\n\n"
            f"Meeting notes:\n{notes}"
        )

        # Call OpenAI service in json mode
        try:
            ai_service = OpenAIService()
            result = ai_service.get_completion(prompt=prompt, json_mode=True)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI service error")

        if not isinstance(result, dict):
            logger.error("AI returned non-dict result: %s", type(result))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid AI response format")

        # Persist analysis result
        try:
            meeting.analysis_result = result
            db.add(meeting)
            db.commit()
            db.refresh(meeting)
            return meeting
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")


@meetings_router.post("/{meeting_id}/extract-actions", response_model=List[ActionItemResponse])
async def extract_actions(
    meeting_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> List[ActionItem]:
    try:
        # Ensure meeting exists and is owned by current user
        stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == current_user.id)
        meeting = db.execute(stmt).scalar_one_or_none()
        if meeting is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

        notes = meeting.notes or ""
        if not notes.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting notes are empty")

        # Build prompt including current date, notes, and existing analysis result if any
        current_date = datetime.now(timezone.utc).isoformat()
        analysis_part = ""
        if meeting.analysis_result:
            try:
                analysis_part = json.dumps(meeting.analysis_result)
            except Exception:
                analysis_part = str(meeting.analysis_result)

        prompt = (
            "Extract action items from the meeting notes. Return a single JSON object with a key \"action_items\" "
            "whose value is a list of action item objects. Each action item must have: description (string), "
            "assignee (string|null), priority (High/Medium/Low), deadline (ISO8601 string or null). "
            "If deadline is not inferable, deadline can be null and the service will default to 7 days from now. "
            "Return only the JSON object, no explanatory text, no markdown.\n\n"
            f"Current date: {current_date}\n"
            f"Meeting notes:\n{notes}\n"
        )
        if analysis_part:
            prompt += f"Existing analysis result:\n{analysis_part}\n"

        # Call AI service
        try:
            ai_service = OpenAIService()
            result = ai_service.get_completion(prompt=prompt, json_mode=True)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI service error")

        if not isinstance(result, dict) or "action_items" not in result:
            logger.error("Invalid AI response structure: %s", result)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid AI response format")

        raw_items = result.get("action_items")
        if not isinstance(raw_items, list):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid AI response format")

        created_items: List[ActionItem] = []
        now_utc = datetime.now(timezone.utc)
        default_deadline = now_utc + timedelta(days=7)

        for idx, it in enumerate(raw_items):
            if not isinstance(it, dict):
                logger.error("AI returned non-dict action item at index %s: %s", idx, it)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid AI response format")

            desc = it.get("description")
            if not desc or not str(desc).strip():
                logger.error("AI returned action item without description: %s", it)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid AI response format")

            assignee = it.get("assignee")

            pri_raw = it.get("priority")
            if pri_raw is None:
                logger.error("AI returned action item without priority: %s", it)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid AI response format")
            pri = str(pri_raw).strip().title()
            if pri not in {"High", "Medium", "Low"}:
                logger.error("AI returned invalid priority: %s", pri)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid AI response format")

            dl = it.get("deadline")
            deadline_dt = None
            try:
                if dl is None:
                    deadline_dt = default_deadline
                elif isinstance(dl, str) and dl.strip() == "":
                    deadline_dt = default_deadline
                elif isinstance(dl, str):
                    dl_str = dl.strip()
                    if dl_str.endswith("Z"):
                        dl_str = dl_str[:-1] + "+00:00"
                    # datetime.fromisoformat supports offset-aware strings
                    deadline_dt = datetime.fromisoformat(dl_str)
                elif isinstance(dl, (int, float)):
                    # unix timestamp
                    deadline_dt = datetime.fromtimestamp(float(dl), tz=timezone.utc)
                else:
                    # unexpected type
                    deadline_dt = default_deadline
            except Exception as e:
                logger.error(e, exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid AI response format")

            try:
                ai_obj = ActionItem(
                    meeting_id=meeting.id,
                    description=str(desc).strip(),
                    assignee=(str(assignee).strip() if assignee is not None else None),
                    priority=pri,
                    deadline=deadline_dt,
                )
                created_items.append(ai_obj)
            except Exception as e:
                logger.error(e, exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to construct action items")

        # Persist all created items
        try:
            db.add_all(created_items)
            db.commit()
            for item in created_items:
                db.refresh(item)
            return created_items
        except Exception as e:
            logger.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")
