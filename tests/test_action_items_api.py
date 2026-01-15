import pytest
from datetime import datetime, timedelta, timezone

from ami_meeting_svc.models import User, Meeting, ActionItem
from ami_meeting_svc.utils.security import get_password_hash


def create_user(db_session, username: str = "alice", email: str = "alice@example.com", password: str = "secret") -> User:
    user = User(username=username, email=email, password_hash=get_password_hash(password))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_meeting(db_session, owner_id: int) -> Meeting:
    meeting = Meeting(owner_id=owner_id, title="Team Sync", date=datetime.utcnow(), attendees=["a"], notes=("x" * 60))
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


def login_and_set_cookie(client, username: str, password: str):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    assert token is not None
    client.cookies.set("access_token", token)
    return token


def test_update_status_transitions(client, db_session):
    user = create_user(db_session)
    meeting = create_meeting(db_session, user.id)

    # create action item directly
    ai = ActionItem(meeting_id=meeting.id, description="Do thing", priority="Medium")
    db_session.add(ai)
    db_session.commit()
    db_session.refresh(ai)

    login_and_set_cookie(client, "alice", "secret")

    # To In Progress
    resp = client.patch(f"/action-items/{ai.id}", json={"status": "In Progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "In Progress"

    # To Done
    resp2 = client.patch(f"/action-items/{ai.id}", json={"status": "Done"})
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "Done"


def test_update_details_assignee_description(client, db_session):
    user = create_user(db_session, username="bob", email="bob@example.com", password="pwd")
    meeting = create_meeting(db_session, user.id)
    ai = ActionItem(meeting_id=meeting.id, description="Old desc", priority="Low")
    db_session.add(ai)
    db_session.commit()
    db_session.refresh(ai)

    login_and_set_cookie(client, "bob", "pwd")

    resp = client.patch(f"/action-items/{ai.id}", json={"assignee": "carol", "description": "New desc"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["assignee"] == "carol"
    assert data["description"] == "New desc"
    # ensure priority unchanged
    assert data["priority"] == "Low"


def test_is_overdue_logic(client, db_session):
    user = create_user(db_session, username="chris", email="chris@example.com", password="pw")
    meeting = create_meeting(db_session, user.id)

    past_deadline = datetime.utcnow() - timedelta(days=2)
    ai = ActionItem(meeting_id=meeting.id, description="Past task", priority="High", deadline=past_deadline)
    db_session.add(ai)
    db_session.commit()
    db_session.refresh(ai)

    login_and_set_cookie(client, "chris", "pw")

    # status To Do with past deadline -> overdue True
    resp = client.patch(f"/action-items/{ai.id}", json={"status": "To Do"})
    assert resp.status_code == 200
    assert resp.json()["is_overdue"] is True

    # mark Done -> overdue False
    resp2 = client.patch(f"/action-items/{ai.id}", json={"status": "Done"})
    assert resp2.status_code == 200
    assert resp2.json()["is_overdue"] is False


def test_patch_nonexistent_returns_404(client, db_session):
    # create and login a user to provide auth
    create_user(db_session, username="dan", email="dan@example.com", password="p")
    login_and_set_cookie(client, "dan", "p")

    resp = client.patch(f"/action-items/999999", json={"description": "x"})
    assert resp.status_code == 404


def test_invalid_status_validation_returns_422(client, db_session):
    user = create_user(db_session, username="erin", email="erin@example.com", password="pw2")
    meeting = create_meeting(db_session, user.id)
    ai = ActionItem(meeting_id=meeting.id, description="Task", priority="Low")
    db_session.add(ai)
    db_session.commit()
    db_session.refresh(ai)

    login_and_set_cookie(client, "erin", "pw2")

    resp = client.patch(f"/action-items/{ai.id}", json={"status": "INVALID"})
    assert resp.status_code == 422
