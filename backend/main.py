import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path

import app.metrics  # noqa: F401 — register custom metrics on the default Prometheus registry
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.chat_log import append_chat_log, append_error_log, mask_pii
from app.rag_config import is_known_country
from app import session_store
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger("vyezdnik")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, include_in_schema=False)

@app.get("/health")
def health():
    payload: dict = {"status": "ok"}
    try:
        session_store.ping_redis()
        payload["redis"] = "ok"
    except Exception:
        payload["redis"] = "unavailable"
    return payload

class ChatRequest(BaseModel):
    message: str
    session_id: str
    country: str

class AnalyticsEvent(BaseModel):
    event_type: str = Field(..., pattern="^(country_select|form_download_click)$")
    country_code: str | None = None
    country_label: str | None = None
    link_url: str | None = None
    link_text: str | None = None

@app.post("/chat")
def chat(req: ChatRequest):
    country = req.country.lower().strip()
    if not is_known_country(country):
        raise HTTPException(
            status_code=400,
            detail="Неизвестный код страны. Используйте одну из поддерживаемых стран.",
        )
    try:
        prior = session_store.get_history(req.session_id)
        # Lazy import: orchestrator pulls RAG/embedder and blocks for a long time on first load.
        from app.agents.orchestrator import orchestrator

        answer = orchestrator(req.message, country, prior_messages=prior)
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        append_error_log(country, req.session_id, msg)
        logger.error("chat failed: %s\n%s", msg, traceback.format_exc())
        raise HTTPException(
            status_code=503,
            detail="Сервис временно недоступен. Попробуйте позже или проверьте конфигурацию.",
        )

    try:
        session_store.append_turn(req.session_id, req.message, answer)
    except Exception as e:
        logger.warning("session_store.append_turn failed (ответ уже сгенерирован): %s", e)

    append_chat_log(country, req.message, answer)
    return {"answer": answer}

@app.post("/analytics")
def analytics(ev: AnalyticsEvent):
    log_dir = Path(__file__).resolve().parent / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "analytics.log"
    ts = datetime.now(timezone.utc).isoformat()
    safe_url = mask_pii(ev.link_url or "")
    safe_text = mask_pii(ev.link_text or "")
    line = (
        f"{ts}\tevent={ev.event_type}\t"
        f"code={ev.country_code or ''}\tlabel={ev.country_label or ''}\t"
        f"url={safe_url}\ttext={safe_text}\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
    return {"ok": True}