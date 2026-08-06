# -*- coding: utf-8 -*-
"""Static bank-vs-bank comparison landing generated from comparison JSON.

Интеракция: пользователь выбирает два банка, после чего видит все уровни
обоих банков. Подтверждённые близкие уровни сопоставляются попарно без
повторов; уровни без надёжного аналога остаются отдельными строками.
Подробное сравнение условий раскрывается внутри каждой строки.

Терминология UI — «уровень пакета». Внутренний ключ данных `tier` не
переименовывается: его читают JSON-экспорт, Excel-отчёт и этот модуль как
контракт данных.
"""

import html
import json
import re
from datetime import datetime
from pathlib import Path

from landing import premium_changes
from scanner.formatting import (
    assert_user_visible_text,
    make_complete_summary,
    normalize_source_text,
    split_summary_and_details,
)
from scanner.scoring import SCORERS
from scanner.sources import NOT_FOUND, NOT_FOUND_AVAILABLE

INTL_SEGMENT = "digital-first (межд.)"

# GitHub Pages keeps HTML in intermediary and browser caches for a short time.
# A time-bucketed URL makes a reopened tab validate the landing regularly,
# including after the browser restores it from the back-forward cache.
CANONICAL_SITE_URL = "https://sberprojectsmvs.github.io/bank_cite/"
FRESHNESS_INTERVAL_MS = 10 * 60 * 1000

# Официальные курсы Банка России на дату текущего набора данных.
# Источник: https://www.cbr.ru/currency_base/daily/
# Значения нужны только для сопоставления страховых сумм в USD и EUR;
# исходная валюта и сумма продолжают отображаться без изменений.
INSURANCE_FX_RUB_PER_UNIT = {
    "$": 78.4049,
    "€": 89.4443,
}
INSURANCE_FX_DATE = "2026-07-24"
INSURANCE_FX_SOURCE_URL = (
    "https://www.cbr.ru/currency_base/daily/"
    "?UniDbQuery.Posted=True&UniDbQuery.To=24.07.2026"
)

FIELD_COLUMNS = {
    "entry_conditions": "Условия входа / поддержания уровня",
    "service_cost": "Стоимость обслуживания",
    "lounge_access": "Бизнес-залы (визиты, спутники)",
    "cashback": "Кэшбэк (ставка, категории, механика)",
    "transfers_payments": "Переводы и платежи без комиссии",
    "cash_withdrawal": "Снятие наличных",
    "supreme": "Supreme",
    "deposits": "Вклады / накопительные счета",
    "taxi": "Такси",
    "restaurants": "Рестораны",
    "insurance": "Страхование",
    "auto": "Авто / помощь на дорогах",
    "concierge": "Консьерж-сервис",
    "other_benefits": "Другие привилегии",
    **{
        field_id: label for field_id, label in (
            ("internal_transfers", "Переводы физлицам внутри банка"),
            ("interbank_transfers_remote", "Межбанковские переводы — приложение / УКО"),
            ("interbank_transfers_office", "Межбанковские переводы — офис / ОКР"),
            ("card_to_card_transfers", "Переводы по номеру карты"),
            ("sbp_transfers", "Переводы через СБП"),
            ("legal_entity_payments", "Платежи / переводы юридическим лицам"),
            ("atm_free_withdrawal", "Бесплатное снятие в банкоматах"),
            ("cash_monthly_operational_limit", "Общий месячный лимит выдачи наличных"),
            ("atm_daily_limit", "Суточный лимит в банкоматах"),
            ("cash_desk_daily_limit", "Суточный лимит через кассу"),
            ("cash_over_limit_fee", "Комиссия сверх бесплатного лимита"),
            ("insurance_russia_coverage", "ВЗР — покрытие в РФ"),
            ("insurance_foreign_coverage", "ВЗР — покрытие за рубежом"),
            ("insurance_covered_people", "ВЗР — кого покрывает страховка"),
            ("insurance_owner_accompaniment", "ВЗР — сопровождение владельцем"),
            ("insurance_trip_duration", "ВЗР — длительность поездки"),
            ("insurance_trip_count", "ВЗР — количество поездок"),
            ("insurance_territorial_exclusions", "ВЗР — территориальные исключения"),
            ("insurance_additional_risks", "ВЗР — дополнительные риски"),
            ("health_option", "Здоровье"),
            ("samokat_option", "Самокат"),
            ("pets_option", "Питомцы"),
            ("sport_beauty_option", "Спорт и красота"),
            ("metal_card", "Металлическая карта"),
            ("personal_banking_support", "Персональное банковское сопровождение"),
        )
    },
}

FIELD_LABELS = {
    "entry_conditions": "Условия входа",
    "service_cost": "Стоимость обслуживания",
    "lounge_access": "Бизнес-залы",
    "concierge": "Консьерж",
    "cashback": "Кэшбэк",
    "transfers_payments": "Переводы и платежи",
    "cash_withdrawal": "Снятие наличных",
    "supreme": "Supreme",
    "deposits": "Вклады и накопительные счета",
    "taxi": "Такси",
    "restaurants": "Рестораны",
    "insurance": "Страхование",
    "other_benefits": "Другие привилегии",
    "transfers_summary": "Переводы и платежи",
    "cash_withdrawal_summary": "Снятие наличных",
}
FIELD_LABELS.update({
    field_id: label for field_id, label in FIELD_COLUMNS.items()
    if field_id not in FIELD_LABELS
})

# Порядок атрибутов в таблице сравнения
COMPARE_FIELDS = (
    "entry_conditions",
    "service_cost",
    "lounge_access",
    "cashback",
    "transfers_summary",
    "cash_withdrawal_summary",
    "supreme",
    "metal_card",
    "deposits",
    "taxi",
    "restaurants",
    "insurance",
    "health_option",
    "samokat_option",
    "pets_option",
    "sport_beauty_option",
    "auto",
    "concierge",
    "personal_banking_support",
    "other_benefits",
)

SCOPED_FACT_FIELDS = set(COMPARE_FIELDS) - {
    "entry_conditions", "service_cost", "lounge_access", "cashback",
    "supreme", "deposits", "taxi", "restaurants", "insurance",
    "concierge", "other_benefits",
}

COMPOSITE_FIELDS = {
    "transfers_summary": (
        ("internal_transfers", "Внутри банка"),
        ("interbank_transfers_remote", "Межбанк в приложении"),
        ("interbank_transfers_office", "Межбанк в офисе"),
        ("card_to_card_transfers", "По номеру карты"),
        ("sbp_transfers", "СБП"),
        ("legal_entity_payments", "Юрлицам"),
    ),
    "cash_withdrawal_summary": (
        ("atm_free_withdrawal", "Без комиссии"),
        ("cash_monthly_operational_limit", "Общий лимит"),
        ("atm_daily_limit", "Банкомат"),
        ("cash_desk_daily_limit", "Касса"),
        ("cash_over_limit_fee", "Сверх лимита"),
    ),
}

# Служебное описание методики. Итоговый балл намеренно не рассчитывается:
# разные категории нельзя складывать без профиля и весов конкретного клиента.
def _methodology_text() -> str:
    return (
        "Условия сравниваются отдельно по каждой категории. Сначала применяется "
        "сравнение всех подтверждённых существенных параметров в одинаковом "
        "контексте: канал, период и вид операции. Подтверждённое условие отмечается "
        "сильнее отсутствующего, отсутствие данных — слабее, а доказанное равенство "
        "лимитов и условий — как равное. Разнонаправленные преимущества помечаются "
        "как неоднозначные."
    )


def build_sber_vs_landing(data_path: Path, output_path: Path) -> dict:
    """Build the static bank comparison landing page."""
    rows = load_summary_rows(data_path)
    banks = build_payload(rows)
    changes = premium_changes.group_by_bank(premium_changes.load_changes(data_path))
    html_text = render_html(banks, rows, changes)
    html_text = "\n".join(line.rstrip() for line in html_text.splitlines()) + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    return {
        "output": str(output_path),
        "banks": len(banks),
        "levels": sum(len(b["levels"]) for b in banks),
    }


def load_summary_rows(data_path: Path) -> list[dict]:
    """Read normalized banking rows from the structured comparison JSON."""
    if not data_path.exists():
        raise FileNotFoundError(
            f"Comparison JSON not found: {data_path}. Run --scan-all first."
        )
    if data_path.suffix.lower() != ".json":
        raise ValueError(
            "Sber VS HTML must be generated from comparison JSON, not Excel."
        )

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or "rows" not in payload:
        raise ValueError(f"Unsupported comparison JSON schema: {data_path}")
    rows = []
    for item in payload["rows"]:
        bank = _clean(item.get("bank"))
        tier = _clean(item.get("tier"))
        if not bank or not tier:
            continue
        field_records = item.get("fields", {})
        row = {
            "tier_id": _clean(item.get("tier_id")),
            "segment": _clean(item.get("segment")),
            "bank": bank,
            "tier": tier,
            "scan_date": _clean(item.get("scan_date")),
            "sources_ok": _clean(item.get("sources_ok")),
            "score": _score_total(item.get("score")),
            "divergent": "да" if any(
                bool(record.get("divergent"))
                for record in field_records.values()
                if isinstance(record, dict)
            ) else "нет",
        }
        row["fields"] = {
            key: _clean(_json_field_value(field_records.get(key)))
            for key in FIELD_COLUMNS
        }
        row["field_records"] = field_records
        row["details"] = {
            key: _clean(_json_field_details(field_records.get(key)))
            for key in FIELD_COLUMNS
        }
        if row["segment"] and row["segment"] != INTL_SEGMENT:
            rows.append(row)
    return rows


def _json_field_value(record) -> str:
    if not isinstance(record, dict):
        return ""
    return record.get("display_value") or record.get("value") or ""


def _json_field_details(record) -> str:
    if not isinstance(record, dict):
        return ""
    return record.get("raw_text") or record.get("display_value") or record.get("value") or ""


def _score_total(score):
    if isinstance(score, dict):
        return _parse_float(score.get("total"))
    return _parse_float(score)


def build_payload(rows: list[dict]) -> list[dict]:
    """Group rows into banks → levels with pre-computed compare attributes."""
    by_bank = {}
    for row in rows:
        by_bank.setdefault(row["bank"], []).append(row)

    banks = []
    # Сбер первым (база сравнения), остальные по алфавиту
    order = sorted(by_bank, key=lambda name: (name != "Сбер", name.lower()))
    for name in order:
        levels = []
        for row in by_bank[name]:
            attrs = []
            for field in COMPARE_FIELDS:
                metric = _attr_metric(field, row)
                attr = {
                    "id": field,
                    "label": FIELD_LABELS[field],
                    "value": metric["value"],
                    "kind": metric.get("kind", "text"),
                    # Legacy scalar is retained for payload compatibility only.
                    # Browser ranking uses the structured evaluation below.
                    "score": metric["score"],
                    "evaluation": metric.get("evaluation_override") or _category_evaluation(
                        field,
                        metric.get("evaluation_text") or row["fields"].get(field, ""),
                        metric.get("value"),
                        row,
                    ),
                    "note": metric["note"],
                    "details": metric.get("details", ""),
                }
                _validate_attr(attr, f"{row['bank']} / {row['tier']} / {field}")
                attrs.append(attr)
            levels.append({
                "tier_id": row["tier_id"],
                "tier": row["tier"],  # значение поля данных; в UI — уровень пакета
                "segment": row["segment"],
                "scan_date": (row.get("scan_date") or "")[:10],
                "entry_hint": _entry_hint(row, attrs),
                "entry_match": _entry_match(row),
                "attrs": attrs,
            })
        banks.append({"bank": name, "levels": levels})
    return banks


def _attr_metric(field: str, row: dict) -> dict:
    """Attribute display value + comparable score for one level."""
    if field in COMPOSITE_FIELDS:
        return _composite_metric(field, row)
    field_record = row["fields"].get(field, "")
    raw = _json_field_value(field_record) if isinstance(field_record, dict) else field_record
    detail_raw = (
        _json_field_details(field_record)
        if isinstance(field_record, dict)
        else row.get("details", {}).get(field) or raw
    )
    if field == "entry_conditions":
        summary = _condition_summary(raw, row.get("tier_id"))
        return {"value": summary or "нет данных", "score": _entry_conditions_score(summary or raw),
                "note": _shorten(raw, 260), "details": _details(detail_raw, summary)}
    if field == "service_cost":
        cost_info = _service_cost_summary(row)
        cost = _monthly_rub_cost(raw)
        return {"value": cost_info["display"],
                "score": _service_cost_score(raw, cost_info["display"], cost),
                "note": _shorten(raw, 260), "details": _details(detail_raw, cost_info["display"])}
    if field == "other_benefits":
        override = _sber_landing_override(field, row)
        if override:
            return override
        # Preserve source bullet boundaries. `display_value` is normalized to
        # one line in JSON, while `raw_text` retains one benefit per line.
        benefits = _benefits_list(detail_raw or raw)
        return {"value": benefits, "score": None,
                "note": _shorten(raw, 260), "kind": "benefits", "details": ""}

    if _is_missing(raw):
        return {"value": NOT_FOUND_AVAILABLE, "score": None, "note": "", "details": ""}
    if raw.strip().startswith(("—", "-")):
        if field == "supreme":
            return {"value": "Не предусмотрено", "score": 0, "note": "", "details": ""}
        return {"value": "Не предусмотрено", "score": 0, "note": "", "details": "",
                "evaluation_text": raw}
    override = _sber_landing_override(field, row)
    if override:
        return override
    if field in SCOPED_FACT_FIELDS:
        return {
            "value": raw,
            "score": None,
            "note": _shorten(raw, 260),
            "details": _details(detail_raw, raw),
            "evaluation_text": raw,
        }
    try:
        scorer_field = "taxi_restaurants" if field in ("taxi", "restaurants") else field
        metric, _legacy_score = SCORERS[scorer_field](raw)
    except Exception:  # noqa: BLE001 — шумный текст источника не роняет лендинг
        metric = "есть, детали не выделены" if _has_benefit(raw) else "нет"
    value = _benefit_display(field, raw, metric)
    if field in {"transfers_payments", "cash_withdrawal"} and not _rub_amounts(value):
        limit_evaluation = _limit_evaluation(raw, field)
        if limit_evaluation.get("status") == "comparable":
            summary = limit_evaluation.get("summary", "")
            if summary:
                value = f"{value.rstrip(' .')}. Лимит без комиссии: {summary}."
    score = _comparison_score(field, raw)
    public_raw = _insurance_display(raw) if field == "insurance" else raw
    public_details = (
        _insurance_display(detail_raw) if field == "insurance" else detail_raw
    )
    return {"value": value, "score": score, "note": _shorten(public_raw, 260),
            "details": _details(public_details, value)}


def _composite_metric(field: str, row: dict) -> dict:
    """Build one compact presentation row from scope-safe JSON facts."""
    parts = []
    missing = []
    details = []
    components = {}
    records = row.get("field_records", {})
    for field_id, label in COMPOSITE_FIELDS[field]:
        record = records.get(field_id)
        value = _json_field_value(record) if isinstance(record, dict) else (
            row.get("fields", {}).get(field_id, "")
        )
        if _is_missing(str(value or "")):
            missing.append(label.lower())
            components[field_id] = {
                "label": label,
                "present": False,
                "evaluation": _missing_evaluation(),
            }
            continue
        evaluation = _category_evaluation(field_id, value, value, row)
        if evaluation.get("status") == "comparable":
            original_scope = dict(evaluation.get("scope") or {})
            if field_id in {
                "internal_transfers", "interbank_transfers_remote",
                "interbank_transfers_office", "card_to_card_transfers",
                "sbp_transfers",
                "legal_entity_payments", "atm_daily_limit",
                "cash_desk_daily_limit",
            }:
                evaluation["scope"] = {"component": field_id}
            else:
                evaluation["scope"] = {
                    "component": field_id,
                    **original_scope,
                }
        components[field_id] = {
            "label": label,
            "present": True,
            "evaluation": evaluation,
        }
        parts.append(f"{label}: {_compact_composite_value(field_id, record, value)}")
        details.append(f"{label}: {value}")
    if not parts:
        display = NOT_FOUND_AVAILABLE
    else:
        display = "; ".join(parts)
        if missing:
            display += f"; нет данных: {', '.join(missing)}"
    evaluation_override = _evaluation(
        "composite",
        {"components": components},
        {},
        _shorten(display, 160),
        scope={"group": field},
        reason=(
            "Каждый подпункт сравнивается отдельно: только при одинаковом виде "
            "операции, канале и периоде."
        ),
    ) if parts else _missing_evaluation()
    return {
        "value": display,
        "score": None,
        "note": display,
        "details": "\n".join(details),
        "evaluation_text": display,
        "evaluation_override": evaluation_override,
    }


def _compact_composite_value(field_id: str, record, value) -> str:
    """Shorten a structured fact without changing its confirmed meaning."""
    text = re.sub(r"\s+", " ", str(value or "")).strip(" .;")
    metadata = record if isinstance(record, dict) else {}
    free_limit = str(metadata.get("free_limit") or "").strip()
    technical_limit = str(metadata.get("technical_limit") or "").strip()
    period = str(metadata.get("period") or "").strip()
    fee = str(metadata.get("over_limit_fee") or "").strip()

    if free_limit.lower().startswith("без опубликованного"):
        return "бесплатно, числовой лимит не опубликован"

    if field_id == "cash_over_limit_fee" and fee:
        return _compact_units(fee)

    if field_id == "legal_entity_payments" and free_limit:
        amount, separator, shared_note = free_limit.partition(" — ")
        compact = _limit_with_period(amount, period)
        if "без комис" in text.lower():
            compact += " бесплатно"
        if separator and shared_note:
            compact += f" ({shared_note})"
        if fee:
            compact += f"; далее {fee}"
        return _compact_units(compact)

    if field_id == "atm_free_withdrawal" and free_limit:
        compact = _limit_with_period(free_limit, period)
        return _compact_units(compact)

    if "Альбома тарифов" in text and free_limit in {"", "не указан"}:
        compact = "по Альбому тарифов"
        if "не указан" in text:
            compact += "; лимит не указан"
        return compact

    if field_id == "sbp_transfers" and free_limit:
        parsed_sbp = _compact_sbp_limits(text)
        if parsed_sbp:
            return parsed_sbp
        compact = f"бесплатно — {_limit_with_period(free_limit, period)}"
        if technical_limit and "не указан" not in technical_limit:
            compact += f"; {technical_limit}"
        return _compact_units(compact)

    if free_limit and free_limit not in {"не указан", "не применяется"}:
        compact = _limit_with_period(free_limit, period)
        if "без комис" in text.lower() or free_limit == "без комиссии":
            compact = compact.replace("без комиссии", "бесплатно")
            if "бесплатно" not in compact:
                compact += " бесплатно"
        if technical_limit and technical_limit not in {
            "не указан", "не выделен отдельно", free_limit,
        }:
            compact += f"; техлимит {technical_limit}"
        if fee and fee not in {"0%", ""}:
            compact += f"; далее {fee}"
        return _compact_units(compact)

    if technical_limit and technical_limit not in {
        "не указан", "не выделен отдельно",
    }:
        return _compact_units(_limit_with_period(technical_limit, period))

    if fee:
        return _compact_units(fee)

    text = re.sub(r"^[^:]{0,120}:\s*", "", text)
    text = text.replace(
        "технический лимит в данном источнике не указан", "лимит не указан"
    )
    text = text.replace("без комиссии", "бесплатно")
    return _compact_units(_shorten(text, 150))


