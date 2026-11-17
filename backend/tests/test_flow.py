import uuid

import pytest
from sqlalchemy import select, text

from tests.conftest import PDF, PNG
from app.constants import STATUSES, TRANSITIONS
from app.models import Application, BankDetail


def test_scholarships_public_list_and_admin_crud(ctx):
    r = ctx.client.get("/api/scholarships")
    assert r.status_code == 200 and r.json()["total"] == 3 and set(r.json()) == {"items", "total", "page", "page_size"}
    assert set(r.json()["items"][0]) == {"id", "title", "description", "amount", "deadline"}
    a = ctx.login("admin@example.com")
    bad = ctx.client.post("/api/scholarships", json={"title": "", "amount": 0, "deadline": "2001-01-01"}, headers=a)
    assert bad.status_code == 422 and {"title", "amount", "deadline"} <= set(bad.json()["fields"])
    made = ctx.client.post("/api/scholarships", json={"title": "New", "description": "d", "amount": 1000, "deadline": "2099-01-01"}, headers=a)
    assert made.status_code == 201
    assert ctx.client.delete(f"/api/scholarships/{made.json()['id']}", headers=a).status_code == 200
    # a scholarship that has applications cannot be deleted
    assert ctx.client.delete(f"/api/scholarships/{ctx.scholarship_id('Merit')}", headers=a).status_code == 409


def test_full_happy_path(ctx):
    c = ctx.client
    s, a, r = ctx.login("uma@example.com"), ctx.login("admin@example.com"), ctx.login("reviewer@example.com")
    sid = ctx.scholarship_id("STEM")
    app_id = ctx.fill_draft(s, sid)
    # same call again resumes the same draft
    assert c.post("/api/applications", json={"scholarship_id": sid}, headers=s).json()["id"] == app_id

    # not visible to staff while it is a draft, and drafts are not in the student's list
    assert c.get(f"/api/applications/{app_id}", headers=a).status_code == 404
    assert all(x["id"] != app_id for x in c.get("/api/applications/mine", headers=s).json()["items"])

    # declaration is mandatory
    assert c.post(f"/api/applications/{app_id}/submit", json={}, headers=s).status_code == 422
    done = c.post(f"/api/applications/{app_id}/submit", json={"declaration_accepted": True}, headers=s)
    assert done.status_code == 200 and done.json()["status"] == "SUBMITTED"
    assert [h["status"] for h in done.json()["history"]] == ["DRAFT", "SUBMITTED"]

    # editing after submit is refused
    assert c.put(f"/api/applications/{app_id}/address", json={"address_line": "x", "city": "y", "state": "z", "postal_code": "123456"}, headers=s).status_code == 409

    # admin must tick every checklist item to verify
    chk = {"identity_matches": True, "address_matches": True, "institution_verified": True, "bank_proof_valid": False}
    assert c.post(f"/api/admin/applications/{app_id}/verify", json={"decision": "VERIFIED", "checklist": chk}, headers=a).status_code == 422
    chk["bank_proof_valid"] = True
    v = c.post(f"/api/admin/applications/{app_id}/verify", json={"decision": "VERIFIED", "checklist": chk, "remarks": "ok"}, headers=a)
    assert v.status_code == 200 and v.json()["status"] == "VERIFIED"
    # verifying twice is an illegal move
    again = c.post(f"/api/admin/applications/{app_id}/verify", json={"decision": "VERIFIED", "checklist": chk}, headers=a)
    assert again.status_code == 409 and again.json()["message"] == "Illegal status change"

    # reviewer scoring limits are 40 / 40 / 20
    over = c.post(f"/api/reviewer/applications/{app_id}/review", json={"scores": {"academic": 41, "financial_need": 10, "other": 5}, "decision": "APPROVED"}, headers=r)
    assert over.status_code == 422 and "academic" in over.json()["fields"]
    no_remarks = c.post(f"/api/reviewer/applications/{app_id}/review", json={"scores": {"academic": 30, "financial_need": 10, "other": 5}, "decision": "CHANGES_REQUESTED"}, headers=r)
    assert no_remarks.status_code == 422
    ok = c.post(f"/api/reviewer/applications/{app_id}/review", json={"scores": {"academic": 30, "financial_need": 30, "other": 15}, "decision": "APPROVED", "remarks": "great"}, headers=r)
    assert ok.status_code == 200 and ok.json()["status"] == "APPROVED"

    # approved applications cannot be withdrawn; student sees the timeline and notifications
    assert c.post(f"/api/applications/{app_id}/withdraw", headers=s).status_code == 409
    hist = c.get(f"/api/applications/{app_id}", headers=s).json()["history"]
    assert [h["status"] for h in hist] == ["DRAFT", "SUBMITTED", "VERIFIED", "APPROVED"]
    msgs = [n["message"] for n in c.get("/api/notifications", headers=s).json()["items"]]
    assert any("Approved" in m for m in msgs) and any("Verified" in m for m in msgs)

    # admin gets told about new submissions
    assert any("waiting for verification" in n["message"] for n in c.get("/api/notifications", headers=a).json()["items"])


