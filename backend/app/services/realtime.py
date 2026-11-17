"""Live notification push over WebSocket.

Single-process only: connections live in this process's memory. Running several workers needs a shared
broker (Redis pub/sub) behind `push()`; the rest of the code would not change.
"""
import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

log = logging.getLogger("app.realtime")


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: dict[str, set[WebSocket]] = defaultdict(set)
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._conns[user_id].add(ws)

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        self._conns[user_id].discard(ws)
        if not self._conns[user_id]:
            self._conns.pop(user_id, None)

    async def _send(self, user_id: str, payload: dict) -> None:
        for ws in list(self._conns.get(user_id, ())):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                self.disconnect(user_id, ws)

    def push(self, user_id: str, payload: dict) -> None:
        """Callable from sync code running in a worker thread."""
        if self.loop is None or user_id not in self._conns:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._send(user_id, payload), self.loop)
        except Exception:
            log.exception("push failed")


manager = ConnectionManager()