def _limit_with_period(amount: str, period: str) -> str:
    """Render a compact but explicit period label for a confirmed limit."""
    value = re.sub(r"\s+", " ", str(amount or "")).strip()
    low = value.lower()
    if any(marker in low for marker in (
        "в месяц", "в сутки", "в день", "за операцию",
    )):
        return value if "лимит" in low else f"лимит {value}"
    period_phrase = {
        "месяц": "в месяц",
        "сутки": "в сутки",
        "операция": "за операцию",
    }.get(str(period or "").lower(), str(period or "").strip())
    if period_phrase:
        return f"лимит {period_phrase} {value}"
    return f"лимит {value}" if value else "лимит не указан"


def _compact_sbp_limits(text: str) -> str:
    """Keep operation, daily, and monthly SBP limits in one readable line."""
    amount = r"(\d[\d\s]*(?:[.,]\d+)?\s*(?:млн|тыс)?\s*₽)"
    operation_daily = re.search(
        rf"до\s+{amount}\s+за\s+один\s+перевод\s+и\s+в\s+сутки",
        text,
        flags=re.IGNORECASE,
    )
    monthly = re.findall(
        rf"до\s+{amount}\s+в\s+месяц", text, flags=re.IGNORECASE,
    )
    if operation_daily and monthly:
        daily_amount = _compact_units(operation_daily.group(1))
        third_month = _compact_units(monthly[0])
        compact = (
            f"третьим лицам — лимит за перевод {daily_amount}, "
            f"лимит в сутки {daily_amount}, лимит в месяц {third_month}"
        )
        if len(monthly) > 1:
            own_month = _compact_units(monthly[1])
            compact += f"; себе — лимит в месяц {own_month}"
        return compact
    return ""


def _compact_units(text: str) -> str:
    compact = str(text)
    compact = compact.replace("максимум", "макс.").replace("минимум", "мин.")
    return re.sub(r"\s+", " ", compact).strip(" .;")


def _sber_landing_override(field: str, row: dict):
    """Narrow, source-backed presentation fixes for named landing levels."""
    bank = row.get("bank")
    tier_id = row.get("tier_id")
    if bank == "Альфа-Банк" and field == "restaurants" and tier_id == "alfa_aclub":
        value = (
            "Включено постоянно: безлимит по 2 500 ₽. Ограничения: один чек "
            "за одну дату до 5 000 ₽ списывает две компенсации по 2 500 ₽; "
            "только в аэропорту при вылете или прилёте, в дату поездки и один "
            "календарный день до или после неё; общий лимит с бизнес-залами."
        )
        return {
            "value": value,
            "score": _comparison_score(field, value),
            "note": value,
            "details": "",
            "evaluation_text": value,
        }
    if bank != "Сбер":
        return None
    text_by_field = {
        "lounge_access": {
            "sber_first_4": (
                "Включено постоянно: безлимит. Доступ через Mir Pass, "
                "ON·PASS, Частично и ON·PASS Premium."
            ),
            "sber_first_5": (
                "Включено постоянно: безлимит. Доступ через Mir Pass, "
                "ON·PASS, Частично и ON·PASS Premium."
            ),
            "sber_private_6": (
                "Включено постоянно: безлимит. Доступ через Mir Pass, "
                "ON·PASS, Частично и ON·PASS Premium."
            ),
        },
        "restaurants": {
            "sber_premier_2": "1 посещение в месяц на 2000 ₽ — опция «Такси и рестораны».",
            "sber_private_6": (
                "Включено постоянно: безлимит по 5000 ₽ — опция «Рестораны» "
                "2 чека в день"
            ),
        },
    }
    value = text_by_field.get(field, {}).get(tier_id)
    if not value:
        return None
    return {"value": value, "score": _comparison_score(field, value),
            "note": value, "details": "", "evaluation_text": value}


# ---------- рендер ----------

def render_html(banks: list[dict], rows: list[dict], changes: list[dict] = None) -> str:
    changes = changes or []
    scan_dates = sorted({r["scan_date"][:10] for r in rows if r.get("scan_date")})
    latest_scan = scan_dates[-1] if scan_dates else "нет данных"
    total_levels = sum(len(b["levels"]) for b in banks)
    payload = json.dumps(banks, ensure_ascii=False).replace("</", "<\\/")
    bank_chips = _render_bank_chips(banks)
    changes_panel = premium_changes.render_changes_panel(changes, datetime.now())
    build_id = datetime.now().strftime("%Y%m%dT%H%M%S%f")

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="bank-analyst-build" content="{build_id}">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <link rel="canonical" href="{CANONICAL_SITE_URL}">
  <script>{_FRESHNESS_JS}</script>
  <title>Сравнение премиальных пакетов банков</title>
  <style>{_CSS}{premium_changes.changes_css(embedded=True)}</style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <p class="eyebrow">Премиальный банкинг РФ</p>
      <h1>Сравнение банков</h1>
      <p class="lead">Выберите два банка — мы сопоставим всю линейку их
      премиальных уровней по подтверждённым условиям входа. Каждый уровень
      будет показан один раз, а подробные условия можно раскрыть внутри пары.</p>
      <div class="stats">
        <div><b>{len(banks)}</b><span>банков</span></div>
        <div><b>{total_levels}</b><span>уровней пакетов</span></div>
        <div><b>{_esc(latest_scan)}</b><span>дата данных</span></div>
      </div>
      {changes_panel}
    </section>

    <section class="pickers">
      <div class="picker" data-side="a">
        <h2>Банк 1</h2>
        <div class="chip-row banks">{bank_chips}</div>
      </div>
      <div class="picker" data-side="b">
        <h2>Банк 2</h2>
        <div class="chip-row banks">{bank_chips}</div>
      </div>
    </section>
    <p id="js-warning" class="js-warning">Если банки не выбираются, файл открыт
    во встроенном просмотрщике без JavaScript. Нажмите «Поделиться» → «Открыть
    в Safari» или откройте этот HTML в Chrome.</p>

    <section id="compare" hidden>
      <div class="compare-actions">
        <div>
          <p class="print-title">Сравнение банков</p>
          <p class="print-date">Дата данных: {_esc(latest_scan)}</p>
        </div>
        <div class="compare-buttons">
          <button type="button" class="secondary-button" id="expand-all">
            Развернуть все</button>
          <button type="button" class="secondary-button" id="collapse-all">
            Свернуть все</button>
          <button type="button" class="pdf-button" id="pdf-button">Выгрузить PDF</button>
        </div>
      </div>
      <div class="map-heading">
        <div>
          <p class="recommendations-kicker">Карта уровней</p>
          <h2 id="map-title"></h2>
        </div>
        <p id="map-summary" class="map-summary" aria-live="polite"></p>
      </div>
      <p class="map-method">Сначала сопоставляются пересекающиеся подтверждённые
      диапазоны входа, затем близкие пороги с сохранением порядка продуктовых
      линеек. Неподтверждённые или удалённые уровни остаются без прямого аналога.</p>
      <div id="pair-list" class="pair-list"></div>
    </section>
    <p id="hint" class="hint">Выберите два разных банка — здесь появится карта
    всех уровней обеих продуктовых линеек.</p>

    <footer class="footer">
      <p>Данные — из JSON-экспорта сканера, у каждого значения зафиксирован
      источник, фрагмент исходного текста и дата проверки. Excel-отчёт —
      только представление этих данных. Дата данных:
      {_esc(latest_scan)}.</p>
    </footer>
  </main>
  <script id="data" type="application/json">{payload}</script>
  <script>{premium_changes.changes_js()}{_JS}</script>
