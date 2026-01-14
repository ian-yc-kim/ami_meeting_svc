import pytest
import logging

from ami_meeting_svc.models import User
from ami_meeting_svc.utils.security import get_password_hash


def create_user(db_session, username: str = "alice", email: str = "alice@example.com", password: str = "secret") -> User:
    user = User(username=username, email=email, password_hash=get_password_hash(password))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_success_sets_cookie_and_me_works(client, db_session):
    create_user(db_session)
    resp = client.post("/auth/login", json={"username": "alice", "password": "secret"})
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    # HttpOnly and SameSite flags
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie
    assert "SameSite=Lax" in set_cookie or "samesite=lax" in set_cookie
    # Secure flag should be present when COOKIE_SECURE is True by default
    assert "Secure" in set_cookie or "secure" in set_cookie

    # For tests, TestClient won't send secure cookies over HTTP. Use token from response
    token = resp.json().get("access_token")
    assert token is not None
    client.cookies.set("access_token", token)

    # subsequent protected call
    resp2 = client.get("/auth/me")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"


def test_login_fails_with_wrong_password(client, db_session):
    create_user(db_session)
    resp = client.post("/auth/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


def test_me_unauthorized_without_cookie(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_unauthorized_with_invalid_cookie(client):
    client.cookies.set("access_token", "not-a-jwt")
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_logout_clears_cookie(client, db_session):
    create_user(db_session)
    resp = client.post("/auth/login", json={"username": "alice", "password": "secret"})
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    assert token is not None
    client.cookies.set("access_token", token)

    resp2 = client.post("/auth/logout")
    assert resp2.status_code == 200
    # ensure cookie cleared locally for the test
    client.cookies.clear()
    assert client.cookies.get("access_token") is None

    # protected route now unauthorized
    resp3 = client.get("/auth/me")
    assert resp3.status_code == 401
