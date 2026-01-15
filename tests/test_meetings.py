import pytest
from datetime import datetime, timedelta

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
        notes = "x" * 60
    return {
        "title": "Team Sync",
        "date": datetime.utcnow().isoformat(),
        "attendees": ["alice", "bob"],
        "notes": notes,
    }


def test_create_meeting_requires_auth(client):
    resp = client.post("/meetings/", json=meeting_payload())
    assert resp.status_code == 401


def test_create_meeting_validates_notes_length(client, db_session):
    create_user(db_session)
    login_and_set_cookie(client, "alice", "secret")

    short_notes = "too short"
    payload = meeting_payload(notes=short_notes)
    resp = client.post("/meetings/", json=payload)
    assert resp.status_code == 422


def test_create_and_list_meetings_scoped_to_owner(client, db_session):
    # user A
    create_user(db_session, username="alice", email="alice@example.com", password="secret")
    login_and_set_cookie(client, "alice", "secret")

    resp = client.post("/meetings/", json=meeting_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Team Sync"
    assert data["owner_id"] is not None

    resp_list = client.get("/meetings/")
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]["title"] == "Team Sync"

    # user B should see none
    create_user(db_session, username="bob", email="bob@example.com", password="secret2")
    login_and_set_cookie(client, "bob", "secret2")
    resp_list_b = client.get("/meetings/")
    assert resp_list_b.status_code == 200
    assert resp_list_b.json() == []


def test_get_meeting_detail_returns_404_when_not_owned(client, db_session):
    # owner A creates
    create_user(db_session, username="alice", email="alice@example.com", password="secret")
    login_and_set_cookie(client, "alice", "secret")
    resp = client.post("/meetings/", json=meeting_payload())
    assert resp.status_code == 201
    meeting_id = resp.json()["id"]

    # other user B
    create_user(db_session, username="charlie", email="charlie@example.com", password="s2")
    login_and_set_cookie(client, "charlie", "s2")

    resp2 = client.get(f"/meetings/{meeting_id}")
    assert resp2.status_code == 404


def test_get_meeting_detail_success_when_owned(client, db_session):
    create_user(db_session, username="alice", email="alice@example.com", password="secret")
    login_and_set_cookie(client, "alice", "secret")
    resp = client.post("/meetings/", json=meeting_payload())
    assert resp.status_code == 201
    meeting_id = resp.json()["id"]

    resp2 = client.get(f"/meetings/{meeting_id}")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["id"] == meeting_id
    assert data["owner_id"] is not None
    assert data.get("created_at") is not None
    assert data.get("updated_at") is not None
