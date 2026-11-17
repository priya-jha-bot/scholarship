import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..constants import ADMIN, ADMIN_VISIBLE, APPROVED, DISBURSED, DRAFT, REJECTED, REJECTED_BY_ADMIN, SUBMITTED, VERIFIED
from ..crypto import FieldCipher
from ..deps import Page, get_cipher, get_db, get_mongo, require_role
from ..errors import ApiError
from ..models import Application, Scholarship, ScholarshipRound, User
from ..schemas import AdminCreateUserIn, VerifyIn
from ..security import hash_password
from ..services import applications as svc
from ..services.notifications import audit
from ..services.state_machine import lock_application, transition

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_role(ADMIN)
QUEUE = {SUBMITTED, VERIFIED}          # oldest first (fair queue); everything else newest first


@router.get("/applications")
def list_applications(status: str | None = Query(None), page: Page = Depends(), db: Session = Depends(get_db),
                      _: User = Depends(admin_only)):
    if status and status not in ADMIN_VISIBLE:
        raise ApiError(422, "Please fix the highlighted fields", {"status": "Unknown status"})
    where = [Application.status != DRAFT] + ([Application.status == status] if status else [])
    total = db.scalar(select(func.count()).select_from(Application).where(*where)) or 0
    order = Application.updated_at.asc() if status in QUEUE else Application.updated_at.desc()
    rows = db.execute(select(Application).where(*where).options(joinedload(Application.student), joinedload(Application.scholarship))
                      .order_by(order).offset(page.offset).limit(page.page_size)).scalars().all()
    return page.wrap([svc.summary(a) for a in rows], total)


@router.post("/applications/{app_id}/verify")
def verify(app_id: str, body: VerifyIn, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
           cipher: FieldCipher = Depends(get_cipher), admin: User = Depends(admin_only)):
    try:
        key = uuid.UUID(app_id)
    except ValueError:
        raise ApiError(404, "Application not found")
    app = lock_application(db, key)
    if not app or app.status == DRAFT:
        db.rollback()
        raise ApiError(404, "Application not found")
    if body.decision == VERIFIED and not all(body.checklist.values()):
        db.rollback()
        raise ApiError(422, "Tick every checklist item before verifying", {"checklist": "All items must be confirmed"})
    if body.decision == REJECTED_BY_ADMIN and not body.remarks:
        db.rollback()
        raise ApiError(422, "Please give a reason when rejecting", {"remarks": "Required"})
    transition(db, mongo, app, body.decision, admin, body.remarks, {"checklist": body.checklist})
    return svc.detail(svc.load(db, app.id), mongo, cipher, admin)


@router.post("/users", status_code=201)
def create_user(body: AdminCreateUserIn, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
                admin: User = Depends(admin_only)):
    email = body.email.lower()
    if db.execute(select(User.id).where(User.email == email)).first():
        raise ApiError(422, "Please fix the highlighted fields", {"email": "Email already registered"})
    user = User(full_name=body.full_name, email=email, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(422, "Please fix the highlighted fields", {"email": "Email already registered"})
    audit(mongo, admin.id, "user_created", "user", user.id, {"role": body.role})
    return {"ok": True}


@router.get("/reports/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """by_status: counts (drafts excluded).
    approval_rate: per scholarship and round = approved / decided, where
      approved = APPROVED + DISBURSED, decided = approved + REJECTED + REJECTED_BY_ADMIN (0 when nothing is decided yet)."""
    by_status = {s: n for s, n in db.execute(select(Application.status, func.count()).where(Application.status != DRAFT)
                                             .group_by(Application.status)).all()}
    rows = db.execute(select(Scholarship.title, ScholarshipRound.label, Application.status, func.count())
                      .join(Application, Application.scholarship_id == Scholarship.id)
                      .join(ScholarshipRound, Application.round_id == ScholarshipRound.id)
                      .where(Application.status.in_([APPROVED, DISBURSED, REJECTED, REJECTED_BY_ADMIN]))
                      .group_by(Scholarship.title, ScholarshipRound.label, Application.status)).all()
    tally: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for title, label, status, n in rows:
        t = tally[(title, label)]
        t[1] += n
        if status in (APPROVED, DISBURSED):
            t[0] += n
    # include scholarships/rounds with no decisions yet so the table is never confusingly empty
    for title, label in db.execute(select(Scholarship.title, ScholarshipRound.label).join(ScholarshipRound)).all():
        tally.setdefault((title, label), [0, 0])
    rates = [{"scholarship": t, "round": r, "rate": (a / d if d else 0.0)} for (t, r), (a, d) in sorted(tally.items())]
    return {"by_status": by_status, "approval_rate": rates}
