# -*- coding: utf-8 -*-
"""Monitor official and industry news about premium banking services."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib import robotparser
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

from scanner.news_text import clean_news_text
from scanner.sources import PREMIUM_NEWS_SOURCES


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_PATH = PROJECT_ROOT / "data" / "monitored_premium_news.json"
USER_AGENT = "bank-analyst-premium-news/1.0"
LOOKBACK_DAYS = 180

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
MONTH_LABELS = (
    "", "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
)
GENERIC_PREMIUM_TERMS = (
    "премиаль", "премиум сервис", "премиум-сервис", "премиум клиент",
    "премиум сегмент", "премиум-сегмент",
    "premium banking", "private banking", "mir supreme", "мир supreme",
    "hnwi", "wealth management",
)
PACKAGE_TERMS_BY_BANK = {
    "Сбер": (
        "сберпремьер", "сбер премьер", "sber premier",
        "сберпервый", "сбер первый", "sber first", "sber private",
    ),
    "Альфа-Банк": (
        "alfa only", "альфа only", "альфа онли",
        "a-club", "a club", "а-клуб", "а клуб",
    ),
    "ВТБ": (
        "втб привилег", "привилег",
        "прайм+", "прайм плюс", "prime+",
    ),
    "Газпромбанк": (
        "газпром бонус премиум", "гпб премиум", "гпб private",
    ),
    "Озон Банк": (
        "ozon ultra", "озон ultra", "ozon ультра", "озон ультра",
        "ultra bronze", "ultra silver", "ultra gold", "ultra platinum",
    ),
    "Райффайзен Банк": (
        "райффайзен premium", "райффайзен премиум",
        "premium banking райффайзен",
    ),
    "Т-Банк": (
        "t-premium", "t premium", "т-премиум", "т премиум",
        "t-private", "t private", "т-private", "т private",
        "premium bronze", "premium silver", "premium gold",
        "premium diamond",
    ),
    "Инго Банк": (
        "инго премиум", "инго premium", "ингокарта премиальная",
        "премиальная ингокарта", "премиальная карта ингосстрах банка",
    ),
    "ОТП Банк": (
        "otp premium", "отп premium", "отп премиум",
        "otp private", "отп private",
    ),
    "БКС Банк": (
        "бкс ультима", "bcs ultima", "ultima консьерж",
    ),
    "МТС Банк": (
        "мтс premium", "мтс премиум", "mts premium",
        "мтс private", "mts private",
    ),
    "Альфа-Капитал": (
        "alfa wealth", "альфа wealth",
    ),
}
PREMIUM_TERMS = (
    *GENERIC_PREMIUM_TERMS,
    *(term for terms in PACKAGE_TERMS_BY_BANK.values() for term in terms),
)
CHANGE_TERMS = (
    "измен", "меня", "обнов", "улучш", "запуст", "запуска", "открыл",
    "добав", "теперь", "вместо", "повыс", "пониз", "увелич", "уменьш",
    "отмен", "ввод", "начнет", "начнёт", "станет", "появ",
    "стал доступ", "стала доступ", "стали доступ", "новые преимуществ",
    "новое премиаль", "новый премиаль", "новую премиаль",
)
STRONG_CONDITION_TERMS = (
    "измен", "обновляет условия", "обновил условия", "обновила условия",
    "обновленный тариф", "обновлённый тариф", "вместо", "отмен",
    "отключ", "огранич",
    "повыс", "пониз", "увелич", "уменьш", "ввод", "начнет",
    "начнёт", "станет",
)
EVENT_TERMS = (
    "приглашаем", "встречаемся", "ждем вас", "ждём вас",
    "состоится", "пройдет", "пройдёт", "регистрация на",
    "открыта регистрация", "организовал", "организовала",
    "провел", "провёл", "провела", "устроил", "устроила",
    "прошел", "прошёл", "прошла",
)
BENEFIT_TERMS = (
    "кэшбэк", "кешбэк", "скидк", "бонус", "сертификат",
    "компенсац", "привилег", "спецпредлож", "специальное предлож",
    "доступ", "бизнес зал", "бизнес-зал", "лаундж",
)
LIFESTYLE_TERMS = (
    "мероприят", "мастер класс", "мастер-класс", "концерт",
    "подкаст", "амбассадор", "ресторан", "бар", "путешеств",
    "маршрут", "тренировк", "дегустац", "коллаборац",
)
MARKET_TERMS = (
    "исследован", "рынок", "капитал", "сегмент", "динамик",
    "аналитик", "статистик",
)
DOCUMENT_TERMS = (
    "тариф", "условия обслуживания", "условия предоставления",
    "правила программы", "программа лояльности", "публичная оферта",
)
EXCLUDED_TERMS = (
    "эквайринг", "факторинг", "расчетно кассов", "расчётно кассов",
    "кредит для бизнеса", "корпоративным клиентам",
)
BANK_ALIASES = {
    "Сбер": ("сбер", "сбербанк"),
    "Альфа-Банк": ("альфа-банк", "альфа банк", "alfa bank"),
    "ВТБ": ("втб",),
    "Газпромбанк": ("газпромбанк",),
    "Озон Банк": ("ozon банк", "озон банк", "ozon банка", "озон банка"),
    "Райффайзен Банк": ("райффайзен",),
    "Т-Банк": ("т-банк", "т банк", "т‑банк", "t-bank"),
    "Инго Банк": ("инго банк", "ингосстрах банк", "ингосстрах банка"),
    "ОТП Банк": ("отп банк", "otp bank", "отп банка"),
    "БКС Банк": ("бкс банк", "бкс ультима", "bcs bank", "bcs ultima"),
    "МТС Банк": ("мтс банк", "mts bank", "мтс банка"),
    "Альфа-Капитал": ("альфа-капитал", "альфа капитал", "alfa capital"),
    "Уралсиб": ("уралсиб",),
    "Совкомбанк": ("совкомбанк",),
    "МКБ": ("мкб", "московский кредитный банк"),
    "Банк ДОМ.РФ": ("банк дом.рф", "банк дом рф", "дом.рф"),
    "Русский Стандарт": ("русский стандарт",),
}

PACKAGE_TERMS_BY_BANK.update({
    "Уралсиб": (
        "уралсиб премиум", "премиум старт", "premium light",
        "пакет услуг премиум", "пакета услуг премиум", "private banking",
    ),
    "Совкомбанк": (
        "xalva premium", "халва premium", "wealth management premium",
        "wm premium", "x card premium", "x-card premium",
    ),
    "МКБ": (
        "мкб премиум", "премиум плюс", "мкб private",
    ),
    "Банк ДОМ.РФ": (
        "пакет услуг премиальный", "дом.рф премиум",
    ),
    "Русский Стандарт": (
        "mir supreme premium", "мир supreme premium",
        "пакет услуг премиум",
    ),
})
AMBIGUOUS_BANK_DETECTION_TERMS = {
    "привилег", "private banking", "premium banking",
    "пакет услуг премиум", "пакета услуг премиум",
    "пакет услуг премиальный", "wealth management premium",
    "mir supreme premium", "мир supreme premium",
}


class PremiumNewsError(RuntimeError):
    """Raised when a news source cannot be safely scanned."""


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\u00a0", " ")).strip()


def _match_text(value: str) -> str:
    """Normalize typography so package aliases match dashes and spacing."""
    value = _clean_text(value).casefold().replace("ё", "е")
    value = re.sub(r"[‐‑‒–—−_/]+", " ", value)
    value = re.sub(r"[«»\"'()]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, "", "", ""))


def _record_id(bank: str, url: str) -> str:
    return hashlib.sha256(
        f"{bank.casefold()}\n{_canonical_url(url)}".encode("utf-8")
    ).hexdigest()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = _match_text(text)
    return any(_match_text(term) in normalized for term in terms)


def is_relevant(text: str, bank: str = "") -> bool:
    """Return True for changes tied to premium language or a bank package."""
    if _contains_any(text, EXCLUDED_TERMS):
        return False
    package_terms = PACKAGE_TERMS_BY_BANK.get(bank, ())
    premium_terms = (*GENERIC_PREMIUM_TERMS, *package_terms)
    bank_terms = BANK_ALIASES.get(bank, ())
    segments = [
        _clean_text(item)
        for item in re.split(
            r"(?:[.!?]\s+|[▪▫🟢✅☑️]\s*)",
            text,
        )
        if _clean_text(item)
    ]
    if not segments:
        segments = [text]
    for index, segment in enumerate(segments):
        windows = [segment]
        if index + 1 < len(segments):
            windows.append(f"{segment} {segments[index + 1]}")
        for window in windows:
            has_package = _contains_any(window, package_terms)
            has_premium = _contains_any(window, premium_terms)
            names_bank = _contains_any(window, bank_terms)
            if (
                has_premium
                and (
                    _contains_any(window, CHANGE_TERMS)
                    or _contains_any(window, EVENT_TERMS)
                    or _contains_any(window, MARKET_TERMS)
                    or (
                        _contains_any(window, BENEFIT_TERMS)
                        and (has_package or names_bank)
                    )
                )
            ):
                return True
    return False


def classify_event(text: str) -> str:
    """Classify an accepted item for the landing filter."""
    if _contains_any(text, ("по слухам", "не подтвержден", "не подтверждён",
                            "без подтверждающ")):
        return "rumor"
    if (
        _contains_any(text, ("запуст", "запуска"))
        and _contains_any(text, LIFESTYLE_TERMS)
    ):
        return "lifestyle"
    if _contains_any(text, ("запуст", "запуска")):
        return "launch"
    if _contains_any(text, DOCUMENT_TERMS):
        return "document"
    if _contains_any(text, STRONG_CONDITION_TERMS):
        return "conditions"
    if _contains_any(text, EVENT_TERMS):
        return "lifestyle"
    if _contains_any(text, BENEFIT_TERMS):
        return "benefit"
    if _contains_any(text, LIFESTYLE_TERMS):
        return "lifestyle"
    if _contains_any(text, MARKET_TERMS):
        return "market"
    if _contains_any(text, CHANGE_TERMS) and not _contains_any(text, ("офис", "филиал")):
        return "conditions"
    return "news"


def detect_bank(text: str) -> str:
    lowered = _match_text(text)
    matched = set()
    for bank, aliases in BANK_ALIASES.items():
        if any(_match_text(alias) in lowered for alias in aliases):
            matched.add(bank)
    for bank, package_terms in PACKAGE_TERMS_BY_BANK.items():
        if any(
            _match_text(term) in lowered
            for term in package_terms
            if term not in AMBIGUOUS_BANK_DETECTION_TERMS
        ):
            matched.add(bank)
    if len(matched) == 1:
        return next(iter(matched))
    if len(matched) > 1:
        return "Рынок"
    compact = re.search(r"\b([А-ЯЁ][А-Яа-яЁё-]{2,}банк)\b", text)
    if compact:
        return compact.group(1)
    before = re.search(
        r"\b([А-ЯЁA-Z][А-Яа-яЁёA-Za-z0-9.-]{2,})\s+Банк\b",
        text,
    )
    if before:
        return f"{before.group(1)} Банк"
    after = re.search(
        r"\bБанк\s+[«\"]?([А-ЯЁA-Z][А-Яа-яЁёA-Za-z0-9.-]{2,})",
        text,
    )
    if after:
        return f"{after.group(1)} Банк"
    return ""


def parse_news_date(text: str, now: datetime) -> datetime | None:
    clean = _clean_text(text).casefold()
    for pattern, date_format in (
        (r"\b(\d{4}-\d{2}-\d{2})\b", "%Y-%m-%d"),
        (r"\b(\d{2}\.\d{2}\.\d{4})\b", "%d.%m.%Y"),
        (r"\b(\d{1,2}/\d{1,2}/\d{4})\b", "%d/%m/%Y"),
    ):
        match = re.search(pattern, clean)
        if match:
            try:
                return datetime.strptime(match.group(1), date_format)
            except ValueError:
                pass

    match = re.search(
        r"\b(\d{1,2})\s+(" + "|".join(MONTHS) + r")(?:\s*,?\s*(20\d{2}))?",
        clean,
    )
    if match:
        year = int(match.group(3) or now.year)
        try:
            return datetime(year, MONTHS[match.group(2)], int(match.group(1)))
        except ValueError:
            return None
    if re.search(r"\b\d{1,2}:\d{2}\b", clean):
        return datetime(now.year, now.month, now.day)
    return None


def _date_label(value: datetime) -> str:
    return f"{MONTH_LABELS[value.month]} {value.year}"


def _article_context(link: Tag) -> str:
    container = link.find_parent(["article", "li"])
    if container is None:
        return ""
    context = _clean_text(container.get_text(" ", strip=True))
    # A giant wrapper can contain many unrelated cards. In that case only the
    # link title is safe evidence; otherwise one premium card contaminates all.
    return context if len(context) <= 900 else ""


def parse_listing(
    page_html: str,
    source: dict,
    *,
    now: datetime | None = None,
) -> list[dict]:
    """Extract relevant recent article candidates from one listing page."""
    now = now or datetime.now()
    soup = BeautifulSoup(page_html, "html.parser")
    base_host = urlparse(source["url"]).netloc.lower()
    records = []
    seen_urls = set()

    for order, link in enumerate(soup.find_all("a", href=True)[:800], start=1):
        title = _clean_text(link.get_text(" ", strip=True))
        if not 12 <= len(title) <= 280:
            continue
        article_url = _canonical_url(urljoin(source["url"], link["href"]))
        parsed_url = urlparse(article_url)
        if parsed_url.scheme not in {"http", "https"}:
            continue
        if parsed_url.netloc.lower() != base_host or article_url in seen_urls:
            continue
        if article_url.rstrip("/") == _canonical_url(source["url"]).rstrip("/"):
            continue
        if re.search(r"/(?:page)?\d+/?$", parsed_url.path):
            continue

        context = _article_context(link)
        bank = source.get("bank", "") or detect_bank(f"{title} {context}")
        if not bank or not is_relevant(f"{title} {context}", bank):
            continue
        published = parse_news_date(title, now) or parse_news_date(context, now)
        if published is None:
            continue
        if published < now - timedelta(days=LOOKBACK_DAYS):
            continue

        seen_urls.add(article_url)
        records.append(
            _make_record(
                bank=bank,
                published=published,
                text=title,
                url=article_url,
                source=source,
                raw_text=context[:1200],
                order=order,
            )
        )
    return records


def parse_direct(
    page_html: str,
    source: dict,
    *,
    now: datetime | None = None,
) -> list[dict]:
    """Turn a registered official announcement into one auditable record."""
    now = now or datetime.now()
    soup = BeautifulSoup(page_html, "html.parser")
    heading = soup.find("h1") or soup.find("title")
    title = _clean_text(heading.get_text(" ", strip=True) if heading else source["name"])
    page_text = _clean_text(soup.get_text(" ", strip=True))
    published = _published_from_markup(soup, now)
    published = published or parse_news_date(page_text[:5000], now) or now
    title_is_relevant = is_relevant(title, source.get("bank", ""))

    candidates = []
    for position, node in enumerate(soup.find_all(["h2", "h3", "p", "li"])):
        value = _clean_text(node.get_text(" ", strip=True))
        if not 18 <= len(value) <= 220 or value == title:
            continue
        concrete_privilege = (
            title_is_relevant
            and bool(re.search(r"\d", value))
            and _contains_any(
                value,
                (
                    "кэшбэк", "кешбэк", "преференц", "бизнес зал",
                    "такси", "ресторан", "актив", "обслуживан", "категор",
                    "комисси", "остат", "покуп",
                ),
            )
        )
        if (
            is_relevant(value, source.get("bank", ""))
            or (
                _contains_any(value, CHANGE_TERMS)
                and is_relevant(f"{title} {value}", source.get("bank", ""))
            )
            or concrete_privilege
        ):
            score = 0
            score += 3 if re.search(r"\d", value) else 0
            score += 2 if any(
                term in value.casefold()
                for term in (
                    "кэшбэк", "кешбэк", "преференц", "бизнес-зал",
                    "такси", "ресторан", "актив", "обслуживан", "категор",
                )
            ) else 0
            score += 3 if "вместо" in value.casefold() else 0
            score += 2 if "компенсац" in value.casefold() else 0
            score += 1 if len(value) >= 45 else 0
            score -= 3 if value.casefold().startswith(("что ", "улучшаем «")) else 0
            candidates.append((score, position, value))
    snippets = [
        value
        for _score, _position, value in sorted(
            candidates,
            key=lambda item: (-item[0], item[1]),
        )[:3]
    ]
    text = ". ".join(dict.fromkeys([title, *snippets]))
    return [
        _make_record(
            bank=source["bank"],
            published=published,
            text=_shorten_excerpt(text, 650),
            url=source["url"],
            source=source,
            raw_text=page_text[:1600],
            order=1,
            event_type=classify_event(text),
        )
    ]


def parse_landing(
    page_html: str,
    source: dict,
    *,
    now: datetime | None = None,
) -> list[dict]:
    """Extract dated premium tariff/document updates linked by a bank landing."""
    now = now or datetime.now()
    soup = BeautifulSoup(page_html, "html.parser")
    records = []
    seen_urls = set()
    allowed_hosts = {
        urlparse(source["url"]).netloc.lower(),
        *(host.lower() for host in source.get("allowed_hosts", [])),
    }
    premium_terms = (
        *GENERIC_PREMIUM_TERMS,
        *PACKAGE_TERMS_BY_BANK.get(source.get("bank", ""), ()),
    )

    for order, link in enumerate(soup.find_all("a", href=True)[:1200], start=1):
        url = _canonical_url(urljoin(source["url"], link.get("href", "")))
        parsed = urlparse(url)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.netloc.lower() not in allowed_hosts
            or url in seen_urls
        ):
            continue
        label = _clean_text(link.get_text(" ", strip=True))
        parent = link.find_parent(["li", "article", "section", "div", "p"])
        context = _clean_text(parent.get_text(" ", strip=True)) if parent else label
        if (
            len(context) > 700
            or (parent is not None and len(parent.find_all("a", href=True)) > 1)
        ):
            context = label
        evidence = _clean_text(f"{label} {context}")
        is_document = (
            parsed.path.casefold().endswith((".pdf", ".xlsx", ".doc", ".docx"))
            or _contains_any(evidence, DOCUMENT_TERMS)
        )
        if not is_document or not _contains_any(evidence, premium_terms):
            continue
        published = parse_news_date(evidence, now)
        if published is None or published < now - timedelta(days=LOOKBACK_DAYS):
            continue
        seen_urls.add(url)
        display_text = label if len(label) >= 12 else context
        display_text = _shorten_excerpt(display_text, 360)
        records.append(
            _make_record(
                bank=source["bank"],
                published=published,
                text=display_text,
                url=url,
                source=source,
                raw_text=evidence[:1600],
                order=order,
                event_type="document",
            )
        )
    return records


def _published_from_markup(soup: BeautifulSoup, now: datetime) -> datetime | None:
    for node in soup.select("time[datetime], meta[property='article:published_time']"):
        raw = node.get("datetime") or node.get("content") or ""
        if not raw:
            continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            parsed = parse_news_date(raw, now)
            if parsed:
                return parsed
    return None


def _strip_channel_footer(text: str) -> str:
    """Remove channel branding that must not make an unrelated post relevant."""
    value = re.sub(
        r"(?:⭐️?\s*)?СберПремьер\s+в\s+МАКС.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"(?:✌️|🌍|📱)?\s*(?:ВТБ|Газпромбанк|Инго Банк)\s+в"
        r"\s*(?:Макс|МАКС|ВК).*$",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\s+@[A-Za-z0-9_]{4,}\s*$", "", value, flags=re.IGNORECASE)
    return _clean_text(value)


def _shorten_excerpt(text: str, max_length: int) -> str:
    """Keep news cards compact without rewriting the source text."""
    value = text.strip()
    if len(value) <= max_length:
        return value
    fragment = value[:max_length]
    sentence_end = max(fragment.rfind(". "), fragment.rfind("! "), fragment.rfind("? "))
    if sentence_end >= 140:
        return fragment[: sentence_end + 1].rstrip()
    word_end = fragment.rfind(" ")
    return fragment[:word_end].rstrip(" ,;:-") + "…"


def _premium_excerpt(text: str, bank: str, max_length: int = 360) -> str:
    """Start display text near the first concrete premium-service reference."""
    terms = (*GENERIC_PREMIUM_TERMS, *PACKAGE_TERMS_BY_BANK.get(bank, ()))
    normalized = _match_text(text)
    positions = []
    for term in terms:
        position = normalized.find(_match_text(term))
        if position >= 0:
            positions.append(position)
    first = min(positions) if positions else 0
    if first <= 220:
        return _shorten_excerpt(text, max_length)

    # Character positions stay close after typography normalization. Move to
    # the beginning of the matching sentence so the card remains readable.
    start = max(
        text.rfind(mark, 0, first)
        for mark in (". ", "! ", "? ", "⬆️ ", "☑️ ", "✅ ", "🟢 ")
    )
    start = 0 if start < 0 else start + 2
    return _shorten_excerpt(text[start:], max_length)


def parse_telegram_listing(
    page_html: str,
    source: dict,
    *,
    now: datetime | None = None,
) -> list[dict]:
    """Extract relevant posts from an official Telegram public channel."""
    now = now or datetime.now()
    soup = BeautifulSoup(page_html, "html.parser")
    records = []
    for order, wrapper in enumerate(
        soup.select(".tgme_widget_message_wrap")[:80],
        start=1,
    ):
        body = wrapper.select_one(".tgme_widget_message_text")
        date_link = wrapper.select_one(".tgme_widget_message_date")
        if body is None or date_link is None:
            continue
        raw_text = _clean_text(body.get_text(" ", strip=True))
        text = _strip_channel_footer(raw_text)
        url = _canonical_url(urljoin(source["url"], date_link.get("href", "")))
        allowed_urls = {
            _canonical_url(item)
            for item in source.get("include_urls", [])
        }
        if allowed_urls and url not in allowed_urls:
            continue
        bank = source.get("bank", "") or detect_bank(text)
        if not text or not url or not bank or not is_relevant(text, bank):
            continue
        published = _published_from_markup(wrapper, now)
        if published is None:
            published = parse_news_date(text, now)
        if published is None:
            continue
        if (
            not source.get("historical")
            and published < now - timedelta(days=LOOKBACK_DAYS)
        ):
            continue
        records.append(
            _make_record(
                bank=bank,
                published=published,
                text=_premium_excerpt(text, bank),
                url=url,
                source=source,
                raw_text=raw_text[:1600],
                order=order,
            )
        )
    return records


def _make_record(
    *,
    bank: str,
    published: datetime,
    text: str,
    url: str,
    source: dict,
    raw_text: str,
    order: int,
    event_type: str | None = None,
) -> dict:
    date_iso = published.strftime("%Y-%m-%d")
    display_text = clean_news_text(_clean_text(text))
    return {
        "bank": bank,
        "dateLabel": _date_label(published),
        "dateSort": date_iso,
        "text": display_text,
        "sourcePage": _canonical_url(url),
        "source_name": source["name"],
        "source_id": source["id"],
        "source_type": source["source_type"],
        "origin": "news_monitor",
        "reliability_status": (
            "official" if source["source_type"] == "official" else "industry"
        ),
        "date_checked": datetime.now(timezone.utc).date().isoformat(),
        "raw_text": _clean_text(raw_text),
        "order": order,
        "record_id": _record_id(bank, url),
        "event_type": event_type or classify_event(display_text),
    }


def _robots_allows(url: str, requester: Callable[..., object]) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = requester(
            robots_url,
            timeout=15,
            headers={"User-Agent": USER_AGENT},
        )
        if getattr(response, "status_code", 200) >= 400:
            return True
        parser = robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(getattr(response, "text", "").splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except Exception:  # noqa: BLE001 - unavailable robots.txt does not imply disallow
        return True


def _fetch_source(
    source: dict,
    requester: Callable[..., object],
) -> list[dict]:
    if not _robots_allows(source["url"], requester):
        raise PremiumNewsError(f"robots.txt запрещает {source['url']}")
    last_error = None
    for _attempt in range(3):
        try:
            response = requester(
                source["url"],
                timeout=30,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            break
        except Exception as exc:  # noqa: BLE001 - retry transient bank-site errors
            last_error = exc
    else:
        raise PremiumNewsError(
            f"не удалось загрузить {source['url']}: {last_error}"
        ) from last_error

    content = getattr(response, "content", b"")
    if content:
        page_html = content.decode("utf-8", errors="replace")
    else:
        page_html = getattr(response, "text", "")
    if source["kind"] == "direct":
        return parse_direct(page_html, source)
    if source["kind"] == "telegram":
        return parse_telegram_listing(page_html, source)
    if source["kind"] == "landing":
        return parse_landing(page_html, source)
    return parse_listing(page_html, source)


def load_monitored_premium_news(
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> list[dict]:
    if not cache_path.exists():
        return []
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Не удалось прочитать кеш новостного монитора: %s", exc)
        return []
    records = payload.get("records", []) if isinstance(payload, dict) else []
    return records if isinstance(records, list) else []


def _write_cache(payload: dict, cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(cache_path)


def sync_premium_news_sources(
    bank_id: str | None = None,
    *,
    cache_path: Path = DEFAULT_CACHE_PATH,
    requester: Callable[..., object] | None = None,
    source_registry: list[dict] | None = None,
) -> dict:
    """Scan registered news sources and atomically merge their latest records."""
    request = requester or requests.get
    registry = source_registry or PREMIUM_NEWS_SOURCES
    selected = [
        source for source in registry
        if not bank_id or not source.get("bank_id") or source.get("bank_id") == bank_id
    ]
    previous = load_monitored_premium_news(cache_path)
    previous_by_id = {
        item.get("record_id"): item
        for item in previous
        if isinstance(item, dict) and item.get("record_id")
    }
    discovered = 0
    duplicates = 0
    sources_ok = []
    sources_failed = {}
    fresh_records = []

    for source in selected:
        try:
            records = _fetch_source(source, request)
            fresh_records.extend(records)
            sources_ok.append(source["name"])
        except PremiumNewsError as exc:
            sources_failed[source["name"]] = str(exc)

    # A listing is only a window into a source's history.  Pagination and
    # shorter current pages must not erase news that was already observed.
    merged_by_id = dict(previous_by_id)
    for item in fresh_records:
        record_id = item["record_id"]
        if record_id in previous_by_id:
            duplicates += 1
        else:
            discovered += 1
        merged_by_id[record_id] = item

    records = sorted(
        merged_by_id.values(),
        key=lambda item: (
            item.get("dateSort", ""),
            item.get("source_type") == "official",
            item.get("source_name", ""),
        ),
        reverse=True,
    )
    synced_at = datetime.now(timezone.utc).isoformat()
    _write_cache(
        {
            "schema_version": 1,
            "synced_at": synced_at,
            "records": records,
            "sources": {
                "ok": sources_ok,
                "failed": sources_failed,
            },
        },
        cache_path,
    )
    return {
        "records": records,
        "discovered": discovered,
        "duplicates": duplicates,
        "sources_ok": sources_ok,
        "sources_failed": sources_failed,
        "synced_at": synced_at,
    }
