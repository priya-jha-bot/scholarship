"""Drop everything, rebuild the schema with Alembic, wipe MongoDB + uploads, and re-seed:   python -m scripts.reset"""
import shutil
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.config import get_settings
from app.crypto import FieldCipher
from app.db.mongo import init_mongo, make_mongo
from app.db.postgres import make_engine, make_session_factory
from app.models import Base
from scripts.seed import seed


def main() -> None:
    s = get_settings()
    s.validate_for_runtime()
    if s.env != "dev":
        raise SystemExit("reset is only allowed when ENV=dev.")
    engine = make_engine(s.database_url)
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS alembic_version"))
    command.upgrade(Config("alembic.ini"), "head")

    mongo = make_mongo(s.mongo_url, s.mongo_db)
    for name in mongo.list_collection_names():
        mongo.drop_collection(name)
    init_mongo(mongo)
    shutil.rmtree(s.upload_dir, ignore_errors=True)
    Path(s.upload_dir).mkdir(parents=True, exist_ok=True)

    r = seed(make_session_factory(engine), mongo, FieldCipher(s.field_encryption_key), s.upload_dir)
    print(f"Reset done: {r['users']} users, {r['scholarships']} scholarships, {len(r['applications'])} applications.")


if __name__ == "__main__":
    main()