</body>
</html>"""


_FRESHNESS_JS = f"""
(function () {{
  const canonical = new URL({json.dumps(CANONICAL_SITE_URL)});
  const intervalMs = {FRESHNESS_INTERVAL_MS};

  function refreshStalePage() {{
    if (location.hostname !== canonical.hostname
        || location.pathname !== canonical.pathname) return;
    const url = new URL(location.href);
    const currentBucket = String(Math.floor(Date.now() / intervalMs));
    if (url.searchParams.get('_fresh') === currentBucket) return;
    url.searchParams.set('_fresh', currentBucket);
    location.replace(url.toString());
  }}

  refreshStalePage();
  addEventListener('pageshow', (event) => {{
    if (event.persisted) refreshStalePage();
  }});
}})();
""".strip()


# ---------- значения и форматирование ----------

def _render_bank_chips(banks: list[dict]) -> str:
    return "".join(
        f'<button type="button" class="chip" data-bank-index="{idx}">'
        f'{_esc(bank["bank"])}</button>'
        for idx, bank in enumerate(banks)
    )

def _service_cost_summary(row) -> dict:
    raw = row["fields"].get("service_cost", "")
    entry = row["fields"].get("entry_conditions", "")
    if row.get("tier_id") == "raif_premium_1":
        cost = _monthly_rub_cost(raw) or _monthly_rub_cost(entry)
        if cost is not None:
            return {"display": f"{_format_rub(cost)} ₽ в месяц"}
    combined_low = f"{raw} {entry}".lower()
    parts = []
    if "бесплат" in combined_low or re.search(r"\b0\s*(?:₽|руб)", combined_low,
                                              flags=re.IGNORECASE):
        parts.append("бесплатно при выполнении условий")
    cost = _monthly_rub_cost(raw)
    if cost is not None and cost > 0 and not parts and entry and not _is_missing(entry):
        parts.append("бесплатно при выполнении условий")
    if cost is not None and cost > 0:
        parts.append(f"{_format_rub(cost)} ₽ в месяц")
    if not parts and _is_missing(raw):
        parts.append("стоимость не указана")
    if not parts and raw:
        parts.append(_shorten(raw, 140))
    if not parts:
        parts.append("нет данных")
    parts[0] = parts[0][0].upper() + parts[0][1:]
    return {"display": " или ".join(parts)}


def _condition_summary(value: str, tier_id=None, limit: int = 5) -> str:
    text = _public_text(value)
    if not text or _is_missing(text):
        return ""
    keep_monthly_fee = tier_id in {"tbank_bronze", "raif_premium_1"}
    text = re.sub(r"\bзп\b", "зарплата", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*(?:и\s+)?или\s+", " | ", text,
                  flags=re.IGNORECASE)
    text = re.sub(r"\s+и\s+или\s+", " | ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*;\s*", " | ", text)
    text = re.sub(r"\s+\|\s+или\s+\|", " | ", text)
    text = re.sub(r"\|\s*или\s*\|", "|", text)
    text = re.sub(r"\s+", " ", text).strip(" |;")
    parts = []
    for part in re.split(r"\s*\|\s*", text):
        cleaned = part.strip(" ;")
        if not cleaned:
            continue
        if cleaned.lower().startswith("или ") and not keep_monthly_fee:
            cleaned = cleaned[4:].strip()
        low = cleaned.lower()
        if re.search(r"\d[\d\s]*\s*₽\s*в\s*мес", low) and not keep_monthly_fee:
            continue
        if "последний календарный день" in low:
            continue
        if "среднемесячный остаток" in low and parts:
            continue
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    if not parts:
        return normalize_source_text(text)
    shown = parts[:limit]
    summary = "; ".join(shown)
    if len(parts) > limit:
        summary += f"; ещё {len(parts) - limit}"
    if tier_id == "tbank_bronze" and len(parts) >= 2:
        fee = parts[0]
        shares = parts[1]
        if shares.lower().startswith("или "):
            shares = shares[4:].strip()
        return f"Уровень за {fee}\nили {shares}"
    if tier_id == "raif_premium_1":
        fee = next(
            (part for part in parts
             if re.search(r"\d[\d\s]*\s*₽\s*в\s*мес", part, flags=re.IGNORECASE)),
            "",
        )
        if fee:
            amount = re.search(r"(\d[\d\s]*)\s*₽", fee)
            if amount:
                return f"{_format_rub(amount.group(1).replace(' ', ''))} ₽ в месяц"
            return normalize_source_text(fee)
    return normalize_source_text(summary)


def _entry_hint(row: dict, attrs: list[dict]) -> str:
    entry_attr = next((attr for attr in attrs if attr["id"] == "entry_conditions"), None)
    summary = entry_attr["value"] if entry_attr else ""
    raw_record = row["fields"].get("entry_conditions", "")
    raw = _json_field_value(raw_record) if isinstance(raw_record, dict) else raw_record
    return _entry_hint_from_text(f"{summary} | {raw}")


def _entry_match(row: dict) -> dict:
    """Return a conservative capital interval for level recommendations."""
    raw_record = row["fields"].get("entry_conditions", "")
    raw = _json_field_value(raw_record) if isinstance(raw_record, dict) else raw_record
    return _entry_match_from_text(raw)


def _entry_match_from_text(value: str) -> dict:
    """Extract only standalone personal-capital entry routes from source text.

    The comparison evaluator intentionally merges alternative metrics.  A
    recommendation must be stricter: a lower balance combined with spending,
    salary, shares, joint access, or a monthly fee is not the same as a pure
    capital threshold and therefore cannot replace it.
    """
    empty = {
        "eligible": False,
        "min_amount": None,
        "max_amount": None,
        "label": "",
    }
    text = _public_text(value)
    if not text or _is_missing(text):
        return empty

    clauses = [
        part.strip(" ,;.|.")
        for part in re.split(
            r"\s*(?:[;|\n]+|\.\s+(?=(?:другие\s+)?регионы\b|москва\b)|"
            r",\s*(?=(?:и\s+)?или\b)|\bи\s+или\b|"
            r"\bили\b|\bлибо\b|"
            r"\bи\b(?=\s*\d[^;|]*(?:моск|мск|регион)))\s*",
            text,
            flags=re.IGNORECASE,
        )
        if part.strip(" ,;.|.")
    ]
    excluded_markers = (
        "трат", "покуп", "оборот", "зарплат", "зп", "поступлен",
        "зачислен", "акци", "совмест", "платное обслуж", "в мес",
        "в месяц", "/мес",
    )
    generic = []
    regional = []
    for clause in clauses:
        low = clause.lower()
        amounts = _rub_amounts(clause)
        if len(amounts) != 1 or _monthly_rub_cost(clause) is not None:
            continue
        if any(marker in low for marker in excluded_markers):
            continue
        amount = amounts[0]
        if "моск" in low or re.search(r"\bмск\b", low):
            regional.append(("moscow", amount, bool(re.search(r"\bдо\b", low))))
        elif "регион" in low:
            regional.append(("regions", amount, bool(re.search(r"\bдо\b", low))))
        else:
            generic.append(amount)

    if generic:
        amount = generic[0]
        return {
            "eligible": True,
            "min_amount": amount,
            "max_amount": amount,
            "label": _compact_rub(amount),
        }
    if regional:
        values = [amount for _scope, amount, _upper_bound in regional]
        minimum, maximum = min(values), max(values)
        if all(upper_bound for _scope, _amount, upper_bound in regional):
            return {
                "eligible": True,
                "min_amount": 0,
                "max_amount": maximum,
                "label": (
                    f"до {_rub_interval_label(minimum, maximum)} по региону"
                ),
            }
        return {
            "eligible": True,
            "min_amount": minimum,
            "max_amount": maximum,
            "label": f"{_rub_interval_label(minimum, maximum)} по региону",
        }
    return empty


def _rub_interval_label(minimum, maximum) -> str:
    left, right = _compact_rub(minimum), _compact_rub(maximum)
    if minimum == maximum:
        return left
    for suffix in (" млн ₽", " тыс ₽", " ₽"):
        if left.endswith(suffix) and right.endswith(suffix):
            return f"{left[:-len(suffix)]}–{right}"
    return f"{left}–{right}"


def _entry_hint_from_text(value: str) -> str:
    text = _public_text(value)
    if not text or _is_missing(text):
        return ""
    parts = [part.strip(" ;.") for part in re.split(r"\s*(?:\||;|\n)\s*", text) if part.strip(" ;.")]
    balance_keywords = (
        "баланс", "капитал", "остат", "счет", "счёт", "актив", "сбереж",
        "размещ", "совместном доступе", "сберпервый", "sber private",
    )
    spend_keywords = ("трат", "покуп", "оборот", "поступлен", "зачислен", "зарплат")

    def amounts(part: str) -> list[float]:
        return _rub_amounts(part)

    def is_monthly_fee(part: str) -> bool:
        low = part.lower()
        return bool(re.search(r"(?:в\s*мес|в\s*месяц|/мес)", low))

    candidates = []
    for part in parts:
        low = part.lower()
        if not amounts(part) or is_monthly_fee(part):
            continue
        if any(keyword in low for keyword in balance_keywords) and not any(
            keyword in low for keyword in spend_keywords
        ):
            candidates.append(part)
    if not candidates:
        candidates = [part for part in parts if amounts(part) and not is_monthly_fee(part)]
    if candidates:
        return f"от {_compact_rub(amounts(candidates[0])[0])}"

    monthly = _monthly_rub_cost(text)
    if monthly is not None:
        return f"{_compact_rub(monthly)} в месяц"
    return ""


def _clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_float(value):
    if value in ("", None):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _monthly_rub_cost(value: str):
    if not value:
        return None
    normalized = value.replace("\xa0", " ")
    match = re.search(
        r"(\d[\d\s.,]*)\s*(?:₽|руб)[^\n;]{0,20}(?:мес|месяц)",
        normalized,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    digits = re.sub(r"[^\d.,]", "", match.group(1)).replace(",", ".")
    try:
        return float(digits)
    except ValueError:
        return None


def _service_cost_score(raw: str, display: str, cost):
    if cost is not None:
        return -cost
    text = f"{raw} {display}".lower()
    if "бесплат" in text or re.search(r"\b0\s*(?:₽|руб)", text, flags=re.IGNORECASE):
        return 0
    return None


def _category_evaluation(field: str, raw_value, display_value, row: dict) -> dict:
    """Build a conservative, structured comparison contract for one cell."""
    if field == "other_benefits":
        return _benefits_evaluation(raw_value, display_value)

    comparison_value = (
        display_value
        if field == "service_cost" and isinstance(display_value, str)
        else raw_value
    )
    raw = _public_text(comparison_value)
    if _is_missing(raw):
        return _missing_evaluation()

    evaluators = {
        "entry_conditions": _entry_evaluation,
        "service_cost": _service_evaluation,
        "transfers_payments": lambda text: _limit_evaluation(
            text, "transfers_payments"
        ),
        "cash_withdrawal": lambda text: _limit_evaluation(
            text, "cash_withdrawal"
        ),
        "lounge_access": _lounge_evaluation,
        "taxi": lambda text: _compensation_evaluation(text, "taxi"),
        "restaurants": lambda text: _compensation_evaluation(text, "restaurants"),
        "cashback": _cashback_evaluation,
        "deposits": lambda text: _deposits_evaluation(
            text, (row.get("scan_date") or "")[:10]
        ),
        "insurance": _insurance_evaluation,
        "sport_beauty_option": _sport_beauty_evaluation,
        "concierge": lambda text: _service_presence_evaluation(text, "concierge"),
        "supreme": lambda text: _service_presence_evaluation(text, "supreme"),
    }
    for field_id in {
        "internal_transfers", "interbank_transfers_remote",
        "interbank_transfers_office", "card_to_card_transfers", "sbp_transfers",
        "legal_entity_payments",
    }:
        evaluators[field_id] = lambda text, _field=field_id: _limit_evaluation(
            text, "transfers_payments"
        )
    for field_id in {
        "atm_free_withdrawal", "cash_monthly_operational_limit",
        "atm_daily_limit", "cash_desk_daily_limit",
    }:
        evaluators[field_id] = lambda text, _field=field_id: _limit_evaluation(
            text, "cash_withdrawal"
        )
    for field_id in {
        "health_option", "samokat_option", "pets_option", "auto",
        "metal_card", "personal_banking_support",
    }:
        evaluators[field_id] = lambda text, _field=field_id: (
            _service_presence_evaluation(text, _field)
        )
    for field_id in {
        "cash_over_limit_fee", "insurance_russia_coverage",
        "insurance_foreign_coverage", "insurance_covered_people",
        "insurance_owner_accompaniment", "insurance_trip_duration",
        "insurance_trip_count", "insurance_territorial_exclusions",
        "insurance_additional_risks",
    }:
        evaluators[field_id] = lambda text: _incomparable_evaluation(
            "Условие показано отдельно; автоматический числовой ранг не применяется.",
            _shorten(text, 110),
        )
    evaluator = evaluators.get(field)
    if evaluator is None:
        return _incomparable_evaluation("Для категории не задана надёжная метрика.")
    display_text = _public_text(display_value)
    if field in {
        "transfers_payments", "cash_withdrawal", "cashback", "deposits",
        "taxi", "restaurants", "insurance", "concierge", "supreme",
    } and display_text and not _is_missing(display_text):
        display_evaluation = evaluator(display_text)
        if display_evaluation.get("status") == "comparable":
            return display_evaluation
        raw_evaluation = evaluator(raw)
        if raw_evaluation.get("status") == "comparable":
            return raw_evaluation
        return display_evaluation
    return evaluator(raw)


def _evaluation(method: str, metrics: dict, directions: dict, summary: str,
                scope: dict = None, status: str = "comparable",
                reason: str = "") -> dict:
    return {
        "status": status,
        "method": method,
        "metrics": metrics,
        "directions": directions,
        "scope": scope or {},
        "summary": normalize_source_text(summary),
        "reason": normalize_source_text(reason),
    }


def _missing_evaluation(reason: str = "Нет подтверждённых данных для сравнения.") -> dict:
    return _evaluation("none", {}, {}, "Нет данных", status="missing", reason=reason)


def _incomparable_evaluation(reason: str, summary: str = "") -> dict:
    return _evaluation(
        "none", {}, {}, summary or "Условия требуют отдельного сравнения",
        status="incomparable", reason=reason,
    )


def _explicit_absence(text: str) -> bool:
    low = text.strip().lower()
    return (
        low.startswith(("—", "-", "нет —", "нет,"))
        or "не предусмотр" in low
        or "не заявлен" in low
        or "подтверждённо отсутств" in low
    )


def _availability_metric(text: str):
    low = text.lower()
    if "включено постоянно" in low or "всегда включ" in low:
        return 2
    if "опция на выбор" in low or re.search(r"\bопци[яи]\b", low):
        return 1
    return None


def _entry_evaluation(text: str) -> dict:
    if _explicit_absence(text):
        return _incomparable_evaluation(
            "Отсутствие требований к остатку нельзя приравнять к отсутствию доступа.",
            "Способ входа отличается",
        )

    fragments = [
        part.strip(" ,;.")
        for part in re.split(
            r"\s*(?:;|\n|,\s*(?=(?:или|и)\b)|\bили\b|\bи\b)\s*",
            text,
            flags=re.IGNORECASE,
        )
        if part.strip(" ,;.")
    ]
    metrics = {}
    labels = {}
    for fragment in fragments:
        amounts = _rub_amounts(fragment)
        if not amounts or _monthly_rub_cost(fragment) is not None:
            continue
        low = fragment.lower()
        if "акци" in low:
            key, label = "special_assets", "специальные активы"
        elif "совмест" in low:
            key, label = "joint_capital", "совместный капитал"
        elif any(marker in low for marker in ("трат", "покуп", "оборот")):
            key, label = "monthly_spend", "траты"
        elif any(marker in low for marker in ("зарплат", "зп", "зачислен", "поступлен")):
            key, label = "monthly_income", "зарплата/поступления"
        elif "моск" in low:
            key, label = "capital_moscow", "капитал для Москвы"
        elif "регион" in low:
            key, label = "capital_regions", "капитал для регионов"
        else:
            key, label = "capital", "капитал/остаток"
        amount = min(amounts)
        metrics[key] = min(metrics.get(key, amount), amount)
        labels[key] = label

    if not metrics:
        monthly = _monthly_rub_cost(text)
        if monthly is not None:
            return _incomparable_evaluation(
                "В условии найден только платный способ входа; он сравнивается в стоимости обслуживания.",
                f"Платный вход {_compact_rub(monthly)} в месяц",
            )
        return _incomparable_evaluation(
            "Не удалось надёжно выделить одинаковые способы входа.",
            _shorten(text, 110),
        )

    summary = "; ".join(
        f"{labels[key]} {_compact_rub(value)}" for key, value in metrics.items()
    )
    structure = _entry_structure_metrics(text)
    metrics.update(structure)
    standalone_capital = _standalone_capital_threshold(text)
    if standalone_capital is not None:
        metrics["standalone_capital_threshold"] = standalone_capital
    directions = {key: "lower" for key in metrics}
    directions["alternative_count"] = "higher"
    return _evaluation(
        "entry", metrics, directions, summary,
        reason=(
            "Меньший порог лучше только для одинакового способа входа; "
            "обязательная комбинация «И» сложнее, а дополнительные варианты "
            "входа через «ИЛИ» выгоднее."
        ),
    )


def _standalone_capital_threshold(text: str):
    """Return the conservative regional asset-only threshold, excluding AND bundles."""
    normalized = re.sub(r"\bи\s+или\b", "или", text, flags=re.IGNORECASE)
    clauses = re.split(
        r"(?:;|\n|\.(?=\s|$)|\b(?:или|либо)\b)", normalized,
        flags=re.IGNORECASE,
    )
    thresholds = []
    for clause in clauses:
        low = clause.lower()
        amounts = _rub_amounts(clause)
        if not amounts or _monthly_rub_cost(clause) is not None:
            continue
        if any(marker in low for marker in (
            "трат", "покуп", "оборот", "зарплат", "зачислен", "поступлен",
        )):
            continue
        if any(marker in low for marker in ("акци", "совмест")):
            continue
        has_capital_context = any(marker in low for marker in (
            "актив", "остат", "капитал", "на счет", "на счёт",
        ))
        if has_capital_context or re.fullmatch(
            r"\s*\d[\d\s.,]*(?:млн|тыс)?\s*(?:₽|руб)\s*", clause,
            flags=re.IGNORECASE,
        ):
            thresholds.append(min(amounts))
    # If regions have different thresholds, use the strictest one. This avoids
    # presenting a regional minimum as if it applied to every client.
    return max(thresholds) if thresholds else None


def _entry_structure_metrics(text: str) -> dict:
    """Describe AND/OR complexity without mixing unrelated money thresholds."""
    normalized = re.sub(r"\bи\s+или\b", "или", text, flags=re.IGNORECASE)
    alternatives = re.split(
        r"(?:;\s*)?\b(?:или|либо)\b\s*", normalized,
        flags=re.IGNORECASE,
    )
    if "одного из условий" in normalized.lower() and ";" in normalized:
        tail = normalized.lower().split("одного из условий", 1)[1]
        semicolon_options = [part for part in tail.split(";") if _rub_amounts(part)]
        if len(semicolon_options) > len(alternatives):
            alternatives = semicolon_options

    mandatory_counts = []
    valid_alternatives = 0
    for option in alternatives:
        if _monthly_rub_cost(option) is not None and not any(
            marker in option.lower() for marker in ("остат", "актив", "трат", "покуп", "зарплат")
        ):
            continue
        criteria = set()
        low = option.lower()
        for marker, criterion in (
            ("трат", "spend"), ("покуп", "spend"),
            ("зарплат", "income"), ("зачислен", "income"),
            ("остат", "capital"), ("актив", "capital"),
            ("счет", "capital"), ("счёт", "capital"),
            ("акци", "special_assets"),
        ):
            if marker in low:
                criteria.add(criterion)
        if not criteria and _rub_amounts(option):
            criteria.add("capital")
        if not criteria:
            continue
        valid_alternatives += 1
        mandatory_counts.append(len(criteria))

    return {
        "mandatory_count": min(mandatory_counts or [1]),
        "alternative_count": max(1, valid_alternatives),
    }


def _service_evaluation(text: str) -> dict:
    low = text.lower()
    cost = _monthly_rub_cost(text)
    conditional = bool(re.search(r"при\s+(?:выполн|услов|остат|трат)", low))
    free = "бесплат" in low or bool(
        re.search(r"\b0\s*(?:₽|руб)", low, flags=re.IGNORECASE)
    )
    if free and not conditional and (cost is None or cost == 0):
        rank, label = 4, "Безусловно бесплатно"
    elif free and conditional and cost is not None and cost > 0:
        rank = 3
        label = (
            "Два способа обслуживания: бесплатно при выполнении условий "
            f"или {_compact_rub(cost)} в месяц"
        )
    elif free and conditional:
        rank, label = 2, "Бесплатно при выполнении условий"
    elif cost is not None:
        rank, label = 1, f"{_compact_rub(cost)} в месяц"
    else:
        return _incomparable_evaluation(
            "Стоимость или условие бесплатности не выделены однозначно.",
            _shorten(text, 110),
        )
    metrics = {"service_rank": rank}
    directions = {"service_rank": "higher"}
    if cost is not None:
        metrics["monthly_cost"] = cost
        directions["monthly_cost"] = "lower"
    return _evaluation(
        "ordinal", metrics, directions, label,
        reason=(
            "Оценивается доступность обслуживания: безусловно бесплатный режим "
            "сильнее двух способов обслуживания, а бесплатность с платным "
            "запасным способом сильнее бесплатности только при выполнении условий."
        ),
    )


def _rub_amount_matches(text: str) -> list[dict]:
    pattern = re.compile(
        r"(?<![\d.,])(\d[\d\s.,]*)(?:\s*)(тыс|млн)?(?:\s*)(?:₽|руб)",
        flags=re.IGNORECASE,
    )
    matches = []
    for match in pattern.finditer(text):
        amount = _parse_rub_number(match.group(1))
        if amount is None:
            continue
        unit = (match.group(2) or "").lower()
        if unit == "тыс":
            amount *= 1000
        elif unit == "млн":
            amount *= 1_000_000
        matches.append({"amount": amount, "start": match.start(), "end": match.end()})
    return matches


def _limit_period(context: str):
    low = context.lower()
    if re.search(r"(?:в сутки|в день|/день|/сут|дневн)", low):
        return "day"
    if re.search(r"(?:в месяц|в мес|/мес|месячн)", low):
        return "month"
    if "расчётн" in low or "расчетн" in low:
        return "billing"
    if re.search(r"(?:за операци|на операци|за раз)", low):
        return "operation"
    if re.search(r"(?:в год|/год)", low):
        return "year"
    return None


def _limit_scope(text: str, field: str):
    low = text.lower()
    if field == "transfers_payments":
        if "расчётн" in low and "кредитн" in low:
            return "mixed_card_types"
        if "другого банка" in low and "по номеру карт" in low:
            return "card_to_other_bank"
        if "клиент" in low and "сбер" in low and "юрлиц" in low:
            return "sber_clients_and_legal_payments"
        if "сбп" in low:
            return "sbp"
        return "general_transfers"
    own = bool(re.search(r"банкоматах?\s+(?:втб|т-банка|банка)", low))
    other = "других банк" in low or "любых банкомат" in low or "по миру" in low
    if own and other:
        return "mixed_atm_scope"
    if other:
        return "all_atms"
    if own or "партнёр" in low or "партнер" in low:
        return "own_and_partner_atms"
    return "general_cash"


def _limit_evaluation(text: str, field: str) -> dict:
    low = text.lower()
    if (
        field == "cash_withdrawal"
        and "при выполнении условий" in low
        and re.search(r"сняти[ея][^.;]{0,90}без комис", low)
        and "сторонних банк" in low
    ):
        return _evaluation(
            "limit", {"unlimited": True, "limits": []}, {},
            "Без комиссии во всех банкоматах при выполнении условий",
            scope={"operation_scope": "all_atms"},
            reason=(
                "Сравнивается отсутствие комиссии во всех банкоматах; "
                "технические операционные лимиты не считаются комиссионным лимитом."
            ),
        )
    scope = _limit_scope(text, field)
    if scope in {"mixed_card_types", "mixed_atm_scope"}:
        return _incomparable_evaluation(
            "В одной ячейке указаны разные типы карт или области действия лимитов.",
            _shorten(text, 110),
        )
    if "при превышении" in low and any(
        marker in low for marker in ("без ограничений", "безлимит")
    ):
        return _incomparable_evaluation(
            "Лимит зависит от дополнительного условия и не является безусловным.",
            _shorten(text, 110),
        )
    if any(marker in low for marker in ("безлимит", "без ограничений", "не ограничен")):
        return _evaluation(
            "limit", {"unlimited": True, "limits": []}, {}, "Безлимит",
            scope={"operation_scope": scope},
            reason="Безлимит сравнивается только при одинаковой области действия.",
        )

    limits = []
    for match in _rub_amount_matches(text):
        if field == "transfers_payments":
            before_long = low[max(0, match["start"] - 100):match["start"]]
            if re.search(
                r"(?:общий|технический)[^.;]{0,80}лимит", before_long
            ):
                continue
        after = text[match["end"]:min(len(text), match["end"] + 36)]
        before = text[max(0, match["start"] - 36):match["start"]]
        period = _limit_period(after) or _limit_period(before)
        if period:
            limits.append({"amount": match["amount"], "period": period})
    unique = []
    for item in limits:
        if item not in unique:
            unique.append(item)
    if not unique:
        return _incomparable_evaluation(
            "Не найден подтверждённый лимит с периодом действия.",
            _shorten(text, 110),
        )
    period_names = {
        "day": "в сутки", "month": "в месяц", "billing": "за расчётный период",
        "operation": "за операцию", "year": "в год",
    }
    summary = "; ".join(
        f"{_compact_rub(item['amount'])} {period_names[item['period']]}"
        for item in unique
    )
    return _evaluation(
        "limit", {"unlimited": False, "limits": unique}, {}, summary,
        scope={"operation_scope": scope},
        reason="Лимиты сравниваются без пересчёта суток в месяц.",
    )


def _lounge_evaluation(text: str) -> dict:
    if _explicit_absence(text):
        return _evaluation(
            "lounge", {"visits_monthly": 0}, {"visits_monthly": "higher"},
            "Бизнес-залы не предусмотрены",
        )
    low = text.lower()
    metrics = {}
    if any(marker in low for marker in ("безлимит", "без ограничений", "не ограничен")):
        metrics["unlimited"] = 1
    else:
        counts = _monthly_counts(text)
        if counts:
            metrics["visits_monthly"] = max(counts)
    preference_equivalence = re.search(
        r"1\s*преференци\w*\s*=\s*1\s*"
        r"(?:проход\w*|использовани\w*)",
        low,
    )
    preference_counts = [
        float(value.replace(",", "."))
        for value in re.findall(
            r"(\d+(?:[.,]\d+)?)\s*преференци\w*"
            r"(?:\s+в\s+месяц|\s*/\s*мес)",
            low,
        )
    ]
    if preference_equivalence and preference_counts:
        preference_visits = max(preference_counts)
        metrics["visits_monthly"] = max(
            preference_visits, metrics.get("visits_monthly", 0)
        )
        metrics["shared_preference_pool"] = 1
    annual_counts = _annual_counts(text)
    if annual_counts:
        metrics["annual_cap"] = max(annual_counts)
    availability = _availability_metric(text)
    if availability is not None:
        metrics["availability"] = availability
    guest = re.search(r"(\d+)\s*(?:гост|спутник)", low)
    if guest:
        metrics["guests"] = float(guest.group(1))
    access_programs = _lounge_access_programs(text)
    if access_programs:
        metrics["access_programs"] = len(access_programs)
    if not metrics or set(metrics) == {"availability"}:
        return _incomparable_evaluation(
            "Количество посещений или безлимит не подтверждены.",
            _shorten(text, 110),
        )
    directions = {key: "higher" for key in metrics}
    if metrics.get("unlimited"):
        summary = "Безлимит"
    else:
        summary = f"{metrics.get('visits_monthly', 0):g} посещений в месяц"
    if availability == 2:
        summary += ", включено постоянно"
    elif availability == 1:
        summary += ", опция на выбор"
    if access_programs:
        summary += f", сервисов доступа: {len(access_programs)}"
    return _evaluation(
        "lounge", metrics, directions, summary,
        reason=(
            "Ранг определяется подтверждённым максимумом посещений. "
            "Сервисы доступа показываются справочно и не разрывают равенство. "
            + (
                "Проходы расходуются из общего баланса преференций. "
                if metrics.get("shared_preference_pool") else ""
            )
        ),
    )


def _lounge_access_programs(text: str) -> list[str]:
    """Return unique, explicitly named lounge-access programs.

    Longer names are matched first and consume their text span. This lets
    ``ON·PASS`` and ``ON·PASS Premium`` count as two programs when both are
    explicitly listed, without double-counting a lone Premium occurrence.
    """
    patterns = (
        ("Phoenix Pass Exclusive", r"\bphoenix\s+pass\s+exclusive\b"),
        ("ON·PASS Premium", r"\bon\s*[·.]\s*pass\s+premium\b"),
        ("MILE·ON·AIR", r"\bmile\s*[·.]\s*on\s*[·.]\s*air\b"),
        ("Persona.aero", r"\bpersona(?:\.aero)?\b"),
        ("Phoenix Pass", r"\bphoenix\s+pass\b"),
        ("Priority Pass", r"\bpriority\s+pass\b"),
        ("Lounge Key", r"\blounge\s*key\b"),
        ("DragonPass", r"\bdragon\s*pass\b"),
        ("Every Lounge", r"\bevery\s+lounge\b"),
        ("Soft Travel", r"\bsoft\s+travel\b"),
        ("Only Assist", r"\bonly\s+assist\b"),
        ("Mir Pass", r"\bmir\s+pass\b"),
        ("Grey Wall", r"\bgrey\s+wall\b"),
        ("ON·PASS", r"\bon\s*[·.]\s*pass\b"),
        ("Частично", r"\bчастично\b"),
    )
    low = text.lower()
    occupied: list[tuple[int, int]] = []
    found: list[str] = []
    for name, pattern in patterns:
        for match in re.finditer(pattern, low, flags=re.IGNORECASE):
            span = match.span()
            if any(span[0] < end and start < span[1] for start, end in occupied):
                continue
            occupied.append(span)
            found.append(name)
    return found


def _compensation_evaluation(text: str, field: str) -> dict:
    if _explicit_absence(text):
        return _evaluation(
            "compensation", {"monthly_total": 0}, {"monthly_total": "higher"},
            "Не предусмотрено",
        )
    low = text.lower()
    if "только при" in low or "только для" in low:
        return _incomparable_evaluation(
            "Привилегия действует с отдельным ограничением.", _shorten(text, 110)
        )
    # Capital, salary and purchase thresholds describe eligibility, not the
    # value of a taxi/restaurant benefit.  Ignore the qualification tail when
    # extracting counts and ruble amounts, but keep the full text for the
    # displayed condition and availability status.
    benefit_text = re.split(
        r"\bусловия\s*:|(?:доступн\w*\s+)?при\s+"
        r"(?:остат|баланс|капитал|покуп|трат|зачисл|поступл|оборот)",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    metrics = {}
    if any(marker in low for marker in ("безлимит", "без ограничений", "не ограничен")):
        metrics["unlimited"] = 1
    counts = _monthly_counts(benefit_text)
    if counts:
        metrics["monthly_count"] = max(counts)
    annual_counts = _annual_counts(benefit_text)
    if annual_counts:
        metrics["annual_count"] = max(annual_counts)
    amounts = _rub_amounts(benefit_text)
    per_use = re.search(
        r"(?:по|до|на|чек(?:а|ом)?\s*(?:до)?|поездк[аи]?\s*(?:до)?)\s*"
        r"(\d[\d\s.,]*)\s*(тыс|млн)?\s*(?:₽|ингорубл(?:ей|я|ь)?)",
        benefit_text,
        flags=re.IGNORECASE,
    )
    if per_use:
        parsed = _parse_rub_number(per_use.group(1))
        if parsed is not None:
            unit = (per_use.group(2) or "").lower()
            if unit == "тыс":
                parsed *= 1000
            elif unit == "млн":
                parsed *= 1_000_000
            metrics["per_use_limit"] = parsed
    if (
        "monthly_count" in metrics
        and "per_use_limit" not in metrics
        and len(amounts) == 1
        and not re.search(
            r"\d[\d\s.,]*\s*(?:тыс|млн)?\s*₽[^.;]{0,16}"
            r"(?:в\s*мес|в\s*месяц|/мес)",
            low,
        )
    ):
        metrics["per_use_limit"] = amounts[0]
    if amounts and not (metrics.get("unlimited") and "monthly_count" not in metrics):
        metrics["monthly_total"] = max(amounts)
    if "monthly_count" in metrics and "per_use_limit" in metrics:
        metrics["monthly_total"] = (
            metrics["monthly_count"] * metrics["per_use_limit"]
        )
    if "monthly_total" in metrics:
        if "annual_count" in metrics and "per_use_limit" in metrics:
            metrics["annual_total"] = (
                metrics["annual_count"] * metrics["per_use_limit"]
            )
        else:
            metrics["annual_total"] = metrics["monthly_total"] * 12
    availability = _availability_metric(text)
    if availability is not None:
        metrics["availability"] = availability
    if not metrics:
        return _incomparable_evaluation(
            "Количество и денежный лимит не выделены.", _shorten(text, 110)
        )
    labels = []
    if metrics.get("unlimited"):
        labels.append("безлимит")
    if "per_use_limit" in metrics:
        if re.search(r"посадочн(?:ый|ого|ому|ым|ом)\s+талон", low):
            labels.append(
                f"до {_compact_rub(metrics['per_use_limit'])} на один посадочный талон"
            )
        elif metrics.get("unlimited"):
            labels.append(f"до {_compact_rub(metrics['per_use_limit'])} за использование")
    if "monthly_total" in metrics:
        labels.append(f"до {_compact_rub(metrics['monthly_total'])} в месяц")
    if "annual_total" in metrics:
        labels.append(f"до {_compact_rub(metrics['annual_total'])} в год")
    if "monthly_count" in metrics:
        labels.append(f"{metrics['monthly_count']:g} использований")
    if "annual_count" in metrics:
        labels.append(f"до {metrics['annual_count']:g} в год")
    if availability == 1:
        labels.append("опция на выбор")
    elif availability == 2:
        labels.append("включено постоянно")
    return _evaluation(
        "compensation", metrics, {key: "higher" for key in metrics},
        ", ".join(labels) or FIELD_LABELS[field],
        reason=(
            "Сначала сравнивается общая компенсация в месяц, затем количество "
            "использований и лимит одного использования."
        ),
    )


def _cashback_evaluation(text: str) -> dict:
    if _explicit_absence(text):
        return _evaluation(
            "cashback", {"max_rate": 0}, {"max_rate": "higher"},
            "Кэшбэк не предусмотрен"
        )
    rates = [float(value.replace(",", ".")) for value in re.findall(
        r"(\d+(?:[.,]\d+)?)\s*%", text
    )]
    low = text.lower()
    metrics = {}
    base_match = re.search(r"базов[^\d]{0,24}(\d+(?:[.,]\d+)?)\s*%", low)
    if base_match:
        metrics["base_rate"] = float(base_match.group(1).replace(",", "."))
    if rates:
        metrics["max_rate"] = max(rates)
    if any(marker in low for marker in ("без лимита", "безлимит")):
        metrics["unlimited_accrual"] = 1
    category_match = re.search(r"(\d+)\s*катег", low)
    if category_match:
        metrics["categories"] = float(category_match.group(1))
    cap_match = re.search(
        r"(?:лимит[^\d]{0,24}|до\s*)"
        r"(\d[\d\s.,]*)\s*(тыс|млн)?\s*₽"
        r"(?:[^.;]{0,18}(?:в\s*мес|в\s*месяц|/мес))?",
        text,
        flags=re.IGNORECASE,
    )
    if cap_match:
        cap = _parse_rub_number(cap_match.group(1))
        if cap is not None:
            if (cap_match.group(2) or "").lower() == "тыс":
                cap *= 1000
            elif (cap_match.group(2) or "").lower() == "млн":
                cap *= 1_000_000
            metrics["monthly_cap"] = cap
    bonus_exchange = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(?:бонус\w*|б)"
        r"(?:\s+балл\w*)?\s*=\s*"
        r"(\d+(?:[.,]\d+)?)\s*₽",
        low,
    )
    if bonus_exchange:
        source_bonus = float(bonus_exchange.group(1).replace(",", "."))
        rub_value = float(bonus_exchange.group(2).replace(",", "."))
        if source_bonus > 0:
            metrics["bonus_rub_value"] = rub_value / source_bonus
    bonus_cap_match = re.search(
        r"лимит[^\d]{0,28}(\d[\d\s.,]*)\s*(?:б(?:/|\b)|бонус)",
        low,
    )
    if bonus_cap_match:
        bonus_cap = _parse_rub_number(bonus_cap_match.group(1))
        if bonus_cap is not None:
            metrics["monthly_bonus_cap"] = bonus_cap
            if "monthly_cap" not in metrics and "bonus_rub_value" in metrics:
                metrics["monthly_cap"] = bonus_cap * metrics["bonus_rub_value"]
    effective_cap = metrics.get("monthly_cap", metrics.get("monthly_bonus_cap"))
    if effective_cap is not None:
        metrics["effective_monthly_cap"] = effective_cap
    if not metrics:
        return _incomparable_evaluation(
            "Ставка, лимит и число категорий кэшбэка не указаны.",
            _shorten(text, 110),
        )
    summary = (
        f"до {metrics['max_rate']:g}%"
        if "max_rate" in metrics
        else "ставка не опубликована"
    )
    if "max_rate" in metrics and "base_rate" not in metrics:
        summary += ", оценка только по опубликованной максимальной ставке"
    return _evaluation(
        "cashback", metrics, {key: "higher" for key in metrics}, summary,
        reason=(
            "Сначала сравнивается подтверждённый месячный лимит кешбэка, "
            "затем общие подтверждённые ставки и количество категорий."
        ),
    )


def _deposits_evaluation(text: str, scan_date: str) -> dict:
    if _explicit_absence(text):
        return _evaluation(
            "dominance", {"rate": 0}, {"rate": "higher"}, "Спецусловия не предусмотрены",
            scope={"scan_date": scan_date},
        )
    rates = [float(value.replace(",", ".")) for value in re.findall(
        r"(\d+(?:[.,]\d+)?)\s*%", text
    )]
    if not rates:
        return _incomparable_evaluation(
            "Ставка или надбавка не опубликована.", _shorten(text, 110)
        )
    rate = max(rates)
    metrics = {"rate": rate}
    directions = {"rate": "higher"}
    minimum = re.search(
        r"(?:от|min(?:imum)?)\s*(\d[\d\s.,]*)\s*(тыс|млн)?\s*₽", text,
        flags=re.IGNORECASE,
    )
    maximum = re.search(
        r"(?:до|max(?:imum)?)\s*(\d[\d\s.,]*)\s*(тыс|млн)?\s*₽", text,
        flags=re.IGNORECASE,
    )
    for match, key, direction in (
        (minimum, "minimum_amount", "lower"),
        (maximum, "maximum_amount", "higher"),
    ):
        if not match:
            continue
        amount = _parse_rub_number(match.group(1))
        if amount is None:
            continue
        if (match.group(2) or "").lower() == "тыс":
            amount *= 1000
        elif (match.group(2) or "").lower() == "млн":
            amount *= 1_000_000
        metrics[key] = amount
        directions[key] = direction
    return _evaluation(
        "dominance", metrics, directions,
        f"до {rate:g}%" if len(set(rates)) > 1 else f"{rate:g}%",
        scope={"scan_date": scan_date},
        reason=(
            "При нескольких опубликованных ставках сравнивается максимальная "
            "ставка категории; даты проверки должны совпадать."
        ),
    )


def _insurance_evaluation(text: str) -> dict:
    if _explicit_absence(text):
        return _evaluation(
            "insurance", {"max_coverage_rub": 0},
            {"max_coverage_rub": "higher"},
            "Страхование не предусмотрено",
        )
    low = text.lower()
    availability = _availability_metric(text)
    metrics = {}
    coverages = _insurance_coverages(text)
    if coverages:
        rub_values = [item["rub"] for item in coverages]
        metrics["max_coverage_rub"] = max(rub_values)
        owner = [item["rub"] for item in coverages if item["person"] == "owner"]
        family = [item["rub"] for item in coverages if item["person"] == "family"]
        russia = [item["rub"] for item in coverages if item["territory"] == "russia"]
        foreign = [item["rub"] for item in coverages if item["territory"] == "foreign"]
        if owner:
            metrics["owner_coverage_rub"] = max(owner)
        if family:
            metrics["family_coverage_rub"] = max(family)
        if russia:
            metrics["russia_coverage_rub"] = max(russia)
        if foreign:
            metrics["foreign_coverage_rub"] = max(foreign)
        territories = {item["territory"] for item in coverages if item["territory"]}
        if territories:
            metrics["territory_count"] = len(territories)
    days = [float(value) for value in re.findall(r"(\d+)\s*(?:дн|дней|дня)", low)]
    if days:
        metrics["trip_days"] = max(days)
    if availability is not None:
        metrics["availability"] = availability
    if any(marker in low for marker in ("по всему миру", "worldwide", "глобальн")):
        metrics["territory_count"] = max(metrics.get("territory_count", 0), 2)
    if not metrics:
        return _incomparable_evaluation(
            "Страховая сумма и сопоставимый объём покрытия не выделены.",
            _shorten(text, 110),
        )
    summary_parts = []
    if "max_coverage_rub" in metrics:
        summary_parts.append(
            f"максимум {_compact_rub(metrics['max_coverage_rub'])} в эквиваленте"
        )
    if "trip_days" in metrics:
        summary_parts.append(f"до {metrics['trip_days']:g} дней")
    return _evaluation(
        "insurance", metrics, {key: "higher" for key in metrics},
        ", ".join(summary_parts) or "Подтверждённое страхование",
        reason=("Учитываются сумма, срок, территория и статус подключения. "
                "Покрытия в долларах и евро сопоставляются в рублёвом "
                f"эквиваленте по официальному курсу ЦБ на {INSURANCE_FX_DATE}."),
    )


def _insurance_coverages(text: str) -> list[dict]:
    """Extract source-stated insurance amounts without changing displayed facts."""
    patterns = (
        re.compile(
            r"(?P<currency>[$€])\s*(?P<amount>\d[\d\s]*(?:[.,]\d+)?)"
            r"\s*(?P<unit>млн|тыс)?",
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"(?P<amount>\d[\d\s]*(?:[.,]\d+)?)\s*(?P<unit>млн|тыс)?\s*"
            r"(?P<currency>евро|eur|доллар(?:ов|а)?|usd)",
            flags=re.IGNORECASE,
        ),
    )
    found = []
    occupied = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            if any(match.start() < end and start < match.end() for start, end in occupied):
                continue
            amount = _parse_rub_number(match.group("amount"))
            if amount is None:
                continue
            unit = (match.group("unit") or "").lower()
            if unit == "тыс":
                amount *= 1000
            elif unit == "млн":
                amount *= 1_000_000
            raw_currency = match.group("currency").lower()
            currency = "€" if raw_currency in {"€", "евро", "eur"} else "$"
            before = text[max(0, match.start() - 25):match.start()].lower()
            after = text[match.end():min(len(text), match.end() + 45)].lower()
            family_pattern = r"(?:для|на)\s+(?:одного\s+)?член\w*\s+семь"
            owner_pattern = r"(?:для|на)\s+владел"
            family_match = re.search(family_pattern, after)
            owner_match = re.search(owner_pattern, after)
            if family_match and owner_match:
                person = (
                    "family" if family_match.start() < owner_match.start() else "owner"
                )
            elif family_match:
                person = "family"
            elif owner_match:
                person = "owner"
            else:
                person = "family" if re.search(family_pattern, before) else (
                    "owner" if re.search(owner_pattern, before) else ""
                )
            territory = "russia" if re.search(r"\b(?:рф|росси)\b", after) else (
                "foreign" if any(marker in after for marker in (
                    "за рубеж", "зарубеж", "иностран", "по всему миру", "worldwide",
                )) else ""
            )
            found.append({
                "amount": amount,
                "currency": currency,
                "rub": amount * INSURANCE_FX_RUB_PER_UNIT[currency],
                "person": person,
                "territory": territory,
            })
            occupied.append(match.span())
    return found


def _insurance_display(text: str) -> str:
    """Show insured amounts, never PBI's estimated market price of a policy."""
    estimate_pattern = (
        r"(?:и|;)?\s*Примерная стоимость на 2 взрослых\s*≈\s*"
        r"[\d\s]+\s*₽"
    )
    text = re.sub(estimate_pattern, "", text, flags=re.IGNORECASE).rstrip(" ;,.")
    coverage = re.search(
        r"([$€])\s*(\d+(?:[.,]\d+)?)"
        r"(?:\s*/\s*(\d+(?:[.,]\d+)?))?\s*(млн|тыс)?",
        text,
        flags=re.IGNORECASE,
    )
    if not coverage:
        return text
    currency, owner, family, unit = coverage.groups()
    unit_suffix = f" {unit}" if unit else ""
    label = f"Страховое покрытие: {currency}{owner}{unit_suffix}"
    if family is not None:
        label += (
            f" для владельца / {currency}{family}{unit_suffix} "
            "для члена семьи"
        )
    return text[:coverage.start()] + label + text[coverage.end():]


