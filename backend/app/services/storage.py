"""Upload handling. Never trusts the client: type comes from the file's own bytes, the stored name is server-generated."""
import hashlib
import os
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from ..errors import ApiError

SIGNATURES = (
    (b"%PDF-", "application/pdf", ".pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
)
CHUNK = 64 * 1024


def clean_filename(name: str | None) -> str:
    base = os.path.basename((name or "document").replace("\\", "/"))
    base = re.sub(r"[^\w.\- ]", "_", base).strip(" .") or "document"
    return base[:120]


def sniff(head: bytes) -> tuple[str, str] | None:
    for sig, mime, ext in SIGNATURES:
        if head.startswith(sig):
            return mime, ext
    return None


class Stored:
    def __init__(self, rel_path: str, mime: str, size: int, sha256: str):
        self.rel_path, self.mime, self.size, self.sha256 = rel_path, mime, size, sha256


def save_upload(root: str, application_id: str, file: UploadFile, max_bytes: int) -> Stored:
    folder = Path(root) / str(application_id)
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / f".{uuid.uuid4().hex}.part"
    h, size, head = hashlib.sha256(), 0, b""
    try:
        with open(tmp, "wb") as out:
            while chunk := file.file.read(CHUNK):
                if not head:
                    head = chunk[:16]
                size += len(chunk)
                if size > max_bytes:
                    raise ApiError(422, "File is too large", {"file": f"File must be under {max_bytes // (1024 * 1024)} MB"})
                h.update(chunk)
                out.write(chunk)
        if size == 0:
            raise ApiError(422, "File is empty", {"file": "File is empty"})
        kind = sniff(head)
        if not kind:
            raise ApiError(422, "Unsupported file type", {"file": "Only PDF, JPG or PNG files are allowed"})
        mime, ext = kind
        final = folder / f"{uuid.uuid4().hex}{ext}"
        os.replace(tmp, final)
        return Stored(f"{application_id}/{final.name}", mime, size, h.hexdigest())
    finally:
        if tmp.exists():
            tmp.unlink()


def resolve(root: str, rel_path: str) -> Path:
    """Absolute path of a stored file, guaranteed to be inside the upload root."""
    base = Path(root).resolve()
    p = (base / rel_path).resolve()
    if base not in p.parents:
        raise ApiError(404, "Not found")
    return p


def remove(root: str, rel_path: str) -> None:
    try:
        resolve(root, rel_path).unlink(missing_ok=True)
    except ApiError:
        pass
