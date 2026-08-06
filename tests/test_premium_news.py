from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from landing import premium_changes
from scanner.premium_news import (
    classify_event,
    detect_bank,
    is_relevant,
    load_monitored_premium_news,
    parse_direct,
    parse_landing,
    parse_listing,
    parse_telegram_listing,
    sync_premium_news_sources,
)
from scanner.news_text import clean_news_text, strip_effective_date_emphasis


OFFICIAL_SOURCE = {
    "id": "vtb_test",
    "name": "Новости ВТБ",
    "bank_id": "vtb",
    "bank": "ВТБ",
    "source_type": "official",
    "kind": "listing",
    "url": "https://example.test/news/",
}


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class PremiumNewsTests(unittest.TestCase):
    def test_effective_date_removal_does_not_leave_leading_dash(self):
        raw = (
            "С 31 июля 2026 года — 5 категорий кэшбэка вместо 3; "
            "максимальный кэшбэк — до 30 000 ₽ в месяц"
        )

        self.assertEqual(
            strip_effective_date_emphasis(raw),
            "5 категорий кэшбэка вместо 3; максимальный кэшбэк — "
            "до 30 000 ₽ в месяц",
        )

    def test_news_text_removes_emoji_and_typed_smileys(self):
        raw = (
            "⭐️ Обновили условия 😊: кэшбэк 15% — до 5 000 ₽ :) "
            "Время 10:30. Спасибо)) ✈️"
        )

        self.assertEqual(
            clean_news_text(raw),
            "Обновили условия: кэшбэк 15% — до 5 000 ₽ "
            "Время 10:30. Спасибо",
        )

    def test_render_removes_emoji_from_existing_cached_news(self):
        records = [{
            "bank": "ВТБ",
            "dateSort": "2026-07-29",
            "dateLabel": "июл 2026",
            "text": "Улучшили Привилегию 🚀 :)",
            "event_type": "conditions",
            "sourcePage": "https://example.test/vtb",
            "source_type": "official",
            "order": 1,
        }]

        html = premium_changes.render_changes_app(
            premium_changes.group_by_bank(records),
            datetime(2026, 7, 29),
        )

        self.assertIn("Улучшили Привилегию", html)
        self.assertNotIn("🚀", html)
        self.assertNotIn(":)", html)

    def test_named_packages_are_recognized_without_word_premium(self):
        examples = (
            ("Сбер", "СберПервый обновляет условия доступа в бизнес-залы"),
            ("Сбер", "Новые преимущества СберПремьер"),
            ("ВТБ", "ВТБ улучшает условия «Привилегии»"),
            ("Альфа-Банк", "Alfa Only меняет программу привилегий"),
            ("Озон Банк", "Ozon Ultra запускает новые категории кешбэка"),
            ("Т-Банк", "Premium Diamond обновил лимиты трансферов"),
        )

        for bank, title in examples:
            with self.subTest(bank=bank, title=title):
                self.assertTrue(is_relevant(title, bank))

    def test_generic_privilege_word_is_not_premium_without_vtb_context(self):
        self.assertFalse(
            is_relevant("Новые привилегии по обычной зарплатной карте", "Сбер")
        )

    def test_shared_page_wrapper_does_not_contaminate_unrelated_links(self):
        page = """
        <div>
          <a href="/news/business/">Эквайринг 0% на три месяца 17 июня 2026</a>
          <a href="/news/ultra/">Ozon Банк запустил премиальное обслуживание
          клиентов 25 мая 2026</a>
        </div>
        """
        source = {
            **OFFICIAL_SOURCE,
            "id": "ozon_test",
            "name": "Новости Ozon Банка",
            "bank_id": "ozonbank",
            "bank": "Озон Банк",
        }

        records = parse_listing(page, source, now=datetime(2026, 7, 28))

        self.assertEqual(len(records), 1)
        self.assertIn("премиальное обслуживание", records[0]["text"])

    def test_new_bank_launch_and_client_event_are_included(self):
        source = {
            **OFFICIAL_SOURCE,
            "id": "ingo_test",
            "name": "Инго Банк",
            "bank_id": "ingo",
            "bank": "Инго Банк",
            "kind": "telegram",
            "url": "https://t.me/s/ingobankru",
        }
        page = """
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message_text">
            Добро пожаловать в мир привилегий: запускаем премиальное
            обслуживание Инго Банка
          </div>
          <a class="tgme_widget_message_date"
             href="https://t.me/ingobankru/630">
            <time datetime="2024-06-14T13:31:00+00:00"></time>
          </a>
        </div>
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message_text">
            Встречаемся на закрытом вечере для клиентов Инго Премиум
          </div>
          <a class="tgme_widget_message_date"
             href="https://t.me/ingobankru/900">
            <time datetime="2026-07-28T10:00:00+00:00"></time>
          </a>
        </div>
        """
        source["historical"] = True

        records = parse_telegram_listing(
            page,
            source,
            now=datetime(2026, 7, 28),
        )

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["bank"], "Инго Банк")
        self.assertEqual(records[0]["dateSort"], "2024-06-14")
        self.assertIn("закрытом вечере", records[1]["text"])

    def test_acquiring_is_rejected_even_next_to_premium_language(self):
        self.assertFalse(
            is_relevant(
                "Инго Премиум запускает интернет-эквайринг для бизнеса",
                "Инго Банк",
            )
        )

    def test_unregistered_bank_launch_is_discovered_from_title(self):
        title = "Совкомбанк запустил новое премиальное обслуживание клиентов"

        bank = detect_bank(title)

        self.assertEqual(bank, "Совкомбанк")
        self.assertTrue(is_relevant(title, bank))

    def test_multi_bank_roundup_is_ranked_as_market_not_first_named_bank(self):
        text = (
            "МТС Банк добавил пакет для премиальных клиентов. "
            "Сбер и ВТБ также изменили свои программы."
        )

        self.assertEqual(detect_bank(text), "Рынок")

    def test_unconfirmed_report_is_visibly_classified_as_rumor(self):
        self.assertEqual(
            classify_event(
                "По слухам, Сбер изменит премиальные тарифы без подтверждающих документов"
            ),
            "rumor",
        )

    def test_unrelated_branded_premium_subscription_is_rejected(self):
        self.assertFalse(
            is_relevant(
                "Максимум выгоды с подпиской Магнит Плюс Премиум",
                "ВТБ",
            )
        )

    def test_monitored_news_and_condition_changes_share_one_filterable_feed(self):
        pbi_change = {
            "bank": "Сбер",
            "dateSort": "2026-07-01",
            "dateLabel": "июл 2026",
            "text": "Изменились условия",
            "order": 1,
        }
        monitored_news = {
            "bank": "Инго Банк",
            "dateSort": "2026-07-20",
            "dateLabel": "июл 2026",
            "text": "Открылся новый премиальный офис",
            "order": 1,
        }
        with (
            patch.object(
                premium_changes,
                "fetch_pbi_updates",
                return_value=([pbi_change], 0),
            ),
            patch.object(
                premium_changes,
                "load_editorial_news",
                return_value=([], {"failed": False}),
            ),
            patch.object(
                premium_changes,
                "load_monitored_premium_news",
                return_value=[monitored_news],
            ),
        ):
            changes, _failed = premium_changes.collect_premium_updates()
            news = premium_changes.load_all_news()
            html = premium_changes.render_changes_app(
                premium_changes.group_by_bank(changes),
                datetime(2026, 7, 28),
                news,
            )

        self.assertEqual(changes, [monitored_news, pbi_change])
        self.assertEqual(news, [monitored_news])
        self.assertIn("<b>2</b> публикаций", html)
        self.assertNotIn("Все новости ·", html)
        self.assertIn('data-bank="Инго Банк"', html)
        self.assertIn("Все новости", html)

    def test_news_text_starts_with_substance_and_keeps_date_in_metadata_only(self):
        records = [{
            "bank": "ВТБ",
            "dateSort": "2026-07-31",
            "dateLabel": "июл 2026",
            "text": (
                "Изменения в программе лояльности ВТБ с 31 июля 2026 года "
                "1. Появится выбор 5 категорий вместо 3"
            ),
            "order": 1,
        }]

        cleaned = premium_changes._clean_news_record(records[0])
        html = premium_changes.render_changes_panel(
            premium_changes.group_by_bank([cleaned]),
            datetime(2026, 7, 31),
        )

        self.assertEqual(cleaned["text"], "1. Появится выбор 5 категорий вместо 3")
        self.assertNotIn("с 31 июля", html)
        self.assertIn("Новости · 1 публикаций", html)
        self.assertIn("Скрыть новости", html)

    def test_failed_pbi_refresh_keeps_last_complete_cached_feed(self):
        cached = [{
            "bank": "Сбер",
            "dateSort": "2026-06-01",
            "dateLabel": "июн 2026",
            "text": "Сохранённое изменение условий",
            "order": 1,
        }]
        with (
            patch.object(
                premium_changes,
                "fetch_pbi_updates",
                return_value=([], 7),
            ),
            patch.object(premium_changes, "_load_changes_cache", return_value=cached),
            patch.object(
                premium_changes,
                "load_editorial_news",
                return_value=([], {"failed": False}),
            ),
            patch.object(
                premium_changes,
                "load_monitored_premium_news",
                return_value=[],
            ),
        ):
            changes, failed = premium_changes.collect_premium_updates(use_cache=True)

        self.assertEqual(failed, 7)
        self.assertEqual(changes, cached)

    def test_landing_extracts_dated_premium_document_and_rejects_generic_file(self):
        source = {
            **OFFICIAL_SOURCE,
            "kind": "landing",
            "bank": "Уралсиб",
            "url": "https://example.test/premium/",
        }
        page = """
        <section>
          <a href="/docs/premium-14072026.pdf">
            Тариф Пакета услуг «Премиум» 14.07.2026
          </a>
          <a href="/docs/mortgage-14072026.pdf">
            Общие условия ипотеки 14.07.2026
          </a>
        </section>
        """

        records = parse_landing(page, source, now=datetime(2026, 7, 28))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event_type"], "document")
        self.assertEqual(records[0]["dateSort"], "2026-07-14")
        self.assertIn("Премиум", records[0]["text"])

    def test_channel_footer_does_not_make_personal_story_relevant(self):
        source = {
            **OFFICIAL_SOURCE,
            "id": "sberpremier_test",
            "name": "СберПремьер",
            "bank_id": "sber",
            "bank": "Сбер",
            "kind": "telegram",
            "url": "https://t.me/s/sberpremiernew",
        }
        page = """
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message_text">
            С отношениями нередко заканчивается и доверие. Поэтому делить
            имущество после развода бывает непросто.
            ⭐️ СберПремьер в МАКС
          </div>
          <a class="tgme_widget_message_date"
             href="https://t.me/sberpremiernew/1">
            <time datetime="2026-07-22T10:00:00+00:00"></time>
          </a>
        </div>
        """

        records = parse_telegram_listing(
            page,
            source,
            now=datetime(2026, 7, 28),
        )

        self.assertEqual(records, [])

    def test_existing_manager_story_is_not_a_news_event(self):
        self.assertFalse(
            is_relevant(
                "У клиентов с премиальным обслуживанием есть личный менеджер, "
                "который пригласит на эксклюзивное мероприятие.",
                "Сбер",
            )
        )

    def test_incidental_premium_participation_is_not_news(self):
        self.assertFalse(
            is_relevant(
                "Получите бонус за приглашение друга. Премиальные и "
                "зарплатные карты тоже участвуют.",
                "Газпромбанк",
            )
        )

    def test_thin_package_marketing_line_is_not_news(self):
        self.assertFalse(
            is_relevant(
                "О лучших столиках для клиентов А-Клуба и Alfa Only "
                "позаботимся мы.",
                "Альфа-Банк",
            )
        )

    def test_new_premium_office_is_news(self):
        self.assertTrue(
            is_relevant(
                "Инго Банк открыл новый премиальный офис в Иркутске.",
                "Инго Банк",
            )
        )

    def test_industry_telegram_detects_bank_for_each_post(self):
        source = {
            **OFFICIAL_SOURCE,
            "id": "industry_telegram",
            "name": "Профильный канал",
            "bank_id": "",
            "bank": "",
            "source_type": "industry",
            "kind": "telegram",
            "url": "https://t.me/s/example",
        }
        page = """
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message_text">
            Альфа-Банк: для клиентов Alfa Only появился кешбэк 15%
          </div>
          <a class="tgme_widget_message_date"
             href="https://t.me/example/10">
            <time datetime="2026-07-28T10:00:00+00:00"></time>
          </a>
        </div>
        """

        records = parse_telegram_listing(
            page,
            source,
            now=datetime(2026, 7, 28),
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["bank"], "Альфа-Банк")
        self.assertEqual(records[0]["source_type"], "industry")
        self.assertEqual(records[0]["event_type"], "benefit")

    def test_premium_benefit_and_lifestyle_categories_are_separate(self):
        self.assertTrue(
            is_relevant(
                "Для клиентов Alfa Only действует кешбэк 15% в NO ONE",
                "Альфа-Банк",
            )
        )
        self.assertEqual(
            classify_event("Для клиентов Alfa Only действует кешбэк 15%"),
            "benefit",
        )
        self.assertEqual(
            classify_event(
                "T-Premium организовал мастер-класс для клиентов в Москве"
            ),
            "lifestyle",
        )

    def test_landing_is_one_chronological_feed_across_banks(self):
        records = [
            {
                "bank": "Альфа-Банк",
                "dateSort": "2026-07-28",
                "dateLabel": "июл 2026",
                "text": "Alfa Only организовал мероприятие",
                "event_type": "lifestyle",
                "sourcePage": "https://example.test/alfa",
                "source_type": "official",
                "order": 1,
            },
            {
                "bank": "Т-Банк",
                "dateSort": "2026-07-29",
                "dateLabel": "июл 2026",
                "text": "T-Premium изменил доступ в бизнес-залы",
                "event_type": "conditions",
                "sourcePage": "https://example.test/tbank",
                "source_type": "official",
                "order": 1,
            },
        ]

        html = premium_changes.render_changes_app(
            premium_changes.group_by_bank(records),
            datetime(2026, 7, 29),
        )

        self.assertNotIn("js-change-bank-group", html)
        self.assertEqual(html.count("js-change-card"), 2)
        self.assertLess(
            html.index('data-bank="Т-Банк"'),
            html.index('data-bank="Альфа-Банк"'),
        )
        self.assertIn("Единая лента", html)

    def test_long_story_is_trimmed_to_premium_conditions(self):
        source = {
            **OFFICIAL_SOURCE,
            "id": "sberpremier_test",
            "name": "СберПремьер",
            "bank_id": "sber",
            "bank": "Сбер",
            "kind": "telegram",
            "url": "https://t.me/s/sberpremiernew",
        }
        story = "Личная история семьи и бизнеса. " * 12
        page = f"""
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message_text">
            {story}
            Обновили условия: балансы на счетах ИП дают право бесплатного
            Премиального обслуживания. От 2 млн ₽ подключается Уровень 1.
            ⭐️ СберПремьер в МАКС
          </div>
          <a class="tgme_widget_message_date"
             href="https://t.me/sberpremiernew/2">
            <time datetime="2026-07-27T10:00:00+00:00"></time>
          </a>
        </div>
        """

        records = parse_telegram_listing(
            page,
            source,
            now=datetime(2026, 7, 28),
        )

        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]["text"].startswith("Обновили условия"))
        self.assertNotIn("Личная история", records[0]["text"])

    def test_telegram_display_text_strips_emoji_but_keeps_raw_evidence(self):
        source = {
            **OFFICIAL_SOURCE,
            "id": "vtb_emoji_test",
            "name": "ВТБ",
            "bank_id": "vtb",
            "bank": "ВТБ",
            "kind": "telegram",
            "url": "https://t.me/s/vtb",
        }
        page = """
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message_text">
            🚀 ВТБ улучшил условия Привилегии: теперь 5 категорий кэшбэка :)
          </div>
          <a class="tgme_widget_message_date" href="https://t.me/vtb/100">
            <time datetime="2026-07-29T10:00:00+00:00"></time>
          </a>
        </div>
        """

        records = parse_telegram_listing(
            page,
            source,
            now=datetime(2026, 7, 29),
        )

        self.assertEqual(len(records), 1)
        self.assertNotIn("🚀", records[0]["text"])
        self.assertNotIn(":)", records[0]["text"])
        self.assertIn("🚀", records[0]["raw_text"])

    def test_listing_keeps_premium_change_and_rejects_unrelated_news(self):
        page = """
        <ul>
          <li><a href="/news/privilege/">ВТБ улучшает условия Привилегии</a>
              <time>28 июля 2026</time></li>
          <li><a href="/news/mortgage/">ВТБ снизил ставку по ипотеке</a>
              <time>28 июля 2026</time></li>
          <li><a href="/news/survey/">ВТБ провёл исследование туристов</a>
              <time>28 июля 2026</time></li>
        </ul>
        """
        records = parse_listing(
            page,
            OFFICIAL_SOURCE,
            now=datetime(2026, 7, 28),
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["bank"], "ВТБ")
        self.assertEqual(records[0]["dateSort"], "2026-07-28")
        self.assertEqual(records[0]["reliability_status"], "official")
        self.assertEqual(
            records[0]["sourcePage"],
            "https://example.test/news/privilege/",
        )

    def test_industry_listing_can_detect_bank_from_article_context(self):
        source = {
            **OFFICIAL_SOURCE,
            "id": "industry_test",
            "name": "Отраслевая лента",
            "bank_id": "",
            "bank": "",
            "source_type": "industry",
        }
        page = """
        <article>
          <span>Альфа-Банк</span>
          <a href="/news/only/">Обновлены условия премиального Alfa Only</a>
          <time>28 июля 2026</time>
        </article>
        """

        records = parse_listing(page, source, now=datetime(2026, 7, 28))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["bank"], "Альфа-Банк")
        self.assertEqual(records[0]["reliability_status"], "industry")

    def test_direct_page_preserves_source_text_and_url(self):
        source = {
            **OFFICIAL_SOURCE,
            "kind": "direct",
            "url": "https://example.test/promo/privilege/",
        }
        page = """
        <html><body>
          <h1>Улучшаем ВТБ «Привилегию» с 31 июля</h1>
          <h2>Улучшаем кешбэк</h2>
          <p>Теперь всегда 5 категорий вместо 3</p>
          <p>Обновленная программа начнет действовать с 31.07.2026 г.</p>
        </body></html>
        """
        records = parse_direct(page, source, now=datetime(2026, 7, 28))

        self.assertEqual(len(records), 1)
        self.assertIn("5 категорий вместо 3", records[0]["text"])
        self.assertEqual(records[0]["dateSort"], "2026-07-31")
        self.assertEqual(records[0]["sourcePage"], source["url"])

    def test_sync_is_idempotent_and_writes_atomic_cache(self):
        source = {**OFFICIAL_SOURCE, "url": "https://example.test/news/"}
        page = """
        <li><a href="/news/privilege/">Обновлены преимущества ВТБ Привилегии</a>
        <span>28 июля 2026</span></li>
        """

        def requester(url, **_kwargs):
            if url.endswith("/robots.txt"):
                return FakeResponse("User-agent: *\nAllow: /\n")
            return FakeResponse(page)

        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "news.json"
            first = sync_premium_news_sources(
                cache_path=cache_path,
                requester=requester,
                source_registry=[source],
            )
            second = sync_premium_news_sources(
                cache_path=cache_path,
                requester=requester,
                source_registry=[source],
            )

            self.assertEqual(first["discovered"], 1)
            self.assertEqual(second["discovered"], 0)
            self.assertEqual(second["duplicates"], 1)
            self.assertEqual(len(load_monitored_premium_news(cache_path)), 1)
            self.assertFalse(cache_path.with_suffix(".json.tmp").exists())
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)

    def test_successful_refresh_never_removes_older_source_records(self):
        source = {**OFFICIAL_SOURCE, "url": "https://example.test/news/"}
        current_page = ["""
        <li><a href="/news/old/">Обновлены преимущества ВТБ Привилегии</a>
        <span>27 июля 2026</span></li>
        """]

        def requester(url, **_kwargs):
            if url.endswith("/robots.txt"):
                return FakeResponse("User-agent: *\nAllow: /\n")
            return FakeResponse(current_page[0])

        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "news.json"
            sync_premium_news_sources(
                cache_path=cache_path,
                requester=requester,
                source_registry=[source],
            )
            current_page[0] = """
            <li><a href="/news/new/">Новые преимущества ВТБ Привилегии</a>
            <span>28 июля 2026</span></li>
            """
            result = sync_premium_news_sources(
                cache_path=cache_path,
                requester=requester,
                source_registry=[source],
            )

        self.assertEqual(len(result["records"]), 2)
        self.assertEqual(
            {record["dateSort"] for record in result["records"]},
            {"2026-07-27", "2026-07-28"},
        )

    def test_successful_landing_build_persists_complete_feed_cache(self):
        cached = [{
            "bank": "Сбер",
            "dateSort": "2026-07-27",
            "dateLabel": "июл 2026",
            "text": "Старая сохранённая новость",
            "order": 1,
        }]
        fresh = [{
            "bank": "ВТБ",
            "dateSort": "2026-07-28",
            "dateLabel": "июл 2026",
            "text": "Новая новость",
            "order": 1,
        }]
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "landing.html"
            cache_path = Path(tmp) / "feed.json"
            with (
                patch.object(
                    premium_changes, "fetch_pbi_updates", return_value=(fresh, 0),
                ),
                patch.object(
                    premium_changes, "_load_changes_cache", return_value=cached,
                ),
                patch.object(
                    premium_changes,
                    "load_editorial_news",
                    return_value=([], {"failed": False}),
                ),
                patch.object(
                    premium_changes, "load_monitored_premium_news", return_value=[],
                ),
                patch.object(premium_changes, "CHANGES_CACHE_PATH", cache_path),
            ):
                premium_changes.build_premium_changes_landing(Path(), output_path)

            payload = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(len(payload["records"]), 2)
        self.assertFalse(cache_path.with_suffix(".json.tmp").exists())

    def test_disallowed_source_is_reported_without_fetching_listing(self):
        requested = []

        def requester(url, **_kwargs):
            requested.append(url)
            return FakeResponse("User-agent: *\nDisallow: /news/\n")

        with tempfile.TemporaryDirectory() as tmp:
            result = sync_premium_news_sources(
                cache_path=Path(tmp) / "news.json",
                requester=requester,
                source_registry=[OFFICIAL_SOURCE],
            )

        self.assertEqual(len(result["sources_failed"]), 1)
        self.assertEqual(requested, ["https://example.test/robots.txt"])


if __name__ == "__main__":
    unittest.main()
