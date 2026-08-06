# -*- coding: utf-8 -*-
"""Derived display model for additional premium benefits.

The scanner keeps normalized source fields such as ecosystem, auto, selectable
options and selection rules. Reports show a single user-facing "Другие
привилегии" list built from those fields without duplicating core rows.
"""

import re

from scanner.benefit_catalog import (
    benefit_id_for_title,
    canonical_title,
    classify_benefit,
    default_description,
)
from scanner.merge import field_value
from scanner.sources import NOT_FOUND

CORE_DUPLICATE_MARKERS = (
    "mir pass",
    "on·pass",
    "priority pass",
    "every lounge",
    "on·pack",
    "on.pack",
    "on pack",
    "бизнес-залы",
    "такси",
    "ресторан",
    "кафе",
    "поездк",
)

INSURANCE_LEAK_MARKERS = (
    "страхование",
    "страховой",
    "страховая",
    "страховую",
    "страховые",
    "виза",
    "визов",
    "рейс",
    "багаж",
    "медицинские расходы",
    "горные лыжи",
    "горнолыж",
    "сноуборд",
    "несчастный случай",
    "ассистанс",
    "assistance",
    "страховая сумма",
    "срок поездки",
    "отмена поездки",
    "задержка",
)

HEALTH_OPTION_MARKERS = (
    "телемедицин",
    "здоровье",
    "доктис",
    "сервис лучи",
    "медицинские онлайн консультации",
    "медицинская программа",
    "медицинское обследование",
    "лабораторная диагностик",
    "онкострахован",
    "медцентр",
    "чекап",
    "дмс",
)

ROADSIDE_MARKERS = (
    "помощь на дорогах",
    "автоконсьерж",
    "автоуслуги",
    "опция авто",
    "breakdown cover",
)

SPORT_BEAUTY_MARKERS = (
    "спорт и красота",
    "пакет спорт",
    "фитмост",
    "fitmost",
    "appoint",
)

OPTION_RE = re.compile(r"опция «([^»]+)»\s*\(([^)]{1,260})\)", re.IGNORECASE)
PACKAGE_RE = re.compile(
    r"пакет\s+«([^»]+)»\s*[—-]\s*([^;|\n•]{1,500})",
    re.IGNORECASE,
)
PACKAGE_PAREN_RE = re.compile(
    r"пакет\s+«([^»]+)»\s*\(([^|;\n•]{1,500})\)",
    re.IGNORECASE,
)

# User-facing comparison rows that take precedence over the catch-all
# "Другие привилегии" list.  A source fragment is removed from that list when
# the same fragment is already present in one of these normalized fields.
SPECIALIZED_BENEFIT_FIELDS = (
    "lounge_access",
    "concierge",
    "cashback",
    "transfers_payments",
    "cash_withdrawal",
    "supreme",
    "deposits",
    "insurance",
    "taxi",
    "restaurants",
    "auto",
    "roadside_option",
    "health_option",
    "samokat_option",
    "pets_option",
    "sport_beauty_option",
    "metal_card",
    "personal_banking_support",
)

SPECIALIZED_CATEGORY_MARKERS = (
    (("cashback",), ("кэшбэк", "кешбэк", "обмен")),
    (("sport_beauty_option",), SPORT_BEAUTY_MARKERS),
    (("auto", "roadside_option"), ROADSIDE_MARKERS),
    (("restaurants",), (
        "ресторан", "кафе", "чек в сутки", "чек за одну дату",
        "вагон ресторан",
    )),
    (("taxi",), ("такси", "трансфер")),
    (("lounge_access",), (
        "бизнес зал", "priority pass", "every lounge", "mir pass", "on pass",
    )),
    (("concierge",), ("консьерж", "concierge", "only assist", "pb service")),
    (("health_option",), ("здоровье", "телемедицина", "медицинский консьерж")),
    (("samokat_option",), ("самокат",)),
    (("pets_option",), ("питомцы", "ветеринар")),
)


