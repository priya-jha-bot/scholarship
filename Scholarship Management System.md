Understood. This version has **two workspaces only**, with all server-side work in Python and the MERN pieces confined to the frontend. The Express gateway from my last plan is gone. FastAPI now does everything the gateway did (auth, uploads, the status state machine, WebSockets and background bot tasks).

## 0. Shared contract (the only thing both workspaces touch)

```
scholarship/
├── contracts/       # openapi.yaml, enums.md, seed-data.json, env-names.md  (read-only for both sides)
├── frontend/        # React workspace
├── backend/         # FastAPI + PostgreSQL + MongoDB workspace (db work lives inside)
└── docker-compose.yml   # written last
```

**Rules that prevent assembly problems**

1. `openapi.yaml` is the single source of truth. The backend must match it, and the frontend builds against a mock of it.
2. **Roles:** `student`, `admin`, `reviewer`.
3. **Status enum:** `SUBMITTED`, `VERIFIED`, `REJECTED_BY_ADMIN`, `CHANGES_REQUESTED`, `APPROVED`, `REJECTED`, `WITHDRAWN`, `DISBURSED`.
4. **Error shape:** `{ "message": "...", "code": "...", "fields": {} }`.
5. **Auth:** a JWT with `sub`, `role` and `exp`, sent as `Authorization: Bearer`. Everything is served under `/api`.
6. **Field names are `snake_case`, dates are ISO 8601 in UTC, ids are UUID strings.**
7. Pagination is `?page=&page_size=`, and lists return `{ items, total, page, page_size }`.
8. File uploads are `multipart/form-data` with a `doc_type` field.
9. Dev ports: frontend `5173`, backend `8000`.

**API surface (write this into `openapi.yaml` first, about 1 day)**

|Area|Endpoints|
|---|---|
|Auth|`POST /auth/register`, `/auth/login`, `GET /auth/me`, `POST /auth/forgot-password`, `/auth/reset-password`|
|Scholarships|`GET /scholarships`, `GET /scholarships/{id}`; admin: `POST`, `PUT`, `DELETE`|
|Student application|`POST /applications`, `PUT /applications/{id}/profile`, `/institution`, `/address`, `/bank`; `POST /applications/{id}/documents`; `POST /applications/{id}/submit`, `/withdraw`, `/resubmit`; `GET /applications/mine`, `GET /applications/{id}`|
|Admin|`GET /admin/applications`, `POST /admin/applications/{id}/verify`, `POST /admin/users`, `GET /admin/reports/summary`|
|Reviewer|`GET /reviewer/applications`, `POST /reviewer/applications/{id}/review`|
|Documents|`GET /documents/{id}/link` (signed URL, 10 minutes)|
|Notifications|`GET /notifications`, `POST /notifications/{id}/read`, WebSocket `/ws?token=`|

**Seed data (`seed-data.json`):** 1 admin, 1 reviewer, 3 students, 3 scholarships and 6 applications in different statuses. Both sides load the same file, so the mock and the real database tell the same story.

## 1. Backend workspace (Python, PostgreSQL, MongoDB, FastAPI)

**Stack:** FastAPI, SQLAlchemy 2 with Alembic, Pydantic v2, PyMongo or Motor, `python-jose` or PyJWT, `passlib[bcrypt]`, `cryptography` (field encryption), `pytest`, Schemathesis.

**Data ownership (each entity lives in exactly one place)**

|Data|Where|
|---|---|
|users, scholarships, scholarship rounds, applications (core and status), documents metadata, bank details (encrypted columns), review scores, status history, disbursements|**PostgreSQL**|
|flexible form sections (profile, institution, address, declarations), notifications, audit logs|**MongoDB**|
|uploaded files|local disk, or S3-compatible storage, with paths in Postgres|

**Phase 1, database foundation (days 1–2)**

- BE-D1: Postgres tables and Alembic migrations, with constraints: one application per student per scholarship per round, a status check limited to the enum, foreign keys and indexes on `status` and `student_id`.
- BE-D2: Mongo collections with JSON-schema validators and indexes on `application_id` and `user_id`.
- BE-D3: encryption helper for bank account number and IFSC. Government ID is stored masked, last 4 only.
- BE-D4: `seed.py` and `reset.py`, reading `contracts/seed-data.json`.

**Phase 2, core API (days 3–7)**

