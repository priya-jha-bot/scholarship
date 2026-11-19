"""Create (or reset the password of) one admin account. Safe for production: no demo data.

    python -m scripts.create_admin

Point it at the deployed databases by setting DATABASE_URL (the EXTERNAL Postgres URL) in the environment first.
"""
import getpass

from sqlalchemy import select

from app.config import get_settings
from app.db.postgres import make_engine, make_session_factory
from app.models import User
from app.security import hash_password


def main() -> None:
    settings = get_settings()
    email = input("Admin email: ").strip().lower()
    name = input("Full name: ").strip()
    password = getpass.getpass("Password (min 8 characters): ")
    if not email or "@" not in email or not name or len(password) < 8 or len(password.encode()) > 72:
        raise SystemExit("Need a valid email, a name, and a password of 8 to 72 characters.")
    db = make_session_factory(make_engine(settings.database_url))()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        user.role, user.is_active, user.password_hash = "admin", True, hash_password(password)
        print(f"Existing account {email} is now an admin with the new password.")
    else:
        db.add(User(full_name=name, email=email, password_hash=hash_password(password), role="admin"))
        print(f"Created admin {email}.")
    db.commit()


if __name__ == "__main__":
    main()
