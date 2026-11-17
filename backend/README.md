# Scholarship backend (FastAPI + PostgreSQL + MongoDB)

Implements exactly the API the React frontend's mock server (`frontend/mock/server.js`) speaks.

## Run it
```bash
docker compose -f docker-compose.db.yml up -d      # Postgres + Mongo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m scripts.init_env                          # creates .env with fresh JWT + encryption keys
alembic upgrade head                                # or: python -m scripts.reset  (drop, migrate, seed)
python -m scripts.seed                              # demo data (ENV=dev only)
uvicorn app.main:get_app --factory --reload --port 8000
```
API docs: http://localhost:8000/api/docs (dev only). Health: `/api/health`.
Demo logins (password `password123`): student@example.com, tara@example.com, uma@example.com, reviewer@example.com, admin@example.com.

## Hook up the frontend
In `frontend/.env` set `VITE_PROXY_TARGET=http://localhost:8000` and restart `npm run dev`. Nothing else changes.

## Tests
```bash
pytest                                              # in-memory SQLite + mongomock (fast)
TEST_DATABASE_URL=postgresql+psycopg2://scholarship:scholarship@localhost:5432/scholarship pytest   # real Postgres
python tools/compare_with_mock.py                   # with mock on :4010 and backend on :8000: diff the two APIs
```

## Where things live
| Data | Store |
|---|---|
| users, scholarships, rounds, applications + status, documents metadata, bank details (encrypted), review scores, status history, disbursements | PostgreSQL |
| form sections (profile, institution, address), notifications, audit logs | MongoDB |
| uploaded files | `UPLOAD_DIR` (signed 10-minute links) |

`app/services/state_machine.py::transition()` is the ONLY code that changes an application's status.

## Rules worth knowing
- Government ID: only `XXXX-XXXX-1234` (last 4) is stored. Bank account number + IFSC: Fernet-encrypted; API shows `****1234`. **Back up FIELD_ENCRYPTION_KEY** - losing it makes stored bank details unreadable.
- Reviewers never see bank details or identity documents. Students only see their own applications (404 otherwise).
- Admin rejecting needs remarks; reviewer "request changes" needs remarks (the student sees them in the timeline).
- Approval rate = (APPROVED + DISBURSED) / (those + REJECTED + REJECTED_BY_ADMIN), per scholarship per round.
- `DISBURSED` and the `disbursements` table exist, but no endpoint/page uses them yet.

## Known limits (be upfront about these in your report)
- WebSockets and the rate limiter are in-process: with several workers you need Redis behind them.
- Uploads are checked by file signature and size, not virus-scanned.
- Reset emails go to the server log unless `MAIL_BACKEND=smtp` is configured.
- The JWT lives in the browser's localStorage (frontend choice): fine for a college project, exposed to XSS.
