import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, Response, UploadFile
from pydantic import BaseModel
from pymongo.database import Database
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..config import Settings
from ..constants import ALLOWED_DOC_TYPES, DRAFT, EDITABLE_STATUSES, STUDENT, SUBMITTED, CHANGES_REQUESTED, WITHDRAWN
from ..crypto import FieldCipher, is_masked_account, is_masked_gov_id, mask_gov_id
from ..deps import Page, get_cipher, get_db, get_mongo, get_settings_dep, require_role, current_user
from ..errors import ApiError
from ..models import Application, BankDetail, Document, Scholarship, StatusHistory, User, now
from ..schemas import AddressIn, BankIn, InstitutionIn, ProfileIn, SubmitIn
from ..services import applications as svc
from ..services import storage
from ..services.document_check import run_document_check
from ..services.notifications import audit
from ..services.state_machine import lock_application, transition

router = APIRouter(prefix="/applications", tags=["applications"])
student_only = require_role(STUDENT)


class CreateIn(BaseModel):
    scholarship_id: str


def parse_id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ApiError(404, "Application not found")


def owned_locked(db: Session, user: User, app_id: str) -> Application:
    app = lock_application(db, parse_id(app_id))
    if not app or app.student_id != user.id:
        db.rollback()
        raise ApiError(404, "Application not found")
    return app


def editable(db: Session, app: Application) -> None:
    if app.status not in EDITABLE_STATUSES:
        db.rollback()
        raise ApiError(409, "This application can no longer be edited", code="not_editable")


# ---------------------------------------------------------------- create / list / read
@router.post("", status_code=201)
def create(body: CreateIn, response: Response, db: Session = Depends(get_db), user: User = Depends(student_only)):
    """Returns the student's existing application for this scholarship if there is one (so the wizard can resume)."""
    try:
        sch = db.get(Scholarship, uuid.UUID(body.scholarship_id))
    except ValueError:
        sch = None
    if not sch:
        raise ApiError(404, "Scholarship not found")

    rnd = svc.current_round(sch)
    mine = db.execute(select(Application).where(Application.student_id == user.id, Application.scholarship_id == sch.id)
                      .order_by(Application.created_at.desc())).scalars().all()
    existing = next((a for a in mine if rnd and a.round_id == rnd.id), None) or (mine[0] if mine and not rnd else None)
    if existing:
        response.status_code = 200
        return {"id": str(existing.id)}
    if not rnd:
        raise ApiError(409, "Applications are closed for this scholarship", code="closed")

    app = Application(student_id=user.id, scholarship_id=sch.id, round_id=rnd.id, status=DRAFT)
    app.history.append(StatusHistory(status=DRAFT, remarks="Draft created", actor_id=user.id))
    db.add(app)
    try:
        db.commit()
    except IntegrityError:           # double click: the other request created it first
        db.rollback()
        again = db.execute(select(Application).where(Application.student_id == user.id, Application.round_id == rnd.id,
                                                     Application.scholarship_id == sch.id)).scalar_one()
        response.status_code = 200
        return {"id": str(again.id)}
    return {"id": str(app.id)}


@router.get("/mine")
def mine(page: Page = Depends(), db: Session = Depends(get_db), user: User = Depends(student_only)):
    where = (Application.student_id == user.id, Application.status != DRAFT)
    total = db.scalar(select(func.count()).select_from(Application).where(*where)) or 0
    rows = db.execute(select(Application).where(*where).options(joinedload(Application.student), joinedload(Application.scholarship))
                      .order_by(Application.created_at.desc()).offset(page.offset).limit(page.page_size)).scalars().all()
    return page.wrap([svc.summary(a) for a in rows], total)


@router.get("/{app_id}")
def read(app_id: str, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
         cipher: FieldCipher = Depends(get_cipher), user: User = Depends(current_user)):
    app = svc.get_viewable(db, user, parse_id(app_id))
    return svc.detail(app, mongo, cipher, user)


# ---------------------------------------------------------------- sections
def _save_mongo_section(mongo: Database, app: Application, name: str, data: dict) -> dict:
    mongo.application_forms.update_one({"_id": str(app.id)}, {"$set": {name: data, "updated_at": now().isoformat()}}, upsert=True)
    return data


def _stored_section(mongo: Database, app: Application, name: str) -> dict:
    return ((mongo.application_forms.find_one({"_id": str(app.id)}) or {}).get(name)) or {}


@router.put("/{app_id}/profile")
def put_profile(app_id: str, body: ProfileIn, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
                user: User = Depends(student_only)):
    app = owned_locked(db, user, app_id)
    editable(db, app)
    data = body.model_dump(mode="json")
    gid = data["government_id_number"]
    if is_masked_gov_id(gid):                        # the form echoes the masked value back: keep what we stored
        old = _stored_section(mongo, app, "profile").get("government_id_number")
        if old != gid:
            db.rollback()
            raise ApiError(422, "Please fix the highlighted fields", {"government_id_number": "Enter the full ID number"})
    else:
        data["government_id_number"] = mask_gov_id(gid)     # the full number is never stored
    out = _save_mongo_section(mongo, app, "profile", data)
    app.updated_at = now()
    db.commit()
    return out


@router.put("/{app_id}/institution")
def put_institution(app_id: str, body: InstitutionIn, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
                    user: User = Depends(student_only)):
    app = owned_locked(db, user, app_id)
    editable(db, app)
    out = _save_mongo_section(mongo, app, "institution", body.model_dump(mode="json", exclude_none=True))
    app.updated_at = now()
    db.commit()
    return out


