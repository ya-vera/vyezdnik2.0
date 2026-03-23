"""История диалога в Redis (TTL как в design.md — 30 мин простоя)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("vyezdnik")

SESSION_TTL_SEC = int(os.getenv("SESSION_TTL_SEC", str(30 * 60)))
KEY_PREFIX = os.getenv("REDIS_SESSION_PREFIX", "vyezdnik:chat:")
MAX_MESSAGES = int(os.getenv("SESSION_MAX_MESSAGES", "40"))

_client: Any = None


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()


def get_client():
    global _client
    if _client is None:
        import redis

        url = _redis_url()
        _client = redis.from_url(url, decode_responses=True, socket_connect_timeout=3)
    return _client


def ping_redis() -> None:
    get_client().ping()


def _key(session_id: str) -> str:
    safe = session_id.replace("\n", "").replace("\r", "")[:128]
    return f"{KEY_PREFIX}{safe}"


def get_history(session_id: str) -> list[dict[str, str]]:
    """Сообщения до текущего хода: [{role: user|assistant, content}, ...]."""
    if not session_id or not session_id.strip():
        return []
    try:
        raw = get_client().get(_key(session_id))
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        out: list[dict[str, str]] = []
        for item in data:
            if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
                c = str(item.get("content", ""))
                out.append({"role": item["role"], "content": c})
        return out
    except Exception as e:
        logger.warning("redis get_history failed: %s", e)
        raise


def append_turn(session_id: str, user_text: str, assistant_text: str) -> None:
    if not session_id or not session_id.strip():
        return
    try:
        r = get_client()
        k = _key(session_id)
        raw = r.get(k)
        msgs: list[dict[str, str]] = []
        if raw:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
                        msgs.append(
                            {
                                "role": item["role"],
                                "content": str(item.get("content", "")),
                            }
                        )
        msgs.append({"role": "user", "content": user_text})
        msgs.append({"role": "assistant", "content": assistant_text})
        if len(msgs) > MAX_MESSAGES:
            msgs = msgs[-MAX_MESSAGES:]
        r.set(k, json.dumps(msgs, ensure_ascii=False), ex=SESSION_TTL_SEC)
    except Exception as e:
        logger.warning("redis append_turn failed: %s", e)
        raise
