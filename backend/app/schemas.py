import re
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .constants import CHECKLIST_KEYS, SCORE_MAX


class In(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


def _pw_ok(v: str) -> str:
    if len(v.encode()) > 72:
        raise ValueError("At most 72 characters")
    return v


# ---------------- auth ----------------
class RegisterIn(In):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    _pw = field_validator("password")(_pw_ok)


class LoginIn(In):
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ForgotIn(In):
    email: str = Field(min_length=1, max_length=254)


class ResetIn(In):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)
    _pw = field_validator("password")(_pw_ok)


class AdminCreateUserIn(In):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str
    _pw = field_validator("password")(_pw_ok)

    @field_validator("role")
    @classmethod
    def _role(cls, v: str) -> str:
        if v not in ("reviewer", "admin"):
            raise ValueError("Role must be reviewer or admin")
        return v


# ---------------- scholarships ----------------
class ScholarshipIn(In):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    amount: int = Field(ge=1, le=100_000_000)
    deadline: date

    @field_validator("deadline")
    @classmethod
    def _future(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Deadline cannot be in the past")
        return v


# ---------------- application sections ----------------
_NAME = re.compile(r"^[\w .,'\-/&()]+$", re.UNICODE)


class ProfileIn(In):
    full_name: str = Field(min_length=1, max_length=120)
    date_of_birth: date
    phone: str = Field(min_length=1, max_length=20)
    government_id_number: str = Field(min_length=1, max_length=40)

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if v >= today or age > 100:
            raise ValueError("Enter a valid date of birth")
        if age < 14:
            raise ValueError("Applicant must be at least 14 years old")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        digits = re.sub(r"[\s\-]", "", v)
        if not re.fullmatch(r"\+?\d{10,15}", digits):
            raise ValueError("Enter a valid phone number (10 to 15 digits)")
        return digits

    @field_validator("government_id_number")
    @classmethod
    def _gid(cls, v: str) -> str:
        if len(re.sub(r"[^A-Za-z0-9]", "", v)) < 4:
            raise ValueError("Enter a valid ID number")
        return v


class InstitutionIn(In):
    institution_name: str = Field(min_length=1, max_length=160)
    registration_number: str = Field(min_length=1, max_length=60)
    enrollment_number: str = Field(min_length=1, max_length=60)
    course: str | None = Field(default=None, max_length=120)
    year_of_study: int | None = Field(default=None, ge=1, le=8)
    admission_year: int | None = Field(default=None, ge=1990, le=2100)
    cgpa: float | None = Field(default=None, ge=0, le=10)

    @field_validator("registration_number", "enrollment_number")
    @classmethod
    def _ids(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9/\-_. ]+", v):
            raise ValueError("Use letters, digits, / - _ . only")
        return v


class AddressIn(In):
    address_line: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=80)
    state: str = Field(min_length=1, max_length=80)
    postal_code: str = Field(min_length=1, max_length=10)

    @field_validator("postal_code")
    @classmethod
    def _pin(cls, v: str) -> str:
        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("Enter a 6-digit PIN code")
        return v


class BankIn(In):
    account_holder_name: str = Field(min_length=1, max_length=120)
    account_number: str = Field(min_length=1, max_length=30)
    ifsc: str = Field(min_length=1, max_length=11)

    @field_validator("account_number")
    @classmethod
    def _acct(cls, v: str) -> str:
        if not re.fullmatch(r"\d{9,18}", v) and not re.fullmatch(r"\*+\d{4}", v):   # masked value = "keep what is stored"
            raise ValueError("Account number must be 9 to 18 digits")
        return v

    @field_validator("ifsc")
    @classmethod
    def _ifsc(cls, v: str) -> str:
        v = v.upper()
        if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", v):
            raise ValueError("Invalid IFSC (e.g. SBIN0001234)")
        return v


SECTION_MODELS = {"profile": ProfileIn, "institution": InstitutionIn, "address": AddressIn, "bank": BankIn}


class SubmitIn(In):
    declaration_accepted: bool = False


# ---------------- admin / reviewer decisions ----------------
class VerifyIn(In):
    decision: str
    checklist: dict[str, bool] = Field(default_factory=dict)
    remarks: str = Field(default="", max_length=2000)

    @field_validator("decision")
    @classmethod
    def _d(cls, v: str) -> str:
        if v not in ("VERIFIED", "REJECTED_BY_ADMIN"):
            raise ValueError("Decision must be VERIFIED or REJECTED_BY_ADMIN")
        return v

    @field_validator("checklist")
    @classmethod
    def _c(cls, v: dict) -> dict:
        return {k: bool(v.get(k)) for k in CHECKLIST_KEYS}


class Scores(In):
    academic: int = Field(ge=0, le=SCORE_MAX["academic"])
    financial_need: int = Field(ge=0, le=SCORE_MAX["financial_need"])
    other: int = Field(ge=0, le=SCORE_MAX["other"])


class ReviewIn(In):
    scores: Scores
    decision: str
    remarks: str = Field(default="", max_length=2000)

    @field_validator("decision")
    @classmethod
    def _d(cls, v: str) -> str:
        if v not in ("APPROVED", "REJECTED", "CHANGES_REQUESTED"):
            raise ValueError("Decision must be APPROVED, REJECTED or CHANGES_REQUESTED")
        return v
