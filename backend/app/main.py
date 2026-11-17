import asyncio
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from . import errors
from .config import Settings, get_settings
from .crypto import FieldCipher
from .db.mongo import init_mongo, make_mongo
from .db.postgres import make_engine, make_session_factory
from .deps import user_from_token
from .routers import admin, applications, auth, documents, notifications, reviewer, scholarships
from .services.realtime import manager


class RedactToken(logging.Filter):
    """The WebSocket token travels in the URL; keep it out of access logs."""
    pattern = re.compile(r"(token=)[^&\s\"]+")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(self.pattern.sub(r"\1***", a) if isinstance(a, str) else a for a in record.args)
        return True


def create_app(settings: Settings | None = None, engine=None, mongo=None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate_for_runtime()
    engine = engine or make_engine(settings.database_url)
    mongo = mongo if mongo is not None else make_mongo(settings.mongo_url, settings.mongo_db)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        init_mongo(mongo)
        manager.loop = asyncio.get_running_loop()
        yield

    dev = settings.env == "dev"
    app = FastAPI(title="Scholarship API", version="1.0.0", lifespan=lifespan,
                  docs_url="/api/docs" if dev else None, redoc_url=None, openapi_url="/api/openapi.json" if dev else None)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.mongo = mongo
    app.state.cipher = FieldCipher(settings.field_encryption_key)

    logging.getLogger("uvicorn.access").addFilter(RedactToken())
    errors.install(app)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_methods=["*"], allow_headers=["*"])

    max_body = (settings.max_upload_mb + 1) * 1024 * 1024

    @app.middleware("http")
    async def guard(request: Request, call_next):
        # refuse oversized uploads early (before they are spooled to disk) and add basic security headers
        if request.method == "POST" and request.url.path.endswith("/documents"):
            length = request.headers.get("content-length")
            if length and length.isdigit() and int(length) > max_body:
                return JSONResponse({"message": "File is too large", "code": "E413", "fields": {"file": f"File must be under {settings.max_upload_mb} MB"}}, status_code=413)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    for r in (auth, scholarships, applications, documents, admin, reviewer, notifications):
        app.include_router(r.router, prefix="/api")

    @app.get("/api/health", tags=["meta"])
    def health():
        problems = []
        try:
            with engine.connect() as c:
                c.exec_driver_sql("SELECT 1")
        except Exception:
            problems.append("postgres")
        try:
            mongo.command("ping")
        except Exception:
            problems.append("mongo")
        if problems:
            return JSONResponse({"ok": False, "down": problems}, status_code=503)
        return {"ok": True}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket, token: str | None = Query(None)):
        """Live notifications. Connect with /ws?token=<access token>. Each message is one notification object."""
        def who() -> str | None:
            db = app.state.session_factory()
            try:
                u = user_from_token(db, settings, token)
                return str(u.id) if u else None
            finally:
                db.close()

        uid = await run_in_threadpool(who)
        if not uid:
            await websocket.close(code=4401)
            return
        await manager.connect(uid, websocket)
        try:
            while True:
                if (await websocket.receive_text()) == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(uid, websocket)

    return app


def get_app() -> FastAPI:       # uvicorn --factory app.main:get_app
    return create_app()
