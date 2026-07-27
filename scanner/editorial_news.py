"""Load manually curated premium-banking news from Google Sheets."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests


LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "data" / "premium_news_sheet.json"
DEFAULT_CACHE_PATH = PROJECT_ROOT / "data" / "editorial_premium_news.json"

REQUIRED_COLUMNS = ("Банк", "Дата", "Новость", "Источник")
KNOWN_BANKS = {
    "Сбер",
    "ВТБ",
    "Альфа-Банк",
    "Газпромбанк",
    "Т-Банк",
    "ПСБ",
    "Совкомбанк",
    "Озон Банк",
    "Райффайзен Банк",
}
MONTH_LABELS = (
    "",
    "янв",
    "фев",
    "мар",
    "апр",
    "май",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
)


class EditorialNewsError(RuntimeError):
    """Raised when the editorial-news source cannot be safely imported."""


def load_sheet_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Return Google Sheets configuration, allowing an environment override."""
    config: dict = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EditorialNewsError(f"Не удалось прочитать конфигурацию Google Sheets: {exc}") from exc
        if isinstance(loaded, dict):
            config = loaded

    env_url = os.getenv("PREMIUM_NEWS_SHEET_CSV_URL", "").strip()
    if env_url:
        config["csv_url"] = env_url
    return config


def _parse_date(raw_value: str, row_number: int) -> datetime:
    value = raw_value.strip()
    for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(value, date_format)
            if not 2000 <= parsed.year <= datetime.now().year + 1:
                raise EditorialNewsError(
                    f"Строка {row_number}: год должен быть между 2000 "
                    f"и {datetime.now().year + 1}"
                )
            return parsed
        except ValueError:
            continue
    raise EditorialNewsError(
        f"Строка {row_number}: дата должна быть в формате ГГГГ-ММ-ДД "
        f"(получено: {raw_value!r})"
    )


def _validate_source_url(raw_value: str, row_number: int) -> str:
    value = raw_value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise EditorialNewsError(
            f"Строка {row_number}: в колонке «Источник» нужна полная ссылка http(s)"
        )
    return value


def _fingerprint(bank: str, date_iso: str, text: str, source_url: str) -> str:
    payload = "\n".join((bank.casefold(), date_iso, " ".join(text.split()), source_url))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_editorial_csv(csv_text: str) -> tuple[list[dict], int]:
    """Validate Google Sheets CSV atomically and return landing-ready records."""
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    fieldnames = tuple((name or "").strip() for name in (reader.fieldnames or []))
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        raise EditorialNewsError(
            "В Google Sheets отсутствуют обязательные колонки: " + ", ".join(missing)
        )

    changes: list[dict] = []
    seen: set[str] = set()
    duplicate_count = 0

    for row_number, raw_row in enumerate(reader, start=2):
        row = {(key or "").strip(): (value or "").strip() for key, value in raw_row.items()}
        values = [row.get(column, "") for column in REQUIRED_COLUMNS]
        if not any(values):
            continue
        empty = [column for column, value in zip(REQUIRED_COLUMNS, values) if not value]
        if empty:
            raise EditorialNewsError(
                f"Строка {row_number}: заполните поля " + ", ".join(empty)
            )

        bank, raw_date, text, raw_source = values
        if bank not in KNOWN_BANKS:
            raise EditorialNewsError(
                f"Строка {row_number}: неизвестный банк {bank!r}. "
                f"Допустимо: {', '.join(sorted(KNOWN_BANKS))}"
            )
        parsed_date = _parse_date(raw_date, row_number)
        source_url = _validate_source_url(raw_source, row_number)
        date_iso = parsed_date.strftime("%Y-%m-%d")
        record_id = _fingerprint(bank, date_iso, text, source_url)
        if record_id in seen:
            duplicate_count += 1
            continue
        seen.add(record_id)

        changes.append(
            {
                "bank": bank,
                "dateLabel": f"{MONTH_LABELS[parsed_date.month]} {parsed_date.year}",
                "dateSort": date_iso,
                "text": text,
                "sourcePage": source_url,
                "origin": "google_sheets",
                "order": row_number,
                "record_id": record_id,
                "raw": {
                    "date": raw_date,
                    "source_url": source_url,
                    "row_number": row_number,
                },
            }
        )

    return changes, duplicate_count


def _write_cache(payload: dict, cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(cache_path)


def load_editorial_cache(cache_path: Path = DEFAULT_CACHE_PATH) -> list[dict]:
    if not cache_path.exists():
        return []
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Не удалось прочитать кеш редакционных новостей: %s", exc)
        return []
    changes = payload.get("changes", []) if isinstance(payload, dict) else []
    return changes if isinstance(changes, list) else []


def sync_editorial_news(
    csv_url: str | None = None,
    *,
    cache_path: Path = DEFAULT_CACHE_PATH,
    fetcher: Callable[..., object] | None = None,
) -> dict:
    """Fetch, validate, and atomically cache the current Google Sheet."""
    config = load_sheet_config()
    source_url = (csv_url or config.get("csv_url") or "").strip()
    if not source_url:
        raise EditorialNewsError(
            "Не задан CSV-адрес Google Sheets в data/premium_news_sheet.json "
            "или PREMIUM_NEWS_SHEET_CSV_URL"
        )

    try:
        request = fetcher or requests.get
        for attempt in range(3):
            try:
                response = request(source_url, timeout=30)
                response.raise_for_status()
                response.encoding = response.encoding or "utf-8"
                csv_text = response.text
                break
            except requests.exceptions.ChunkedEncodingError:
                if attempt == 2:
                    raise
    except Exception as exc:
        raise EditorialNewsError(f"Не удалось загрузить Google Sheets: {exc}") from exc

    changes, duplicate_count = parse_editorial_csv(csv_text)
    synced_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": 1,
        "synced_at": synced_at,
        "source_url": source_url,
        "changes": changes,
    }
    _write_cache(payload, cache_path)
    return {
        "changes": changes,
        "imported": len(changes),
        "duplicates": duplicate_count,
        "synced_at": synced_at,
        "source_url": source_url,
    }


def load_editorial_news(
    *,
    sync: bool = True,
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> tuple[list[dict], dict]:
    """Use a fresh sheet when possible and the last valid cache otherwise."""
    config = load_sheet_config()
    configured = bool((config.get("csv_url") or "").strip())
    if sync and configured:
        try:
            result = sync_editorial_news(cache_path=cache_path)
            return result["changes"], {
                "configured": True,
                "failed": False,
                "from_cache": False,
                **{key: result[key] for key in ("imported", "duplicates", "synced_at")},
            }
        except EditorialNewsError as exc:
            LOGGER.warning("%s. Используется последняя корректная версия.", exc)
            return load_editorial_cache(cache_path), {
                "configured": True,
                "failed": True,
                "from_cache": True,
                "error": str(exc),
            }

    return load_editorial_cache(cache_path), {
        "configured": configured,
        "failed": False,
        "from_cache": True,
    }