def other_benefits_text(fields: dict) -> str:
    """Return a multiline bullet list for Excel/HTML display."""
    benefits = build_other_benefits(fields)
    if not benefits:
        return NOT_FOUND
    lines = []
    for item in benefits:
        line = f"• {item['title']}"
        if item.get("description"):
            line += f" — {item['description']}"
        if item.get("availability") == "selectable":
            line += " [опция на выбор]"
        elif item.get("availability") == "always_included" and _mixed_availability(benefits):
            line += " [включено постоянно]"
        lines.append(line)
    return "\n".join(lines)


def build_other_benefits(fields: dict) -> list[dict]:
    items = []
    _extend_from_text(items, field_value(fields.get("always_included_options", NOT_FOUND)),
                      "always_included")
    _extend_from_text(items, field_value(fields.get("selectable_options", NOT_FOUND)),
                      "selectable")
    _extend_from_text(items, field_value(fields.get("ecosystem", NOT_FOUND)), "unknown")
    standalone_ids = {"health", "samokat", "pets", "auto", "консьерж"}
    return [
        item for item in _dedupe(items)
        if (item.get("id") not in standalone_ids
            and not _is_roadside_item(item)
            and not _is_sport_beauty_item(item)
            and not _is_health_item(item)
            and not _duplicates_specialized_field(item, fields))
    ]


def _is_roadside_item(item: dict) -> bool:
    """Never expose the dedicated auto category in «Другие привилегии»."""
    text = _dedupe_text(
        " ".join((
            item.get("raw_text", ""),
            item.get("title", ""),
            item.get("description", ""),
        ))
    )
    return any(marker in text for marker in ROADSIDE_MARKERS)


def _is_sport_beauty_item(item: dict) -> bool:
    """Never repeat Fitmost/appoint in the catch-all benefits row."""
    text = _dedupe_text(
        " ".join((
            item.get("raw_text", ""),
            item.get("title", ""),
            item.get("description", ""),
        ))
    )
    return any(marker in text for marker in SPORT_BEAUTY_MARKERS)


def _is_health_item(item: dict) -> bool:
    """Never repeat a dedicated health service in other benefits."""
    text = _dedupe_text(
        " ".join((
            item.get("raw_text", ""),
            item.get("title", ""),
            item.get("description", ""),
        ))
    )
    if any(marker in text for marker in SPORT_BEAUTY_MARKERS):
        return False
    return any(marker in text for marker in HEALTH_OPTION_MARKERS)


def health_option_field(fields: dict):
    """Return confirmed health fragments as one dedicated category field."""
    direct = fields.get("health_option")
    if _has_value(direct):
        return _health_without_pet_overlap(direct)

    fragments = []
    source_records = []
    for field_id in (
        "always_included_options",
        "selectable_options",
        "ecosystem",
        "other_benefits",
    ):
        field = fields.get(field_id)
        value = field_value(field)
        if not value or value == NOT_FOUND or _negative(value):
            continue
        found = []
        for part in _split_parts(value):
            normalized = _dedupe_text(part)
            if any(marker in normalized for marker in SPORT_BEAUTY_MARKERS):
                continue
            if any(marker in normalized for marker in HEALTH_OPTION_MARKERS):
                cleaned = _remove_veterinary_fragment(part)
                if cleaned:
                    cleaned_low = cleaned.lower()
                    if (field_id == "always_included_options"
                            and "включено постоянно" not in cleaned_low):
                        cleaned += " — включено постоянно"
                    elif (field_id == "selectable_options"
                          and "опция на выбор" not in cleaned_low):
                        cleaned += " — опция на выбор"
                    found.append(cleaned)
        if found:
            fragments.extend(found)
            if isinstance(field, dict):
                source_records.append(field)

    unique = []
    seen = set()
    for fragment in fragments:
        key = _dedupe_text(fragment)
        if key and key not in seen:
            seen.add(key)
            unique.append(fragment)
    if not unique:
        return direct

    value = " | ".join(unique)
    result = dict(source_records[0]) if source_records else {
        "source_id": "derived",
        "source_type": "derived",
        "source_name": "Нормализация",
        "quality": "derived",
    }
    urls = [record.get("source_url", "") for record in source_records]
    urls = [url for url in urls if url]
    if urls:
        result["source_url"] = "; ".join(dict.fromkeys(urls))
    result.update({
        "value": value,
        "raw_text": value,
        "publication_status": "published",
        "publication_reason": (
            "Категория выделена из опубликованного текста того же уровня"
        ),
    })
    return _health_without_pet_overlap(result)


