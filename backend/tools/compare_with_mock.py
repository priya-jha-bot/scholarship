"""Replay the same calls against the frontend's mock API and the real backend and compare status codes + JSON shapes.

    # terminal 1: cd frontend && npm run mock            (http://localhost:4010)
    # terminal 2: start the backend on :8000 and seed it  (python -m scripts.reset)
    python tools/compare_with_mock.py
"""
import io
import sys

import httpx

MOCK, REAL = "http://localhost:4010/api", "http://localhost:8000/api"
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def shape(v):
    if isinstance(v, dict):
        return {k: shape(x) for k, x in sorted(v.items())}
    if isinstance(v, list):
        return [shape(v[0])] if v else []
    return type(v).__name__ if v is not None else "null"


def keys_only_diff(a, b, path=""):
    """Differences that matter to the frontend: keys the mock has but the real API lacks (extra real keys are fine)."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k not in b:
                out.append(f"{path}/{k}: missing in real API")
            else:
                out += keys_only_diff(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if a and b:
            out += keys_only_diff(a[0], b[0], path + "[]")
    elif a != b and not (a in ("int", "float") and b in ("int", "float")) and "null" not in (a, b):
        out.append(f"{path}: type {a} (mock) vs {b} (real)")
    return out


class Side:
    def __init__(self, base):
        self.base, self.c, self.h, self.ids = base, httpx.Client(timeout=15), {}, {}

    def login(self, who):
        r = self.c.post(f"{self.base}/auth/login", json={"email": f"{who}@example.com", "password": "password123"})
        self.h[who] = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def call(self, who, method, path, **kw):
        return self.c.request(method, self.base + path, headers=self.h.get(who, {}), **kw)


fails = 0


def check(name, mock, real, want_status=None):
    global fails
    problems = []
    if mock.status_code != real.status_code:
        problems.append(f"status {mock.status_code} (mock) vs {real.status_code} (real)")
    try:
        problems += keys_only_diff(shape(mock.json()), shape(real.json()))
    except Exception:
        pass
    print(("OK   " if not problems else "FAIL ") + name + ("" if not problems else "  -> " + "; ".join(problems)))
    fails += bool(problems)


def main():
    m, r = Side(MOCK), Side(REAL)
    for who in ("student", "admin", "reviewer"):
        m.login(who), r.login(who)
    import uuid
    fresh = f"cmp-{uuid.uuid4().hex[:8]}@example.com"          # a brand-new student so the draft flow starts clean on both sides
    for side in (m, r):
        side.c.post(f"{side.base}/auth/register", json={"full_name": "Cmp Student", "email": fresh, "password": "password123"})
        side.h["fresh"] = {"Authorization": "Bearer " + side.c.post(f"{side.base}/auth/login", json={"email": fresh, "password": "password123"}).json()["access_token"]}

    def both(name, who, method, path_fn, **kw):
        a = m.call(who, method, path_fn(m), **(kw(m) if callable(kw.get("json_fn")) else {k: v for k, v in kw.items()}))
        b = r.call(who, method, path_fn(r), **{k: v for k, v in kw.items()})
        check(name, a, b)
        return a, b

    # public + auth
    both("login ok", None, "POST", lambda s: "/auth/login", json={"email": "student@example.com", "password": "password123"})
    both("login wrong", None, "POST", lambda s: "/auth/login", json={"email": "student@example.com", "password": "nope"})
    both("register invalid", None, "POST", lambda s: "/auth/register", json={"full_name": "", "email": "student@example.com", "password": "x"})
    both("forgot", None, "POST", lambda s: "/auth/forgot-password", json={"email": "a@b.co"})
    both("me", "student", "GET", lambda s: "/auth/me")
    both("me no token", None, "GET", lambda s: "/auth/me")
    a, b = both("scholarships", None, "GET", lambda s: "/scholarships")
    sid = {"mock": a.json()["items"][0]["id"], "real": next(i["id"] for i in b.json()["items"] if "Merit" in i["title"])}
    both("scholarship create invalid", "admin", "POST", lambda s: "/scholarships", json={"title": ""})
    both("scholarship create forbidden", "student", "POST", lambda s: "/scholarships", json={"title": "x"})

    # student lists
    both("my applications", "student", "GET", lambda s: "/applications/mine")
    a, b = both("admin list", "admin", "GET", lambda s: "/admin/applications?status=SUBMITTED&page=1&page_size=10")
    both("reviewer list", "reviewer", "GET", lambda s: "/reviewer/applications?status=VERIFIED&page=1&page_size=10")
    both("reports", "admin", "GET", lambda s: "/admin/reports/summary")
    both("notifications", "student", "GET", lambda s: "/notifications")

    # detail (use each side's own SUBMITTED application)
    ids = {"mock": a.json()["items"][0]["id"], "real": b.json()["items"][0]["id"]}
    key = lambda s: "mock" if s is m else "real"
    both("application detail (admin)", "admin", "GET", lambda s: f"/applications/{ids[key(s)]}")
    both("application 404", "admin", "GET", lambda s: "/applications/does-not-exist")
    both("illegal review", "reviewer", "POST", lambda s: f"/reviewer/applications/{ids[key(s)]}/review",
         json={"scores": {"academic": 1, "financial_need": 1, "other": 1}, "decision": "APPROVED", "remarks": ""})

    # a full draft on each side (mock + real) using an unused scholarship per side
    drafts = {}
    for side, who_sid in ((m, a.json()["items"] and None), (r, None)):
        pass
    sch = {"mock": m.call(None, "GET", "/scholarships").json()["items"][2]["id"],
           "real": next(i["id"] for i in r.call(None, "GET", "/scholarships").json()["items"] if "STEM" in i["title"])}
    x = m.call("fresh", "POST", "/applications", json={"scholarship_id": sch["mock"]})
    y = r.call("fresh", "POST", "/applications", json={"scholarship_id": sch["real"]})
    check("create draft", x, y)
    drafts = {"mock": x.json()["id"], "real": y.json()["id"]}
    for sec, body in {
        "profile": {"full_name": "N", "date_of_birth": "2002-02-02", "phone": "9876543210", "government_id_number": "123412341234"},
        "institution": {"institution_name": "U", "registration_number": "R1", "enrollment_number": "E1"},
        "address": {"address_line": "1 Rd", "city": "K", "state": "WB", "postal_code": "700001"},
        "bank": {"account_holder_name": "N", "account_number": "998877665544", "ifsc": "SBIN0001234"},
    }.items():
        both(f"save {sec}", "fresh", "PUT", lambda s, sec=sec: f"/applications/{drafts[key(s)]}/{sec}", json=body)
    both("bank invalid ifsc", "fresh", "PUT", lambda s: f"/applications/{drafts[key(s)]}/bank",
         json={"account_holder_name": "N", "account_number": "998877665544", "ifsc": "BAD"})
    for side in (m, r):
        pass
    both("submit missing docs", "fresh", "POST", lambda s: f"/applications/{drafts[key(s)]}/submit", json={"declaration_accepted": True})
    ups = []
    for s in (m, r):
        for t in ("government_id", "address_proof", "cancelled_cheque"):
            ups.append(s.call("fresh", "POST", f"/applications/{drafts[key(s)]}/documents", data={"doc_type": t},
                              files={"file": (f"{t}.pdf", io.BytesIO(PDF + t.encode()), "application/pdf")}))
    check("upload document", ups[0], ups[3])
    both("submit", "fresh", "POST", lambda s: f"/applications/{drafts[key(s)]}/submit", json={"declaration_accepted": True})
    both("withdraw", "fresh", "POST", lambda s: f"/applications/{drafts[key(s)]}/withdraw")
    both("document link", "admin", "GET", lambda s: f"/documents/{(s.call('admin','GET',f'/applications/{ids[key(s)]}').json()['documents'][0]['id'])}/link")
    both("admin create user dup", "admin", "POST", lambda s: "/admin/users", json={"full_name": "A", "email": "admin@example.com", "password": "longenough1", "role": "admin"})
    print("\nDifferences:", fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