- BE-1: app skeleton, settings from `.env`, CORS for `localhost:5173`, global exception handler producing the contract's error shape, request logging, rate limiting.
- BE-2: auth: register (students only), login, `me`, password reset, role dependencies.
- BE-3: scholarship CRUD and listing.
- BE-4: application flow: draft, per-section saves to Mongo, typed document upload with type and size checks, submit, withdraw, resubmit.
- BE-5: **status state machine**, one function that is the only place status changes. It also writes `status_history` and an audit log entry. Illegal jumps return a clear error.
- BE-6: admin verify (checklist and decision), reviewer review (scores of 40, 40 and 20, plus decision), admin user creation, signed document links.
- BE-7: notifications created on every status change, and the read endpoints.
- BE-8: reports summary (counts by status, approval rate per scholarship and round).

**Phase 3, extras (last)**

- BE-9: WebSocket `/ws` that pushes notifications, authenticated with the token on connect.
- BE-10: bot tasks using FastAPI `BackgroundTasks`, or Celery with Redis later. Examples are file readability checks, duplicate-hash detection, and masked-ID validation after each upload.

**Backend done when**

- Schemathesis run against `openapi.yaml` passes.
- Pytest covers the state machine and role permissions.
- `reset.py` followed by starting the app gives a populated system.
- `/docs` shows every contract endpoint.

## 2. Frontend workspace (MERN technologies only here)

**Stack:** React (Vite), React Router, and, if you want all four letters represented, a small **Node and Express static server** that serves the built React app and proxies `/api` to FastAPI. This is a frontend-side server with no business logic. MongoDB is the "M", and it sits in the backend workspace.

Be honest in your report about this split: "M" is the document database behind the API, and "E" and "N" are the frontend's web server. A strict reviewer may still say this is not a conventional MERN project, so if your assessment is strict, tell me and we'll revisit.

**Work against a mock:** run Prism on `openapi.yaml`, or MSW with the seed data, so you never wait for the backend.

- FE-1: Vite and React Router setup, `VITE_API_BASE=/api`, and a dev proxy to port 8000.
- FE-2: port `api.js`, `auth.js` and the CSS into React. Add `AuthContext` and a `<RequireRole>` guard.
- FE-3: shared components: toast, form fields, file upload, status badge, table, modal, loading and error states.
- FE-4: public pages: home, login, register, forgot and reset password.
- FE-5 (student):
    - Dashboard and scholarship list.
    - Multi-step apply wizard: profile, institution (name, registration number, enrollment number), proofs (government ID, address proof), address, bank (account holder name, account number, IFSC, cancelled cheque), declaration, review and submit.
    - Save as draft, field-level errors, status timeline, resubmit and withdraw, and a notifications panel.
- FE-6 (admin): dashboard, scholarship management, verify queue with a document viewer beside the checklist, create reviewer or admin accounts, reports.
- FE-7 (reviewer): dashboard, review page with scoring, history.
- FE-8 (last): live notifications over the WebSocket with a polling fallback.
- FE-9: the optional Express static and proxy server, plus a production build.
- Cleanup: delete the duplicated `public/admin/public/` folder first.

**Frontend done when:** every page works end to end against the mock, and pointing at the real backend changes only the proxy target.

## 3. Assembly (about 1 day if the contract held)

1. Write `docker-compose.yml` with `postgres`, `mongo`, `backend` and `frontend` (the Express server, or Nginx).
2. Run the backend's `reset.py`, then start everything.
3. Run Schemathesis once more, then one walkthrough per role:
    - Student registers, applies with all documents and submits.
    - Admin verifies.
    - Reviewer approves.
    - Student sees the new status and a notification.
4. Tag the release.

## 4. Order and independence

|Step|Backend|Frontend|
|---|---|---|
|Contract and seed data|both read it|both read it|
|Main build|BE-D1 to BE-8|FE-1 to FE-7 (mock)|
|Extras|BE-9, BE-10|FE-8, FE-9|
|Assembly|together|together|

The two sides never need each other until assembly, which is the point.

## 5. What most often breaks assembly

- **Field-name drift** (`fullName` versus `full_name`). Prevented by the OpenAPI file.
- **A second place changing status.** Keep the state machine as the only entry point.
- **CORS and cookies.** The proxy keeps everything on one origin.
- **Time zones.** Store UTC and format only in the UI.
- **Encryption keys.** Agree on the variable name in `env-names.md`, and never log decrypted values.

The best first move is for me to write `contracts/openapi.yaml` and `seed-data.json`, since both workspaces depend on them. I can also turn this into a Word or PDF document for your report if you'd like.