def pets_option_field(fields: dict):
    """Expose confirmed veterinary access in the dedicated pets row."""
    direct = fields.get("pets_option")
    if _has_value(direct):
        return direct

    source_records = []
    fragments = []
    pattern = re.compile(
        r"консультаци[ия]\s+ветеринар[а-я]*"
        r"(?:\s*\(?\s*всегда\s+включен[ао]?\s*\)?)?",
        flags=re.IGNORECASE,
    )
    for field_id in (
        "always_included_options", "selectable_options", "ecosystem",
        "health_option", "other_benefits",
    ):
        field = fields.get(field_id)
        value = field_value(field)
        if not value or value == NOT_FOUND or _negative(value):
            continue
        matches = [_clean_sentence(match.group(0)) for match in pattern.finditer(value)]
        if matches:
            fragments.extend(matches)
            if isinstance(field, dict):
                source_records.append(field)
    if not fragments:
        return direct

    value = max(
        fragments,
        key=lambda item: ("всегда включ" in item.lower(), len(item)),
    )
    if "всегда включ" in value.lower():
        value = re.sub(
            r"\s*\(?\s*всегда\s+включен[ао]?\s*\)?",
            "",
            value,
            flags=re.IGNORECASE,
        ).strip(" ,;()")
        value = f"{value} — включено постоянно"
    result = dict(source_records[0]) if source_records else {
        "source_id": "derived",
        "source_type": "derived",
        "source_name": "Нормализация",
        "quality": "derived",
    }
    result.update({
        "value": value,
        "raw_text": value,
        "publication_status": "published",
        "publication_reason": (
            "Категория выделена из опубликованного текста того же уровня"
        ),
    })
    return result


