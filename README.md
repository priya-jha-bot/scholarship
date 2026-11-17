I opened the zip, and two things shape everything below.

- **The zip contains only the frontend.** It has no backend, database or Python code. Everything I say about the FastAPI and PostgreSQL side comes from the earlier summary, not from this upload. If you have the backend in a separate folder, send it and I'll verify it against this.
- **The folder is messy.** Everything under `public/admin/public/` is an exact duplicate of `public/`, almost certainly a bad copy. Delete it before building on top of this.

## 1. Your idea, in one picture

A scholarship portal with three kinds of people:

| Role | Job |
|---|---|
| **Student/candidate** | Registers, applies with documents, tracks status, withdraws |
| **Admin** | Creates scholarships, checks documents, marks Verified or Rejected, views reports |
| **Reviewer** | Sees only verified applications, scores them, then Approves, Rejects or Requests Changes |

The lifecycle is: Submitted → Verified (or Rejected) → Approved, Rejected, or Changes Requested. Bots are planned as a later add-on that calls the same endpoints. Nothing links to outside databases yet.

## 2. What exists and what is missing

**Frontend (verified in the zip): 12 pages**
- `index`, `login`, `register`
- Student: dashboard, apply, status
- Admin: dashboard, scholarships, verify, reports
- Reviewer: dashboard, review
- Shared pieces: `api.js` (a fetch wrapper that adds the JWT, handles 401 and 429, and sends FormData for uploads), `auth.js` (role checks and redirects), `ui.js` (toasts), and three CSS files.

**Backend (from the earlier summary, unverified): built**
- REST with JSON and JWT login
- Student, admin and reviewer endpoints
- Signed 10-minute document links
- SQLAlchemy models on PostgreSQL

**Missing everywhere**
- Forgot and reset password, email verification, profile edit
- Admin screen to create reviewers and admins (currently a script)
- Resubmission after "Request Changes"
- Notifications and a reviewer history page
- Payment/disbursement stage, which is the real end of a scholarship
- Audit log of who verified or approved what, and when
- Scholarship deadlines and rounds, and duplicate-application checks
- File-type and size validation and virus scanning on uploads
- Role-based access tests

**Frontend issues I noticed**
- The JWT is stored in `sessionStorage`, which is fine for a college project but exposed to XSS. Mention this in your report as a known trade-off.
- The apply form asks only for name, university, major, GPA and 3 files. That is far thinner than what you now want to collect.
- The register form asks for university, major, GPA and contact. Academic details like these should live on the application, not the account.
- The API base is `/api`, so your backend must be served under that prefix or proxied.

## 3. Data to collect from the candidate

You were missing a few things. I've grouped everything and marked what I added.

**Identity and contact**
- Full name (as on documents), date of birth, gender, nationality
- Email and phone, guardian or parent name and contact *(added)*
- Passport-size photo *(added)*

**Institution and academics**
- Institution name, course, year or semester, admission year *(added)*
- Registration number, enrollment number, roll number *(added)*
- CGPA or percentage, backlogs *(added)*
- Marksheet or transcript, bonafide certificate or ID card

**Proofs**
- Government ID proof
- Address proof
- Current and permanent address *(added)*
- Income certificate and family details, if the scholarship is need-based *(added)*
- Category or disability certificate, if relevant *(added)*

**Banking** (for disbursement)
- Account holder name (this is your "billing name"), account number, IFSC, bank and branch
- Cancelled cheque or passbook first page *(added)*

**Declarations** *(added)*
- Consent to data use
- Declaration that the information is true
- Whether the student is already receiving another scholarship

**Handling rules, which belong in your report**
- Store Aadhaar and PAN masked, such as the last 4 digits only. Full government ID numbers carry legal restrictions. Prefer DigiLocker-style verification over keeping the number.
- Encrypt bank account numbers at rest, never write them to logs, and show them masked in the UI.
- Check that the bank account holder name matches the student's name. Verifying with a ₹1 "penny drop" API is a later upgrade.
- India's DPDP Act applies to this kind of data, so keep only what you need.

## 4. What to build, by layer

**Database**
- Split `applications` into related tables: `applicant_profiles`, `institution_details`, `addresses`, `bank_details` (encrypted), and `documents` (with type, path, status and verifier).
- Add `review_scores`, `status_history` (the audit trail), `notifications`, `scholarship_rounds` and `disbursements`.
- Add real foreign keys, unique constraints (one application per student per scholarship), and indexes on status.

**Backend**
- Endpoints for profile, address, bank details and document upload by type.
- Resubmit-after-changes, reviewer and admin account creation, password reset and notifications.
- A status state machine that blocks illegal jumps, for example Submitted straight to Approved.
- Background tasks for bots such as automatic document checks, plus rate limiting.

**Frontend**
- Turn the apply page into a multi-step form: personal, institution, proofs, bank, declaration, review and submit.
- Add the missing pages from section 2.
- Add a document viewer for admins, with the checklist next to it.
- Add a status timeline on the student status page.

**Easy reuse from your current frontend**
- All CSS, `ui.js`, the role-guard logic, the dashboard layouts and the file-upload handling can be reused.
- Nothing conflicts as long as you keep the same `/api` contract.

## 5. Making it a MERN project

MERN means MongoDB, Express, React and Node. That conflicts directly with Postgres and FastAPI, so you have two honest options.

**Option A, pure MERN.** Rewrite the backend in Express and Node with MongoDB, and drop FastAPI and Postgres. It is clean, but it throws away the stack you want to keep.

**Option B, hybrid (my recommendation).** This one qualifies as MERN and keeps your stack, with a clear split so nothing overlaps:

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | **React** (Vite), reusing your CSS and API logic | All 12 pages as routes |
| API gateway | **Node + Express** | Auth, routing, uploads, WebSockets via Socket.IO, rate limiting |
| Document store | **MongoDB** | Applications' flexible form data, notifications, audit logs |
| System of record | **PostgreSQL** | Users, scholarships, decisions, disbursements |
| Python service | **FastAPI** | Scoring, bots, automatic verification, report generation |

Rules that prevent conflicts:
- Each entity lives in exactly one database. Don't duplicate.
- React talks only to Express, and Express calls FastAPI internally.
- A shared JWT secret lets both services trust the same login.

How to get there from here:
1. Delete the duplicate folder and scaffold a Vite React app.
2. Convert each HTML page to a React route, reusing `api.js` and the CSS.
3. Put an Express layer in front and move login there.
4. Move the flexible form data and notifications to MongoDB.
5. Keep Postgres and FastAPI behind Express for the core records and the bots.

One caveat: a reviewer who knows MERN well may call the hybrid "MERN plus extras" rather than pure MERN. If your assessment is strict about that, Option A is the safe choice.

## 6. Architecture points you may be missing

- Documents should live in object storage such as S3 or local disk with signed access, and not in the database.
- Decisions need an audit trail so any approval can be explained later.
- Admin and reviewer accounts must be created by a trusted path, never by public registration.
- Real-time updates should be added only after the notification model exists.
- Reports need clear definitions, such as approval rate per scholarship per round.

I can put this into a Word or PDF document for your report. Or, if you'd rather start building, the best first step is the multi-step apply form with the new fields and the matching database tables.