@router.put("/{app_id}/address")
def put_address(app_id: str, body: AddressIn, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
                user: User = Depends(student_only)):
    app = owned_locked(db, user, app_id)
    editable(db, app)
    out = _save_mongo_section(mongo, app, "address", body.model_dump(mode="json"))
    app.updated_at = now()
    db.commit()
    return out


@router.put("/{app_id}/bank")
def put_bank(app_id: str, body: BankIn, db: Session = Depends(get_db), cipher: FieldCipher = Depends(get_cipher),
             user: User = Depends(student_only)):
    app = owned_locked(db, user, app_id)
    editable(db, app)
    bank = app.bank
    if is_masked_account(body.account_number):       # unchanged account number echoed back from the form
        if not bank or bank.account_last4 != body.account_number[-4:]:
            db.rollback()
            raise ApiError(422, "Please fix the highlighted fields", {"account_number": "Enter the full account number"})
        number_enc, last4 = bank.account_number_enc, bank.account_last4
    else:
        number_enc, last4 = cipher.encrypt(body.account_number), body.account_number[-4:]
    if not bank:
        bank = BankDetail(application_id=app.id)
        db.add(bank)
        app.bank = bank
    bank.account_holder_name, bank.account_number_enc, bank.account_last4 = body.account_holder_name, number_enc, last4
    bank.ifsc_enc, bank.updated_at = cipher.encrypt(body.ifsc), now()
    app.updated_at = now()
    db.commit()
    return svc.bank_view(app, cipher, user)


# ---------------------------------------------------------------- documents
@router.post("/{app_id}/documents", status_code=201)
def upload_document(app_id: str, background: BackgroundTasks, request: Request, file: UploadFile = File(...),
                    doc_type: str = Form(...), db: Session = Depends(get_db), user: User = Depends(student_only),
                    settings: Settings = Depends(get_settings_dep)):
    if doc_type not in ALLOWED_DOC_TYPES:
        raise ApiError(422, "Please fix the highlighted fields", {"doc_type": "Unknown document type"})
    pre = db.get(Application, parse_id(app_id))                 # cheap check BEFORE reading a big file
    if not pre or pre.student_id != user.id:
        raise ApiError(404, "Application not found")
    if pre.status not in EDITABLE_STATUSES:
        raise ApiError(409, "This application can no longer be edited", code="not_editable")

    stored = storage.save_upload(settings.upload_dir, str(pre.id), file, settings.max_upload_mb * 1024 * 1024)
    try:
        app = owned_locked(db, user, app_id)
        editable(db, app)
        old = db.execute(select(Document).where(Document.application_id == app.id, Document.doc_type == doc_type)).scalar_one_or_none()
        old_path = old.stored_path if old else None
        if old:
            db.delete(old)
            db.flush()
        doc = Document(application_id=app.id, doc_type=doc_type, filename=storage.clean_filename(file.filename),
                       stored_path=stored.rel_path, content_type=stored.mime, size_bytes=stored.size, sha256=stored.sha256)
        db.add(doc)
        app.updated_at = now()
        db.commit()
    except Exception:
        db.rollback()
        storage.remove(settings.upload_dir, stored.rel_path)
        raise
    if old_path:
        storage.remove(settings.upload_dir, old_path)
    background.add_task(run_document_check, str(doc.id), request.app.state.session_factory, request.app.state.mongo, settings.upload_dir)
    return {"id": str(doc.id), "doc_type": doc.doc_type, "filename": doc.filename}


# ---------------------------------------------------------------- submit / resubmit / withdraw
def _respond(db: Session, mongo: Database, cipher: FieldCipher, user: User, app_id) -> dict:
    return svc.detail(svc.load(db, app_id), mongo, cipher, user)


@router.post("/{app_id}/submit")
def submit(app_id: str, body: SubmitIn | None = None, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
           cipher: FieldCipher = Depends(get_cipher), user: User = Depends(student_only)):
    app = owned_locked(db, user, app_id)
    if app.status != DRAFT:
        db.rollback()
        raise ApiError(409, "This application has already been submitted", code="already_submitted")
    if not (body and body.declaration_accepted):
        db.rollback()
        raise ApiError(422, "You must accept the declaration before submitting", {"declaration_accepted": "Required"})
    if app.round.closes_on < date.today():
        db.rollback()
        raise ApiError(409, "The deadline for this scholarship has passed", code="closed")
    if err := svc.completeness_error(app, mongo):
        db.rollback()
        raise err
    app.declaration_accepted_at = now()
    transition(db, mongo, app, SUBMITTED, user, "Application submitted")
    return _respond(db, mongo, cipher, user, app.id)


@router.post("/{app_id}/resubmit")
def resubmit(app_id: str, body: SubmitIn | None = None, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
             cipher: FieldCipher = Depends(get_cipher), user: User = Depends(student_only)):
    app = owned_locked(db, user, app_id)
    if app.status != CHANGES_REQUESTED:
        db.rollback()
        raise ApiError(409, "Only applications with requested changes can be resubmitted", code="illegal_status_change")
    if err := svc.completeness_error(app, mongo):
        db.rollback()
        raise err
    if body and body.declaration_accepted:
        app.declaration_accepted_at = now()
    transition(db, mongo, app, SUBMITTED, user, "Application resubmitted after requested changes")
    return _respond(db, mongo, cipher, user, app.id)


@router.post("/{app_id}/withdraw")
def withdraw(app_id: str, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
             cipher: FieldCipher = Depends(get_cipher), user: User = Depends(student_only)):
    app = owned_locked(db, user, app_id)
    transition(db, mongo, app, WITHDRAWN, user, "Withdrawn by the student")
    return _respond(db, mongo, cipher, user, app.id)