def _remove_veterinary_fragment(text: str) -> str:
    cleaned = re.sub(
        r",?\s*консультаци[ия]\s+ветеринар[а-я]*"
        r"(?:\s*\(?\s*всегда\s+включен[ао]?\s*\)?)?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = _clean_sentence(cleaned).strip(" ,;")
    if cleaned.count("(") > cleaned.count(")"):
        cleaned += ")"
    return cleaned


def _health_without_pet_overlap(field):
    if not isinstance(field, dict):
        return field
    value = _remove_veterinary_fragment(field_value(field))
    if not value:
        return field
    low = value.lower()
    if (re.search(r"\bопци[яи]\b", low)
            and "опция на выбор" not in low
            and "включено постоянно" not in low):
        value = f"{value} — опция на выбор"
    result = dict(field)
    result.update({"value": value, "raw_text": value})
    return result


def sport_beauty_field(fields: dict):
    """Return a source-backed field for the dedicated sport/beauty row.

    Older history entries keep Fitmost and appoint inside option/ecosystem
    fields.  Derive only matching source fragments so a rebuild can normalize
    existing data without a new network scan.
    """
    direct = fields.get("sport_beauty_option")
    if _has_value(direct):
        return _sport_beauty_with_availability(direct)

    fragments = []
    source_records = []
    for field_id in (
        "selectable_options",
        "always_included_options",
        "ecosystem",
    ):
        field = fields.get(field_id)
        value = field_value(field)
        if not value or value == NOT_FOUND or _negative(value):
            continue
        found = _sport_beauty_fragments(value)
        if not found:
            continue
        fragments.extend(found)
        if isinstance(field, dict):
            source_records.append(field)

    # Historical snapshots can lack the normalized component fields while
    # still retaining their already-derived bullet list. Use it only as a
    # fallback; combining both forms would repeat the same option twice.
    if not fragments:
        field = fields.get("other_benefits")
        value = field_value(field)
        if value and value != NOT_FOUND and not _negative(value):
            fragments.extend(_sport_beauty_fragments(value))
            if fragments and isinstance(field, dict):
                source_records.append(field)

    unique = []
    seen = set()
    for fragment in fragments:
        key = _dedupe_text(fragment)
        if key and key not in seen:
            seen.add(key)
            unique.append(fragment)
    if not unique:
        return direct

    value = " | ".join(unique)
    if source_records:
        result = dict(source_records[0])
        urls = [record.get("source_url", "") for record in source_records]
        urls = [url for url in urls if url]
        if urls:
            result["source_url"] = "; ".join(dict.fromkeys(urls))
    else:
        result = {
            "source_id": "derived",
            "source_type": "derived",
            "source_name": "Нормализация",
            "quality": "derived",
        }
    result.update({
        "value": value,
        "raw_text": value,
        "publication_status": "published",
        "publication_reason": (
            "Категория выделена из опубликованного текста того же уровня"
        ),
    })
    return _sport_beauty_with_availability(result)


def _sport_beauty_with_availability(field):
    """Make the option status explicit in the user-facing field value."""
    if not isinstance(field, dict):
        return field
    value = field_value(field)
    low = value.lower()
    if not value or value == NOT_FOUND:
        return field
    if "опция на выбор" in low or "включено постоянно" in low:
        return field
    if ("опция «спорт" in low or "пакет «спорт»" in low):
        status = "опция на выбор"
    elif "appoint" in low:
        status = "включено постоянно"
    else:
        return field
    display = f"{value} — {status}"
    result = dict(field)
    result.update({"value": display, "raw_text": display})
    return result


def _sport_beauty_fragments(text: str) -> list[str]:
    value = str(text)
    fragments = []
    spans = []
    structured_matches = (
        list(OPTION_RE.finditer(value))
        + list(PACKAGE_RE.finditer(value))
        + list(PACKAGE_PAREN_RE.finditer(value))
    )
    for match in structured_matches:
        snippet = _clean_sentence(match.group(0))
        normalized = _dedupe_text(snippet)
        name = _dedupe_text(match.group(1))
        if (name in {"спорт", "спорт и красота"}
                or any(marker in normalized for marker in SPORT_BEAUTY_MARKERS)):
            fragments.append(snippet)
            spans.append(match.span())

    remainder = value
    for start, end in sorted(spans, reverse=True):
        remainder = remainder[:start] + " " + remainder[end:]
    for part in _split_parts(remainder):
        normalized = _dedupe_text(part)
        if any(marker in normalized for marker in SPORT_BEAUTY_MARKERS):
            fragments.append(part)
    return fragments


def _duplicates_specialized_field(item: dict, fields: dict) -> bool:
    """Return True when the same confirmed fragment has its own report row."""
    candidates = (
        item.get("raw_text", ""),
        f"{item.get('title', '')} {item.get('description', '')}",
    )
    all_item_texts = [
        normalized for text in candidates
        if (normalized := _dedupe_text(text))
    ]
    if not all_item_texts:
        return False
    combined_item_text = " ".join(all_item_texts)
    for field_ids, markers in SPECIALIZED_CATEGORY_MARKERS:
        if (any(_has_value(fields.get(field_id)) for field_id in field_ids)
                and any(marker in combined_item_text for marker in markers)):
            return True
    item_texts = [text for text in all_item_texts if len(text) >= 20]
    for field_id in SPECIALIZED_BENEFIT_FIELDS:
        value = field_value(fields.get(field_id, NOT_FOUND))
        if not value or value == NOT_FOUND or _negative(value):
            continue
        field_text = _dedupe_text(value)
        if any(text in field_text or field_text in text for text in item_texts):
            return True
    return False


def _has_value(field) -> bool:
    value = field_value(field)
    return bool(value and value != NOT_FOUND and not _negative(value))


def _dedupe_text(text: str) -> str:
    return re.sub(
        r"[^a-zа-я0-9]+", " ", str(text).lower().replace("ё", "е")
    ).strip()


def selection_rule_summary(text: str) -> str:
    if not text or text == NOT_FOUND:
        return ""
    low = text.lower()
    if not any(marker in low for marker in ("выб", "опци", "менять", "измен", "7")):
        return ""
    blocked = ("обмен", "бонус", "менеджер", "инвест", "очеред", "запис")
    parts = []
    for part in _split_parts(text):
        part_low = part.lower()
        if any(marker in part_low for marker in blocked):
            continue
        if not any(marker in part_low for marker in ("выб", "опци", "менять", "измен", "7")):
            continue
        cleaned = _clean_sentence(part)
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    summary = "; ".join(parts[:3])
    summary = re.sub(r"раз в месяц можно выбрать одну из опций пакета",
                     "одна опция в месяц", summary, flags=re.IGNORECASE)
    summary = re.sub(r"если в текущем месяце ещё не использовались привилегии",
                     "изменить можно до использования", summary,
                     flags=re.IGNORECASE)
    summary = re.sub(r"выбранная опция действует до ближайшего 7 числа",
                     "действует до ближайшего 7-го числа", summary,
                     flags=re.IGNORECASE)
    return summary


def _extend_from_text(items: list, text: str, availability: str):
    if not text or text == NOT_FOUND or _negative(text):
        return
    matched = False
    for match in list(PACKAGE_RE.finditer(text)) + list(PACKAGE_PAREN_RE.finditer(text)):
        matched = True
        package_name = _normalize_option_title(match.group(1))
        if package_name.lower() in {"комфортное путешествие", "путешествия"}:
            continue
        title = package_name if package_name.lower() == "спорт" else f"Пакет «{package_name}»"
        description = _clean_description(match.group(2))
        item_availability = "selectable" if availability == "unknown" else availability
        _add_item(items, title, description, item_availability, match.group(0))
    for match in OPTION_RE.finditer(text):
        matched = True
        title = _normalize_option_title(match.group(1))
        description = _clean_description(match.group(2))
        item_availability = ("always_included"
                             if "всегда включ" in description.lower()
                             else availability)
        if _is_core_duplicate(title, description):
            continue
        _add_item(items, title, description, item_availability, match.group(0))
    for part in _split_parts(text):
        if (not part or OPTION_RE.search(part) or PACKAGE_RE.search(part)
                or PACKAGE_PAREN_RE.search(part)):
            continue
        title, description = _title_description(part)
        if _is_core_duplicate(title, description):
            continue
        if _looks_like_rule(part):
            continue
        if _too_generic(part):
            continue
        _add_item(items, title, description, availability, part)


def _add_item(items: list, title: str, description: str, availability: str,
              raw_text: str):
    title = _normalize_option_title(title)
    description = _clean_description(description)
    if _similar_title_description(title, description):
        description = ""
    if (not title or _too_generic(title)
            or _is_core_duplicate(title, description)
            or _is_insurance_leak(title, description)):
        return
    benefit_id = _benefit_id(title)
    if benefit_id == "sber_prime":
        availability = "always_included"
    items.append({
        "id": benefit_id,
        "title": title,
        "description": description,
        "availability": availability,
        "raw_text": raw_text,
    })


def _dedupe(items: list) -> list[dict]:
    by_id = {}
    for item in items:
        key = item["id"]
        current = by_id.get(key)
        if current is None or len(item.get("description", "")) > len(current.get("description", "")):
            by_id[key] = item
        elif current and current.get("availability") == "unknown" and item.get("availability") != "unknown":
            current["availability"] = item["availability"]
    return list(by_id.values())


def _split_parts(text: str) -> list[str]:
    public = re.sub(r"\s*\[[^\]]+\]", "", str(text))
    raw_parts = re.split(r"\s+\|\s+|;\s*|\n+|\s*•\s*", public)
    return [_clean_sentence(p) for p in raw_parts if _clean_sentence(p)]


def _title_description(part: str) -> tuple[str, str]:
    text = re.sub(r"^опция\s+", "", part, flags=re.IGNORECASE).strip(" «»")
    if " — " in text:
        title, description = text.split(" — ", 1)
        return canonical_title(title.strip(" «»")), description.strip()
    if ": " in text:
        title, description = text.split(": ", 1)
        return canonical_title(title.strip()), description.strip()
    if "(" in text and text.endswith(")"):
        title, description = text[:-1].split("(", 1)
        return canonical_title(title.strip(" «»")), description.strip()
    low = text.lower()
    if "alfa only lounge" in low:
        return "Alfa Only Лаундж", _clean_description(
            re.sub(r"alfa only\s+lounge\s*", "", text, flags=re.IGNORECASE)
        )
    if "а-клуб lounge" in low:
        return "А-Клуб Лаундж", _clean_description(
            re.sub(r"а-клуб\s+lounge\s*", "", text, flags=re.IGNORECASE)
        )
    if "alfa only" in low and "лаундж" in low:
        return "Alfa Only Лаундж", _clean_description(
            re.sub(r"alfa only\s+лаундж\s*", "", text, flags=re.IGNORECASE)
        )
    if "smart reading" in low and "саммари" in low:
        return "Саммари от Smart Reading", ""
    whole_line_markers = (
        "обмен ",
        "компенсация ",
        "3 консультации",
        "5 тыс баллов",
        "10 тыс баллов",
        "медицинское обследование",
        "учёт остатков",
        "учет остатков",
        "по тарифам платно",
        "телемедицина",
        "сбер мобайл",
        "консьерж pb service",
        "звонки ",
        "оформление бз",
        "технический лимит",
        "страхование имущества",
        "1 уровень bronze",
        "3 уровня bronze",
        "1 private",
        "2 private",
        "6 проходов",
        "юридические услуги",
        "поездки копятся",
        "кэшбэк 20%",
        "комплексный чекап",
        "медицинская программа",
        "сервис «лучи»",
        "акция «привилегии",
        "мобильная связь",
        "премиум консьерж",
        "газпром бонус",
        "до 8 бесплатных",
        "ограничено количество",
        "посещение третьяковской",
        "от 150м",
        "от 300м",
    )
    if low.startswith(whole_line_markers):
        return _clean_description(text), ""
    known_benefit = classify_benefit(text)
    if known_benefit:
        description = default_description(known_benefit.benefit_id)
        cleaned = _clean_description(
            text.replace(known_benefit.title, "", 1).strip(" ,—-")
        )
        return known_benefit.title, cleaned or description
    words = text.split()
    return " ".join(words[:4]).strip(" ,—-"), " ".join(words[4:]).strip(" ,—-")


def _normalize_option_title(title: str) -> str:
    cleaned = title.strip()
    if cleaned.startswith("«") and cleaned.endswith("»"):
        cleaned = cleaned[1:-1].strip()
    mapping = {
        "авто": "Авто",
        "самокат": "Самокат",
        "питомцы": "Питомцы",
        "здоровье": "Здоровье",
        "спорт и красота": "Спорт и красота",
        "комфортное путешествие": "Комфортное путешествие",
        "спорт": "Спорт",
        "развлечения": "Развлечения",
    }
    normalized = mapping.get(cleaned.lower(), cleaned[:1].upper() + cleaned[1:])
    return canonical_title(normalized)


def _clean_description(text: str) -> str:
    cleaned = _clean_sentence(text)
    cleaned = re.sub(r"\s*\(всегда включен[ао]\)\s*", "", cleaned,
                     flags=re.IGNORECASE)
    cleaned = cleaned.replace("кешбэк", "кэшбэк")
    return cleaned.strip(" ,;—-")


def _clean_sentence(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text).replace("•", "").strip()).strip(" |;")
    value = re.sub(r"«\s+", "«", value)
    value = re.sub(r"\s+»", "»", value)
    return value


