"""Create .env from .env.example with fresh random secrets:   python -m scripts.init_env"""
import re
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

target = Path(".env")
if target.exists():
    raise SystemExit(".env already exists - not overwriting it.")
text = Path(".env.example").read_text()
text = re.sub(r"^JWT_SECRET=.*$", f"JWT_SECRET={secrets.token_urlsafe(48)}", text, flags=re.M)
text = re.sub(r"^FIELD_ENCRYPTION_KEY=.*$", f"FIELD_ENCRYPTION_KEY={Fernet.generate_key().decode()}", text, flags=re.M)
target.write_text(text)
print("Wrote .env with new JWT_SECRET and FIELD_ENCRYPTION_KEY. Keep the encryption key safe: losing it makes stored bank details unreadable.")
