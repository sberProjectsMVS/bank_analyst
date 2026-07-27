from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from landing.premium_changes import _source_button_url
from scanner.editorial_news import (
    EditorialNewsError,
    load_editorial_news,
    parse_editorial_csv,
    sync_editorial_news,
)


VALID_CSV = """Банк,Дата,Новость,Источник
Сбер,2026-04-15,Изменились условия начисления бонусов,https://www.sberbank.com/news
ВТБ,20.03.2026,Обновлена программа привилегий,https://www.vtb.ru/news/
"""


class FakeResponse:
    def __init__(self, text: str, status_error: Exception | None = None):
        self.text = text
        self.encoding = "utf-8"
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error


class EditorialNewsTests(unittest.TestCase):
    def test_parse_builds_landing_records(self):
        changes, duplicates = parse_editorial_csv(VALID_CSV)

        self.assertEqual(duplicates, 0)
        self.assertEqual([change["bank"] for change in changes], ["Сбер", "ВТБ"])
        self.assertEqual(changes[0]["dateLabel"], "апр 2026")
        self.assertEqual(changes[0]["dateSort"], "2026-04-15")
        self.assertEqual(changes[0]["origin"], "google_sheets")
        self.assertEqual(changes[0]["raw"]["row_number"], 2)

    def test_duplicate_rows_are_skipped(self):
        changes, duplicates = parse_editorial_csv(
            VALID_CSV + VALID_CSV.splitlines()[1] + "\n"
        )

        self.assertEqual(len(changes), 2)
        self.assertEqual(duplicates, 1)

    def test_incomplete_row_rejects_entire_import(self):
        with self.assertRaisesRegex(EditorialNewsError, "Строка 2"):
            parse_editorial_csv(
                "Банк,Дата,Новость,Источник\n"
                "Сбер,2026-04-15,Новость без ссылки,\n"
            )

    def test_implausible_old_date_is_rejected(self):
        with self.assertRaisesRegex(EditorialNewsError, "год должен быть"):
            parse_editorial_csv(
                "Банк,Дата,Новость,Источник\n"
                "Сбер,1900-01-26,Слишком старая дата,https://example.com/news\n"
            )

    def test_failed_sync_does_not_replace_last_valid_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "editorial.json"
            cache_path.write_text(
                json.dumps({"changes": [{"bank": "Сбер", "text": "Старая новость"}]}),
                encoding="utf-8",
            )

            with self.assertRaises(EditorialNewsError):
                sync_editorial_news(
                    "https://example.test/news.csv",
                    cache_path=cache_path,
                    fetcher=lambda *args, **kwargs: FakeResponse(
                        "Банк,Дата,Новость,Источник\n"
                        "Сбер,2026-04-15,Ошибка,\n"
                    ),
                )

            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(cached["changes"][0]["text"], "Старая новость")

    def test_load_uses_cache_when_sheet_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "editorial.json"
            cache_path.write_text(
                json.dumps({"changes": [{"bank": "Сбер", "text": "Кеш"}]}),
                encoding="utf-8",
            )
            with patch.dict(
                "os.environ",
                {"PREMIUM_NEWS_SHEET_CSV_URL": "https://example.test/news.csv"},
            ), patch(
                "scanner.editorial_news.requests.get",
                return_value=FakeResponse("", RuntimeError("offline")),
            ):
                changes, status = load_editorial_news(
                    sync=True,
                    cache_path=cache_path,
                )

            self.assertEqual(changes[0]["text"], "Кеш")
            self.assertTrue(status["failed"])
            self.assertTrue(status["from_cache"])

    def test_editorial_card_uses_direct_row_source(self):
        source = "https://example.com/direct-news"
        self.assertEqual(
            _source_button_url(
                {
                    "bank": "Сбер",
                    "origin": "google_sheets",
                    "sourcePage": source,
                }
            ),
            source,
        )


if __name__ == "__main__":
    unittest.main()
