import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from ami_meeting_svc.models import User, Meeting, ActionItem


def create_user(db_session):
    user = User(username="testuser", email="testuser@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_meeting(db_session, owner_id: int):
    meeting = Meeting(owner_id=owner_id, title="Team Sync", date=datetime.utcnow(), attendees=[], notes="Notes")
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


def test_action_item_crud_and_defaults(db_session):
    # create user and meeting
    user = create_user(db_session)
    meeting = create_meeting(db_session, user.id)

    # create action item
    ai = ActionItem(meeting_id=meeting.id, description="Follow up on task", assignee="alice@example.com", priority="High")
    db_session.add(ai)
    db_session.commit()
    db_session.refresh(ai)

    assert ai.id is not None
    assert ai.status == "To Do"
    assert ai.is_overdue is False
    assert ai.created_at is not None
    assert ai.updated_at is not None

    # update
    ai.status = "In Progress"
    db_session.commit()
    db_session.refresh(ai)
    assert ai.status == "In Progress"

    # delete
    db_session.delete(ai)
    db_session.commit()
    assert db_session.get(ActionItem, ai.id) is None


def test_action_item_foreign_key_constraint(db_session):
    # Ensure SQLite enforces foreign keys for this connection by using raw DB-API connection
    try:
        bind = db_session.get_bind()
        raw_conn = bind.raw_connection()
        try:
            raw_conn.execute("PRAGMA foreign_keys=ON")
            raw_conn.commit()
        finally:
            raw_conn.close()
    except Exception:
        # If DB driver doesn't support raw_connection or PRAGMA, proceed; integrity will still be attempted
        pass

    ai = ActionItem(meeting_id=999999, description="Orphan action", priority="Low")
    db_session.add(ai)
    with pytest.raises(IntegrityError):
        db_session.commit()