def _benefit_id(title: str) -> str:
    catalog_match = classify_benefit(title)
    if catalog_match:
        return catalog_match.benefit_id
    low = title.lower().replace("ё", "е")
    aliases = {
        "консьерж aspire": "консьерж",
        "aspire": "консьерж",
        "консьерж": "консьерж",
        "автоуслуги": "auto",
        "авто": "auto",
    }
    for marker, value in aliases.items():
        if marker in low:
            return value
    return benefit_id_for_title(title)


def _is_core_duplicate(title: str, description: str) -> bool:
    low = f"{title} {description}".lower()
    if title.strip().lower().startswith("пакет «"):
        return False
    if "промокод" in low or "сертификат" in low:
        return False
    if title.strip().lower() in {"консьерж", "aspire"}:
        return True
    if "бизнес-зал сбер" in low or "alfa only lounge" in low:
        return False
    return any(marker in low for marker in CORE_DUPLICATE_MARKERS)


def _similar_title_description(title: str, description: str) -> bool:
    title_norm = re.sub(r"[^a-zа-я0-9]+", " ", title.lower().replace("ё", "е")).strip()
    desc_norm = re.sub(r"[^a-zа-я0-9]+", " ", description.lower().replace("ё", "е")).strip()
    title_norm = re.sub(r"\bи\b", " ", title_norm)
    desc_norm = re.sub(r"\bи\b", " ", desc_norm)
    title_norm = re.sub(r"\s+", " ", title_norm).strip()
    desc_norm = re.sub(r"\s+", " ", desc_norm).strip()
    if title_norm == "спорт":
        return False
    if not title_norm or not desc_norm:
        return False
    if title_norm == desc_norm:
        return True
    return title_norm in desc_norm or desc_norm in title_norm


