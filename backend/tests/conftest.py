import os
import tempfile

import mongomock
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.config import Settings
from app.constants import ADMIN
from app.crypto import FieldCipher
from app.db.mongo import init_mongo
from app.db.postgres import make_engine, make_session_factory
from app.main import create_app
from app.models import Base
from scripts.seed import PASSWORD, seed

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


class Ctx:
    """Everything a test needs: the client plus handles to both databases."""
    def __init__(self, client, app, mongo, upload_dir):
        self.client, self.app, self.mongo, self.upload_dir = client, app, mongo, upload_dir
        self.db = app.state.session_factory

    def login(self, email: str, password: str = PASSWORD) -> dict:
        r = self.client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def scholarship_id(self, title_part="Merit") -> str:
        items = self.client.get("/api/scholarships?page_size=50").json()["items"]
        return next(s["id"] for s in items if title_part in s["title"])

    def fill_draft(self, headers, scholarship_id, docs=True, suffix="") -> str:
        c = self.client
        app_id = c.post("/api/applications", json={"scholarship_id": scholarship_id}, headers=headers).json()["id"]
        sections = {
            "profile": {"full_name": "Nina Test", "date_of_birth": "2002-02-02", "phone": "9876543210", "government_id_number": "123412341234"},
            "institution": {"institution_name": "Test University", "registration_number": "REG1", "enrollment_number": "ENR1"},
            "address": {"address_line": "1 Test Road", "city": "Kolkata", "state": "West Bengal", "postal_code": "700001"},
            "bank": {"account_holder_name": "Nina Test", "account_number": "998877665544", "ifsc": "sbin0001234"},
        }
        for name, body in sections.items():
            r = c.put(f"/api/applications/{app_id}/{name}", json=body, headers=headers)
            assert r.status_code == 200, r.text
        if docs:
            for i, t in enumerate(("government_id", "address_proof", "cancelled_cheque")):
                r = c.post(f"/api/applications/{app_id}/documents", data={"doc_type": t},
                           files={"file": (f"{t}.pdf", PDF + f"{suffix}{i}".encode(), "application/pdf")}, headers=headers)
                assert r.status_code == 201, r.text
        return app_id


@pytest.fixture
def ctx(tmp_path):
    key = Fernet.generate_key().decode()
    settings = Settings(env="dev", jwt_secret="test-secret-test-secret-test-secret!", field_encryption_key=key,
                        upload_dir=str(tmp_path / "uploads"), rate_limit_enabled=False, database_url="sqlite://")
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")      # set it to run the suite on real PostgreSQL
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    mongo = mongomock.MongoClient()["test"]
    app = create_app(settings, engine, mongo)
    with TestClient(app) as client:
        seed(make_session_factory(engine), mongo, FieldCipher(key), settings.upload_dir)
        yield Ctx(client, app, mongo, settings.upload_dir)