def test_changes_requested_loop(ctx):
    c = ctx.client
    s, r = ctx.login("student@example.com"), ctx.login("reviewer@example.com")
    mine = c.get("/api/applications/mine", headers=s).json()["items"]
    cr = next(x for x in mine if x["status"] == "CHANGES_REQUESTED")
    assert c.put(f"/api/applications/{cr['id']}/address", json={"address_line": "New 1", "city": "Kolkata", "state": "WB", "postal_code": "700002"}, headers=s).status_code == 200
    res = c.post(f"/api/applications/{cr['id']}/resubmit", headers=s)
    assert res.status_code == 200 and res.json()["status"] == "SUBMITTED"
    assert c.post(f"/api/applications/{cr['id']}/resubmit", headers=s).status_code == 409     # no longer CHANGES_REQUESTED


def test_withdraw_rules(ctx):
    c, s = ctx.client, ctx.login("student@example.com")
    sub = next(x for x in c.get("/api/applications/mine", headers=s).json()["items"] if x["status"] == "SUBMITTED")
    w = c.post(f"/api/applications/{sub['id']}/withdraw", headers=s)
    assert w.status_code == 200 and w.json()["status"] == "WITHDRAWN"
    assert c.post(f"/api/applications/{sub['id']}/withdraw", headers=s).status_code == 409


def test_submit_reports_what_is_missing(ctx):
    c, s = ctx.client, ctx.login("uma@example.com")
    app_id = ctx.fill_draft(s, ctx.scholarship_id("STEM"), docs=False)
    r = c.post(f"/api/applications/{app_id}/submit", json={"declaration_accepted": True}, headers=s)
    assert r.status_code == 422 and r.json()["message"].startswith("Missing documents:")


def test_section_validation_messages(ctx):
    c, s = ctx.client, ctx.login("uma@example.com")
    app_id = c.post("/api/applications", json={"scholarship_id": ctx.scholarship_id("STEM")}, headers=s).json()["id"]
    r = c.put(f"/api/applications/{app_id}/profile", json={"full_name": " ", "date_of_birth": "2999-01-01", "phone": "12", "government_id_number": "1"}, headers=s)
    f = r.json()["fields"]
    assert r.status_code == 422 and f["full_name"] == "Required" and "date of birth" in f["date_of_birth"].lower() and "phone" in f["phone"].lower()
    b = c.put(f"/api/applications/{app_id}/bank", json={"account_holder_name": "A", "account_number": "12", "ifsc": "BAD"}, headers=s)
    assert "ifsc" in b.json()["fields"] and "account_number" in b.json()["fields"]
    a = c.put(f"/api/applications/{app_id}/address", json={"address_line": "x", "city": "y", "state": "z", "postal_code": "70"}, headers=s)
    assert "postal_code" in a.json()["fields"]


