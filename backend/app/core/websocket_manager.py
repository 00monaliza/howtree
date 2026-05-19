"""
WebSocket connection manager.

Design:
- One Redis pub/sub channel per job_id.
- Celery workers publish progress to Redis.
- The WS endpoint subscribes and relays to connected clients.
- Multiple clients can watch the same job simultaneously.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

PROGRESS_CHANNEL_PREFIX = "job_progress:"


class WebSocketManager:
    """
    Manages active WebSocket connections and bridges them to Redis pub/sub.
    Lifecycle: one singleton per FastAPI process.
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_keepalive=True,
            )
        return self._redis

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[job_id].add(websocket)
        logger.info("websocket_connected", job_id=job_id)

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        self._connections[job_id].discard(websocket)
        if not self._connections[job_id]:
            del self._connections[job_id]
        logger.info("websocket_disconnected", job_id=job_id)

    async def broadcast(self, job_id: str, payload: dict[str, Any]) -> None:
        """Send payload to all clients watching this job."""
        message = json.dumps(payload)
        dead: set[WebSocket] = set()

        for ws in list(self._connections.get(job_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        for ws in dead:
            self._connections[job_id].discard(ws)

    async def stream_job_progress(self, job_id: str, websocket: WebSocket) -> None:
        """
        Subscribe to Redis pub/sub for this job and relay messages to the WS client.
        Terminates when the job completes/fails or the client disconnects.
        """
        redis = await self._get_redis()
        pubsub = redis.pubsub()
        channel = f"{PROGRESS_CHANNEL_PREFIX}{job_id}"

        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    await websocket.send_text(json.dumps(payload))
                    # Stop streaming when job reaches terminal state
                    if payload.get("status") in ("completed", "failed"):
                        break
                except Exception as exc:
                    logger.warning("ws_relay_error", error=str(exc))
                    break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


# Singleton — created once at startup
ws_manager = WebSocketManager()


# ── Utility for workers (sync Redis publish) ──────────────────────────────────
def publish_progress(
    redis_url: str,
    job_id: str,
    progress: int,
    message: str,
    status: str = "processing",
) -> None:
    """
    Sync function called from Celery workers to publish progress updates.
    Uses a separate sync Redis client to avoid event loop conflicts.
    """
    import redis as sync_redis

    client = sync_redis.from_url(redis_url, decode_responses=True)
    payload = json.dumps(
        {"progress": progress, "message": message, "status": status, "job_id": job_id}
    )
    channel = f"{PROGRESS_CHANNEL_PREFIX}{job_id}"
    client.publish(channel, payload)
    client.close()
