"""Единые имена коллекций Qdrant и подписи стран (синхронно с ingest.py и countries.json)."""
import json
from pathlib import Path

_METADATA = Path(__file__).resolve().parent.parent / "data" / "metadata" / "countries.json"


def rules_collection_name(country_code: str) -> str:
    """Коллекция = travel_rules_<код>, как в backend/scripts/ingest.py."""
    return f"travel_rules_{country_code.lower().strip()}"


def country_display_name(country_code: str) -> str:
    code = country_code.lower().strip()
    if _METADATA.exists():
        try:
            with open(_METADATA, "r", encoding="utf-8") as f:
                data = json.load(f)
            entry = data.get(code)
            if entry and isinstance(entry.get("name"), str):
                return entry["name"]
        except (json.JSONDecodeError, OSError):
            pass
    return code


def is_known_country(country_code: str) -> bool:
    """Код страны есть в countries.json (синхронно с фронтом)."""
    code = country_code.lower().strip()
    if not _METADATA.exists():
        return False
    try:
        with open(_METADATA, "r", encoding="utf-8") as f:
            data = json.load(f)
        return code in data
    except (json.JSONDecodeError, OSError):
        return False
