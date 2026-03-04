"""
api/v1/endpoints/auth.py

Authentication endpoints: user registration and login.

Security events logged here feed into any SIEM or log aggregator
(CloudWatch, Datadog, Loki) used in the DevSecOps pipeline.
Every login attempt — success or failure — produces a structured log entry.
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """
    Create a new user account.
    Returns the user object (without password hash).
    Rejects duplicate emails with HTTP 409.
    """
    # Check for existing email before attempting insert
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info("New user registered: %s", payload.email)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and receive a JWT access token",
)
async def login(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> Token:
    """
    Validate credentials and return a JWT access token.

    Logs both successful and failed attempts for security monitoring.
    Uses a generic error message on failure to prevent user enumeration attacks.
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Deliberate: same error for "user not found" and "wrong password"
    # This prevents attackers from discovering valid email addresses.
    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning(
            "SECURITY: Failed login attempt for email=%s", payload.email
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(
            "SECURITY: Login attempt on disabled account email=%s", payload.email
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    access_token = create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    logger.info("Successful login: email=%s", payload.email)
    return Token(access_token=access_token)
