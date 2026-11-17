"""Building API responses for applications, and the access rules for who may see what."""
from datetime import date

from pymongo.database import Database
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..constants import (ADMIN, ADMIN_VISIBLE, REQUIRED_DOCS, REVIEWER, REVIEWER_VISIBLE, SENSITIVE_DOC_TYPES, STUDENT)
from ..crypto import FieldCipher, mask_account
from ..errors import ApiError
from ..models import Application, Document, User
from ..schemas import AddressIn, InstitutionIn, ProfileIn

SECTIONS = ("profile", "institution", "address")     # stored in MongoDB; "bank" is in PostgreSQL (encrypted)


def load(db: Session, application_id) -> Application | None:
    return db.execute(
        select(Application).where(Application.id == application_id)
        .options(joinedload(Application.student), joinedload(Application.scholarship),
                 joinedload(Application.documents), joinedload(Application.history), joinedload(Application.bank))
        .execution_options(populate_existing=True)       # always reflect the database, never a stale loaded collection
    ).unique().scalar_one_or_none()


def can_view(user: User, app: Application) -> bool:
    if user.role == STUDENT:
        return app.student_id == user.id
    if user.role == ADMIN:
        return app.status in ADMIN_VISIBLE
    if user.role == REVIEWER:
        return app.status in REVIEWER_VISIBLE
    return False


def get_viewable(db: Session, user: User, application_id) -> Application:
    """404 (not 403) when you may not see it, so ids cannot be probed."""
    app = None
    try:
        app = load(db, application_id)
    except Exception:
        db.rollback()
    if not app or not can_view(user, app):
        raise ApiError(404, "Application not found")
    return app


def visible_docs(user: User, app: Application) -> list[Document]:
    docs = list(app.documents)
    if user.role == REVIEWER:
        docs = [d for d in docs if d.doc_type not in SENSITIVE_DOC_TYPES]
    return docs


def summary(app: Application) -> dict:
    return {
        "id": str(app.id), "student_id": str(app.student_id), "student_name": app.student.full_name,
        "scholarship_id": str(app.scholarship_id), "scholarship_title": app.scholarship.title,
        "status": app.status, "created_at": app.created_at.isoformat(), "updated_at": app.updated_at.isoformat(),
    }


def bank_view(app: Application, cipher: FieldCipher, viewer: User) -> dict:
    b = app.bank
    if not b or viewer.role == REVIEWER:        # reviewers never see bank details
        return {}
    return {"account_holder_name": b.account_holder_name, "account_number": mask_account(b.account_last4),
            "ifsc": cipher.decrypt(b.ifsc_enc)}


def detail(app: Application, mongo: Database, cipher: FieldCipher, viewer: User) -> dict:
    form = mongo.application_forms.find_one({"_id": str(app.id)}) or {}
    return {
        **summary(app),
        "profile": form.get("profile", {}),
        "institution": form.get("institution", {}),
        "address": form.get("address", {}),
        "bank": bank_view(app, cipher, viewer),
        "documents": [{"id": str(d.id), "doc_type": d.doc_type, "filename": d.filename, "check_status": d.check_status}
                      for d in visible_docs(viewer, app)],
        "history": [{"status": h.status, "at": h.at.isoformat(), "remarks": h.remarks or ""} for h in app.history],
    }


def completeness_error(app: Application, mongo: Database) -> ApiError | None:
    """What is still missing before an application can be (re)submitted."""
    form = mongo.application_forms.find_one({"_id": str(app.id)}) or {}
    todo = []
    for name, model in (("profile", ProfileIn), ("institution", InstitutionIn), ("address", AddressIn)):
        data = form.get(name) or {}
        missing = [f for f, info in model.model_fields.items() if info.is_required() and not data.get(f)]
        if missing:
            todo.append(name)
    if not app.bank:
        todo.append("bank")
    if todo:
        return ApiError(422, f"Please complete: {', '.join(todo)}", {s: "Incomplete" for s in todo}, code="incomplete_application")
    have = {d.doc_type for d in app.documents}
    missing_docs = [t for t in REQUIRED_DOCS if t not in have]
    if missing_docs:
        return ApiError(422, f"Missing documents: {', '.join(missing_docs)}", code="missing_documents")
    return None


def current_round(scholarship) -> "ScholarshipRound | None":      # noqa: F821
    today = date.today()
    open_rounds = [r for r in scholarship.rounds if r.opens_on <= today <= r.closes_on]
    return open_rounds[-1] if open_rounds else None
