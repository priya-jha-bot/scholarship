from fastapi import APIRouter, Depends
from pymongo import DESCENDING
from pymongo.database import Database

from ..deps import Page, current_user, get_mongo
from ..models import User
from ..services.notifications import serialize

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(page: Page = Depends(), mongo: Database = Depends(get_mongo), user: User = Depends(current_user)):
    q = {"user_id": str(user.id)}
    total = mongo.notifications.count_documents(q)
    rows = mongo.notifications.find(q).sort("created_at", DESCENDING).skip(page.offset).limit(page.page_size)
    return page.wrap([serialize(n) for n in rows], total)


@router.post("/{notification_id}/read")
def mark_read(notification_id: str, mongo: Database = Depends(get_mongo), user: User = Depends(current_user)):
    """Only the owner's notification can be marked; anything else is silently ignored (no id probing)."""
    mongo.notifications.update_one({"_id": notification_id, "user_id": str(user.id)}, {"$set": {"read": True}})
    return {"ok": True}
