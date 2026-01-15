from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ami_meeting_svc.models import Meeting, User
from ami_meeting_svc.models.base import get_db
from ami_meeting_svc.schemas.meeting import (
    MeetingCreate,
    MeetingResponse,
)
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