def _is_insurance_leak(title: str, description: str) -> bool:
    low = f"{title} {description}".lower().replace("ё", "е")
    if title.strip().lower().startswith("пакет «"):
        return False
    if "доктис" in low or "телемедицин" in low:
        return False
    if "страхование имущества" in low:
        return False
    if title.strip().lower().replace("ё", "е") == "здоровье":
        return not any(marker in low for marker in HEALTH_OPTION_MARKERS)
    return any(marker in low for marker in INSURANCE_LEAK_MARKERS)


def _negative(text: str) -> bool:
    low = text.strip().lower()
    return low.startswith(("—", "-", "нет —", "нет,"))


def _too_generic(text: str) -> bool:
    low = text.lower()
    short_allowed = {"авто", "рбк", "okko"}
    return ((len(text) < 5 and low not in short_allowed)
            or low in {"включено", "на выбор"}
            or low.startswith("преференци")
            or bool(re.match(
                r"^(?:до\s+)?\d+\s+(?:в\s+(?:мес|месяц|год|сут)|"
                r"посещени|чек|заказ|поезд)",
                low,
            ))
            or low.startswith("включено исследование")
            or low.startswith("исследование до")
            or low.startswith(("в вопросе #", "подробнее")))


def _looks_like_rule(text: str) -> bool:
    low = text.lower()
    return ("можно выбрать" in low or "можно сменить" in low
            or "выбранная опция" in low
            or low.startswith("по тарифам платно")
            or low.startswith(("учёт остатков", "учет остатков")))


def _auto_status(fields: dict) -> str:
    auto = field_value(fields.get("auto", NOT_FOUND)).lower()
    if "всегда включ" in auto:
        return "always_included"
    if "опция" in auto:
        return "selectable"
    return "unknown"


def _clean_title_text(text: str) -> str:
    text = re.sub(r"^есть\s+[—-]\s*", "", text, flags=re.IGNORECASE)
    return _clean_description(text)


def _concierge_benefit(text: str) -> tuple[str, str]:
    low = text.lower()
    if "only assist" in low:
        return "Only Assist", "Консьерж-сервис"
    if "prime" in low:
        return "PRIME", "Консьерж-сервис"
    if "pb service" in low:
        return "Консьерж Pb Service", ""
    if "aspire" in low:
        return "Консьерж Aspire", ""
    return "Консьерж", _clean_title_text(text)


def _mixed_availability(items: list[dict]) -> bool:
    statuses = {i.get("availability") for i in items if i.get("availability") != "unknown"}
    return len(statuses) > 1
