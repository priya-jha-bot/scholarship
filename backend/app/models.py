"""PostgreSQL = system of record. (Flexible form sections, notifications and audit logs live in MongoDB.)"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, MetaData, String, Text,
                        UniqueConstraint, Uuid)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .constants import ROLES, STATUSES

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def now() -> datetime:
    return datetime.now(timezone.utc)


def _in(col: str, values) -> str:
    return f"{col} IN ({', '.join(repr(v) for v in values)})"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)          # always stored lower-case
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint(_in("role", ROLES), name="role_valid"),)


class Scholarship(Base):
    __tablename__ = "scholarships"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[int] = mapped_column(Integer)                           # whole rupees
    deadline: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    rounds: Mapped[list["ScholarshipRound"]] = relationship(back_populates="scholarship", cascade="all, delete-orphan",
                                                            order_by="ScholarshipRound.opens_on")
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)


class ScholarshipRound(Base):
    __tablename__ = "scholarship_rounds"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scholarship_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scholarships.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(40))
    opens_on: Mapped[date] = mapped_column(Date)
    closes_on: Mapped[date] = mapped_column(Date)
    scholarship: Mapped[Scholarship] = relationship(back_populates="rounds")
    __table_args__ = (UniqueConstraint("scholarship_id", "label"), Index("ix_rounds_scholarship", "scholarship_id"))


class Application(Base):
    __tablename__ = "applications"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    scholarship_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scholarships.id"))
    round_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scholarship_rounds.id"))
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")
    declaration_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    student: Mapped[User] = relationship()
    scholarship: Mapped[Scholarship] = relationship()
    round: Mapped[ScholarshipRound] = relationship()
    documents: Mapped[list["Document"]] = relationship(back_populates="application", cascade="all, delete-orphan",
                                                       order_by="Document.uploaded_at")
    history: Mapped[list["StatusHistory"]] = relationship(back_populates="application", cascade="all, delete-orphan",
                                                          order_by="StatusHistory.id")
    bank: Mapped["BankDetail | None"] = relationship(back_populates="application", cascade="all, delete-orphan",
                                                     uselist=False)
    __table_args__ = (
        CheckConstraint(_in("status", STATUSES), name="status_valid"),
        UniqueConstraint("student_id", "scholarship_id", "round_id", name="uq_one_application_per_round"),
        Index("ix_applications_status", "status"),
        Index("ix_applications_student", "student_id"),
    )


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    doc_type: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(160))                    # display name only
    stored_path: Mapped[str] = mapped_column(String(300))                 # relative to UPLOAD_DIR, server generated
    content_type: Mapped[str] = mapped_column(String(60))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    check_status: Mapped[str] = mapped_column(String(10), default="pending")   # pending | ok | flagged
    check_note: Mapped[str] = mapped_column(String(200), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    application: Mapped[Application] = relationship(back_populates="documents")
    __table_args__ = (UniqueConstraint("application_id", "doc_type"), Index("ix_documents_sha256", "sha256"),
                      CheckConstraint(_in("check_status", ("pending", "ok", "flagged")), name="check_status_valid"))


class BankDetail(Base):
    __tablename__ = "bank_details"
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True)
    account_holder_name: Mapped[str] = mapped_column(String(120))
    account_number_enc: Mapped[str] = mapped_column(Text)                 # Fernet token
    ifsc_enc: Mapped[str] = mapped_column(Text)                           # Fernet token
    account_last4: Mapped[str] = mapped_column(String(4))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    application: Mapped[Application] = relationship(back_populates="bank")


class ReviewScore(Base):
    __tablename__ = "review_scores"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    academic: Mapped[int] = mapped_column(Integer)
    financial_need: Mapped[int] = mapped_column(Integer)
    other: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(24))
    remarks: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        CheckConstraint("academic BETWEEN 0 AND 40", name="academic_range"),
        CheckConstraint("financial_need BETWEEN 0 AND 40", name="need_range"),
        CheckConstraint("other BETWEEN 0 AND 20", name="other_range"),
        Index("ix_review_scores_application", "application_id"),
    )


class StatusHistory(Base):
    """Audit trail of every status the application has been in (timeline on the student page)."""
    __tablename__ = "status_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(24))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    remarks: Mapped[str] = mapped_column(Text, default="")
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    application: Mapped[Application] = relationship(back_populates="history")
    __table_args__ = (CheckConstraint(_in("status", STATUSES), name="status_valid"),
                      Index("ix_status_history_application", "application_id"))


class Disbursement(Base):
    """Table only for now: the payment step after APPROVED (no endpoint in the current contract)."""
    __tablename__ = "disbursements"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str] = mapped_column(String(80), default="")
    disbursed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
