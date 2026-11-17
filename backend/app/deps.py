import time
import uuid
from collections import defaultdict, deque
from typing import Iterator

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.database import Database
from sqlalchemy.orm import Session

from .config import Settings
from .crypto import FieldCipher
from .errors import ApiError
from .models import User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_cipher(request: Request) -> FieldCipher:
    return request.app.state.cipher


def get_mongo(request: Request) -> Database:
    return request.app.state.mongo


def get_db(request: Request) -> Iterator[Session]:
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def user_from_token(db: Session, settings: Settings, token: str | None) -> User | None:
    claims = decode_access_token(settings, token) if token else None
    if not claims:
        return None
    try:
        user = db.get(User, uuid.UUID(claims["sub"]))
    except ValueError:
        return None
    return user if user and user.is_active else None      # role always comes from the DB, never from the token


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db),
                 settings: Settings = Depends(get_settings_dep)) -> User:
    user = user_from_token(db, settings, creds.credentials if creds else None)
    if not user:
        raise ApiError(401, "Please log in again")
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise ApiError(403, "Not allowed")
        return user
    return dep


class Page:
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
        self.page, self.page_size = page, page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def wrap(self, items: list, total: int) -> dict:
        return {"items": items, "total": total, "page": self.page, "page_size": self.page_size}


class RateLimiter:
    """Small in-memory sliding window per client IP (single process). Use a shared store if you run many workers."""

    def __init__(self, limit: int, window_seconds: int, name: str):
        self.limit, self.window, self.name = limit, window_seconds, name
        self.hits: dict[str, deque] = defaultdict(deque)

    def __call__(self, request: Request) -> None:
        if not request.app.state.settings.rate_limit_enabled:
            return
        key = f"{self.name}:{request.client.host if request.client else 'unknown'}"
        q, now = self.hits[key], time.monotonic()
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            raise ApiError(429, "Too many attempts. Please wait a minute and try again.", code="rate_limited")
        q.append(now)