def _service_presence_evaluation(text: str, field: str) -> dict:
    low = text.lower()
    if _explicit_absence(text):
        label = "Не предусмотрено" if field == "concierge" else "Supreme не заявлена"
        return _evaluation(
            "ordinal", {"service_rank": 0}, {"service_rank": "higher"}, label
        )
    if any(marker in low for marker in ("при актив", "при выполн", "покупк от", "может быть")):
        rank, label = 2, "Доступно при выполнении условий"
    elif "бесплат" in low or "включён в пакет" in low or "включен в пакет" in low:
        rank, label = 4, "Бесплатно включено"
    elif re.search(r"(?<!бес)платн", low) or re.search(
        r"(?:стоимост|обслуживан|выпуск)[^.;]{0,28}\d[\d\s]*\s*₽", text,
        flags=re.IGNORECASE,
    ):
        rank, label = 1, "Доступно платно"
    elif _has_benefit(text):
        rank, label = 3, "Наличие подтверждено, стоимость не выделена"
    else:
        return _incomparable_evaluation(
            "Наличие услуги не подтверждено однозначно.", _shorten(text, 110)
        )
    if (
        field == "supreme"
        and rank == 4
        and "дополнительн" in low
        and "бесплат" in low
    ):
        rank, label = 3, "Карта подтверждена; дополнительные карты бесплатны"
    metrics = {"service_rank": rank}
    directions = {"service_rank": "higher"}
    if field == "concierge" and any(marker in low for marker in ("24/7", "круглосуточ")):
        metrics["round_the_clock"] = 1
        directions["round_the_clock"] = "higher"
    extra_cards = re.search(r"до\s*(\d+)\s*дополнительн", low)
    if field == "supreme" and extra_cards:
        metrics["additional_cards"] = float(extra_cards.group(1))
        directions["additional_cards"] = "higher"
    if field == "supreme":
        if "world elite" in low or re.search(r"\bprime\b", low):
            metrics["card_tier_rank"] = 5
        elif "supreme" in low:
            metrics["card_tier_rank"] = 4
        else:
            metrics["card_tier_rank"] = 2
        directions["card_tier_rank"] = "higher"
    return _evaluation(
        "ordinal", metrics, directions, label,
        reason="Статус наличия, бесплатность и подтверждённые условия сравниваются раздельно.",
    )


def _sport_beauty_evaluation(text: str) -> dict:
    """Compare access to sport/beauty without equating unlike currencies.

    Fitmost bonus rubles and appoint points have different providers and
    periods, so their nominal amounts are displayed but not ranked against one
    another. The reliable common dimension is whether access is included or
    requires choosing an option.
    """
    low = text.lower()
    if _explicit_absence(text):
        return _evaluation(
            "ordinal", {"service_rank": 0}, {"service_rank": "higher"},
            "Не предусмотрено",
            reason="Сравнивается подтверждённая доступность категории.",
        )
    if not _has_benefit(text):
        return _incomparable_evaluation(
            "Доступность категории не подтверждена однозначно.",
            _shorten(text, 110),
        )
    if "всегда включ" in low or "включено постоянно" in low:
        rank, label = 4, "Включено постоянно"
    elif re.search(r"\bопци[яи]\b", low) or "пакет «спорт»" in low:
        rank, label = 2, "Доступно как опция на выбор"
    else:
        rank, label = 3, "Доступ к категории подтверждён"
    return _evaluation(
        "ordinal", {"service_rank": rank}, {"service_rank": "higher"},
        label,
        reason=(
            "Сравнивается доступность категории. Номиналы Фитмост и appoint "
            "не сопоставляются: это разные сервисы, единицы и периоды."
        ),
    )


