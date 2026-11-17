"""Field-level encryption for bank details + masking helpers. Decrypted values are never logged."""
import re
from cryptography.fernet import Fernet, InvalidToken

_MASKED_ACCOUNT = re.compile(r"^\*+\d{4}$")
_MASKED_GOV_ID = re.compile(r"^X{4}-X{4}-[A-Za-z0-9]{4}$")


class FieldCipher:
    def __init__(self, key: str):
        self._f = Fernet(key.encode())

    def encrypt(self, plain: str) -> str:
        return self._f.encrypt(plain.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._f.decrypt(token.encode()).decode()
        except InvalidToken as e:  # wrong key or tampered data
            raise ValueError("Cannot decrypt field (wrong FIELD_ENCRYPTION_KEY?)") from e


def mask_account(last4: str) -> str:
    return "****" + last4


def is_masked_account(value: str) -> bool:
    return bool(_MASKED_ACCOUNT.match(value or ""))


def mask_gov_id(raw: str) -> str:
    """Only the last 4 characters of a government ID are ever stored: XXXX-XXXX-1234."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw)
    return f"XXXX-XXXX-{cleaned[-4:].upper()}"


def is_masked_gov_id(value: str) -> bool:
    return bool(_MASKED_GOV_ID.match(value or ""))
