"""Automatic checks that run in the background after each upload (BackgroundTasks).

Flags (never rejects): unreadable/mismatched file, or the same file reused on another application or for two
document types. A human admin still makes the decision; the flag is only a hint stored on the document and in
the audit log.
"""
import logging
import uuid

from pymongo.database import Database
from sqlalchemy import select

from ..models import Document
from .notifications import audit
from .storage import resolve, sniff

log = logging.getLogger("app.bot")


def run_document_check(doc_id: str, session_factory, mongo: Database, upload_dir: str) -> None:
    db = session_factory()
    try:
        doc = db.get(Document, uuid.UUID(doc_id))
        if not doc:
            return
        status, note = "ok", ""
        try:
            path = resolve(upload_dir, doc.stored_path)
            head = path.read_bytes()[:16] if path.exists() else b""
            kind = sniff(head)
            if not head or not kind or kind[0] != doc.content_type:
                status, note = "flagged", "File could not be read or does not match its type"
            else:
                twins = db.execute(select(Document).where(Document.sha256 == doc.sha256, Document.id != doc.id)).scalars().all()
                if any(t.application_id != doc.application_id for t in twins):
                    status, note = "flagged", "Identical file was uploaded on another application"
                elif twins:
                    status, note = "flagged", "Same file used for two different document types"
        except Exception:
            log.exception("document check failed")
            status, note = "flagged", "Automatic check could not run"
        doc.check_status, doc.check_note = status, note
        db.commit()
        if status == "flagged":
            audit(mongo, None, "document_flagged", "document", doc.id, {"application_id": str(doc.application_id), "note": note})
    finally:
        db.close()
