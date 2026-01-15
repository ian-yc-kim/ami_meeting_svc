from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, func

from .base import Base


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    description = Column(String(1024), nullable=False)
    assignee = Column(String(255), nullable=True)
    deadline = Column(DateTime, nullable=True)
    priority = Column(String(50), nullable=False)
    # Keep both SQLAlchemy defaults and server_defaults to match migration and DB behavior
    status = Column(String(50), nullable=False, default="To Do", server_default=sa.text("'To Do'"))
    is_overdue = Column(Boolean, nullable=False, default=False, server_default=sa.text('false'))
    # Use SQLAlchemy-level defaults for application-side behavior and server_default for DB consistency
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=sa.text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=sa.text('CURRENT_TIMESTAMP'))

    def __repr__(self) -> str:
        return f"<ActionItem(id={self.id}, meeting_id={self.meeting_id}, status='{self.status}')>"
