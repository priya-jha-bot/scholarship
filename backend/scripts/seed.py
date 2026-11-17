"""Development seed data (same story as the frontend mock): 1 admin, 1 reviewer, 3 students, 3 scholarships, 6 applications.

    python -m scripts.seed

Refuses to run unless ENV=dev. All seeded accounts use the password  password123  (development only!).
"""
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.constants import (APPROVED, CHANGES_REQUESTED, DRAFT, REJECTED, SUBMITTED, VERIFIED)
from app.crypto import FieldCipher, mask_gov_id
from app.db.mongo import init_mongo, make_mongo
from app.db.postgres import make_engine, make_session_factory
from app.models import (Application, BankDetail, Document, ReviewScore, Scholarship, ScholarshipRound, StatusHistory, User)
from app.security import hash_password
from app.services.notifications import notify

PASSWORD = "password123"
DEMO_USERS = [
    ("admin@example.com", "Asha Admin", "admin"), ("reviewer@example.com", "Rahul Reviewer", "reviewer"),
    ("student@example.com", "Sara Student", "student"), ("tara@example.com", "Tara Student", "student"),
    ("uma@example.com", "Uma Student", "student"),
]


def tiny_pdf(text: str) -> bytes:
    return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 360 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 70>>stream\nBT /F1 14 Tf 20 100 Td (" + text.encode()[:60] + b") Tj ET\nendstream\nendobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\ntrailer<</Root 1 0 R/Size 6>>\n%%EOF\n")


def seed(session_factory, mongo, cipher: FieldCipher, upload_dir: str) -> dict:
    db = session_factory()
    if db.execute(select(User.id).limit(1)).first():
        raise SystemExit("Database is not empty. Run `python -m scripts.reset` first.")
    pw = hash_password(PASSWORD)
    users = {e: User(full_name=n, email=e, password_hash=pw, role=r) for e, n, r in DEMO_USERS}
    db.add_all(users.values())

    today = date.today()
    sch = {}
    for key, title, desc, amount, days in (
        ("s1", "Merit Excellence Award", "For top performers", 50000, 45),
        ("s2", "Need-Based Support Grant", "For families with limited income", 30000, 60),
        ("s3", "STEM Women Scholarship", "Supporting women in STEM", 40000, 75),
    ):
        d = today + timedelta(days=days)
        s = Scholarship(title=title, description=desc, amount=amount, deadline=d)
        s.rounds.append(ScholarshipRound(label=str(d.year), opens_on=today - timedelta(days=30), closes_on=d))
        sch[key] = s
        db.add(s)
    db.flush()

    plan = [("student@example.com", "s1", SUBMITTED), ("student@example.com", "s2", VERIFIED),
            ("student@example.com", "s3", CHANGES_REQUESTED), ("tara@example.com", "s1", APPROVED),
            ("tara@example.com", "s2", DRAFT), ("uma@example.com", "s2", REJECTED)]
    path_of_status = {SUBMITTED: [DRAFT, SUBMITTED], VERIFIED: [DRAFT, SUBMITTED, VERIFIED],
                      CHANGES_REQUESTED: [DRAFT, SUBMITTED, VERIFIED, CHANGES_REQUESTED],
                      APPROVED: [DRAFT, SUBMITTED, VERIFIED, APPROVED], REJECTED: [DRAFT, SUBMITTED, VERIFIED, REJECTED], DRAFT: [DRAFT]}
    admin, reviewer = users["admin@example.com"], users["reviewer@example.com"]
    created = []
    for email, skey, status in plan:
        student, s = users[email], sch[skey]
        app = Application(student_id=student.id, scholarship_id=s.id, round_id=s.rounds[0].id, status=status)
        db.add(app)
        db.flush()
        path = path_of_status[status]
        start = datetime.now(timezone.utc) - timedelta(days=len(path) + 1)
        for i, st in enumerate(path):
            actor = student if st in (DRAFT, SUBMITTED) else (admin if st == VERIFIED else reviewer)
            db.add(StatusHistory(application_id=app.id, status=st, at=start + timedelta(days=i), actor_id=actor.id,
                                 remarks={CHANGES_REQUESTED: "Please upload a clearer cancelled cheque."}.get(st, "")))
        app.created_at, app.updated_at = start, start + timedelta(days=len(path) - 1)

        first = student.full_name.split()[0]
        mongo.application_forms.replace_one({"_id": str(app.id)}, {
            "_id": str(app.id),
            "profile": {"full_name": student.full_name, "date_of_birth": "2003-05-14", "phone": "9876543210",
                        "government_id_number": mask_gov_id("123412341234")},
            "institution": {"institution_name": "Calcutta University", "registration_number": f"REG-{first[:3].upper()}-123",
                            "enrollment_number": f"ENR-{first[:3].upper()}-456"},
            "address": {"address_line": "12 Park Street", "city": "Kolkata", "state": "West Bengal", "postal_code": "700016"},
            "updated_at": datetime.now(timezone.utc).isoformat()}, upsert=True)
        if status != DRAFT:
            db.add(BankDetail(application_id=app.id, account_holder_name=student.full_name,
                              account_number_enc=cipher.encrypt("123456789012"), ifsc_enc=cipher.encrypt("SBIN0001234"), account_last4="9012"))
            for t in ("government_id", "address_proof", "cancelled_cheque"):
                data = tiny_pdf(f"{t} {first} {skey}")
                rel = f"{app.id}/{uuid.uuid4().hex}.pdf"
                (Path(upload_dir) / str(app.id)).mkdir(parents=True, exist_ok=True)
                (Path(upload_dir) / rel).write_bytes(data)
                import hashlib
                db.add(Document(application_id=app.id, doc_type=t, filename=f"{t}.pdf", stored_path=rel, content_type="application/pdf",
                                size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), check_status="ok"))
        if status in (APPROVED, REJECTED):
            sc = (35, 30, 15) if status == APPROVED else (12, 10, 5)
            db.add(ReviewScore(application_id=app.id, reviewer_id=reviewer.id, academic=sc[0], financial_need=sc[1], other=sc[2],
                               total=sum(sc), decision=status, remarks="Seed data"))
        created.append((email, skey, status))
    db.commit()
    for u in users.values():
        notify(mongo, u.id, "Welcome to the Scholarship Portal!")
    db.close()
    return {"users": len(users), "scholarships": len(sch), "applications": created}


def main() -> None:
    settings = get_settings()
    settings.validate_for_runtime()
    if settings.env != "dev":
        raise SystemExit("Seeding is only allowed when ENV=dev.")
    mongo = make_mongo(settings.mongo_url, settings.mongo_db)
    init_mongo(mongo)
    result = seed(make_session_factory(make_engine(settings.database_url)), mongo, FieldCipher(settings.field_encryption_key), settings.upload_dir)
    print(f"Seeded {result['users']} users, {result['scholarships']} scholarships, {len(result['applications'])} applications.")
    print("Log in with admin@example.com / reviewer@example.com / student@example.com  (password: password123)")


if __name__ == "__main__":
    sys.exit(main())
