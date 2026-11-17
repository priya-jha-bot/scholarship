"""One error shape for the whole API:  { "message": str, "code": str, "fields": {name: message} }"""
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class ApiError(Exception):
    def __init__(self, status: int, message: str, fields: dict | None = None, code: str | None = None):
        self.status, self.message, self.fields, self.code = status, message, fields or {}, code or f"E{status}"


def body(message: str, code: str, fields: dict | None = None) -> dict:
    return {"message": message, "code": code, "fields": fields or {}}


def _friendly(err: dict) -> str:
    t, msg = err.get("type", ""), err.get("msg", "Invalid value")
    if t == "missing" or (t == "string_too_short" and err.get("ctx", {}).get("min_length") == 1):
        return "Required"          # empty or whitespace-only (the value is stripped before the length check)
    if msg.startswith("Value error, "):
        return msg[len("Value error, "):]
    if t == "string_too_short":
        return f"At least {err['ctx']['min_length']} characters"
    if t == "string_too_long":
        return f"At most {err['ctx']['max_length']} characters"
    if t in ("greater_than_equal", "less_than_equal", "greater_than", "less_than"):
        return msg[:1].upper() + msg[1:]
    if t == "string_pattern_mismatch":
        return "Invalid format"
    if "email" in t or "email" in msg.lower():
        return "Enter a valid email address"
    if t.startswith("date") or t.startswith("datetime"):
        return "Enter a valid date (YYYY-MM-DD)"
    return msg[:1].upper() + msg[1:]


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError):
        return JSONResponse(body(e.message, e.code, e.fields), status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _val(_: Request, e: RequestValidationError):
        fields: dict[str, str] = {}
        for err in e.errors():
            loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
            key = loc[-1] if loc else "_"
            fields.setdefault(key, _friendly(err))
        return JSONResponse(body("Please fix the highlighted fields", "E422", fields), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        msg = {404: "Not found", 405: "Method not allowed"}.get(e.status_code, str(e.detail))
        return JSONResponse(body(msg, f"E{e.status_code}"), status_code=e.status_code)

    @app.exception_handler(Exception)
    async def _any(_: Request, e: Exception):
        log.exception("Unhandled error")
        return JSONResponse(body("Internal server error", "E500"), status_code=500)
