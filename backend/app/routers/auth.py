import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import Settings
from ..deps import RateLimiter, current_user, get_db, get_settings_dep
from ..errors import ApiError
from ..models import User
from ..schemas import ForgotIn, LoginIn, RegisterIn, ResetIn
from ..security import (DUMMY_HASH, create_access_token, create_reset_token, decode_reset_token, hash_password,
                        reset_fingerprint_ok, verify_password)
from ..services.mail import send_mail

router = APIRouter(prefix="/auth", tags=["auth"])
limit_login = RateLimiter(10, 60, "login")
limit_register = RateLimiter(10, 60, "register")
limit_forgot = RateLimiter(5, 60, "forgot")


def user_out(u: User) -> dict:
    return {"id": str(u.id), "full_name": u.full_name, "email": u.email, "role": u.role}


def find_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()


@router.post("/register", status_code=201, dependencies=[Depends(limit_register)])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """Public registration creates STUDENTS only. Reviewers/admins are created by an admin (POST /admin/users)."""
    email = body.email.lower()
    if find_by_email(db, email):
        raise ApiError(422, "Please fix the highlighted fields", {"email": "Email already registered"})
    db.add(User(id=uuid.uuid4(), full_name=body.full_name, email=email, password_hash=hash_password(body.password), role="student"))
    try:
        db.commit()
    except IntegrityError:       # two sign-ups with the same email at the same instant
        db.rollback()
        raise ApiError(422, "Please fix the highlighted fields", {"email": "Email already registered"})
    return {"ok": True}


@router.post("/login", dependencies=[Depends(limit_login)])
def login(body: LoginIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)):
    user = find_by_email(db, body.email)
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok or not user.is_active:
        raise ApiError(401, "Wrong email or password")
    return {"access_token": create_access_token(settings, str(user.id), user.role), "token_type": "bearer", "user": user_out(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


@router.post("/forgot-password", dependencies=[Depends(limit_forgot)])
def forgot_password(body: ForgotIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)):
    """Always answers ok, so the endpoint cannot be used to discover which emails are registered."""
    user = find_by_email(db, body.email)
    if user and user.is_active:
        token = create_reset_token(settings, str(user.id), user.password_hash)
        link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
        send_mail(settings, user.email, "Reset your Scholarship Portal password",
                  f"Hello {user.full_name},\n\nOpen this link to choose a new password (valid for 30 minutes):\n{link}\n\n"
                  "If you did not ask for this, ignore this email.")
    return {"ok": True}


@router.post("/reset-password", dependencies=[Depends(limit_forgot)])
def reset_password(body: ResetIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)):
    claims = decode_reset_token(settings, body.token)
    user = None
    if claims:
        try:
            user = db.get(User, uuid.UUID(claims["sub"]))
        except ValueError:
            user = None
    if not claims or not user or not user.is_active or not reset_fingerprint_ok(claims, user.password_hash):
        raise ApiError(400, "This reset link is invalid or has expired", code="invalid_reset_token")
    user.password_hash = hash_password(body.password)      # changes the fingerprint, so the link works only once
    db.commit()
    return {"ok": True}
