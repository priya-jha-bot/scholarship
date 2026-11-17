"""MongoDB = flexible data: application form sections, notifications, audit logs.

Collections
  application_forms : _id = application id (str)  { profile, institution, address, updated_at }
  notifications     : { _id (uuid str), user_id, message, read, created_at }
  audit_logs        : { actor_id, action, entity, entity_id, data, at }
"""
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

NOTIFICATION_SCHEMA = {"$jsonSchema": {
    "bsonType": "object", "required": ["user_id", "message", "read", "created_at"],
    "properties": {"user_id": {"bsonType": "string"}, "message": {"bsonType": "string"},
                   "read": {"bsonType": "bool"}, "created_at": {"bsonType": "string"}}}}
AUDIT_SCHEMA = {"$jsonSchema": {
    "bsonType": "object", "required": ["action", "entity", "entity_id", "at"],
    "properties": {"action": {"bsonType": "string"}, "entity": {"bsonType": "string"},
                   "entity_id": {"bsonType": "string"}, "at": {"bsonType": "string"}}}}


def make_mongo(url: str, db_name: str) -> Database:
    return MongoClient(url, serverSelectionTimeoutMS=3000, tz_aware=True)[db_name]


def init_mongo(db: Database) -> None:
    """Idempotent: safe to call on every startup."""
    existing = set(db.list_collection_names())
    for name, schema in (("notifications", NOTIFICATION_SCHEMA), ("audit_logs", AUDIT_SCHEMA)):
        try:
            if name not in existing:
                db.create_collection(name, validator=schema)
            else:
                db.command("collMod", name, validator=schema)
        except Exception:               # e.g. in-memory fakes without validator support
            if name not in existing:
                db.create_collection(name)
    db.notifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.audit_logs.create_index([("entity_id", ASCENDING), ("at", DESCENDING)])
    db.audit_logs.create_index([("actor_id", ASCENDING)])
