import pytest
from datetime import datetime, timedelta

from ami_meeting_svc.models import User, Meeting, ActionItem
from ami_meeting_svc.utils.security import get_password_hash


def create_user(db_session, username: str = "alice", email: str = "alice@example.com") -> User:
    user = User(username=username, email=email, password_hash=get_password_hash("secret"))
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


def login_and_set_cookie(client, username: str, password: str = "secret"):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    assert token is not None
    client.cookies.set("access_token", token)
    return token


def test_dashboard_empty_db(client, db_session):
    # create and login a user for auth
    create_user(db_session, username="u_empty", email="u_empty@example.com")
    login_and_set_cookie(client, "u_empty")

    resp = client.get("/dashboard/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items"] == 0
    assert data["completion_rate"] == 0.0
    assert data["overdue_count"] == 0
    assert data["assignee_stats"] == []


def test_dashboard_with_data(client, db_session):
    # create user and meeting for FK constraints and login
    user = create_user(db_session, username="u1", email="u1@example.com")
    meeting = create_meeting(db_session, user.id)
    login_and_set_cookie(client, "u1")

    now = datetime.utcnow()
    past = now - timedelta(days=5)

    items = [
        ActionItem(meeting_id=meeting.id, description="Task1", assignee="alice", priority="High", status="To Do", is_overdue=False),
        ActionItem(meeting_id=meeting.id, description="Task2", assignee="alice", priority="Low", status="In Progress", is_overdue=False),
        ActionItem(meeting_id=meeting.id, description="Task3", assignee="bob", priority="Medium", status="Done", is_overdue=False),
        ActionItem(meeting_id=meeting.id, description="Task4", assignee=None, priority="Low", status="To Do", is_overdue=True),
        ActionItem(meeting_id=meeting.id, description="Task5", assignee="bob", priority="High", status="Done", is_overdue=False),
        ActionItem(meeting_id=meeting.id, description="Task6", assignee=None, priority="Low", status="In Progress", is_overdue=True),
    ]

    db_session.add_all(items)
    db_session.commit()

    resp = client.get("/dashboard/metrics")
    assert resp.status_code == 200
    data = resp.json()

    # total items
    assert data["total_items"] == 6
    # done count = 2 -> completion_rate = (2/6)*100 = 33.3
    assert abs(data["completion_rate"] - 33.3) < 0.01
    # overdue_count = 2
    assert data["overdue_count"] == 2

    # assignee stats: expect entries for alice, bob, and null assignee
    stats = { (s.get("assignee") if s.get("assignee") is not None else None): s for s in data["assignee_stats"] }

    # alice: Task1 (To Do)=1, Task2 (In Progress)=1, Done=0
    alice = stats.get("alice")
    assert alice is not None
    assert alice["todo_count"] == 1
    assert alice["in_progress_count"] == 1
    assert alice["done_count"] == 0

    # bob: two Done
    bob = stats.get("bob")
    assert bob is not None
    assert bob["todo_count"] == 0
    assert bob["in_progress_count"] == 0
    assert bob["done_count"] == 2

    # None assignee
    none_assignee = stats.get(None)
    assert none_assignee is not None
    assert none_assignee["todo_count"] == 1
    assert none_assignee["in_progress_count"] == 1
    assert none_assignee["done_count"] == 0
