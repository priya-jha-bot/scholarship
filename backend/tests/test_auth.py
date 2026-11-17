from app.security import create_reset_token
from sqlalchemy import select
from app.models import User


def test_register_validation_uses_contract_error_shape(ctx):
    r = ctx.client.post("/api/auth/register", json={"full_name": "", "email": "nope", "password": "short"})
    assert r.status_code == 422
    body = r.json()
    assert set(body) == {"message", "code", "fields"}
    assert body["fields"]["full_name"] == "Required"
    assert "email" in body["fields"] and "password" in body["fields"]


def test_register_then_login_and_me(ctx):
    r = ctx.client.post("/api/auth/register", json={"full_name": "New Kid", "email": "New@Kid.org", "password": "longenough1"})
    assert r.status_code == 201 and r.json() == {"ok": True}
    dup = ctx.client.post("/api/auth/register", json={"full_name": "X", "email": "new@kid.org", "password": "longenough1"})
    assert dup.status_code == 422 and dup.json()["fields"]["email"] == "Email already registered"
    h = ctx.login("new@kid.org", "longenough1")
    me = ctx.client.get("/api/auth/me", headers=h).json()
    assert me["role"] == "student" and me["email"] == "new@kid.org"


def test_public_registration_cannot_choose_a_role(ctx):
    ctx.client.post("/api/auth/register", json={"full_name": "Sneaky", "email": "s@s.org", "password": "longenough1", "role": "admin"})
    with ctx.db() as db:
        assert db.execute(select(User.role).where(User.email == "s@s.org")).scalar_one() == "student"


def test_login_failures_are_uniform_and_401_without_token(ctx):
    a = ctx.client.post("/api/auth/login", json={"email": "student@example.com", "password": "wrongwrong"})
    b = ctx.client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "wrongwrong"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()
    assert ctx.client.get("/api/auth/me").status_code == 401
    assert ctx.client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_roles_are_enforced(ctx):
    s, a, r = ctx.login("student@example.com"), ctx.login("admin@example.com"), ctx.login("reviewer@example.com")
    assert ctx.client.get("/api/admin/applications", headers=s).status_code == 403
    assert ctx.client.get("/api/admin/applications", headers=r).status_code == 403
    assert ctx.client.get("/api/reviewer/applications", headers=a).status_code == 403
    assert ctx.client.get("/api/applications/mine", headers=a).status_code == 403
    assert ctx.client.post("/api/scholarships", json={}, headers=s).status_code == 403


def test_password_reset_is_single_use(ctx):
    ctx.client.post("/api/auth/forgot-password", json={"email": "ghost@example.com"})       # unknown email still answers ok
    assert ctx.client.post("/api/auth/forgot-password", json={"email": "ghost@example.com"}).json() == {"ok": True}
    with ctx.db() as db:
        u = db.execute(select(User).where(User.email == "student@example.com")).scalar_one()
        token = create_reset_token(ctx.app.state.settings, str(u.id), u.password_hash)
    ok = ctx.client.post("/api/auth/reset-password", json={"token": token, "password": "brandnew123"})
    assert ok.status_code == 200
    again = ctx.client.post("/api/auth/reset-password", json={"token": token, "password": "another1234"})
    assert again.status_code == 400 and again.json()["code"] == "invalid_reset_token"
    ctx.login("student@example.com", "brandnew123")


def test_admin_creates_reviewer_and_rejects_bad_role(ctx):
    a = ctx.login("admin@example.com")
    ok = ctx.client.post("/api/admin/users", json={"full_name": "Rita", "email": "rita@example.com", "password": "longenough1", "role": "reviewer"}, headers=a)
    assert ok.status_code == 201
    bad = ctx.client.post("/api/admin/users", json={"full_name": "Eve", "email": "eve@example.com", "password": "longenough1", "role": "student"}, headers=a)
    assert bad.status_code == 422 and "role" in bad.json()["fields"]
    dup = ctx.client.post("/api/admin/users", json={"full_name": "Rita", "email": "rita@example.com", "password": "longenough1", "role": "admin"}, headers=a)
    assert dup.json()["fields"]["email"]
