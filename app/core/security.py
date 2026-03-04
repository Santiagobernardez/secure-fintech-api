"""
core/security.py

All cryptographic operations live here and nowhere else.
This single-responsibility design means security auditors only need
to review one file to assess the auth implementation.

Password hashing: bcrypt via passlib (industry standard, adaptive cost factor).
JWT: HS256 signing via python-jose. Tokens contain only the user's email (subject)
     and an expiry claim — no sensitive data in the payload.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# bcrypt cost factor is handled automatically by passlib.
# CryptContext also supports transparent scheme upgrades in the future.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password Utilities ────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Constant-time comparison between plain and hashed passwords.
    Returns True if they match, False otherwise.
    Uses passlib's built-in timing-attack protection.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Utilities ─────────────────────────────────────────

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: The user identifier to embed in the token (typically email).
        expires_delta: Optional custom expiry. Defaults to settings value.

    Returns:
        Signed JWT string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,    # Subject — who this token represents
        "exp": expire,     # Expiry — token is invalid after this timestamp
        "iat": datetime.now(timezone.utc),  # Issued-at — for audit trail
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """
    Decode and validate a JWT token.

    Returns the subject (email) if the token is valid and not expired.
    Returns None if the token is invalid — callers must handle this case.

    Logs validation failures for security monitoring (SIEM ingestion).
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        subject: str = payload.get("sub")
        if subject is None:
            logger.warning("JWT decode failed: missing 'sub' claim")
            return None
        return subject
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", str(exc))
        return None
