from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ami_meeting_svc.config import COOKIE_SECURE, ACCESS_TOKEN_EXPIRE_MINUTES
from ami_meeting_svc.models import User
from ami_meeting_svc.models.base import get_db
from ami_meeting_svc.schemas.auth import Token, UserLogin, UserOut
from ami_meeting_svc.utils.security import (
    verify_password,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/login", response_model=Token)
async def login(login: UserLogin, response: Response, db: Session = Depends(get_db)) -> Token:
    try:
        stmt = select(User).where(User.username == login.username)
        user = db.execute(stmt).scalar_one_or_none()
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

    if user is None or not verify_password(login.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)

    # set cookie using configured secure flag
    max_age = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="Lax",
        max_age=max_age,
        path="/",
    )

    return Token(access_token=token)


@auth_router.post("/logout")
async def logout(response: Response) -> dict:
    # clear cookie
    response.delete_cookie("access_token", path="/")
    return {"message": "logged out"}


@auth_router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return current_user
