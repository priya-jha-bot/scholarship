"""Single source of truth for roles, statuses and the status state machine (mirrors contracts/enums)."""

STUDENT, ADMIN, REVIEWER = "student", "admin", "reviewer"
ROLES = (STUDENT, ADMIN, REVIEWER)

DRAFT = "DRAFT"
SUBMITTED = "SUBMITTED"
VERIFIED = "VERIFIED"
REJECTED_BY_ADMIN = "REJECTED_BY_ADMIN"
CHANGES_REQUESTED = "CHANGES_REQUESTED"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"
DISBURSED = "DISBURSED"

STATUSES = (DRAFT, SUBMITTED, VERIFIED, REJECTED_BY_ADMIN, CHANGES_REQUESTED, APPROVED, REJECTED, WITHDRAWN, DISBURSED)

# The ONLY legal status moves. services/state_machine.transition() is the only code that applies them.
TRANSITIONS = {
    DRAFT: {SUBMITTED},
    SUBMITTED: {VERIFIED, REJECTED_BY_ADMIN, WITHDRAWN},
    VERIFIED: {APPROVED, REJECTED, CHANGES_REQUESTED, WITHDRAWN},
    CHANGES_REQUESTED: {SUBMITTED, WITHDRAWN},
    APPROVED: {DISBURSED},
    REJECTED_BY_ADMIN: set(),
    REJECTED: set(),
    WITHDRAWN: set(),
    DISBURSED: set(),
}

EDITABLE_STATUSES = {DRAFT, CHANGES_REQUESTED}          # student may change sections/documents
REVIEWER_VISIBLE = {VERIFIED, APPROVED, REJECTED, CHANGES_REQUESTED, DISBURSED}
ADMIN_VISIBLE = set(STATUSES) - {DRAFT}

REQUIRED_DOCS = ("government_id", "address_proof", "cancelled_cheque")
ALLOWED_DOC_TYPES = REQUIRED_DOCS + ("marksheet", "income_certificate", "photo")
SENSITIVE_DOC_TYPES = {"government_id", "address_proof", "cancelled_cheque"}   # reviewers never see these

CHECKLIST_KEYS = ("identity_matches", "address_matches", "institution_verified", "bank_proof_valid")
SCORE_MAX = {"academic": 40, "financial_need": 40, "other": 20}