def _benefit_key(title: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", " ", title.lower()).strip()


def _benefit_rub_total(description: str):
    """Return a confirmed total when one benefit states count × rubles."""
    match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*"
        r"(?:заказ(?:а|ов)?|посещени(?:е|я|й)|поезд(?:ка|ки|ок))"
        r"(?:\s+в\s+месяц)?\s+(?:по|на)\s+"
        r"(\d[\d\s.,]*)\s*(тыс|млн)?\s*₽",
        description,
        flags=re.IGNORECASE,
    )
    if not match:
        bonus_rubles = re.search(
            r"(\d[\d\s.,]*)\s*бонусн(?:ых|ые)?\s+руб(?:лей|ля|ль)?"
            r"(?:\s+в\s+(?:месяц|мес\.?))?",
            description,
            flags=re.IGNORECASE,
        )
        if bonus_rubles:
            return _parse_rub_number(bonus_rubles.group(1))
        promo = re.search(
            r"промокод(?:ы|ов)?\s+на\s+(\d[\d\s.,]*)\s*(тыс|млн)?(?:\s*₽)?",
            description,
            flags=re.IGNORECASE,
        )
        if not promo:
            return None
        amount = _parse_rub_number(promo.group(1))
        if amount is None:
            return None
        unit = (promo.group(2) or "").lower()
        if unit == "тыс":
            amount *= 1000
        elif unit == "млн":
            amount *= 1_000_000
        return amount
    count = _parse_float(match.group(1))
    amount = _parse_rub_number(match.group(2))
    if count is None or amount is None:
        return None
    unit = (match.group(3) or "").lower()
    if unit == "тыс":
        amount *= 1000
    elif unit == "млн":
        amount *= 1_000_000
    return count * amount


def _benefits_evaluation(raw_value, display_value) -> dict:
    source_text = str(raw_value or "")
    raw = _public_text(source_text)
    if _is_missing(raw):
        return _missing_evaluation()
    items = (
        display_value
        if isinstance(display_value, list)
        else _benefits_list(source_text)
    )
    benefits = {}
    labels = {}
    status_rank = {"selectable": 1, "always_included": 2}
    for item in items:
        if item.get("availability") == "rule":
            continue
        key = _benefit_key(item.get("title", ""))
        if not key:
            continue
        availability = item.get("availability", "")
        benefit = {
            "status": status_rank.get(availability, 1),
            "status_known": 1 if availability in status_rank else 0,
        }
        rub_total = _benefit_rub_total(item.get("description", ""))
        if rub_total is not None:
            benefit["rub_total"] = rub_total
        benefits[key] = benefit
        labels[key] = item.get("title", key)
    if not benefits:
        return _incomparable_evaluation(
            "Не найден набор привилегий с подтверждённым статусом.",
            _shorten(raw, 110),
        )
    always_count = sum(
        1 for benefit in benefits.values() if benefit["status"] == 2
    )
    selectable_count = sum(
        1 for benefit in benefits.values() if benefit["status"] == 1
        and benefit["status_known"] == 1
    )
    confirmed_count = sum(
        1 for benefit in benefits.values() if benefit["status_known"] == 0
    )
    summary_parts = [
        f"{always_count} постоянно",
        f"{selectable_count} на выбор",
    ]
    if confirmed_count:
        summary_parts.append(f"{confirmed_count} с подтверждённым наличием")
    summary = ", ".join(summary_parts)
    valued = [
        f"{labels[key]}: {_compact_rub(benefit['rub_total'])}"
        for key, benefit in benefits.items()
        if "rub_total" in benefit
    ]
    if valued:
        summary += f"; {', '.join(valued)}"
    return _evaluation(
        "benefit_set", {"benefits": benefits, "labels": labels}, {}, summary,
        reason=(
            "Наборы сравниваются по подтверждённому наличию одинаковых "
            "привилегий, известному статусу включения и подтверждённому "
            "номиналу одинаковых услуг."
        ),
    )


def _comparison_score(field: str, value: str):
    text = _public_text(value)
    if _is_missing(text):
        return None
    low = text.lower()
    if any(marker in low for marker in ("безлимит", "без ограничений", "не ограничен")):
        if field in {"lounge_access", "taxi", "restaurants", "transfers_payments", "cash_withdrawal"}:
            return 1_000_000
    if field in {"cashback", "deposits"}:
        return _max_percent(text) or _presence_score(text)
    if field == "entry_conditions":
        return _entry_conditions_score(text)
    if field in {"transfers_payments", "cash_withdrawal"}:
        return _limit_score(text) or _presence_score(text)
    if field == "lounge_access":
        return _lounge_score(text) or _presence_score(text)
    if field in {"taxi", "restaurants"}:
        return _compensation_score(text) or _presence_score(text)
    if field == "insurance":
        return _insurance_compare_score(text) or _presence_score(text)
    if field == "concierge":
        return _presence_score(text)
    if field == "supreme":
        return _presence_score(text)
    return None


def _entry_conditions_score(text: str):
    amounts = _rub_amounts(text)
    if not amounts:
        return None
    return -min(amounts)


def _limit_score(text: str):
    low = text.lower()
    if any(marker in low for marker in ("безлимит", "без ограничений", "не ограничен")):
        return 1_000_000_000_000
    amounts = _rub_amounts(text)
    if not amounts:
        return None
    amount = max(amounts)
    # Periods are deliberately not converted: the structured evaluator compares
    # them explicitly and refuses an ambiguous daily/monthly ordering.
    return amount


def _presence_score(text: str):
    return 1 if _has_benefit(text) else 0


def _max_percent(text: str):
    values = [
        float(match.replace(",", "."))
        for match in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", text)
    ]
    return max(values) if values else None


def _rub_amounts(text: str) -> list[float]:
    values = []
    pattern = r"(?<![\d.,])(\d[\d\s.,]*)(?:\s*)(тыс|млн)?(?:\s*)(?:₽|руб)"
    for number, unit in re.findall(pattern, text, flags=re.IGNORECASE):
        amount = _parse_rub_number(number)
        if amount is None:
            continue
        if unit.lower() == "тыс":
            amount *= 1000
        elif unit.lower() == "млн":
            amount *= 1_000_000
        values.append(amount)
    return values


def _parse_rub_number(number: str):
    compact = re.sub(r"\s+", "", number)
    if not compact:
        return None
    if "," in compact or "." in compact:
        separators = [char for char in compact if char in ",."]
        if len(separators) > 1:
            groups = re.split(r"[,.]", compact)
            if groups[0].isdigit() and all(len(group) == 3 and group.isdigit() for group in groups[1:]):
                compact = "".join(groups)
        if "," in compact or "." in compact:
            sep = "," if "," in compact else "."
            head, tail = compact.rsplit(sep, 1)
            if len(tail) == 3 and head.isdigit():
                compact = head + tail
            else:
                compact = compact.replace(",", ".")
    try:
        return float(compact)
    except ValueError:
        return None


def _monthly_counts(text: str) -> list[float]:
    low = text.lower()
    counts = [
        float(n.replace(",", "."))
        for n in re.findall(
            r"(\d+(?:[.,]\d+)?)\s*(?:в мес|/мес|раз(?:а|ов)? в месяц|"
            r"посещени(?:е|я|й) в месяц|привилеги(?:я|и|й) в месяц|"
            r"проход(?:а|ов)? в месяц|преференци(?:я|и|й) в месяц|"
            r"компенсаци(?:я|и|й)[^.;]{0,35}в месяц|"
            r"поезд(?:ка|ки|ок)[^.;]{0,20}в месяц)", low
        )
    ]
    annual = [count / 12 for count in _annual_counts(text)]
    return counts + annual


def _annual_counts(text: str) -> list[float]:
    low = text.lower()
    return [
        float(n.replace(",", "."))
        for n in re.findall(
            r"(\d+(?:[.,]\d+)?)\s*(?:в год|/год|раз(?:а|ов)? в год|"
            r"посещени(?:е|я|й) в год)", low
        )
    ]


def _lounge_score(text: str):
    counts = _monthly_counts(text)
    if counts:
        return max(counts)
    return None


def _compensation_score(text: str):
    amounts = _rub_amounts(text)
    counts = _monthly_counts(text)
    if not amounts and not counts:
        return None
    # Amount wins first, visit count breaks ties.
    return (max(amounts) if amounts else 0) * 1000 + (max(counts) if counts else 0)


def _insurance_compare_score(text: str):
    low = text.lower()
    amounts = []
    for number, unit in re.findall(r"(\d+(?:[.,]\d+)?)\s*(млн|тыс)?", low):
        try:
            amount = float(number.replace(",", "."))
        except ValueError:
            continue
        if unit == "млн":
            amount *= 1_000_000
        elif unit == "тыс":
            amount *= 1000
        amounts.append(amount)
    days = [
        float(n.replace(",", "."))
        for n in re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:дн|дней|дня)", low)
    ]
    if not amounts and not days:
        return None
    return (max(amounts) if amounts else 0) + (max(days) if days else 0) / 1000


def _is_missing(value: str) -> bool:
    text = (value or "").strip()
    return not text or text == NOT_FOUND or "не найдено" in text.lower()


def _has_benefit(value: str) -> bool:
    text = (value or "").strip()
    if _is_missing(text):
        return False
    low = text.lower()
    if low.startswith(("—", "-")):
        return False
    if low.startswith("нет —") or low.startswith("нет,"):
        return False
    return True


def _format_rub(value) -> str:
    try:
        amount = int(float(value))
    except (TypeError, ValueError):
        return str(value)
    return f"{amount:,}".replace(",", " ")


def _compact_rub(value) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    if amount >= 1_000_000:
        millions = amount / 1_000_000
        if millions.is_integer():
            return f"{int(millions)} млн ₽"
        return f"{millions:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " млн ₽"
    if amount >= 1000 and amount % 1000 == 0:
        return f"{int(amount / 1000)} тыс ₽"
    return f"{_format_rub(amount)} ₽"


def _shorten(value: str, limit: int = 120) -> str:
    return make_complete_summary(value or NOT_FOUND, limit)


def _details(raw: str, summary: str) -> str:
    split = split_summary_and_details(raw, 220)
    details = split["details"]
    if not details:
        return ""
    clean_summary = normalize_source_text(summary)
    return "" if details == clean_summary else details


def _esc(value) -> str:
    return html.escape(_display_text(value))


def _public_text(value) -> str:
    return normalize_source_text(value)