def test_sensitive_values_are_masked_and_encrypted_at_rest(ctx):
    c, s = ctx.client, ctx.login("uma@example.com")
    app_id = ctx.fill_draft(s, ctx.scholarship_id("STEM"))
    d = c.get(f"/api/applications/{app_id}", headers=s).json()
    assert d["bank"]["account_number"] == "****5544" and d["bank"]["ifsc"] == "SBIN0001234"
    assert d["profile"]["government_id_number"] == "XXXX-XXXX-1234"
    # the form echoes masked values back on revisit: that must keep the stored values, not overwrite them
    assert c.put(f"/api/applications/{app_id}/bank", json={"account_holder_name": "Nina Test", "account_number": "****5544", "ifsc": "SBIN0001234"}, headers=s).status_code == 200
    assert c.put(f"/api/applications/{app_id}/profile", json={**d["profile"]}, headers=s).status_code == 200
    # a masked value that does not match what is stored is refused
    assert c.put(f"/api/applications/{app_id}/bank", json={"account_holder_name": "N", "account_number": "****0000", "ifsc": "SBIN0001234"}, headers=s).status_code == 422
    with ctx.db() as db:
        row = db.execute(select(BankDetail).where(BankDetail.application_id == uuid.UUID(app_id))).scalar_one()
        assert "998877665544" not in row.account_number_enc and "SBIN" not in row.ifsc_enc
        assert ctx.app.state.cipher.decrypt(row.account_number_enc) == "998877665544"
    raw = str(ctx.mongo.application_forms.find_one({"_id": app_id}))
    assert "123412341234" not in raw


def test_upload_rules(ctx):
    c, s = ctx.client, ctx.login("uma@example.com")
    app_id = c.post("/api/applications", json={"scholarship_id": ctx.scholarship_id("STEM")}, headers=s).json()["id"]
    url = f"/api/applications/{app_id}/documents"
    def up(name, data, t="government_id"):
        return c.post(url, data={"doc_type": t}, files={"file": (name, data, "application/pdf")}, headers=s)
    assert up("x.pdf", b"").status_code == 422
    assert up("evil.pdf", b"MZ\x90\x00 not a pdf").json()["fields"]["file"].startswith("Only PDF")
    assert up("a.pdf", PDF, "passport").json()["fields"]["doc_type"]
    just_over = up("big.pdf", PDF + b"0" * (5 * 1024 * 1024))              # over the 5 MB limit, under the early guard
    assert just_over.status_code == 422 and "5 MB" in just_over.json()["fields"]["file"]
    huge = up("huge.pdf", PDF + b"0" * (7 * 1024 * 1024))                  # refused before it is even read
    assert huge.status_code == 413 and "file" in huge.json()["fields"]
    r = up("../../etc/passwd.pdf", PNG)                            # real PNG content wins over the claimed name/type
    assert r.status_code == 201 and "/" not in r.json()["filename"] and r.json()["doc_type"] == "government_id"
    with ctx.db() as db:
        from app.models import Document
        d = db.execute(select(Document)).scalars().all()[-1]
        assert d.content_type == "image/png" and d.stored_path.endswith(".png") and "passwd" not in d.stored_path
    # replacing a document keeps exactly one per type
    assert up("again.pdf", PDF + b"2").status_code == 201
    docs = c.get(f"/api/applications/{app_id}", headers=s).json()["documents"]
    assert [x["doc_type"] for x in docs].count("government_id") == 1


def test_bot_flags_reused_files(ctx):
    c, s = ctx.client, ctx.login("uma@example.com")
    app_id = c.post("/api/applications", json={"scholarship_id": ctx.scholarship_id("STEM")}, headers=s).json()["id"]
    for t in ("government_id", "address_proof"):
        c.post(f"/api/applications/{app_id}/documents", data={"doc_type": t}, files={"file": ("same.pdf", PDF + b"SAME", "application/pdf")}, headers=s)
    docs = c.get(f"/api/applications/{app_id}", headers=s).json()["documents"]
    assert {d["check_status"] for d in docs} == {"flagged"} or "flagged" in {d["check_status"] for d in docs}
    assert ctx.mongo.audit_logs.count_documents({"action": "document_flagged"}) >= 1


@pytest.mark.parametrize("src", STATUSES)
@pytest.mark.parametrize("dst", STATUSES)
def test_state_machine_table(src, dst):
    legal = dst in TRANSITIONS[src]
    if src == dst:
        assert not legal           # nothing may "move" to itself
