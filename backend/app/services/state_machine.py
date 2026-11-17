"""The ONLY code allowed to change Application.status.

transition() validates the move, writes status_history, commits, then (after the commit) writes the audit log
and notifications. Callers must add any other DB changes (e.g. a ReviewScore row) to the session BEFORE calling it,
so everything lands in one transaction.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from pymongo.database import Database

from ..constants import ADMIN, REVIEWER, SUBMITTED, TRANSITIONS, VERIFIED
from ..errors import ApiError
from ..models import Application, StatusHistory, User, now
from .notifications import audit, notify


def pretty(status: str) -> str:
    return status.replace("_", " ").title()


def lock_application(db: Session, application_id) -> Application | None:
    """Load an application with a row lock so two clicks / two reviewers cannot both win (no-op on SQLite)."""
    return db.execute(select(Application).where(Application.id == application_id).with_for_update()).scalar_one_or_none()


def transition(db: Session, mongo: Database, app: Application, new_status: str, actor: User,
               remarks: str = "", data: dict | None = None) -> Application:
    if new_status not in TRANSITIONS.get(app.status, set()):
        db.rollback()
        raise ApiError(409, "Illegal status change", code="illegal_status_change")

    old = app.status
    app.status = new_status
    app.updated_at = now()
    db.add(StatusHistory(application_id=app.id, status=new_status, remarks=remarks or "", actor_id=actor.id))
    db.commit()

    audit(mongo, actor.id, "status_change", "application", app.id, {"from": old, "to": new_status, "remarks": remarks, **(data or {})})
    title = app.scholarship.title
    notify(mongo, app.student_id, f"Your application for {title} is now {pretty(new_status)}.")
    if new_status == SUBMITTED:
        for admin_id in db.execute(select(User.id).where(User.role == ADMIN, User.is_active)).scalars():
            notify(mongo, admin_id, f"New application from {app.student.full_name} for {title} is waiting for verification.")
    elif new_status == VERIFIED:
        for rid in db.execute(select(User.id).where(User.role == REVIEWER, User.is_active)).scalars():
            notify(mongo, rid, f"{app.student.full_name}'s application for {title} is ready for review.")
    return app