def _display_text(value) -> str:
    text = _public_text(value)
    text = re.sub(r"(\d+)\s+визит\(ов\)/мес", _visit_text, text)
    text = re.sub(r"(\d+)\s+компенсаций/мес суммарно", _compensation_text, text)
    text = re.sub(r"(\d+)\s+опций/подписок упомянуто", _option_text, text)
    replacements = {
        "Excel": "таблица",
        "excel": "таблица",
        "автоматически": "",
        "распознанная метрика": "метрика",
        "распознанный балл": "балл",
        "распознанного": "",
        "распознанной": "",
        "распознано": "выделено",
        "распознан": "выделен",
        "исходные фрагменты": "детали",
        "исходный фрагмент": "детали",
        "безусловное": "",
        "проседает": "ниже",
        "выигрывает": "сильнее",
        "дешевле": "ниже по цене",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def _benefit_display(field: str, raw: str, metric: str) -> str:
    text = _public_text(raw)
    if field == "insurance":
        return _shorten(_insurance_display(text), 230)
    if field in {
        "cashback", "deposits", "taxi", "restaurants",
        "always_included_options", "selectable_options", "selection_rules",
        "auto", "ecosystem", "concierge", "lounge_access",
        "transfers_payments", "cash_withdrawal", "supreme",
    }:
        return _status_prefix(field, text) + _shorten(text, 170)
    return _display_text(metric)


def _benefits_list(raw: str) -> list[dict]:
    if _is_missing(raw):
        return []
    items = []
    for line in str(raw).splitlines():
        line = _public_text(line).strip()
        if not line:
            continue
        if line.lower().startswith("условия выбора:"):
            items.append({
                "title": "Условия выбора",
                "description": line.split(":", 1)[1].strip(),
                "availability": "rule",
            })
            continue
        line = line.lstrip("• ").strip()
        availability = ""
        if "[опция на выбор]" in line.lower():
            availability = "selectable"
            line = re.sub(r"\s*\[опция на выбор\]\s*", "", line,
                          flags=re.IGNORECASE)
        elif "[включено постоянно]" in line.lower():
            availability = "always_included"
            line = re.sub(r"\s*\[включено постоянно\]\s*", "", line,
                          flags=re.IGNORECASE)
        if " — " in line:
            title, description = line.split(" — ", 1)
        else:
            title, description = line, ""
        if title:
            items.append({
                "title": normalize_source_text(title.strip()),
                "description": normalize_source_text(description.strip()),
                "availability": availability,
            })
    return items


def _validate_attr(attr: dict, context: str):
    values = []
    if isinstance(attr.get("value"), list):
        for idx, item in enumerate(attr["value"]):
            values.append((f"{context} / benefit {idx} title", item.get("title", "")))
            values.append((f"{context} / benefit {idx} description", item.get("description", "")))
    else:
        values.append((f"{context} / value", attr.get("value", "")))
    values.append((f"{context} / note", attr.get("note", "")))
    values.append((f"{context} / details", attr.get("details", "")))
    for item_context, text in values:
        if text:
            assert_user_visible_text(str(text), item_context)


def _status_prefix(field: str, text: str) -> str:
    low = text.lower()
    if low.startswith(("опция на выбор:", "включено постоянно:", "общий лимит:")):
        return ""
    if field == "always_included_options":
        return "Включено постоянно: "
    if field == "selectable_options":
        return "Опция на выбор: "
    badges = []
    if "всегда включ" in low:
        badges.append("Включено постоянно")
    if "опция" in low and "всегда включ" not in low:
        badges.append("Опция на выбор")
    if "общий лимит" in low:
        badges.append("Общий лимит")
    return (" · ".join(badges) + ": ") if badges else ""


def _visit_text(match) -> str:
    count = int(match.group(1))
    noun = _ru_plural(count, "визит", "визита", "визитов")
    return f"{count} {noun} в месяц"


def _compensation_text(match) -> str:
    count = int(match.group(1))
    noun = _ru_plural(count, "компенсация", "компенсации", "компенсаций")
    return f"{count} {noun} в месяц"


def _option_text(match) -> str:
    count = int(match.group(1))
    option = _ru_plural(count, "опция", "опции", "опций")
    subscription = _ru_plural(count, "подписка", "подписки", "подписок")
    return f"{count} {option} или {subscription}"


def _ru_plural(count: int, one: str, few: str, many: str) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return one
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return few
    return many


# Токен-сет единый с лендингом отзывов (landing/premium_reviews.py):
# белый фон, зелёный акцент, терракот — только для негативного сигнала
# (здесь — меньший итоговый балл в шапке сравнения).
_CSS = """
:root {
  --bg: #F2F5F1;
  --surface: #FFFFFF;
  --card: #FFFFFF;
  --ink: #1A1D1B;
  --muted: #64746b;
  --line: #DDE2DA;
  --line-strong: #C9D0C6;
  --green: #188f4f;
  --green-soft: #188f4f1a;
  --neg: #B3492F;
  --shadow: 0 6px 20px rgba(29, 43, 34, 0.07);
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  -webkit-tap-highlight-color: rgba(24, 143, 79, 0.18);
}
button, summary { touch-action: manipulation; }
button { -webkit-appearance: none; appearance: none; }
.page { max-width: 1160px; margin: 0 auto; padding: 36px 18px 56px; }
.hero { padding: 18px 0 24px; border-bottom: 1px solid var(--line); }
.eyebrow { margin: 0 0 8px; color: var(--green); font-size: 13px;
  font-weight: 700; text-transform: uppercase; }
h1 { margin: 0; font-size: 42px; line-height: 1.08; }
.lead { max-width: 780px; margin: 14px 0 0; color: var(--muted); font-size: 17px; }
.stats { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
.stats div { min-width: 150px; background: var(--surface);
  border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px;
  box-shadow: var(--shadow); }
.stats b { display: block; font-size: 24px; color: var(--green);
  font-family: ui-monospace, "SF Mono", Menlo, monospace; }
.stats span { color: var(--muted); font-size: 13px; }
.pickers { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px;
  margin-top: 22px; }
.picker { background: var(--surface); border: 1px solid var(--line);
  border-radius: 8px; min-width: 0; padding: 14px 16px;
  box-shadow: var(--shadow); }
.picker h2 { margin: 0 0 10px; font-size: 16px; }
.picker h3 { margin: 12px 0 8px; font-size: 12px; color: var(--muted);
  text-transform: uppercase; }
.chip-row { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { border: 1px solid var(--line); background: var(--surface); color: var(--ink);
  border-radius: 999px; min-height: 44px; padding: 10px 14px; font-size: 14px;
  line-height: 1.2; cursor: pointer; font-family: inherit; }
.level-chip { display: inline-flex; flex-direction: column; align-items: flex-start;
  gap: 2px; text-align: left; border-radius: 12px; }
.chip-main { font-weight: 700; }
.chip-meta { color: var(--muted); font-size: 12px; }
.chip:hover { border-color: var(--green); color: var(--green); }
.chip.active { background: var(--green); border-color: var(--green); color: #fff; }
.chip.active .chip-meta { color: rgba(255, 255, 255, 0.84); }
.chip:disabled { cursor: not-allowed; opacity: .38; }
.recommendations { margin-top: 16px; padding: 16px; border: 1px solid var(--line);
  border-radius: 8px; background: var(--surface); box-shadow: var(--shadow); }
.recommendations-head { display: flex; align-items: end; justify-content: space-between;
  gap: 16px; margin-bottom: 12px; }
.recommendations-kicker { margin: 0 0 2px; color: var(--green); font-size: 11px;
  font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
.recommendations h2 { margin: 0; font-size: 20px; }
.recommendations-summary { max-width: 620px; margin: 0; color: var(--muted);
  font-size: 13px; text-align: right; }
.recommendation-grid { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 8px; }
.recommendation-card { display: flex; min-width: 0; min-height: 116px;
  flex-direction: column; align-items: flex-start; gap: 5px; padding: 12px;
  border: 1px solid var(--line); border-radius: 8px; background: #fff;
  color: var(--ink); cursor: pointer; text-align: left; font: inherit; }
.recommendation-card:hover:not(:disabled),
.recommendation-card:focus-visible:not(:disabled) { border-color: var(--green);
  box-shadow: 0 0 0 2px rgba(24, 143, 79, 0.12); outline: 0; }
.recommendation-card:disabled { cursor: default; opacity: .55; }
.recommendation-bank { color: var(--green); font-size: 12px; font-weight: 800; }
.recommendation-tier { font-size: 14px; font-weight: 750; line-height: 1.3; }
.recommendation-threshold { color: var(--muted); font-size: 12px; }
.recommendation-match { margin-top: auto; padding: 3px 7px; border-radius: 999px;
  background: var(--green-soft); color: var(--green); font-size: 11px;
  font-weight: 750; }
.recommendation-card.nearest .recommendation-match { background: #fff8e8;
  color: #795f1e; }
.recommendation-empty { grid-column: 1 / -1; margin: 0; padding: 12px;
  border-radius: 8px; background: #f7f9f5; color: var(--muted); font-size: 13px; }
.hint { margin: 18px 0 0; color: var(--muted); }
.js-warning { margin: 14px 0 0; padding: 12px 14px; border: 1px solid var(--line);
  border-radius: 8px; background: #fff8e8; color: #6f5a25; font-size: 14px; }
.js-ready .js-warning { display: none; }
.compare-actions { display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 12px; }
.compare-buttons { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.print-title, .print-date { display: none; }
.pdf-button, .secondary-button { min-height: 44px; border: 1px solid var(--green);
  border-radius: 8px; cursor: pointer; padding: 10px 14px; font: inherit;
  font-weight: 700; }
.pdf-button { background: var(--green); color: #fff; }
.secondary-button { background: var(--surface); color: var(--green); }
.pdf-button:hover, .pdf-button:focus-visible { background: #0f7a41;
  border-color: #0f7a41; outline: 2px solid rgba(24, 143, 79, 0.24);
  outline-offset: 2px; }
.secondary-button:hover, .secondary-button:focus-visible {
  background: var(--green-soft); outline: 2px solid rgba(24, 143, 79, 0.18);
  outline-offset: 2px; }
.pdf-button:disabled { cursor: wait; opacity: 0.72; }
#compare {
  --compare-level-count: 2;
  --compare-attr-column: minmax(8.5rem, 0.38fr);
  --compare-level-column: minmax(0, 1fr);
  --compare-grid-template:
    var(--compare-attr-column)
    repeat(var(--compare-level-count), var(--compare-level-column));
  --compare-cell-padding: 10px 12px;
  margin-top: 22px;
}
.map-heading { display: flex; align-items: end; justify-content: space-between;
  gap: 18px; padding: 18px 0 10px; border-bottom: 1px solid var(--line); }
.map-heading h2 { margin: 0; font-size: 26px; line-height: 1.2; }
.map-summary { max-width: 520px; margin: 0; color: var(--muted); font-size: 13px;
  text-align: right; }
.map-method { margin: 10px 0 16px; color: var(--muted); font-size: 13px; }
.pair-list { display: grid; gap: 12px; counter-reset: pair; }
.level-pair { border: 1px solid var(--line-strong); border-radius: 10px;
  background: var(--surface); box-shadow: var(--shadow); overflow: hidden; }
.level-pair > summary { display: block; padding: 0; cursor: pointer; list-style: none; }
.level-pair > summary::-webkit-details-marker { display: none; }
.level-pair > summary:focus-visible { outline: 3px solid rgba(24, 143, 79, .22);
  outline-offset: -3px; }
.pair-grid { display: grid; grid-template-columns: minmax(0, 1fr) 170px minmax(0, 1fr);
  align-items: stretch; min-width: 0; }
.pair-level { min-width: 0; padding: 16px 18px; }
.pair-level:first-child { border-left: 4px solid var(--green); }
.pair-level:last-child { border-right: 4px solid var(--green); }
.pair-bank { margin: 0 0 3px; color: var(--green); font-size: 12px;
  font-weight: 800; text-transform: uppercase; }
.pair-level h3 { margin: 0; font-size: 17px; line-height: 1.3; overflow-wrap: anywhere; }
.pair-entry { margin: 7px 0 0; color: var(--muted); font-size: 13px; }
.pair-level.empty { display: flex; align-items: center; justify-content: center;
  background: #f7f9f5; color: var(--muted); text-align: center; }
.pair-match { display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 5px; padding: 12px; border-right: 1px solid var(--line);
  border-left: 1px solid var(--line); background: #f7f9f5; text-align: center; }
.match-badge { display: inline-block; border-radius: 999px; padding: 4px 9px;
  background: var(--green-soft); color: var(--green); font-size: 11px;
  font-weight: 800; line-height: 1.3; }
.match-badge.nearest { background: #fff8e8; color: #795f1e; }
.match-badge.unmatched { background: #f0f2ef; color: #667069; }
.pair-toggle { color: var(--muted); font-size: 11px; font-weight: 700; }
.level-pair[open] .pair-toggle::before { content: "Свернуть"; }
.level-pair:not([open]) .pair-toggle::before { content: "Сравнить подробно"; }
.pair-detail { padding: 0 14px 14px; border-top: 1px solid var(--line); }
.pair-detail .cmp-scroll { max-height: none; margin-top: 14px; box-shadow: none; }
.pair-detail-note { margin: 12px 2px 0; color: var(--muted); font-size: 12px; }
.level-pdf-actions { display: flex; justify-content: flex-end; margin-top: 12px; }
.level-pdf-button { min-height: 40px; }
.no-analog { background: #f7f9f5; color: var(--muted); font-style: italic; }
.cmp-head {
  display: grid;
  grid-template-columns: var(--compare-grid-template);
  gap: 0;
}
.cmp-attr-spacer { min-width: 0; }
.cmp-col { background: var(--surface); border: 1px solid var(--line-strong);
  border-top: 3px solid var(--green); border-radius: 8px; min-width: 0;
  padding: 14px 16px; box-shadow: var(--shadow); }
.cmp-col h2 { margin: 2px 0 6px; font-size: 20px; }
.cmp-entry-hint { margin: -2px 0 0; color: var(--muted); font-size: 13px; }
.cmp-col .sc { font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 26px; color: var(--green); font-weight: 700; }
.cmp-col .sc.lower { color: var(--neg); }
.cmp-col .sc small { font-size: 12px; color: var(--muted); font-weight: 400; }
.method { margin: 12px 0 0; color: var(--muted); font-size: 13px; }
.method summary { cursor: pointer; font-weight: 700; color: var(--ink); }
.method p { margin: 6px 0 0; max-width: 900px; }
.cmp-scroll { margin-top: 12px; max-height: 62vh; overflow: auto;
  border: 1px solid var(--line-strong); border-radius: 8px;
  background: var(--surface); box-shadow: var(--shadow); }
.cmp-table { display: block; width: 100%; border-collapse: separate; border-spacing: 0; }
.cmp-table thead,
.cmp-table tbody { display: block; }
.cmp-table tr {
  display: grid;
  grid-template-columns: var(--compare-grid-template);
}
.cmp-table th, .cmp-table td { text-align: left; padding: 10px 12px;
  border-bottom: 1px solid var(--line); vertical-align: top; font-size: 14px;
  min-width: 0; overflow-wrap: anywhere; }
.cmp-table td:not(:first-child) { white-space: pre-line; }
.cmp-table thead th { background: #F7F9F5;
  color: var(--muted); font-size: 12px; text-transform: uppercase; z-index: 1;
  box-shadow: 0 1px 0 var(--line); }
.cmp-table td:first-child { color: var(--muted); font-size: 13px;
  white-space: normal; }
.cmp-table td.rank-best, .cmp-table td.win { box-shadow: inset 3px 0 0 #2e9b62;
  background: #f0faf4; }
.cmp-table td.rank-mid { box-shadow: inset 3px 0 0 #d7a51d;
  background: #fff9e8; }
.cmp-table td.rank-low { box-shadow: inset 3px 0 0 #d16d5d;
  background: #fff3f1; }
.cmp-table td .tag { display: inline-block; margin-left: 6px;
  background: var(--green-soft); color: var(--green); border-radius: 999px;
  padding: 1px 8px; font-size: 11px; font-weight: 700; }
.cmp-table td.rank-best .tag, .cmp-table td.win .tag {
  background: #e3f4ea; color: #187347; }
.cmp-table td.rank-mid .tag { background: #fff0bf; color: #806010; }
.cmp-table td.rank-low .tag { background: #ffe2de; color: #9b3d31; }
.cmp-table td .rank-reason { display: block; margin-top: 5px; color: var(--muted);
  font-size: 11px; line-height: 1.35; white-space: normal; }
.benefits-list { list-style: none; margin: 0; padding: 0; display: grid;
  gap: 7px; }
.benefits-list li { position: relative; padding-left: 0; }
.benefit-title { font-weight: 700; }
.benefit-description { color: var(--ink); }
.tag.selectable { background: #fff4df; color: #8a5a00; }
.tag.always { background: var(--green-soft); color: var(--green); }
.benefit-rule { margin-top: 8px; color: var(--muted); font-size: 13px; }
.attr-details { margin-top: 8px; color: var(--muted); font-size: 13px; }
.attr-details summary { cursor: pointer; color: var(--green); font-weight: 700; }
.attr-details p { margin: 6px 0 0; color: var(--ink); white-space: normal; }
.pdf-exporting #compare { width: 1120px; margin: 0; background: #fff; color: #111; }
.pdf-exporting .compare-actions { display: block; margin: 0 0 10px; }
.pdf-exporting .compare-actions .pdf-button,
.pdf-exporting .compare-actions .secondary-button { display: none; }
.pdf-exporting .level-pdf-actions { display: none; }
.pdf-exporting .print-title { display: block; margin: 0; font-size: 24px;
  line-height: 1.2; font-weight: 800; color: #111; }
.pdf-exporting .print-date { display: block; margin: 4px 0 0; color: #4f5c55; }
.pdf-exporting .cmp-scroll { max-height: none; overflow: visible; box-shadow: none; }
.pdf-exporting .cmp-col { box-shadow: none; }
.pdf-exporting .attr-details summary { display: none; }
.footer { margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line);
  color: var(--muted); font-size: 13px; }
@media (max-width: 820px) {
  .page { padding: 24px 14px 42px; }
  h1 { font-size: 32px; }
  .stats div { flex: 1 1 138px; min-width: 0; }
  .pickers, .cmp-head { grid-template-columns: 1fr; }
  .cmp-attr-spacer { display: none; }
  .picker, .recommendations { padding: 14px; }
  .recommendations-head { display: block; }
  .recommendations-summary { margin-top: 6px; text-align: left; }
  .compare-actions, .map-heading { display: block; }
  .compare-buttons { justify-content: stretch; margin-top: 10px; }
  .compare-buttons button { flex: 1 1 140px; }
  .map-summary { margin-top: 6px; text-align: left; }
  .pair-grid { grid-template-columns: 1fr; }
  .pair-level:first-child { border-left: 4px solid var(--green);
    border-bottom: 1px solid var(--line); }
  .pair-level:last-child { border-right: 0; border-left: 4px solid var(--green);
    border-top: 1px solid var(--line); }
  .pair-match { border: 0; padding: 9px 12px; }
  .pair-detail { padding: 0 0 2px; border-top: 1px solid var(--line); }
  .pair-detail .cmp-scroll { margin-top: 0; }
  .pair-detail-note { padding: 0 12px; }
  .level-pdf-actions { padding: 0 12px 10px; }
  .recommendation-grid { grid-template-columns: 1fr; }
  .recommendation-card { min-height: 0; }
  .chip-row { gap: 8px; }
  .chip { flex: 1 1 auto; justify-content: center; min-width: min(46%, 220px); }
  .level-chip { align-items: center; min-width: min(100%, 220px); text-align: center; }
  .cmp-scroll { max-height: none; overflow: visible; border: 0; border-radius: 0; }
  .cmp-table, .cmp-table colgroup, .cmp-table tbody, .cmp-table tr,
  .cmp-table td { display: block; width: 100%; }
  .cmp-table thead { display: none; }
  .cmp-table tr { margin-bottom: 14px; border: 1px solid var(--line-strong);
    border-radius: 8px; background: var(--surface); overflow: hidden;
    box-shadow: var(--shadow); }
  .cmp-table td { border-bottom: 1px solid var(--line); padding: 11px 12px;
    white-space: normal; }
  .cmp-table td:first-child { background: #F7F9F5; font-weight: 700;
    color: var(--ink); font-size: 14px; }
  .cmp-table td:last-child { border-bottom: 0; }
  .cmp-table td[data-label]::before { content: attr(data-label); display: block;
    margin-bottom: 4px; color: var(--muted); font-size: 12px; font-weight: 700; }
  .cmp-table td.rank-best, .cmp-table td.win { box-shadow: inset 3px 0 0 #2e9b62; }
  .cmp-table td.rank-mid { box-shadow: inset 3px 0 0 #d7a51d; }
  .cmp-table td.rank-low { box-shadow: inset 3px 0 0 #d16d5d; }
}
@media print {
  @page { size: A4 landscape; margin: 10mm; }
  :root {
    --bg: #fff;
    --surface: #fff;
    --line: #d4d8d2;
    --line-strong: #b8c0b5;
    --green-soft: #eef7f2;
  }
  body { background: #fff; color: #111; font-size: 10px; line-height: 1.35; }
  .page { max-width: none; margin: 0; padding: 0; }
  .hero, .pickers, .recommendations, #hint,
  #js-warning, .footer,
  .compare-actions .pdf-button, .compare-actions .secondary-button,
  .level-pdf-actions {
    display: none !important;
  }
  #compare { display: block !important; margin: 0; }
  .compare-actions { display: block; margin: 0 0 8px; }
  .print-title { display: block; margin: 0; font-size: 18px; line-height: 1.2;
    font-weight: 800; color: #111; }
  .print-date { display: block; margin: 3px 0 0; color: #4f5c55; font-size: 10px; }
  .cmp-scroll { max-height: none; overflow: visible; margin-top: 8px;
    border: 1px solid var(--line-strong); border-radius: 0; box-shadow: none; }
  .cmp-head { break-inside: avoid; page-break-inside: avoid; }
  .cmp-col { border-radius: 0; box-shadow: none; padding: 7px 8px;
    border-top-width: 2px; }
  .cmp-col h2 { margin: 0; font-size: 12px; line-height: 1.25; }
  .cmp-entry-hint { margin: 2px 0 0; font-size: 8px; color: #4f5c55; }
  .cmp-table, .cmp-table thead, .cmp-table tbody { display: block !important; }
  .cmp-table tr { display: grid !important; grid-template-columns: var(--compare-grid-template); }
  .cmp-table thead { display: block !important; }
  .cmp-table th, .cmp-table td { padding: 5px 6px; font-size: 9px;
    line-height: 1.28; color: #111; overflow-wrap: anywhere; word-break: normal; }
  .cmp-table thead th { color: #4f5c55; font-size: 8px; box-shadow: none; }
  .cmp-table td:first-child { color: #4f5c55; font-size: 8px; font-weight: 700; }
  .cmp-table tr { break-inside: avoid; page-break-inside: avoid; }
  .level-pair { break-inside: avoid; page-break-inside: avoid; box-shadow: none; }
  .cmp-table td.rank-best, .cmp-table td.win {
    background: #f0faf4; box-shadow: inset 2px 0 0 #2e9b62; }
  .cmp-table td.rank-mid {
    background: #fff9e8; box-shadow: inset 2px 0 0 #d7a51d; }
  .cmp-table td.rank-low {
    background: #fff3f1; box-shadow: inset 2px 0 0 #d16d5d; }
  .cmp-table td .tag { border: 1px solid #cfe1d6; padding: 0 4px; font-size: 7px;
    background: #f5faf7; color: #146c40; }
  .benefits-list { gap: 3px; }
  .benefit-rule, .attr-details, .attr-details p, .cmp-table td .rank-reason {
    font-size: 8px; color: #4f5c55; }
  .attr-details summary { display: none; }
  .attr-details p { margin: 3px 0 0; color: #111; }
}
"""

_JS = """
const DATA = JSON.parse(document.getElementById('data').textContent);
const SIDES = ['a', 'b'];
const ALWAYS_SHOW_FIELDS = new Set([
  'transfers_summary', 'cash_withdrawal_summary',
  'supreme', 'metal_card', 'auto', 'personal_banking_support'
]);
const HTML2CANVAS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
const JSPDF_URL = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
let pdfLibraryPromise = null;
const state = Object.fromEntries(SIDES.map((side) => [side, { bank: null }]));
document.documentElement.classList.add('js-ready');

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderBanks(side) {
  const picker = document.querySelector(`.picker[data-side="${side}"]`);
  const row = picker.querySelector('.banks');
  const otherSide = side === 'a' ? 'b' : 'a';
  row.querySelectorAll('.chip').forEach((chip) => {
    const i = Number(chip.dataset.bankIndex);
    if (state[side].bank === i) chip.classList.add('active');
    else chip.classList.remove('active');
    chip.disabled = state[otherSide].bank === i;
    chip.onclick = () => {
      state[side].bank = i;
      renderBanks(side);
      renderBanks(otherSide);
      renderMap();
    };
  });
}

function selectedBank(side) {
  const index = state[side].bank;
  return index === null ? null : DATA[index];
}

function validEntryMatch(level) {
  const match = level && level.entry_match;
  return Boolean(match && match.eligible
    && Number.isFinite(Number(match.min_amount))
    && Number.isFinite(Number(match.max_amount)));
}

function intervalDistance(left, right) {
  const leftMin = Number(left.min_amount);
  const leftMax = Number(left.max_amount);
  const rightMin = Number(right.min_amount);
  const rightMax = Number(right.max_amount);
  if (leftMax < rightMin) return rightMin - leftMax;
  if (rightMax < leftMin) return leftMin - rightMax;
  return 0;
}

function recommendationKind(reference, candidate) {
  const sameScalar = Number(reference.min_amount) === Number(reference.max_amount)
    && Number(candidate.min_amount) === Number(candidate.max_amount)
    && Number(reference.min_amount) === Number(candidate.min_amount);
  if (sameScalar) return { id: 'exact', rank: 0, label: 'Точное совпадение' };
  const distance = intervalDistance(reference, candidate);
  if (distance === 0) {
    return { id: 'overlap', rank: 1, label: 'Подходит по диапазону' };
  }
  const direction = Number(candidate.max_amount) < Number(reference.min_amount)
    ? 'ниже' : 'выше';
  return {
    id: 'nearest', rank: 2,
    label: `На ${formatRub(distance)} ${direction}`
  };
}

function formatRub(amount) {
  const value = Number(amount);
  if (!Number.isFinite(value)) return '';
  if (value >= 1000000) {
    const millions = value / 1000000;
    return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 })
      .format(millions)} млн ₽`;
  }
  if (value >= 1000 && value % 1000 === 0) {
    return `${new Intl.NumberFormat('ru-RU').format(value / 1000)} тыс ₽`;
  }
  return `${new Intl.NumberFormat('ru-RU').format(value)} ₽`;
}

function levelCompatibility(left, right) {
  if (!validEntryMatch(left) || !validEntryMatch(right)) return null;
  const leftMatch = left.entry_match;
  const rightMatch = right.entry_match;
  const distance = intervalDistance(leftMatch, rightMatch);
  const sameScalar = Number(leftMatch.min_amount) === Number(leftMatch.max_amount)
    && Number(rightMatch.min_amount) === Number(rightMatch.max_amount)
    && Number(leftMatch.min_amount) === Number(rightMatch.min_amount);
  if (sameScalar) {
    return {
      id: 'exact', label: 'Точное совпадение порога', cost: 0,
      reason: `Подтверждённый порог входа совпадает: ${leftMatch.label}.`
    };
  }
  if (distance === 0) {
    return {
      id: 'overlap', label: 'Диапазоны входа пересекаются', cost: 0.05,
      reason: `Подтверждённые диапазоны пересекаются: `
        + `${leftMatch.label} и ${rightMatch.label}.`
    };
  }
  const leftMiddle = (Number(leftMatch.min_amount) + Number(leftMatch.max_amount)) / 2;
  const rightMiddle = (Number(rightMatch.min_amount) + Number(rightMatch.max_amount)) / 2;
  const relativeDistance = distance / Math.max(1, Math.min(leftMiddle, rightMiddle));
  if (relativeDistance > 0.5) return null;
  return {
    id: 'nearest', label: `Ближайшие уровни · разница ${formatRub(distance)}`,
    cost: 0.25 + relativeDistance,
    reason: `Прямого пересечения нет. Разница между ближайшими границами `
      + `${formatRub(distance)}; порядок продуктовых линеек сохранён.`
  };
}

function alignLevels(leftLevels, rightLevels) {
  const gapCost = 0.7;
  const rows = leftLevels.length + 1;
  const cols = rightLevels.length + 1;
  const dp = Array.from({ length: rows }, () => Array(cols).fill(Infinity));
  const previous = Array.from({ length: rows }, () => Array(cols).fill(null));
  dp[0][0] = 0;
  for (let i = 1; i < rows; i += 1) {
    dp[i][0] = dp[i - 1][0] + gapCost;
    previous[i][0] = { action: 'left', i: i - 1, j: 0 };
  }
  for (let j = 1; j < cols; j += 1) {
    dp[0][j] = dp[0][j - 1] + gapCost;
    previous[0][j] = { action: 'right', i: 0, j: j - 1 };
  }
  for (let i = 1; i < rows; i += 1) {
    for (let j = 1; j < cols; j += 1) {
      const compatibility = levelCompatibility(leftLevels[i - 1], rightLevels[j - 1]);
      const candidates = [
        {
          cost: dp[i - 1][j] + gapCost, priority: 1,
          step: { action: 'left', i: i - 1, j }
        },
        {
          cost: dp[i][j - 1] + gapCost, priority: 2,
          step: { action: 'right', i, j: j - 1 }
        }
      ];
      if (compatibility) {
        candidates.push({
          cost: dp[i - 1][j - 1] + compatibility.cost, priority: 0,
          step: { action: 'pair', i: i - 1, j: j - 1, compatibility }
        });
      }
      candidates.sort((left, right) => left.cost - right.cost
        || left.priority - right.priority);
      dp[i][j] = candidates[0].cost;
      previous[i][j] = candidates[0].step;
    }
  }

  const pairs = [];
  let i = leftLevels.length;
  let j = rightLevels.length;
  while (i > 0 || j > 0) {
    const step = previous[i][j];
    if (step.action === 'pair') {
      pairs.push({
        left: leftLevels[i - 1], right: rightLevels[j - 1],
        match: step.compatibility
      });
    } else if (step.action === 'left') {
      pairs.push({ left: leftLevels[i - 1], right: null, match: null });
    } else {
      pairs.push({ left: null, right: rightLevels[j - 1], match: null });
    }
    i = step.i;
    j = step.j;
  }
  return pairs.reverse();
}

function renderLevelCard(bankName, level, emptyText) {
  if (!level) {
    const empty = el('div', 'pair-level empty');
    empty.appendChild(el('span', '', emptyText));
    return empty;
  }
  const card = el('article', 'pair-level');
  card.dataset.tierId = level.tier_id || '';
  card.appendChild(el('p', 'pair-bank', bankName));
  card.appendChild(el('h3', '', level.tier));
  const entry = level.entry_match && level.entry_match.label
    ? level.entry_match.label
    : 'нет подтверждённого числового порога';
  card.appendChild(el('p', 'pair-entry', `Вход: ${entry}`));
  return card;
}

function renderPairDetail(container, pair, leftBank, rightBank) {
  const detail = el('div', 'pair-detail');
  const note = pair.match
    ? pair.match.reason
    : 'Прямой аналог не показан: сопоставление по подтверждённым условиям '
      + 'входа невозможно или разница порогов слишком велика.';
  detail.appendChild(el('p', 'pair-detail-note', note));
  const scroll = el('div', 'cmp-scroll');
  const table = el('table', 'cmp-table');
  const thead = el('thead');
  const headRow = el('tr');
  headRow.appendChild(el('th', '', 'Атрибут'));
  headRow.appendChild(el('th', '',
    pair.left ? `${leftBank.bank} — ${pair.left.tier}` : leftBank.bank));
  headRow.appendChild(el('th', '',
    pair.right ? `${rightBank.bank} — ${pair.right.tier}` : rightBank.bank));
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = el('tbody');
  const template = pair.left || pair.right;
  template.attrs.forEach((baseAttr, index) => {
    const leftAttr = pair.left ? pair.left.attrs[index] : null;
    const rightAttr = pair.right ? pair.right.attrs[index] : null;
    const presentAttrs = [leftAttr, rightAttr].filter(Boolean);
    if (!ALWAYS_SHOW_FIELDS.has(baseAttr.id)
        && presentAttrs.every((attr) => isEmptyDisplay(attr.value))) return;
    const tr = el('tr');
    tr.appendChild(el('td', '', baseAttr.label));
    const cellsBySide = {};
    const attrsBySide = {};
    [
      ['a', pair.left, leftAttr, leftBank],
      ['b', pair.right, rightAttr, rightBank]
    ].forEach(([side, level, attr, bank]) => {
      const td = el('td');
      if (level && attr) {
        renderAttrValue(td, attr);
        td.dataset.label = `${bank.bank} — ${level.tier}`;
        if (attr.note) td.title = attr.note;
        cellsBySide[side] = td;
        attrsBySide[side] = attr;
      } else {
        td.className = 'no-analog';
        td.dataset.label = bank.bank;
        td.textContent = 'Нет прямого аналога для сравнения';
      }
      tr.appendChild(td);
    });
    if (pair.left && pair.right) {
      highlightWinners([
        { side: 'a', item: { bank: leftBank.bank, ...pair.left } },
        { side: 'b', item: { bank: rightBank.bank, ...pair.right } }
      ], attrsBySide, cellsBySide);
    }
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  scroll.appendChild(table);
  detail.appendChild(scroll);
  const actions = el('div', 'level-pdf-actions');
  const pdfButton = el('button', 'pdf-button level-pdf-button', 'Выгрузить PDF этого уровня');
  pdfButton.type = 'button';
  pdfButton.addEventListener('click', () => exportLevelPdf(container, pdfButton));
  actions.appendChild(pdfButton);
  detail.appendChild(actions);
  container.appendChild(detail);
}

function renderPair(pair, leftBank, rightBank) {
  const details = el('details', 'level-pair');
  details.dataset.leftTier = pair.left ? pair.left.tier : '';
  details.dataset.rightTier = pair.right ? pair.right.tier : '';
  const summary = el('summary');
  const grid = el('div', 'pair-grid');
  grid.appendChild(renderLevelCard(
    leftBank.bank, pair.left, `Нет прямого аналога в ${leftBank.bank}`
  ));
  const match = el('div', 'pair-match');
  const matchInfo = pair.match || {
    id: 'unmatched', label: 'Нет прямого аналога'
  };
  match.appendChild(el('span', `match-badge ${matchInfo.id}`, matchInfo.label));
  match.appendChild(el('span', 'pair-toggle'));
  grid.appendChild(match);
  grid.appendChild(renderLevelCard(
    rightBank.bank, pair.right, `Нет прямого аналога в ${rightBank.bank}`
  ));
  summary.appendChild(grid);
  details.appendChild(summary);
  renderPairDetail(details, pair, leftBank, rightBank);
  return details;
}

function renderMap() {
  const cmp = document.getElementById('compare');
  const hint = document.getElementById('hint');
  const leftBank = selectedBank('a');
  const rightBank = selectedBank('b');
  if (!leftBank || !rightBank) {
    cmp.hidden = true;
    hint.hidden = false;
    return;
  }
  const wasHidden = cmp.hidden;
  cmp.hidden = false;
  hint.hidden = true;
  document.getElementById('map-title').textContent =
    `${leftBank.bank} против ${rightBank.bank}`;
  const pairs = alignLevels(leftBank.levels, rightBank.levels);
  const matched = pairs.filter((pair) => pair.left && pair.right).length;
  const unmatched = pairs.length - matched;
  document.getElementById('map-summary').textContent =
    `${leftBank.levels.length + rightBank.levels.length} уровней · `
    + `${matched} сопоставленных пар · ${unmatched} без прямого аналога`;
  const list = document.getElementById('pair-list');
  list.innerHTML = '';
  pairs.forEach((pair) => list.appendChild(renderPair(pair, leftBank, rightBank)));
  if (wasHidden) {
    cmp.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function loadPdfScript(url, ready) {
  if (ready()) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = url;
    script.async = true;
    script.onload = () => ready()
      ? resolve()
      : reject(new Error(`PDF dependency did not initialize: ${url}`));
    script.onerror = () => reject(new Error(`PDF dependency failed to load: ${url}`));
    document.head.appendChild(script);
  });
}

function loadPdfLibrary() {
  if (window.html2canvas && window.jspdf && window.jspdf.jsPDF) {
    return Promise.resolve({ html2canvas: window.html2canvas, jsPDF: window.jspdf.jsPDF });
  }
  if (pdfLibraryPromise) return pdfLibraryPromise;
  pdfLibraryPromise = Promise.all([
    loadPdfScript(HTML2CANVAS_URL, () => Boolean(window.html2canvas)),
    loadPdfScript(JSPDF_URL, () => Boolean(window.jspdf && window.jspdf.jsPDF))
  ]).then(() => ({ html2canvas: window.html2canvas, jsPDF: window.jspdf.jsPDF }));
  return pdfLibraryPromise;
}

function comparePdfFileName() {
  const parts = SIDES
    .map((side) => selectedBank(side))
    .filter(Boolean)
    .map((item) => item.bank);
  const name = 'premium-comparison-' + parts.join('-vs-');
  return name
    .toLowerCase()
    .replace(/[^a-zа-яё0-9]+/gi, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120) + '.pdf';
}

function pdfCaptureSizeForElement(element) {
  const rect = element.getBoundingClientRect();
  const widthPx = Math.ceil(Math.max(element.scrollWidth, element.offsetWidth, rect.width));
  const heightPx = Math.ceil(Math.max(element.scrollHeight, element.offsetHeight, rect.height));
  const maxCanvasSide = 16000;
  return {
    widthPx,
    heightPx,
    scale: Math.min(2, maxCanvasSide / widthPx, maxCanvasSide / heightPx)
  };
}

async function exportComparePdf() {
  const cmp = document.getElementById('compare');
  if (!cmp || cmp.hidden) return;
  const button = document.getElementById('pdf-button');
  const originalText = button.textContent;
  const openedDetails = [];
  cmp.querySelectorAll('details').forEach((details) => {
    if (!details.open) {
      details.open = true;
      openedDetails.push(details);
    }
  });
  const restore = () => {
    openedDetails.forEach((details) => { details.open = false; });
    document.body.classList.remove('pdf-exporting');
    button.disabled = false;
    button.textContent = originalText;
  };
  button.disabled = true;
  button.textContent = 'Готовлю PDF...';
  document.body.classList.add('pdf-exporting');
  try {
    const { html2canvas, jsPDF } = await loadPdfLibrary();
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(
      () => requestAnimationFrame(resolve)
    ));
    const marginMm = 8;
    const captureSize = pdfCaptureSizeForElement(cmp);
    const canvas = await html2canvas(cmp, {
      scale: captureSize.scale,
      useCORS: true,
      backgroundColor: '#ffffff',
      width: captureSize.widthPx,
      height: captureSize.heightPx,
      windowWidth: Math.max(document.documentElement.clientWidth, captureSize.widthPx)
    });
    const pdf = new jsPDF({
      unit: 'mm',
      format: 'a3',
      orientation: 'landscape',
      compress: true
    });
    const sheetWidth = pdf.internal.pageSize.getWidth();
    const sheetHeight = pdf.internal.pageSize.getHeight();
    const availableWidth = sheetWidth - marginMm * 2;
    const availableHeight = sheetHeight - marginMm * 2;
    const fit = Math.min(
      availableWidth / canvas.width,
      availableHeight / canvas.height
    );
    const imageWidth = canvas.width * fit;
    const imageHeight = canvas.height * fit;
    const imageX = (sheetWidth - imageWidth) / 2;
    const imageY = marginMm;
    pdf.addImage(
      canvas.toDataURL('image/jpeg', 0.98),
      'JPEG', imageX, imageY, imageWidth, imageHeight, undefined, 'FAST'
    );
    pdf.save(comparePdfFileName());
  } catch (error) {
    console.error('PDF export failed', error);
    const detail = error && error.message ? `\n${error.message}` : '';
    window.alert(`Не удалось подготовить PDF. Повторите выгрузку.${detail}`);
  } finally {
    restore();
  }
}

function levelPdfFileName(pairElement) {
  const tiers = [pairElement.dataset.leftTier, pairElement.dataset.rightTier]
    .filter(Boolean);
  const name = 'premium-level-comparison-' + tiers.join('-vs-');
  return name
    .toLowerCase()
    .replace(/[^a-zа-яё0-9]+/gi, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120) + '.pdf';
}

async function exportLevelPdf(pairElement, button) {
  if (!pairElement || !button) return;
  const originalText = button.textContent;
  const wasOpen = pairElement.open;
  const restore = () => {
    pairElement.open = wasOpen;
    document.body.classList.remove('pdf-exporting');
    button.disabled = false;
    button.textContent = originalText;
  };
  pairElement.open = true;
  button.disabled = true;
  button.textContent = 'Готовлю PDF...';
  document.body.classList.add('pdf-exporting');
  try {
    const { html2canvas, jsPDF } = await loadPdfLibrary();
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(
      () => requestAnimationFrame(resolve)
    ));
    const marginMm = 8;
    const captureSize = pdfCaptureSizeForElement(pairElement);
    const canvas = await html2canvas(pairElement, {
      scale: captureSize.scale,
      useCORS: true,
      backgroundColor: '#ffffff',
      width: captureSize.widthPx,
      height: captureSize.heightPx,
      windowWidth: Math.max(document.documentElement.clientWidth, captureSize.widthPx)
    });
    const pdf = new jsPDF({
      unit: 'mm',
      format: 'a3',
      orientation: 'landscape',
      compress: true
    });
    const sheetWidth = pdf.internal.pageSize.getWidth();
    const sheetHeight = pdf.internal.pageSize.getHeight();
    const availableWidth = sheetWidth - marginMm * 2;
    const availableHeight = sheetHeight - marginMm * 2;
    const fit = Math.min(
      availableWidth / canvas.width,
      availableHeight / canvas.height
    );
    const imageWidth = canvas.width * fit;
    const imageHeight = canvas.height * fit;
    const imageX = (sheetWidth - imageWidth) / 2;
    const imageY = marginMm;
    pdf.addImage(
      canvas.toDataURL('image/jpeg', 0.98),
      'JPEG', imageX, imageY, imageWidth, imageHeight, undefined, 'FAST'
    );
    pdf.save(levelPdfFileName(pairElement));
  } catch (error) {
    console.error('Level PDF export failed', error);
    const detail = error && error.message ? `\n${error.message}` : '';
    window.alert(`Не удалось подготовить PDF уровня. Повторите выгрузку.${detail}`);
  } finally {
    restore();
  }
}

function highlightWinners(selectedItems, attrsBySide, cellsBySide) {
  const entries = selectedItems.map((entry) => ({
    side: entry.side,
    bank: entry.item.bank,
    tierId: entry.item.tier_id,
    attr: attrsBySide[entry.side],
    evaluation: attrsBySide[entry.side].evaluation || {
      status: 'missing', reason: 'Нет структурированной оценки.'
    }
  }));
  const results = rankEvaluations(entries);
  results.forEach((result) => {
    const cell = cellsBySide[result.side];
    const attr = attrsBySide[result.side];
    cell.dataset.evaluationStatus = result.status;
    const explanation = [attr.note, result.reason].filter(Boolean).join('\\n');
    if (explanation) cell.title = explanation;
    if (!result.cls) return;
    cell.classList.add(result.cls);
    cell.appendChild(el('span', 'tag rank-tag', result.label));
    if (result.summary) {
      cell.appendChild(el('span', 'rank-reason', result.summary));
    }
  });
}

function rankEvaluations(entries) {
  const results = new Map(entries.map((entry) => [entry.side, {
    side: entry.side,
    status: isMissingRankEntry(entry) ? 'missing' : entry.evaluation.status,
    reason: entry.evaluation.reason || 'Для условия нет структурированного пояснения.'
  }]));
  const available = entries.filter(
    (entry) => !isMissingRankEntry(entry)
  );
  const missing = entries.filter((entry) => isMissingRankEntry(entry));
  missing.forEach((entry) => {
    results.set(entry.side, visualRankResult(
      entry, 'missing', 'rank-low', 'слабее',
      'Подтверждённое условие отсутствует в доступных источниках.'
    ));
  });
  if (!available.length) {
    missing.forEach((entry) => {
      results.set(entry.side, visualRankResult(
        entry, 'equal', 'rank-mid', 'равно',
        'У обоих вариантов условие отсутствует или не найдено.'
      ));
    });
    return entries.map((entry) => results.get(entry.side));
  }
  if (available.length === 1) {
    const entry = available[0];
    results.set(entry.side, visualRankResult(
      entry, 'comparable', 'rank-best', 'сильнее',
      'Условие подтверждено; у второго варианта данных нет.'
    ));
    return entries.map((item) => results.get(item.side));
  }
  if (available.length !== 2
      || !available.every((entry) => entry.evaluation.status === 'comparable')) {
    available.forEach((entry) => {
      results.set(entry.side, neutralRankResult(
        entry, 'insufficient',
        entry.evaluation.reason || 'Ключевые данные отсутствуют.'
      ));
    });
    return entries.map((entry) => results.get(entry.side));
  }

  const comparison = compareEvaluations(
    available[0].evaluation, available[1].evaluation
  );
  if (comparison.order === null) {
    const status = comparison.status === 'ambiguous'
      ? 'ambiguous' : 'insufficient';
    const reason = comparison.reason;
    available.forEach((entry) => {
      results.set(entry.side, neutralRankResult(entry, status, reason));
    });
    return entries.map((entry) => results.get(entry.side));
  }
  if (comparison.order === 0) {
    available.forEach((entry) => {
      results.set(entry.side, {
        side: entry.side,
        status: 'equal',
        cls: 'rank-mid',
        label: 'равно',
        summary: entry.evaluation.summary,
        reason: comparison.reason || entry.evaluation.reason
      });
    });
    return entries.map((entry) => results.get(entry.side));
  }
  const winner = comparison.order > 0 ? available[0] : available[1];
  const loser = comparison.order > 0 ? available[1] : available[0];
  results.set(winner.side, rankedResult(
    winner, { cls: 'rank-best', label: 'сильнее' }, comparison.reason
  ));
  results.set(loser.side, rankedResult(
    loser, { cls: 'rank-low', label: 'слабее' }, comparison.reason
  ));
  return entries.map((entry) => results.get(entry.side));
}

function visualRankResult(entry, status, cls, label, reason) {
  return {
    side: entry.side,
    status,
    cls,
    label,
    summary: entry.evaluation?.summary || '',
    reason
  };
}

function neutralRankResult(entry, status, reason) {
  return {
    side: entry.side,
    status,
    cls: '',
    label: '',
    summary: entry.evaluation?.summary || '',
    reason
  };
}

function rankedResult(entry, visual, comparisonReason = '') {
  return {
    side: entry.side,
    status: 'comparable',
    cls: visual.cls,
    label: visual.label,
    summary: entry.evaluation.summary,
    reason: comparisonReason || entry.evaluation.reason
  };
}

function isMissingRankEntry(entry) {
  if (entry.evaluation.status === 'missing') return true;
  const value = entry.attr ? entry.attr.value : '';
  if (Array.isArray(value)) return value.length === 0;
  const text = String(value || '').trim().toLowerCase();
  return !text || text.includes('не найдено') || text.includes('не нашли')
    || text === 'нет данных';
}

function compareEvaluations(left, right) {
  if (left.method !== right.method) {
    return {
      order: null, status: 'insufficient',
      reason: 'Используются разные методы оценки.'
    };
  }
  if (!deepEqual(left.scope || {}, right.scope || {})) {
    return {
      order: null, status: 'insufficient',
      reason: 'Различается область действия условий.'
    };
  }
  if (left.method === 'composite') return compareComposite(left, right);
  if (left.method === 'entry') return compareEntry(left, right);
  if (left.method === 'cashback') return compareCashback(left, right);
  if (left.method === 'compensation') return compareCompensation(left, right);
  if (left.method === 'insurance') return compareInsurance(left, right);
  if (left.method === 'limit') return compareLimits(left, right);
  if (left.method === 'lounge') return compareLounges(left, right);
  if (left.method === 'benefit_set') return compareBenefitSets(left, right);
  if (left.method === 'ordinal') return compareOrdinal(left, right);
  if (left.method === 'dominance') return compareDominance(left, right);
  return {
    order: null, status: 'insufficient',
    reason: 'Для условий нет доказуемого порядка.'
  };
}

function compareCompensation(left, right) {
  const priority = [
    'monthly_total', 'monthly_count', 'per_use_limit', 'annual_total', 'availability'
  ];
  for (const key of priority) {
    const leftValue = Number(left.metrics?.[key]);
    const rightValue = Number(right.metrics?.[key]);
    if (!Number.isFinite(leftValue) || !Number.isFinite(rightValue)
        || leftValue === rightValue) continue;
    return {
      order: leftValue > rightValue ? 1 : -1,
      status: 'comparable',
      reason: key === 'monthly_total'
        ? `Общая компенсация в месяц: ${formatRub(leftValue)} против ${formatRub(rightValue)}.`
        : `Показатель ${key}: ${leftValue} против ${rightValue}; больше — лучше.`
    };
  }
  const shared = priority.filter((key) => Number.isFinite(Number(left.metrics?.[key]))
    && Number.isFinite(Number(right.metrics?.[key])));
  return shared.length
    ? { order: 0, status: 'equal', reason: 'Ключевые показатели компенсации равны.' }
    : { order: null, status: 'insufficient', reason: 'Нет общего показателя компенсации.' };
}

function compareInsurance(left, right) {
  const priority = [
    'max_coverage_rub', 'owner_coverage_rub', 'territory_count',
    'family_coverage_rub', 'trip_days', 'availability'
  ];
  for (const key of priority) {
    const leftValue = Number(left.metrics?.[key]);
    const rightValue = Number(right.metrics?.[key]);
    if (!Number.isFinite(leftValue) || !Number.isFinite(rightValue)
        || leftValue === rightValue) continue;
    return {
      order: leftValue > rightValue ? 1 : -1,
      status: 'comparable',
      reason: key.includes('coverage')
        ? `Страховое покрытие в рублёвом эквиваленте: ${formatRub(leftValue)} `
          + `против ${formatRub(rightValue)}.`
        : `Показатель страхования ${key}: ${leftValue} против ${rightValue}.`
    };
  }
  const shared = priority.filter((key) => Number.isFinite(Number(left.metrics?.[key]))
    && Number.isFinite(Number(right.metrics?.[key])));
  return shared.length
    ? { order: 0, status: 'equal', reason: 'Ключевые показатели страхования равны.' }
    : { order: null, status: 'insufficient', reason: 'Нет общего показателя страхования.' };
}

function compareCashback(left, right) {
  const leftCap = Number(
    left.metrics?.effective_monthly_cap
      ?? left.metrics?.monthly_cap
      ?? left.metrics?.monthly_bonus_cap
  );
  const rightCap = Number(
    right.metrics?.effective_monthly_cap
      ?? right.metrics?.monthly_cap
      ?? right.metrics?.monthly_bonus_cap
  );
  if (Number.isFinite(leftCap) && Number.isFinite(rightCap)
      && leftCap !== rightCap) {
    return {
      order: leftCap > rightCap ? 1 : -1,
      status: 'comparable',
      reason: `Месячный лимит кешбэка: ${formatRub(leftCap)} против `
        + `${formatRub(rightCap)}; больший лимит выгоднее.`
    };
  }
  const keys = ['max_rate', 'base_rate', 'categories'].filter(
    (key) => Number.isFinite(Number(left.metrics?.[key]))
      && Number.isFinite(Number(right.metrics?.[key]))
  );
  if (!keys.length) {
    return Number.isFinite(leftCap) && Number.isFinite(rightCap)
      ? { order: 0, status: 'equal', reason: 'Месячные лимиты кешбэка равны.' }
      : {
        order: null, status: 'insufficient',
        reason: 'Нет общего подтверждённого показателя кешбэка.'
      };
  }
  return compareDominance(
    {
      metrics: Object.fromEntries(keys.map((key) => [key, left.metrics[key]])),
      directions: Object.fromEntries(keys.map((key) => [key, 'higher']))
    },
    {
      metrics: Object.fromEntries(keys.map((key) => [key, right.metrics[key]])),
      directions: Object.fromEntries(keys.map((key) => [key, 'higher']))
    }
  );
}

function compareEntry(left, right) {
  const leftStandalone = Number(left.metrics?.standalone_capital_threshold);
  const rightStandalone = Number(right.metrics?.standalone_capital_threshold);
  if (Number.isFinite(leftStandalone) && Number.isFinite(rightStandalone)
      && leftStandalone !== rightStandalone) {
    return {
      order: leftStandalone < rightStandalone ? 1 : -1,
      status: 'comparable',
      reason: `Самостоятельный порог активов: ${formatRub(leftStandalone)} против `
        + `${formatRub(rightStandalone)}; меньший порог выгоднее.`
    };
  }
  const normalizedKeys = [
    'standalone_capital_threshold', 'mandatory_count', 'alternative_count'
  ].filter((key) => Number.isFinite(Number(left.metrics?.[key]))
    && Number.isFinite(Number(right.metrics?.[key])));
  if (!normalizedKeys.length) {
    return {
      order: null, status: 'insufficient',
      reason: 'Не найден общий сценарий входа для корректного сравнения.'
    };
  }
  return compareDominance(
    {
      metrics: Object.fromEntries(normalizedKeys.map(
        (key) => [key, left.metrics[key]]
      )),
      directions: Object.fromEntries(normalizedKeys.map(
        (key) => [key, left.directions[key]]
      ))
    },
    {
      metrics: Object.fromEntries(normalizedKeys.map(
        (key) => [key, right.metrics[key]]
      )),
      directions: Object.fromEntries(normalizedKeys.map(
        (key) => [key, right.directions[key]]
      ))
    }
  );
}

function compareComposite(left, right) {
  const leftParts = left.metrics?.components || {};
  const rightParts = right.metrics?.components || {};
  const componentIds = [...new Set([
    ...Object.keys(leftParts), ...Object.keys(rightParts)
  ])].sort();
  let leftWins = 0;
  let rightWins = 0;
  let equal = 0;
  let skipped = 0;
  const decisions = [];
  for (const componentId of componentIds) {
    const leftPart = leftParts[componentId] || { present: false };
    const rightPart = rightParts[componentId] || { present: false };
    const label = leftPart.label || rightPart.label || componentId;
    if (Boolean(leftPart.present) !== Boolean(rightPart.present)) {
      if (leftPart.present) leftWins += 1;
      else rightWins += 1;
      decisions.push(`${label}: условие подтверждено только у одного банка`);
      continue;
    }
    if (!leftPart.present) continue;
    const leftEvaluation = leftPart.evaluation || {};
    const rightEvaluation = rightPart.evaluation || {};
    if (leftEvaluation.status !== 'comparable'
        || rightEvaluation.status !== 'comparable') {
      skipped += 1;
      continue;
    }
    const comparison = compareEvaluations(leftEvaluation, rightEvaluation);
    if (comparison.order === null) {
      skipped += 1;
    } else if (comparison.order > 0) {
      leftWins += 1;
      decisions.push(`${label}: первый банк сильнее`);
    } else if (comparison.order < 0) {
      rightWins += 1;
      decisions.push(`${label}: второй банк сильнее`);
    } else {
      equal += 1;
    }
  }
  const reason = `По сопоставимым подпунктам: ${leftWins}–${rightWins}; `
    + `равно: ${equal}; без числового ранга: ${skipped}.`
    + (decisions.length ? ` ${decisions.join('; ')}.` : '');
  if (leftWins === rightWins) {
    if (!leftWins && !equal) {
      return { order: null, status: 'insufficient', reason };
    }
    return {
      order: leftWins ? null : 0,
      status: leftWins ? 'ambiguous' : 'equal',
      reason
    };
  }
  return { order: leftWins > rightWins ? 1 : -1, status: 'comparable', reason };
}

function compareLounges(left, right) {
  const leftUnlimited = Boolean(left.metrics.unlimited);
  const rightUnlimited = Boolean(right.metrics.unlimited);
  let visitOrder = 0;
  if (leftUnlimited !== rightUnlimited) {
    visitOrder = leftUnlimited ? 1 : -1;
  } else if (!leftUnlimited) {
    const leftVisits = Number(left.metrics.visits_monthly);
    const rightVisits = Number(right.metrics.visits_monthly);
    if (!Number.isFinite(leftVisits) || !Number.isFinite(rightVisits)) {
      return {
        order: null, status: 'insufficient',
        reason: 'Не у всех вариантов подтверждено количество посещений.'
      };
    }
    visitOrder = leftVisits === rightVisits ? 0 : leftVisits > rightVisits ? 1 : -1;
  }
  if (visitOrder) return { order: visitOrder, reason: '' };
  return {
    order: 0,
    reason: 'Максимальное подтверждённое количество посещений одинаково; '
      + 'системы доступа и общий баланс преференций показаны справочно.'
  };
}

function compareOrdinal(left, right) {
  const leftRank = Number(left.metrics.service_rank);
  const rightRank = Number(right.metrics.service_rank);
  if (Number.isFinite(leftRank) && Number.isFinite(rightRank) && leftRank !== rightRank) {
    return { order: leftRank > rightRank ? 1 : -1, reason: '' };
  }
  return compareDominance(left, right);
}

function compareDominance(left, right) {
  const leftKeys = Object.keys(left.metrics || {}).sort();
  const rightKeys = Object.keys(right.metrics || {}).sort();
  const commonKeys = leftKeys.filter((key) => rightKeys.includes(key));
  const hasMissingMetrics = !deepEqual(leftKeys, rightKeys);
  if (!commonKeys.length) {
    return {
      order: null, status: 'insufficient',
      reason: 'Нет общих подтверждённых показателей.'
    };
  }
  let leftBetter = false;
  let rightBetter = false;
  for (const key of commonKeys) {
    const leftValue = Number(left.metrics[key]);
    const rightValue = Number(right.metrics[key]);
    const direction = left.directions[key];
    if (!Number.isFinite(leftValue) || !Number.isFinite(rightValue)
        || direction !== right.directions[key]) {
      return {
        order: null, status: 'insufficient',
        reason: 'Метрики нельзя привести к общей шкале.'
      };
    }
    if (leftValue === rightValue) continue;
    const leftWins = direction === 'lower'
      ? leftValue < rightValue
      : leftValue > rightValue;
    if (leftWins) leftBetter = true;
    else rightBetter = true;
  }
  if (leftBetter && rightBetter) {
    return {
      order: null, status: 'ambiguous',
      reason: 'Каждый вариант лучше по разным подтверждённым параметрам.'
    };
  }
  if (hasMissingMetrics) {
    return {
      order: null,
      status: leftBetter || rightBetter ? 'ambiguous' : 'insufficient',
      reason: leftBetter || rightBetter
        ? 'По общим показателям есть преимущество, но часть ключевых данных '
          + 'подтверждена только для одного варианта.'
        : 'Общие показатели равны, но часть ключевых данных отсутствует.'
    };
  }
  if (leftBetter) return { order: 1, reason: '' };
  if (rightBetter) return { order: -1, reason: '' };
  return { order: 0, reason: '' };
}

function compareLimits(left, right) {
  if (left.metrics.unlimited || right.metrics.unlimited) {
    if (left.metrics.unlimited && right.metrics.unlimited) return { order: 0, reason: '' };
    return { order: left.metrics.unlimited ? 1 : -1, reason: '' };
  }
  const leftLimits = left.metrics.limits || [];
  const rightLimits = right.metrics.limits || [];
  if (leftLimits.length === 1 && rightLimits.length === 1) {
    return compareSingleLimit(leftLimits[0], rightLimits[0]);
  }
  const leftByPeriod = Object.fromEntries(leftLimits.map((item) => [item.period, item.amount]));
  const rightByPeriod = Object.fromEntries(rightLimits.map((item) => [item.period, item.amount]));
  const periods = Object.keys(leftByPeriod).sort();
  if (!deepEqual(periods, Object.keys(rightByPeriod).sort())) {
    return { order: null, reason: 'набор дневных и месячных лимитов различается.' };
  }
  return compareDominance(
    {
      metrics: leftByPeriod,
      directions: Object.fromEntries(periods.map((period) => [period, 'higher']))
    },
    {
      metrics: rightByPeriod,
      directions: Object.fromEntries(periods.map((period) => [period, 'higher']))
    }
  );
}

function compareSingleLimit(left, right) {
  if (left.period === right.period) {
    if (left.amount === right.amount) return { order: 0, reason: '' };
    return { order: left.amount > right.amount ? 1 : -1, reason: '' };
  }
  return {
    order: null, status: 'insufficient',
    reason: 'Лимиты указаны за разные периоды и не сравниваются между собой.'
  };
}

function compareBenefitSets(left, right) {
  const leftBenefits = left.metrics.benefits || {};
  const rightBenefits = right.metrics.benefits || {};
  const leftKeys = new Set(Object.keys(leftBenefits));
  const rightKeys = new Set(Object.keys(rightBenefits));
  const leftContainsRight = [...rightKeys].every((key) => leftKeys.has(key));
  const rightContainsLeft = [...leftKeys].every((key) => rightKeys.has(key));

  function compareBenefitValue(containerValue, containedValue) {
    let containerBetter = false;
    let containedBetter = false;
    const containerStatus = Number(containerValue.status);
    const containedStatus = Number(containedValue.status);
    if (containerStatus !== containedStatus) {
      if (containerStatus > containedStatus) containerBetter = true;
      else containedBetter = true;
    }
    const containerRub = Number(containerValue.rub_total);
    const containedRub = Number(containedValue.rub_total);
    const containerHasRub = Number.isFinite(containerRub);
    const containedHasRub = Number.isFinite(containedRub);
    if (containerHasRub !== containedHasRub) return null;
    if (containerHasRub && containerRub !== containedRub) {
      if (containerRub > containedRub) containerBetter = true;
      else containedBetter = true;
    }
    if (containerBetter && containedBetter) return null;
    if (containerBetter) return 1;
    if (containedBetter) return -1;
    return 0;
  }

  function containsWithoutWeaker(container, contained) {
    return Object.keys(contained).every((key) => {
      if (container[key] === undefined) return false;
      const comparison = compareBenefitValue(container[key], contained[key]);
      return comparison !== null && comparison >= 0;
    });
  }

  const leftDominates = leftContainsRight
    && containsWithoutWeaker(leftBenefits, rightBenefits);
  const rightDominates = rightContainsLeft
    && containsWithoutWeaker(rightBenefits, leftBenefits);
  if (leftDominates && rightDominates && deepEqual(leftBenefits, rightBenefits)) {
    return { order: 0, reason: '' };
  }
  if (leftDominates && !rightDominates) return { order: 1, reason: '' };
  if (rightDominates && !leftDominates) return { order: -1, reason: '' };
  return { order: null, reason: 'наборы привилегий различаются по составу или статусу.' };
}

function deepEqual(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function isEmptyDisplay(value) {
  if (Array.isArray(value)) return value.length === 0;
  const text = String(value || '').toLowerCase();
  return !text || text === 'не найдено' || text.includes('не найдено');
}

function renderAttrValue(cell, attr) {
  if (attr.kind === 'benefits' && Array.isArray(attr.value)) {
    renderBenefits(cell, attr.value);
    appendDetails(cell, attr);
    return;
  }
  cell.textContent = attr.value;
  appendDetails(cell, attr);
}

function appendDetails(cell, attr) {
  if (!attr.details || attr.details === attr.value) return;
  const details = el('details', 'attr-details');
  details.appendChild(el('summary', '', 'Подробнее'));
  details.appendChild(el('p', '', attr.details));
  cell.appendChild(details);
}

function renderBenefits(cell, items) {
  const listItems = items.filter((item) => item.availability !== 'rule');
  const rule = items.find((item) => item.availability === 'rule');
  if (!listItems.length && !rule) {
    cell.textContent = 'Не найдено в доступных источниках';
    return;
  }
  if (listItems.length) {
    const ul = el('ul', 'benefits-list');
    listItems.forEach((item) => {
      const li = el('li');
      li.appendChild(el('span', 'benefit-title', item.title));
      if (item.description) {
        li.appendChild(document.createTextNode(' — '));
        li.appendChild(el('span', 'benefit-description', item.description));
      }
      if (item.availability === 'selectable') {
        li.appendChild(document.createTextNode(' '));
        li.appendChild(el('span', 'tag selectable', 'Опция на выбор'));
      } else if (item.availability === 'always_included'
          && hasMixedBenefitStatuses(listItems)) {
        li.appendChild(document.createTextNode(' '));
        li.appendChild(el('span', 'tag always', 'Включено постоянно'));
      }
      ul.appendChild(li);
    });
    cell.appendChild(ul);
  }
  if (rule && rule.description) {
    cell.appendChild(el('div', 'benefit-rule',
      'Условия выбора: ' + rule.description));
  }
}

function hasMixedBenefitStatuses(items) {
  const statuses = new Set(items
    .map((item) => item.availability)
    .filter((status) => status && status !== 'unknown'));
  return statuses.size > 1;
}

SIDES.forEach((side) => {
  renderBanks(side);
});
document.getElementById('expand-all').addEventListener('click', () => {
  document.querySelectorAll('#pair-list .level-pair').forEach((item) => {
    item.open = true;
  });
});
document.getElementById('collapse-all').addEventListener('click', () => {
  document.querySelectorAll('#pair-list .level-pair').forEach((item) => {
    item.open = false;
  });
});
document.getElementById('pdf-button').addEventListener('click', exportComparePdf);
initChangesApp(document.querySelector('.changes-app'));
initChangesPanel(document.querySelector('.js-changes-panel'));
"""
