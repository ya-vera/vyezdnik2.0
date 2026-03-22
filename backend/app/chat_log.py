"""Простой журнал переписки для анализа качества RAG (без привязки к IP)."""
import re
from datetime import datetime, timezone
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
CHAT_LOG = _LOG_DIR / "chat.log"
ERROR_LOG = _LOG_DIR / "errors.log"


def mask_pii(text: str) -> str:
    """Маскирование потенциальных ПДн перед записью в лог."""
    if not text:
        return text
    t = text
    # Телефоны РФ: +7, 8, пробелы/скобки
    t = re.sub(
        r"\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
        "[PHONE]",
        t,
    )
    t = re.sub(
        r"(?<!\d)8[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)",
        "[PHONE]",
        t,
    )
    t = re.sub(r"(?<!\d)9\d{9}(?!\d)", "[PHONE]", t)
    # Серия и номер паспорта РФ (4 + 6 цифр подряд)
    t = re.sub(r"\b\d{4}\s?\d{6}\b", "[PASSPORT]", t)
    return t


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def append_chat_log(country: str, question: str, answer: str) -> None:
    _ensure_log_dir()
    ts = datetime.now(timezone.utc).isoformat()
    q = mask_pii(question.strip())
    a = mask_pii(answer.strip())
    line = f"{ts}\tcountry={country}\tQ: {q}\tA: {a}\n"
    with open(CHAT_LOG, "a", encoding="utf-8") as f:
        f.write(line)


def append_error_log(country: str, session_id: str, message: str) -> None:
    _ensure_log_dir()
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts}\tcountry={country}\tsession={session_id}\t{mask_pii(message)}\n"
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(line)
