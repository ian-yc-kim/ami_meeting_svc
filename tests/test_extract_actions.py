import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select

from ami_meeting_svc.models import ActionItem, Meeting
from ami_meeting_svc.models import User
from ami_meeting_svc.utils.security import get_password_hash


def create_user(db_session, username: str = "alice", email: str = "alice@example.com", password: str = "secret") -> User:
    user = User(username=username, email=email, password_hash=get_password_hash(password))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login_and_set_cookie(client, username: str, password: str):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    assert token is not None
    client.cookies.set("access_token", token)
    return token


def meeting_payload(notes: str = None):
    if notes is None:
        notes = "This is a sufficiently long meeting note to pass validation. " + ("detail " * 6)
    return {
        "title": "Team Sync",
        "date": datetime.utcnow().isoformat(),
        "attendees": ["alice", "bob"],
        "notes": notes,
    }


def test_extract_actions_success_persists(client, db_session):
    # create user and meeting
    user = create_user(db_session, username="alice", email="alice@example.com", password="secret")
    login_and_set_cookie(client, "alice", "secret")

    resp = client.post("/meetings/", json=meeting_payload())
    assert resp.status_code == 201
    meeting_id = resp.json()["id"]

    # Mock OpenAIService used in routers.meetings
    mocked_ai_response = {
        "action_items": [
            {"description": "Send recap email", "assignee": "alice", "priority": "High", "deadline": None},
            {"description": "Update roadmap", "assignee": None, "priority": "Low", "deadline": "2026-01-20T00:00:00Z"}
        ]
    }

    with patch("ami_meeting_svc.routers.meetings.OpenAIService") as MockAI:
        instance = MockAI.return_value
        instance.get_completion.return_value = mocked_ai_response

        resp2 = client.post(f"/meetings/{meeting_id}/extract-actions")
        assert resp2.status_code == 200
        data = resp2.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify DB persistence
        stmt = select(ActionItem).where(ActionItem.meeting_id == meeting_id)
        persisted = db_session.execute(stmt).scalars().all()
        assert len(persisted) == 2
        descriptions = {p.description for p in persisted}
        assert "Send recap email" in descriptions and "Update roadmap" in descriptions

        # Check default deadline applied to first item
        ai_first = next(p for p in persisted if p.description == "Send recap email")
        assert ai_first.deadline is not None
        now = datetime.now(timezone.utc)
        assert now + timedelta(days=6, hours=-1) < ai_first.deadline.replace(tzinfo=timezone.utc) < now + timedelta(days=8)

        # Check explicit deadline preserved
        ai_second = next(p for p in persisted if p.description == "Update roadmap")
        assert ai_second.deadline is not None
        assert ai_second.priority == "Low"

        # Ensure the AI service was called with a prompt containing meeting notes
        called_args = instance.get_completion.call_args[1]
        assert "Meeting notes" in called_args["prompt"] or "Meeting notes" in instance.get_completion.call_args[0][0]


def test_extract_actions_empty_notes_returns_400_and_no_ai_call(client, db_session):
    # create user and meeting bypassing validation with empty notes
    user = create_user(db_session, username="alice", email="alice@example.com", password="secret")
    meeting = Meeting(owner_id=user.id, title="Empty Notes", date=datetime.utcnow(), attendees=["a"], notes="")
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)

    login_and_set_cookie(client, "alice", "secret")

    with patch("ami_meeting_svc.routers.meetings.OpenAIService") as MockAI:
        resp = client.post(f"/meetings/{meeting.id}/extract-actions")
        assert resp.status_code == 400
        MockAI.assert_not_called()


def test_extract_actions_not_found_returns_404(client, db_session):
    create_user(db_session, username="alice", email="alice@example.com", password="secret")
    login_and_set_cookie(client, "alice", "secret")

    resp = client.post(f"/meetings/99999/extract-actions")
    assert resp.status_code == 404


def test_extract_actions_not_owner_returns_404(client, db_session):
    # owner A creates meeting
    owner = create_user(db_session, username="alice", email="alice@example.com", password="secret")
    meeting = Meeting(owner_id=owner.id, title="Owner Meeting", date=datetime.utcnow(), attendees=["a"], notes="Some notes")
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)

    # user B
    create_user(db_session, username="bob", email="bob@example.com", password="secret2")
    login_and_set_cookie(client, "bob", "secret2")

    resp = client.post(f"/meetings/{meeting.id}/extract-actions")
    assert resp.status_code == 404
