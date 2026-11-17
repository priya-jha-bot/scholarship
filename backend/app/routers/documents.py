import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pymongo.database import Database
from sqlalchemy.orm import Session

from ..config import Settings
from ..constants import ADMIN, REVIEWER, SENSITIVE_DOC_TYPES, STUDENT
from ..deps import current_user, get_db, get_mongo, get_settings_dep
from ..errors import ApiError
from ..models import Application, Document, User
from ..security import create_doc_token, decode_doc_token
from ..services import applications as svc
from ..services import storage
from ..services.notifications import audit

router = APIRouter(prefix="/documents", tags=["documents"])


def _doc(db: Session, doc_id: str) -> Document:
    try:
        doc = db.get(Document, uuid.UUID(doc_id))
    except ValueError:
        doc = None
    if not doc:
        raise ApiError(404, "Document not found")
    return doc


@router.get("/{doc_id}/link")
def link(doc_id: str, db: Session = Depends(get_db), mongo: Database = Depends(get_mongo),
         settings: Settings = Depends(get_settings_dep), user: User = Depends(current_user)):
    """Returns a signed URL that works for DOC_LINK_TTL_SECONDS (10 minutes), so an <iframe> can show the file."""
    doc = _doc(db, doc_id)
    app: Application = db.get(Application, doc.application_id)
    allowed = svc.can_view(user, app) and not (user.role == REVIEWER and doc.doc_type in SENSITIVE_DOC_TYPES)
    if not allowed:
        raise ApiError(404, "Document not found")
    audit(mongo, user.id, "document_link", "document", doc.id, {"application_id": str(app.id), "doc_type": doc.doc_type})
    token = create_doc_token(settings, str(doc.id), str(user.id))
    return {"url": f"/api/documents/download?token={token}", "expires_in": settings.doc_link_ttl_seconds}


@router.get("/download", include_in_schema=False)
def download(token: str = Query(...), db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep)):
    claims = decode_doc_token(settings, token)
    if not claims:
        raise ApiError(403, "This link has expired. Open the document again.", code="link_expired")
    doc = _doc(db, claims["sub"])
    path = storage.resolve(settings.upload_dir, doc.stored_path)
    if not path.exists():
        raise ApiError(404, "File is missing")
    return FileResponse(path, media_type=doc.content_type, content_disposition_type="inline", filename=doc.filename,
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
