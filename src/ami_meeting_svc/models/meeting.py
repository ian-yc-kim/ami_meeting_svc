from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy import JSON as SAJSON

from .base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id: int = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    owner_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    title: str = Column(String(255), nullable=False)
    date: datetime = Column(DateTime, nullable=False)
    attendees: list = Column(SAJSON, nullable=False)
    notes: str = Column(Text, nullable=False)
    # New analysis_result column to store AI analysis output
    analysis_result: dict = Column(SAJSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Meeting(id={self.id}, owner_id={self.owner_id}, title='{self.title}')>"
