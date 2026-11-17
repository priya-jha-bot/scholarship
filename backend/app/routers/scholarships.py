import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import ADMIN
from ..deps import Page, get_db, require_role
from ..errors import ApiError
from ..models import Application, Scholarship, ScholarshipRound, User
from ..schemas import ScholarshipIn

router = APIRouter(prefix="/scholarships", tags=["scholarships"])


def out(s: Scholarship) -> dict:
    return {"id": str(s.id), "title": s.title, "description": s.description, "amount": s.amount, "deadline": s.deadline.isoformat()}


def get_or_404(db: Session, sid: str) -> Scholarship:
    try:
        s = db.get(Scholarship, uuid.UUID(sid))
    except ValueError:
        s = None
    if not s:
        raise ApiError(404, "Scholarship not found")
    return s


@router.get("")
def list_scholarships(page: Page = Depends(), db: Session = Depends(get_db)):
    """Public (the home page shows it). Soonest deadline first."""
    total = db.scalar(select(func.count()).select_from(Scholarship)) or 0
    rows = db.execute(select(Scholarship).order_by(Scholarship.deadline, Scholarship.title).offset(page.offset).limit(page.page_size)).scalars()
    return page.wrap([out(s) for s in rows], total)


@router.get("/{sid}")
def get_scholarship(sid: str, db: Session = Depends(get_db)):
    return out(get_or_404(db, sid))


@router.post("", status_code=201)
def create(body: ScholarshipIn, db: Session = Depends(get_db), _: User = Depends(require_role(ADMIN))):
    s = Scholarship(title=body.title, description=body.description, amount=body.amount, deadline=body.deadline)
    s.rounds.append(ScholarshipRound(label=str(body.deadline.year), opens_on=date.today(), closes_on=body.deadline))
    db.add(s)
    db.commit()
    return out(s)


@router.put("/{sid}")
def update(sid: str, body: ScholarshipIn, db: Session = Depends(get_db), _: User = Depends(require_role(ADMIN))):
    s = get_or_404(db, sid)
    s.title, s.description, s.amount, s.deadline = body.title, body.description, body.amount, body.deadline
    if s.rounds:                             # keep the latest round in step with the deadline
        s.rounds[-1].closes_on = body.deadline
    db.commit()
    return out(s)


@router.delete("/{sid}")
def delete(sid: str, db: Session = Depends(get_db), _: User = Depends(require_role(ADMIN))):
    s = get_or_404(db, sid)
    if db.scalar(select(func.count()).select_from(Application).where(Application.scholarship_id == s.id)):
        raise ApiError(409, "This scholarship already has applications and cannot be deleted", code="has_applications")
    db.delete(s)
    db.commit()
    return {"ok": True}
