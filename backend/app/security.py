import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import Settings

ALGO = "HS256"
RESET_TTL_MINUTES = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


# A real bcrypt hash used to burn the same time when the email is unknown (blocks timing-based user discovery).
DUMMY_HASH = hash_password("not-a-real-password")


def _encode(settings: Settings, payload: dict, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({**payload, "iat": now, "exp": now + ttl}, settings.jwt_secret, algorithm=ALGO)


def _decode(settings: Settings, token: str, purpose: str) -> dict | None:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None
    return data if data.get("purpose", "access") == purpose else None


# ---- access tokens: { sub, role, exp } ----
def create_access_token(settings: Settings, user_id: str, role: str) -> str:
    return _encode(settings, {"sub": user_id, "role": role, "purpose": "access"}, timedelta(minutes=settings.jwt_expire_minutes))


def decode_access_token(settings: Settings, token: str) -> dict | None:
    return _decode(settings, token, "access")


# ---- password reset tokens: single use because they are bound to the current password hash ----
def _fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def create_reset_token(settings: Settings, user_id: str, password_hash: str) -> str:
    return _encode(settings, {"sub": user_id, "purpose": "reset", "fp": _fingerprint(password_hash)}, timedelta(minutes=RESET_TTL_MINUTES))


def decode_reset_token(settings: Settings, token: str) -> dict | None:
    return _decode(settings, token, "reset")


def reset_fingerprint_ok(claims: dict, password_hash: str) -> bool:
    return claims.get("fp") == _fingerprint(password_hash)


# ---- signed document links (default 10 minutes) ----
def create_doc_token(settings: Settings, doc_id: str, viewer_id: str) -> str:
    return _encode(settings, {"sub": doc_id, "uid": viewer_id, "purpose": "doc"}, timedelta(seconds=settings.doc_link_ttl_seconds))


def decode_doc_token(settings: Settings, token: str) -> dict | None:
    return _decode(settings, token, "doc")
