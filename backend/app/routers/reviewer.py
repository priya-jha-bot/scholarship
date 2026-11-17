import uuid

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..constants import CHANGES_REQUESTED, REVIEWER, REVIEWER_VISIBLE, VERIFIED
from ..crypto import FieldCipher
from ..deps import Page, get_cipher, get_db, get_mongo, require_role
from ..errors import ApiError
from ..models import Application, ReviewScore, User
from ..schemas import ReviewIn
from ..services import applications as svc
from ..services.state_machine import lock_application, transition

router = APIRouter(prefix="/reviewer", tags=["reviewer"])
reviewer_only = require_role(REVIEWER)


@router.get("/applications")
def list_applications(status: str = Query(VERIFIED), page: Page = Depends(), db: Session = Depends(get_db),
                      _: User = Depends(reviewer_only)):
    """Default = the pending pool (VERIFIED). Other statuses are the review history."""
    if status not in REVIEWER_VISIBLE:
        raise ApiError(422, "Please fix the highlighted fields", {"status": "Unknown status"})
    total = db.scalar(select(func.count()).select_from(Application).where(Application.status == status)) or 0
    order = Application.updated_at.asc() if status == VERIFIED else Application.updated_at.desc()
    rows = db.execute(select(Application).where(Application.status == status)
                      .options(joinedload(Application.student), joinedload(Application.scholarship))
                      .order_by(order).offset(page.offset).limit(page.page_size)).scalars().all()
    return page.wrap([svc.summary(a) for a in rows], total)


@router.post("/applications/{app_id}/review")
def review(app_id: str, body: ReviewIn, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
           cipher: FieldCipher = Depends(get_cipher), reviewer: User = Depends(reviewer_only)):
    try:
        key = uuid.UUID(app_id)
    except ValueError:
        raise ApiError(404, "Application not found")
    app = lock_application(db, key)
    if not app or app.status not in REVIEWER_VISIBLE:
        db.rollback()
        raise ApiError(404, "Application not found")
    if app.status != VERIFIED:
        db.rollback()
        raise ApiError(409, "Illegal status change", code="illegal_status_change")
    if body.decision == CHANGES_REQUESTED and not body.remarks:
        db.rollback()
        raise ApiError(422, "Tell the student what to change", {"remarks": "Required when requesting changes"})

    s = body.scores
    db.add(ReviewScore(application_id=app.id, reviewer_id=reviewer.id, academic=s.academic, financial_need=s.financial_need,
                       other=s.other, total=s.academic + s.financial_need + s.other, decision=body.decision, remarks=body.remarks))
    # transition() commits the score row and the status change together
    transition(db, mongo, app, body.decision, reviewer, body.remarks, {"total_score": s.academic + s.financial_need + s.other})
    return svc.detail(svc.load(db, app.id), mongo, cipher, reviewer)
