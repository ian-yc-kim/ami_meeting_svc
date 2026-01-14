from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ami_meeting_svc.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from ami_meeting_svc.models import User
from ami_meeting_svc.models.base import get_db

logger = logging.getLogger(__name__)

# Use passlib CryptContext with bcrypt_sha256. passlib handles pre-hashing.
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password.

    Uses passlib CryptContext directly. Returns False on any verification error.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error("Password verification failed: %s", e, exc_info=True)
        return False


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using passlib (bcrypt_sha256 scheme).

    Rely on passlib's bcrypt_sha256 to handle bcrypt's internal limits and security.
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error("Failed to hash password: %s", e, exc_info=True)
        raise


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    try:
        to_encode = data.copy()
        now = datetime.now(tz=timezone.utc)
        if expires_delta is None:
            expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = now + expires_delta
        # Use timezone-aware datetimes for iat/exp
        to_encode.update({"exp": expire, "iat": now})
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return token
    except Exception as e:
        logger.error("Failed to create access token: %s", e, exc_info=True)
        raise


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    try:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError as e:
            logger.error("Token expired: %s", e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.error("Invalid token: %s", e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to validate token: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    try:
        user_id = int(sub)
    except (TypeError, ValueError) as e:
        logger.error("Invalid user id in token payload: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user id in token")

    try:
        user = db.get(User, user_id)
    except Exception as e:
        logger.error("Database error fetching user: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to fetch user")

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
