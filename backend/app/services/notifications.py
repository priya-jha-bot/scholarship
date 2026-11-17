import uuid
from datetime import datetime, timezone

from pymongo.database import Database

from .realtime import manager


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def serialize(n: dict) -> dict:
    return {"id": n["_id"], "user_id": n["user_id"], "message": n["message"], "read": n["read"], "created_at": n["created_at"]}


def notify(mongo: Database, user_id: str, message: str) -> dict:
    doc = {"_id": str(uuid.uuid4()), "user_id": str(user_id), "message": message, "read": False, "created_at": _now()}
    mongo.notifications.insert_one(doc)
    out = serialize(doc)
    manager.push(str(user_id), out)          # live update; the bell also polls as a fallback
    return out


def audit(mongo: Database, actor_id, action: str, entity: str, entity_id, data: dict | None = None) -> None:
    """Append-only trail. Never put decrypted or full sensitive values in `data`."""
    mongo.audit_logs.insert_one({
        "actor_id": str(actor_id) if actor_id else None, "action": action, "entity": entity,
        "entity_id": str(entity_id), "data": data or {}, "at": _now(),
    })
