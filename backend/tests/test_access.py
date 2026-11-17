import time

import jwt
from sqlalchemy import inspect

from app.models import Base
from app.security import ALGO


def _apps(ctx, headers, url="/api/applications/mine"):
    return ctx.client.get(url, headers=headers).json()["items"]


def test_students_only_see_their_own_applications(ctx):
    c = ctx.client
    sara, uma = ctx.login("student@example.com"), ctx.login("uma@example.com")
    sara_app = _apps(ctx, sara)[0]["id"]
    assert c.get(f"/api/applications/{sara_app}", headers=uma).status_code == 404            # 404, not 403: ids cannot be probed
    assert c.put(f"/api/applications/{sara_app}/address", json={"address_line": "x", "city": "y", "state": "z", "postal_code": "123456"}, headers=uma).status_code == 404
    assert c.post(f"/api/applications/{sara_app}/withdraw", headers=uma).status_code == 404
    assert c.get("/api/applications/not-a-uuid", headers=sara).status_code == 404


def test_reviewer_view_is_limited(ctx):
    c = ctx.client
    r, a = ctx.login("reviewer@example.com"), ctx.login("admin@example.com")
    pending = _apps(ctx, r, "/api/reviewer/applications")                                       # default = VERIFIED
    assert pending and all(x["status"] == "VERIFIED" for x in pending)
    d = c.get(f"/api/applications/{pending[0]['id']}", headers=r).json()
    assert d["bank"] == {} and d["documents"] == []                                              # no bank, no identity documents
    submitted = _apps(ctx, a, "/api/admin/applications?status=SUBMITTED")[0]["id"]
    assert c.get(f"/api/applications/{submitted}", headers=r).status_code == 404                # not verified yet
    assert c.get("/api/reviewer/applications?status=SUBMITTED", headers=r).status_code == 422
    assert c.get("/api/admin/applications?status=DRAFT", headers=a).status_code == 422


def test_admin_sees_masked_bank_and_documents_open_through_signed_links(ctx):
    c = ctx.client
    a, r, other = ctx.login("admin@example.com"), ctx.login("reviewer@example.com"), ctx.login("tara@example.com")
    app_id = _apps(ctx, a, "/api/admin/applications?status=SUBMITTED")[0]["id"]
    d = c.get(f"/api/applications/{app_id}", headers=a).json()
    assert d["bank"]["account_number"] == "****9012" and len(d["documents"]) == 3
    doc_id = d["documents"][0]["id"]

    link = c.get(f"/api/documents/{doc_id}/link", headers=a).json()
    assert link["url"].startswith("/api/documents/download?token=") and link["expires_in"] == 600
    f = c.get(link["url"])
    assert f.status_code == 200 and f.headers["content-type"] == "application/pdf" and f.content.startswith(b"%PDF")
    assert f.headers["x-content-type-options"] == "nosniff" and "no-store" in f.headers["cache-control"]

    assert c.get(f"/api/documents/{doc_id}/link", headers=other).status_code == 404           # a student who does not own the application
    assert c.get("/api/documents/download?token=garbage").status_code == 403
    assert c.get(f"/api/documents/{doc_id}/link").status_code == 401

    # an expired signed link stops working
    claims = jwt.decode(link["url"].split("token=")[1], options={"verify_signature": False})
    claims["exp"] = int(time.time()) - 5
    expired = jwt.encode(claims, ctx.app.state.settings.jwt_secret, algorithm=ALGO)
    assert c.get(f"/api/documents/download?token={expired}").json()["code"] == "link_expired"

    # reviewers may not open identity documents even for verified applications
    verified = _apps(ctx, r, "/api/reviewer/applications")[0]["id"]
    with ctx.db() as db:
        from sqlalchemy import select
        from app.models import Document
        import uuid
        vdoc = db.execute(select(Document).where(Document.application_id == uuid.UUID(verified))).scalars().first()
    assert c.get(f"/api/documents/{vdoc.id}/link", headers=r).status_code == 404
    assert ctx.mongo.audit_logs.count_documents({"action": "document_link"}) >= 1             # every link is audited


def test_notifications_are_private_and_markable(ctx):
    c = ctx.client
    s, u = ctx.login("student@example.com"), ctx.login("uma@example.com")
    n = c.get("/api/notifications", headers=s).json()["items"][0]
    assert set(n) == {"id", "user_id", "message", "read", "created_at"} and n["read"] is False
    c.post(f"/api/notifications/{n['id']}/read", headers=u)                                    # someone else: silently ignored
    assert c.get("/api/notifications", headers=s).json()["items"][0]["read"] is False
    c.post(f"/api/notifications/{n['id']}/read", headers=s)
    assert c.get("/api/notifications", headers=s).json()["items"][0]["read"] is True


def test_reports_summary_shape(ctx):
    r = ctx.client.get("/api/admin/reports/summary", headers=ctx.login("admin@example.com")).json()
    assert r["by_status"]["APPROVED"] == 1 and r["by_status"]["REJECTED"] == 1 and "DRAFT" not in r["by_status"]
    row = next(x for x in r["approval_rate"] if x["scholarship"].startswith("Merit"))
    assert set(row) == {"scholarship", "round", "rate"} and row["rate"] == 1.0                 # 1 approved / 1 decided


def test_pagination_shape_and_limits(ctx):
    a = ctx.login("admin@example.com")
    r = ctx.client.get("/api/admin/applications?status=VERIFIED&page=1&page_size=1", headers=a).json()
    assert r["page"] == 1 and r["page_size"] == 1 and len(r["items"]) <= 1 and r["total"] >= 1
    assert ctx.client.get("/api/admin/applications?page_size=1000", headers=a).status_code == 422


def test_websocket_pushes_notifications(ctx):
    c = ctx.client
    admin, uma = ctx.login("admin@example.com"), ctx.login("uma@example.com")
    token = admin["Authorization"].split()[1]
    with c.websocket_connect(f"/ws?token={token}") as ws:
        app_id = ctx.fill_draft(uma, ctx.scholarship_id("STEM"))
        c.post(f"/api/applications/{app_id}/submit", json={"declaration_accepted": True}, headers=uma)
        msg = ws.receive_json()
        assert "waiting for verification" in msg["message"] and set(msg) == {"id", "user_id", "message", "read", "created_at"}
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_websocket_rejects_bad_token(ctx):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with ctx.client.websocket_connect("/ws?token=bad") as ws:
            ws.receive_text()


def test_every_error_uses_the_contract_shape(ctx):
    for r in (ctx.client.get("/api/nope"), ctx.client.get("/api/auth/me"), ctx.client.post("/api/auth/login", json={})):
        assert set(r.json()) == {"message", "code", "fields"}


def test_alembic_migration_matches_models(tmp_path):
    """The migration files (what production runs) must build exactly the tables the models define."""
    import os
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    url = f"sqlite:///{tmp_path/'m.db'}"
    os.environ["DATABASE_URL"] = url
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
        insp = inspect(create_engine(url))
        assert set(insp.get_table_names()) - {"alembic_version"} == set(Base.metadata.tables)
        command.downgrade(Config("alembic.ini"), "base")
    finally:
        os.environ.pop("DATABASE_URL", None)
        get_settings.cache_clear()
