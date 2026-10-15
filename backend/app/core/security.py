"""Security utilities: JWT, secret hashing, pairing codes."""

import secrets
import string
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

import hashlib
import hmac

def hash_secret(secret: str) -> str:
    """Hash a device secret using PBKDF2-HMAC-SHA256 with unique salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}:{key.hex()}"


def verify_secret(plain: str, hashed: str) -> bool:
    """Verify secret against PBKDF2-HMAC-SHA256 hash using constant-time comparison."""
    try:
        salt, key_hex = hashed.split(":", 1)
        key = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Pairing codes
# ---------------------------------------------------------------------------

def generate_pairing_code(length: int = 6) -> str:
    """Generate a short, human-readable numeric pairing code."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def generate_device_secret(length: int = 32) -> str:
    """Generate a cryptographically random device secret."""
    return secrets.token_urlsafe(length)


def generate_device_id() -> str:
    """Generate a UUID-based device ID."""
    import uuid
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_session_token(device_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": device_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "session",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_session_token(token: str) -> Optional[str]:
    """Return device_id if token is valid, else None."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload.get("sub")
    except JWTError:
        return None


def create_controller_token() -> str:
    """Create a short-lived controller session token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": "controller",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "controller",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_controller_token(token: str) -> bool:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload.get("type") == "controller"
    except JWTError:
        return False
