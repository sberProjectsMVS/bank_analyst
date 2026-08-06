# -*- coding: utf-8 -*-
"""
Верифицированные вручную факты (source_id = "curated").

Это НЕ разовый хардкод в ячейках отчёта: записи применяются при каждом
скане как источник с наивысшим приоритетом, каждая несёт ссылку на
первоисточник и дату проверки (`date_checked`). Если запись устарела —
обновите значение и дату или удалите её, чтобы поле снова заполнялось
автоматическим парсингом.

Правила ведения:
  - значение — факт с точными цифрами и формулировками первоисточника;
  - source_url — официальная страница (или страница ПБИ, если официальный
    сайт не публикует деталь);
  - date_checked — дата последней сверки с первоисточником;
  - note — контекст: что проверено, что не подтвердилось.

Записи со старым date_checked (> STALE_DAYS) помечаются в отчёте
«проверить актуальность».
"""

STALE_DAYS = 90

_SBER_PREMIER = "https://www.sberbank.ru/ru/person/sb_premier_new"
_SBER_PREMIUM_LEVELS = "https://www.sberbank.ru/ru/person/premium"
_SBER_FIRST = "https://www.sberbank.ru/first"
_SBER_VKLAD = "https://www.sberbank.ru/ru/person/premium/premium_vklad"
_SBER_FIRST_VKLADY = "https://www.sberbank.ru/ru/person/sb1/vklad/vse_vklady"
_SBER_CARD = "https://www.sberbank.ru/ru/person/bank_cards/debit/sberkarta_premium"
_SBER_PREMIUM_TARIFF = (
    "https://www.sberbank.ru/common/img/uploaded/files/pdf/"
    "tarif_premobsl_07072026.pdf"
)
_SBER_PREMIER_VZR = (
    "https://www.sberbank.ru/common/img/uploaded/pdf/"
    "usloviya_vzr_newpremier_2025.pdf"
)
_SBER_FIRST_4_VZR = (
    "https://www.sberbank.ru/common/img/uploaded/files/sb1/"
    "usloviya_vzr_premobsl_4.pdf"
)
_PBI_SBER = "https://premiumbanking.info/sber"
_ALFA_ACLUB_OFFICIAL = "https://alfabank.ru/a-club/"

_CHECKED = "2026-07-02"


def _fact_from(source_fact, value, note=""):
    return {
        "value": value,
        "source_url": source_fact["source_url"],
        "date_checked": source_fact["date_checked"],
        "note": note or source_fact.get("note", ""),
    }


def _scoped_fact(value, source_url, document_title, quoted_fragment, **metadata):
    fact = {
        "value": value,
        "source_url": source_url,
        "date_checked": "2026-07-31",
        "document_title": document_title,
        "quoted_fragment": quoted_fragment,
        "note": metadata.pop("note", ""),
    }
    fact.update(metadata)
    return fact

# ---------- Карты (Премиальная СберКарта, тарифы одной страницы для всех уровней)
_PREMIER_CARD = {
    "value": ("Премиальная СберКарта: пластик или металл (металлический носитель "
              "доступен всем премиальным уровням). Снятие наличных до 1 млн ₽ "
              "в день. Стоимость "
              "выпуска металлической карты на странице тарифов не указана"),
    "source_url": _SBER_CARD,
    "date_checked": _CHECKED,
    "note": "Лимиты переводов зависят от уровня и хранятся отдельными фактами",
}

_FIRST_CARD = {
    "value": ("Премиальная СберКарта: пластик или металл. Снятие наличных "
              "до 2 млн ₽ в день"),
    "source_url": _SBER_CARD,
    "date_checked": _CHECKED,
    "note": ("Вторичные источники (banki.ru) упоминали выпуск металлической "
             "карты СберПервый за 7 500 ₽ — на официальной странице цена "
             "не опубликована, требует сверки в тарифах PDF"),
}

_PRIVATE_CARD = {
    "value": ("Премиальная СберКарта уровня Private: снятие наличных до "
              "3 млн ₽ в день; "
              "лимитированная серия металлических карт (чёрные и белые) — "
              "только для уровня 6 / Sber Private Banking"),
    "source_url": _SBER_CARD,
    "date_checked": _CHECKED,
    "note": "Лимит переводов уровня 6 хранится отдельным фактом",
}

# Официальный popup «Переводы и платежи без комиссии» задаёт разные лимиты
# для конкретных уровней. Не объединять и не переносить их между тирами.
_SBER_TRANSFER_LEVELS = {
    "sber_premier_1": {
        "value": "Переводы без комиссии до 1 млн ₽ в месяц",
        "source_url": _SBER_PREMIUM_LEVELS,
        "date_checked": "2026-07-23",
        "note": ("Официальный popup: «1 и 2 уровни — 1 млн ₽ в месяц». "
                 "Лимит относится к переводам клиентам Сбера и платежам юрлицам"),
    },
    "sber_premier_2": {
        "value": "Переводы без комиссии до 1 млн ₽ в месяц",
        "source_url": _SBER_PREMIUM_LEVELS,
        "date_checked": "2026-07-23",
        "note": ("Официальный popup: «1 и 2 уровни — 1 млн ₽ в месяц». "
                 "Лимит относится к переводам клиентам Сбера и платежам юрлицам"),
    },
    "sber_premier_3": {
        "value": "Переводы без комиссии до 1 млн ₽ в сутки",
        "source_url": _SBER_PREMIUM_LEVELS,
        "date_checked": "2026-07-23",
        "note": ("Официальный popup: «3 уровень — 1 млн ₽ в сутки». "
                 "Лимит относится к переводам клиентам Сбера и платежам юрлицам"),
    },
    "sber_first_4": {
        "value": "Переводы без комиссии до 35 млн ₽ в сутки",
        "source_url": _SBER_PREMIUM_LEVELS,
        "date_checked": "2026-07-23",
        "note": ("Официальный popup: «4 и 5 уровни — 35 млн ₽ в сутки». "
                 "Лимит относится к переводам клиентам Сбера и платежам юрлицам"),
    },
    "sber_first_5": {
        "value": "Переводы без комиссии до 35 млн ₽ в сутки",
        "source_url": _SBER_PREMIUM_LEVELS,
        "date_checked": "2026-07-23",
        "note": ("Официальный popup: «4 и 5 уровни — 35 млн ₽ в сутки». "
                 "Лимит относится к переводам клиентам Сбера и платежам юрлицам"),
    },
    "sber_private_6": {
        "value": "Переводы без комиссии до 50 млн ₽ в сутки",
        "source_url": _SBER_PREMIUM_LEVELS,
        "date_checked": "2026-07-23",
        "note": ("Официальный popup: «6 уровень — до 50 млн ₽ в сутки». "
                 "Лимит относится к переводам клиентам Сбера и платежам юрлицам"),
    },
}

_SBER_TIER_NUMBERS = {
    "sber_premier_1": 1,
    "sber_premier_2": 2,
    "sber_premier_3": 3,
    "sber_first_4": 4,
    "sber_first_5": 5,
    "sber_private_6": 6,
}


def _sber_operation_facts(tier_id):
    level = _SBER_TIER_NUMBERS[tier_id]
    internal_value = (
        "Переводы другому физлицу внутри Сбера через приложение/УКО: "
        "до 1 000 000 ₽ включительно в месяц без комиссии; сверх лимита "
        "0,5% от суммы, максимум 5 000 ₽"
        if level <= 2 else
        "Переводы другому физлицу внутри Сбера через приложение/УКО: "
        "без комиссии; технический лимит в данном источнике не указан"
    )
    internal = _scoped_fact(
        internal_value, _SBER_PREMIUM_TARIFF,
        "Тарифы премиального обслуживания СберБанка от 07.07.2026",
        internal_value,
        recipient="физическое лицо — клиент Сбера",
        channel="приложение / УКО",
        free_limit="1 000 000 ₽" if level <= 2 else "без комиссии",
        technical_limit=(
            "не указан" if level >= 3 else "не выделен отдельно"
        ),
        period="месяц" if level <= 2 else "",
        over_limit_fee=(
            "0,5% от суммы, максимум 5 000 ₽" if level <= 2 else ""
        ),
        effective_date="2026-07-07",
        pdf_page=4,
    )
    marketing_limits = {
        1: ("1 000 000 ₽", "месяц"),
        2: ("1 000 000 ₽", "месяц"),
        3: ("1 000 000 ₽", "сутки"),
        4: ("35 000 000 ₽", "сутки"),
        5: ("35 000 000 ₽", "сутки"),
        6: ("50 000 000 ₽", "сутки"),
    }
    marketing_limit, marketing_period = marketing_limits[level]
    if level <= 2:
        legal_value = (
            "Платежи/переводы юридическим лицам в РФ в рублях через "
            "приложение/УКО: в пределах общего лимита 1 000 000 ₽ в месяц "
            "без комиссии; сверх лимита — по Разделам I и III Альбома тарифов"
        )
        legal_free_limit = "1 000 000 ₽ — общий с переводами физлицам"
        legal_period = "месяц"
        legal_over_limit = "по Разделам I и III Альбома тарифов"
    else:
        legal_value = (
            "Платежи/переводы юридическим лицам в РФ в рублях через "
            "приложение/УКО: без комиссии; технический лимит в данном "
            "источнике не указан"
        )
        legal_free_limit = "без комиссии"
        legal_period = ""
        legal_over_limit = ""
    legal = _scoped_fact(
        legal_value,
        _SBER_PREMIUM_TARIFF,
        "Тарифы премиального обслуживания СберБанка от 07.07.2026",
        "п. 2.3: переводы на счета юридических лиц через УКО",
        recipient="юридическое лицо",
        channel="приложение / УКО",
        free_limit=legal_free_limit,
        technical_limit="не указан",
        period=legal_period,
        over_limit_fee=legal_over_limit,
        effective_date="2026-07-07",
        pdf_page=4,
        additional_source_url=_SBER_PREMIUM_LEVELS,
        additional_source_value=(
            f"Маркетинговая сводка уровня {level}: {marketing_limit} "
            f"в {marketing_period}; юридический тариф имеет приоритет"
        ),
        note=(
            "Юридический тариф имеет приоритет. Маркетинговая сводка "
            "сохранена как дополнительное пояснение, а не как технический лимит."
        ),
    )
    if level <= 3:
        interbank_remote_value = (
            "Межбанковский перевод с дебетовой карты/платёжного счёта через "
            "приложение/УКО: комиссия по Разделу III Альбома тарифов; "
            "числовой бесплатный лимит в данном документе не указан"
        )
        interbank_office_value = (
            "Межбанковский перевод с дебетовой карты/платёжного счёта через "
            "офис/ОКР: комиссия по Разделу III Альбома тарифов; числовой "
            "лимит в данном документе не указан"
        )
        remote_fee = "по Разделу III Альбома тарифов"
        office_fee = "по Разделу III Альбома тарифов"
    else:
        interbank_remote_value = (
            "Межбанковский перевод с дебетовой карты/платёжного счёта через "
            "приложение/УКО: без комиссии; технический лимит в данном "
            "источнике не указан"
        )
        interbank_office_value = (
            "Межбанковский перевод с дебетовой карты/платёжного счёта через "
            "офис/ОКР: 2% от суммы, минимум 50 ₽, максимум 10 000 ₽"
        )
        remote_fee = "0%"
        office_fee = "2% от суммы, минимум 50 ₽, максимум 10 000 ₽"
    interbank_common = {
        "source_url": _SBER_PREMIUM_TARIFF,
        "document_title": "Тарифы премиального обслуживания СберБанка от 07.07.2026",
        "recipient": "получатель в другой кредитной организации РФ",
        "technical_limit": "не указан",
        "period": "",
        "effective_date": "2026-07-07",
        "pdf_page": 5,
    }
    interbank_remote = _scoped_fact(
        interbank_remote_value,
        interbank_common["source_url"],
        interbank_common["document_title"],
        "п. 2.5: через УКО — бесплатно для уровней 4–6; для уровней 1–3 — Раздел III Альбома тарифов",
        recipient=interbank_common["recipient"],
        channel="приложение / УКО",
        free_limit="без комиссии" if level >= 4 else "не указан",
        technical_limit=interbank_common["technical_limit"],
        period=interbank_common["period"],
        over_limit_fee=remote_fee,
        effective_date=interbank_common["effective_date"],
        pdf_page=interbank_common["pdf_page"],
    )
    interbank_office = _scoped_fact(
        interbank_office_value,
        interbank_common["source_url"],
        interbank_common["document_title"],
        "п. 2.5: через ОКР — 2%, min 50 руб., max 10 000 руб. для уровней 4–6; для уровней 1–3 — Раздел III Альбома тарифов",
        recipient=interbank_common["recipient"],
        channel="офис / ОКР",
        free_limit="не применяется" if level >= 4 else "не указан",
        technical_limit=interbank_common["technical_limit"],
        period=interbank_common["period"],
        over_limit_fee=office_fee,
        effective_date=interbank_common["effective_date"],
        pdf_page=interbank_common["pdf_page"],
    )
    daily_limit = 1_000_000 if level <= 3 else 2_000_000 if level <= 5 else 3_000_000
    monthly_limit = 5_000_000 if level <= 3 else 30_000_000
    free_atm = _scoped_fact(
        "До 1 000 000 ₽ в месяц в банкоматах без комиссии"
        + (
            "; сверх бесплатного лимита — 2% от суммы превышения"
            if level <= 3 else
            "; выше 1 000 000 ₽ также без комиссии, в пределах операционных лимитов"
        ),
        _SBER_PREMIUM_TARIFF,
        "Тарифы премиального обслуживания СберБанка от 07.07.2026",
        "Бесплатное снятие в банкоматах до 1 000 000 ₽ в месяц",
        channel="банкомат",
        free_limit="1 000 000 ₽",
        technical_limit=f"{daily_limit:,} ₽ в сутки".replace(",", " "),
        period="месяц",
        over_limit_fee="2% от суммы превышения" if level <= 3 else "0%",
        effective_date="2026-07-07",
    )
    return {
        "internal_transfers": internal,
        "interbank_transfers_remote": interbank_remote,
        "interbank_transfers_office": interbank_office,
        "legal_entity_payments": legal,
        "atm_free_withdrawal": free_atm,
        "cash_monthly_operational_limit": _scoped_fact(
            f"{monthly_limit:,} ₽ в месяц через все каналы суммарно".replace(",", " "),
            _SBER_PREMIUM_TARIFF,
            "Тарифы премиального обслуживания СберБанка от 07.07.2026",
            f"Общий месячный лимит выдачи: {monthly_limit} ₽",
            channel="все каналы суммарно",
            technical_limit=f"{monthly_limit:,} ₽".replace(",", " "),
            period="месяц",
            effective_date="2026-07-07",
        ),
        "atm_daily_limit": _scoped_fact(
            f"{daily_limit:,} ₽ в сутки".replace(",", " "),
            _SBER_PREMIUM_TARIFF,
            "Тарифы премиального обслуживания СберБанка от 07.07.2026",
            f"Суточный лимит в банкоматах: {daily_limit} ₽",
            channel="банкомат",
            technical_limit=f"{daily_limit:,} ₽".replace(",", " "),
            period="сутки",
            effective_date="2026-07-07",
        ),
        "cash_desk_daily_limit": _scoped_fact(
            f"{daily_limit:,} ₽ в сутки".replace(",", " "),
            _SBER_PREMIUM_TARIFF,
            "Тарифы премиального обслуживания СберБанка от 07.07.2026",
            f"Суточный лимит через кассу: {daily_limit} ₽",
            channel="касса",
            technical_limit=f"{daily_limit:,} ₽".replace(",", " "),
            period="сутки",
            effective_date="2026-07-07",
        ),
        "cash_over_limit_fee": _scoped_fact(
            "2% от суммы превышения бесплатного месячного лимита"
            if level <= 3 else
            "Комиссия сверх 1 000 000 ₽ не взимается; действуют операционные лимиты",
            _SBER_PREMIUM_TARIFF,
            "Тарифы премиального обслуживания СберБанка от 07.07.2026",
            "Комиссия сверх бесплатного лимита",
            channel="банкомат",
            free_limit="1 000 000 ₽",
            over_limit_fee="2%" if level <= 3 else "0%",
            period="месяц",
            effective_date="2026-07-07",
        ),
    }


def _sber_insurance_facts(tier_id):
    if tier_id in {"sber_premier_1", "sber_premier_2", "sber_premier_3"}:
        source = _SBER_PREMIER_VZR
        title = "Условия ВЗР СберПремьер"
        return {
            "insurance": _scoped_fact(
                "ВЗР одной строкой: медицинская и медико-транспортная помощь — "
                "30 000 евро в РФ и 100 000 евро за рубежом; владелец 18–75 лет, "
                "члены семьи покрываются при сопровождении владельца; первые "
                "90 дней каждой поездки, число поездок не ограничено; в РФ "
                "исключена территория в пределах 100 км от места проживания; "
                "багаж — 500 евро в РФ / 2 000 евро за рубежом; отмена или "
                "досрочное возвращение — 1 500 евро в РФ / 3 000 евро за рубежом",
                source, title,
                "30 000 евро в РФ; 100 000 евро за рубежом; 90 дней; поездки не ограничены",
            ),
            "insurance_russia_coverage": _scoped_fact(
                "30 000 евро — медицинская и медико-транспортная помощь в РФ",
                source, title, "30 000 евро на территории РФ", region="РФ"),
            "insurance_foreign_coverage": _scoped_fact(
                "100 000 евро — медицинская и медико-транспортная помощь за пределами РФ",
                source, title, "100 000 евро за пределами РФ", region="за пределами РФ"),
            "insurance_covered_people": _scoped_fact(
                "Владелец пакета 18–75 лет и сопровождающие его в поездке члены семьи",
                source, title, "члены семьи при сопровождении владельца"),
            "insurance_owner_accompaniment": _scoped_fact(
                "Для покрытия членов семьи требуется сопровождение владельцем пакета",
                source, title, "члены семьи сопровождают владельца"),
            "insurance_trip_duration": _scoped_fact(
                "Первые 90 дней каждой поездки", source, title, "первые 90 дней",
                period="поездка"),
            "insurance_trip_count": _scoped_fact(
                "Количество поездок не ограничено", source, title,
                "количество поездок не ограничено"),
            "insurance_territorial_exclusions": _scoped_fact(
                "В РФ не покрывается территория в пределах 100 км по автомобильным дорогам от места постоянного проживания",
                source, title, "в пределах 100 км от места постоянного проживания",
                region="РФ"),
            "insurance_additional_risks": _scoped_fact(
                "Багаж: 500 евро в РФ / 2 000 евро за рубежом; отмена или досрочное возвращение: 1 500 евро в РФ / 3 000 евро за рубежом",
                source, title, "багаж и отмена/досрочное возвращение"),
        }
    if tier_id == "sber_first_4":
        source = _SBER_FIRST_4_VZR
        title = "Условия ВЗР СберПервый — уровень 4"
        return {
            "insurance": _scoped_fact(
                "ВЗР одной строкой: медицинская и медико-транспортная помощь — "
                "100 000 евро в РФ и 1 000 000 евро за рубежом; владелец и "
                "члены семьи до 75 лет, семья покрывается и без владельца; "
                "первые 90 дней каждой поездки, число поездок не ограничено; "
                "в РФ исключена территория в пределах 100 км от места проживания; "
                "багаж — 1 000 евро в РФ / 2 500 евро за рубежом; отмена или "
                "досрочное возвращение — 6 000 евро; гражданская ответственность — "
                "100 000 евро; юридическая помощь — 7 500 евро",
                source, title,
                "100 000 евро в РФ; 1 000 000 евро за рубежом; 90 дней; поездки не ограничены",
            ),
            "insurance_russia_coverage": _scoped_fact(
                "100 000 евро — медицинская и медико-транспортная помощь в РФ",
                source, title, "100 000 евро на территории РФ", region="РФ"),
            "insurance_foreign_coverage": _scoped_fact(
                "1 000 000 евро — медицинская и медико-транспортная помощь за пределами РФ",
                source, title, "1 000 000 евро за пределами РФ", region="за пределами РФ"),
            "insurance_covered_people": _scoped_fact(
                "Владелец и члены семьи до 75 лет; члены семьи покрываются и без владельца",
                source, title, "члены семьи до 75 лет, в том числе без владельца"),
            "insurance_owner_accompaniment": _scoped_fact(
                "Сопровождение владельцем не требуется", source, title,
                "члены семьи путешествуют без владельца"),
            "insurance_trip_duration": _scoped_fact(
                "Первые 90 дней каждой поездки", source, title, "первые 90 дней",
                period="поездка"),
            "insurance_trip_count": _scoped_fact(
                "Количество поездок не ограничено", source, title,
                "количество поездок не ограничено"),
            "insurance_territorial_exclusions": _scoped_fact(
                "В РФ исключена территория в пределах 100 км от места проживания",
                source, title, "в пределах 100 км от места проживания", region="РФ"),
            "insurance_additional_risks": _scoped_fact(
                "Багаж: 1 000 евро в РФ / 2 500 евро за рубежом; отмена или досрочное возвращение: 6 000 евро; гражданская ответственность: 100 000 евро; юридическая помощь: 7 500 евро",
                source, title, "багаж, отмена, гражданская ответственность, юридическая помощь"),
        }
    return {}


def _sber_option_and_service_facts(tier_id):
    level = _SBER_TIER_NUMBERS[tier_id]
    facts = {}
    if level <= 3:
        for field_id, title in (
            ("health_option", "Здоровье"),
            ("samokat_option", "Самокат"),
            ("pets_option", "Питомцы"),
            ("roadside_option", "Авто / помощь на дорогах"),
        ):
            value = f"Опция «{title}» — доступна на выбор"
            facts[field_id] = _scoped_fact(
                value, _SBER_PREMIER, "СберПремьер — опции привилегий",
                value, channel="опция на выбор")
        facts["personal_banking_support"] = _scoped_fact(
            "Личный менеджер и выделенная линия премиальной поддержки 900",
            _SBER_PREMIER, "СберПремьер", "личный менеджер; выделенная линия 900")
    metal_value = (
        "Премиальная СберКарта: доступен металлический носитель; стоимость выпуска на официальной странице не указана"
        if level <= 5 else
        "Лимитированная металлическая Премиальная СберКарта (чёрная или белая) для Sber Private Banking; стоимость на официальной странице не указана"
    )
    facts["metal_card"] = _scoped_fact(
        metal_value, _SBER_CARD, "Премиальная СберКарта",
        metal_value, channel="основная/дополнительная не уточнено")
    return facts

# Консьерж на СберПремьер отсутствует — общая запись для уровней 1–3
_PREMIER_CONCIERGE = {
    "value": ("Нет — консьерж-сервис не входит в СберПремьер. На уровнях 1–3 "
              "только личный менеджер и выделенная линия 900; набор привилегий — "
              "опции «Бизнес-залы», «Такси и рестораны», «Здоровье», «Самокат», "
              "«Питомцы», «Авто» + СберПрайм"),
    "source_url": _SBER_PREMIER,
    "date_checked": _CHECKED,
    "note": "Сверено с официальной страницей и ПБИ /sber/1–3",
}

_PREMIER_DEPOSITS = {
    "value": ("Вклад «Премиум» до 13,8% годовых (базовая ставка + надбавки: "
              "до +1,3 п.п. за уровень премиального обслуживания, до +0,5 п.п. "
              "за инвестиции, +0,5 п.п. за покупки от 30 тыс ₽/мес для уровней "
              "1–3; мин. сумма 100 тыс ₽, сроки 1 мес–3 года). Накопительный "
              "счёт «Премиум» до 13%. Ставки на дату проверки, меняются вслед "
              "за ключевой ставкой ЦБ"),
    "source_url": _SBER_VKLAD,
    "date_checked": _CHECKED,
    "note": "Максимум 13,8% — новые деньги, 3–4 мес, проценты в конце срока",
}

_FIRST_DEPOSITS = {
    "value": ("Линейка премиальных вкладов: СберВклад Премиум, «Лучший % Премиум», "
              "«Управляй Премиум», накопительный счёт «Премиум». Позиционирование "
              "«самые высокие ставки в СберБанке»; конкретные надбавки для уровней "
              "4–5 публикуются в PDF-тарифах, на продуктовой странице цифр нет. "
              "Ориентир — вклад «Премиум» до 13,8% (доступен и для СберПервого)"),
    "source_url": _SBER_FIRST_VKLADY,
    "date_checked": _CHECKED,
    "note": "Ставки меняются вслед за КС ЦБ — сверять на дату скана",
}

_SBER_FIRST_4_ECOSYSTEM = {
    "value": (
        "СберПрайм, Okko «Премиум» с Amediateka; "
        "Обмен 10 бонусов = 8 ₽ с лимитом 12 500 Б в мес; "
        "Консьерж Aspire; "
        "Компенсация БЗ за границей по 3 тыс ₽ на 1 чел; "
        "Бизнес-зал Сбер в SVO"
    ),
    "source_url": f"{_PBI_SBER}/4",
    "date_checked": "2026-07-14",
    "note": "Закреплено из блока «Другие привилегии» для уровня 4; официальный сайт отдавал битую кодировку.",
}

_SBER_FIRST_5_ECOSYSTEM = {
    "value": (
        "СберПрайм, Okko «Премиум» с Amediateka; "
        "Обмен 10 бонусов = 8 ₽ с лимитом 12 500 Б в мес; "
        "Консьерж Aspire; "
        "Компенсация БЗ за границей по 3 тыс ₽ на 1 чел; "
        "Бизнес-зал Сбер в SVO"
    ),
    "source_url": f"{_PBI_SBER}/5",
    "date_checked": "2026-07-14",
    "note": "Закреплено из блока «Другие привилегии» для уровня 5; официальный сайт отдавал битую кодировку.",
}

_SBER_PRIVATE_ECOSYSTEM = {
    "value": (
        "СберПрайм, Okko «Премиум» с Amediateka; "
        "Компенсация ВИП-залов до 5 тыс ₽ в одном городе; "
        "Компенсация БЗ до 5 тыс ₽, если нет в списке; "
        "Бизнес-зал Сбер в SVO без ограничений; "
        "3 консультации в год СберПраво; "
        "Консьерж Pb Service; "
        "Сбер Мобайл: звонки + 5 ГБ в месяц; "
        "Обмен 10 бонусов = 8 ₽ с лимитом 12 500 Б в мес"
    ),
    "source_url": f"{_PBI_SBER}/6",
    "date_checked": "2026-07-14",
    "note": "Закреплено из блока «Другие привилегии» для уровня 6.",
}

CURATED_FACTS = {
    # ---------- СберПремьер (уровни 1–3) ----------
    "sber_premier_1": {
        "concierge": _PREMIER_CONCIERGE,
        "cashback": {
            "value": ("Кэшбэк до 10% бонусами СберСпасибо в 5 категориях на выбор "
                      "ежемесячно, суммарный лимит 20 000 бонусов за расчётный "
                      "период. Повышенный курс обмена бонусов на уровне 1 не указан"),
            "source_url": _SBER_PREMIER,
            "date_checked": _CHECKED,
            "note": ("«10% по 6 категориям» из вводной относится к уровню Private "
                     "(6 категорий, безлимит), у Премьера/Первого — 5 категорий"),
        },
        "card_terms": _PREMIER_CARD,
        "transfers_payments": _SBER_TRANSFER_LEVELS["sber_premier_1"],
        "cash_withdrawal": _fact_from(
            _PREMIER_CARD, "Снятие наличных до 1 млн ₽ в день"),
        "deposits": _PREMIER_DEPOSITS,
    },
    "sber_premier_2": {
        "concierge": _PREMIER_CONCIERGE,
        "cashback": {
            "value": ("Кэшбэк до 10% бонусами СберСпасибо в 5 категориях на выбор "
                      "ежемесячно, лимит 20 000 бонусов за расчётный период. "
                      "Повышенный курс обмена бонусов на уровне 2 не указан"),
            "source_url": _SBER_PREMIER,
            "date_checked": _CHECKED,
            "note": "5 категорий (6 — только на Private)",
        },
        "card_terms": _PREMIER_CARD,
        "transfers_payments": _SBER_TRANSFER_LEVELS["sber_premier_2"],
        "cash_withdrawal": _fact_from(
            _PREMIER_CARD, "Снятие наличных до 1 млн ₽ в день"),
        "deposits": _PREMIER_DEPOSITS,
    },
    "sber_premier_3": {
        "concierge": _PREMIER_CONCIERGE,
        "cashback": {
            "value": ("Кэшбэк до 10% бонусами СберСпасибо в 5 категориях на выбор "
                      "ежемесячно, лимит 20 000 бонусов за расчётный период. "
                      "Обмен бонусов по повышенному курсу: 10 бонусов = 7 ₽, "
                      "лимит 12 500 бонусов/мес"),
            "source_url": f"{_PBI_SBER}/3",
            "date_checked": _CHECKED,
            "note": "Курс обмена — по ПБИ; ставка/категории — sberbank.ru",
        },
        "card_terms": _PREMIER_CARD,
        "transfers_payments": _SBER_TRANSFER_LEVELS["sber_premier_3"],
        "cash_withdrawal": _fact_from(
            _PREMIER_CARD, "Снятие наличных до 1 млн ₽ в день"),
        "deposits": _PREMIER_DEPOSITS,
    },
    # ---------- СберПервый (уровни 4–5) ----------
    "sber_first_4": {
        "concierge": {
            "value": ("Есть — консьерж Aspire («поддержка профессионального "
                      "ассистента во всех сферах жизни»). Также: безлимитные "
                      "бизнес-залы, компенсация БЗ за границей 3 тыс ₽/чел, "
                      "СберПрайм+ (Okko Премиум с Amediateka)"),
            "source_url": _SBER_FIRST,
            "date_checked": _CHECKED,
            "note": "Название Aspire — по ПБИ /sber/4; официальный сайт "
                    "описывает сервис без бренда",
        },
        "cashback": {
            "value": ("Кэшбэк до 10% бонусами Спасибо в 5 категориях ежемесячно. "
                      "Обмен бонусов по повышенному курсу 1 бонус = 0,8 ₽ "
                      "(10 Б = 8 ₽), до 10 000 ₽/мес (лимит 12 500 Б/мес)"),
            "source_url": _SBER_FIRST,
            "date_checked": _CHECKED,
            "note": "Курс подтверждён двумя источниками: sberbank.ru/first и ПБИ",
        },
        "card_terms": _FIRST_CARD,
        "transfers_payments": _SBER_TRANSFER_LEVELS["sber_first_4"],
        "cash_withdrawal": _fact_from(
            _FIRST_CARD, "Снятие наличных до 2 млн ₽ в день"),
        "deposits": _FIRST_DEPOSITS,
        "ecosystem": _SBER_FIRST_4_ECOSYSTEM,
    },
    "sber_first_5": {
        "concierge": {
            "value": "Есть — консьерж Aspire (как на уровне 4)",
            "source_url": _SBER_FIRST,
            "date_checked": _CHECKED,
            "note": "См. sber_first_4",
        },
        "cashback": {
            "value": ("Кэшбэк до 10% бонусами Спасибо в 5 категориях. Обмен "
                      "10 бонусов = 8 ₽, лимит 12 500 Б/мес"),
            "source_url": _SBER_FIRST,
            "date_checked": _CHECKED,
            "note": "",
        },
        "card_terms": _FIRST_CARD,
        "transfers_payments": _SBER_TRANSFER_LEVELS["sber_first_5"],
        "cash_withdrawal": _fact_from(
            _FIRST_CARD, "Снятие наличных до 2 млн ₽ в день"),
        "deposits": _FIRST_DEPOSITS,
        "ecosystem": _SBER_FIRST_5_ECOSYSTEM,
    },
    # ---------- Sber Private Banking (уровень 6) ----------
    "sber_private_6": {
        "concierge": {
            "value": ("Есть — консьерж Pb Service (отдельный private-консьерж, "
                      "НЕ Aspire). Дополнительно: 3 консультации в год СберПраво, "
                      "Сбер Мобайл (звонки + 5 ГБ/мес), бизнес-зал Сбер в SVO "
                      "без ограничений"),
            "source_url": f"{_PBI_SBER}/6",
            "date_checked": _CHECKED,
            "note": ("Вопрос из вводной «тот же Aspire или отдельный?» — отдельный: "
                     "Pb Service. sberpb.ru — JS-сайт, детально мандат сервиса "
                     "на нём не опубликован"),
        },
        "cashback": {
            "value": ("Кэшбэк до 10% бонусами в 6 категориях на выбор, бонусы "
                      "без лимита (безлимитное начисление — отличие уровня "
                      "Private). Обмен бонусов Спасибо по повышенному курсу: "
                      "10 бонусов = 8 ₽, лимит обмена 12 500 Б/мес"),
            "source_url": _SBER_CARD,
            "date_checked": _CHECKED,
            "note": ("Это источник цифры «10% по 6 категориям» из вводной — "
                     "она относится именно к Private, не к Премьеру/Первому. "
                     "Курс обмена — по ПБИ /sber/6"),
        },
        "card_terms": _PRIVATE_CARD,
        "transfers_payments": _SBER_TRANSFER_LEVELS["sber_private_6"],
        "cash_withdrawal": _fact_from(
            _PRIVATE_CARD, "Снятие наличных до 3 млн ₽ в день"),
        "deposits": _FIRST_DEPOSITS,
        "ecosystem": _SBER_PRIVATE_ECOSYSTEM,
    },
}

for _sber_tier_id in _SBER_TIER_NUMBERS:
    CURATED_FACTS[_sber_tier_id].update(
        _sber_operation_facts(_sber_tier_id)
    )
    CURATED_FACTS[_sber_tier_id].update(
        _sber_insurance_facts(_sber_tier_id)
    )
    CURATED_FACTS[_sber_tier_id].update(
        _sber_option_and_service_facts(_sber_tier_id)
    )


# ============================================================================
# КОНКУРЕНТЫ — целевое дозаполнение пустых полей (2026-07-02).
# Значение «— (…)» = услуга отсутствует по официальным условиям тира
# (НЕ путать с «не найдено» — то уходит в лист «Требует ручной проверки»).
# ============================================================================

def _fact(value, url, note="", date_checked=None):
    return {"value": value, "source_url": url,
            "date_checked": date_checked or _CHECKED, "note": note}


def _free_on_conditions(pbi_url):
    return _fact("0 ₽ — бесплатно при выполнении условий уровня (остаток/траты/"
                 "акции определяют сам уровень, отдельная плата не предусмотрена)",
                 pbi_url, "Выведено из условий входа уровня (ПБИ)")


# ---------- Т-Банк ----------
_TBANK_PREMIUM = "https://www.tbank.ru/tinkoff-premium/"
_TBANK_SAVINGS = "https://www.tbank.ru/savings/saving-account/"
_TBANK_PRIVATE_BANKING = "https://www.tbank.ru/private/banking-services/"
_TBANK_PREMIUM_ACCESS = (
    "https://www.tbank.ru/bank/help/general/premium/access/what-is/"
)
_TBANK_PREMIUM_TERMS = (
    "https://www.tbank.ru/bank/help/general/premium/access/terms/"
)
_TBANK_SERVICES = "https://www.tbank.ru/bank/help/general/premium/services/"
_TBANK_CARD = ("https://www.tbank.ru/tinkoff-premium/cards/debit-cards/"
               "tinkoff-black-premium/")
_TBANK_PREMIUM_TARIFF = (
    "https://cdn.tbank.ru/static/documents/docs-terms-of-service-premium.pdf")
_TBANK_PRIVATE_TARIFF = (
    "https://cdn.tbank.ru/static/documents/docs-terms-of-service-private.pdf")

_TBANK_PREMIUM_TRANSFERS = _fact(
    "Лимит бесплатных переводов с расчётной карты Т-Банка на карту другого "
    "банка через сервисы Т-Банка — 100 000 ₽ в расчётном периоде по всем "
    "счетам. Лимит бесплатных переводов с кредитной карты: Bronze — "
    "150 000 ₽, Silver/Gold/Diamond — 200 000 ₽ в расчётном периоде",
    _TBANK_PREMIUM_TARIFF,
    "Официальные условия сервиса Premium, раздел «Тарифы Сервиса»")

_TBANK_PREMIUM_CASH_WITHDRAWAL = _fact(
    "Снятие наличных по расчётным картам: в банкоматах Т-Банка — бесплатно; "
    "в других банкоматах — бесплатно в расчётном периоде в 2 раза больше "
    "относительно суммы, указанной в тарифе карты",
    _TBANK_PREMIUM_TARIFF,
    "Официальные условия сервиса Premium, раздел «Тарифы Сервиса»")

_TBANK_PREMIUM_SUPREME = _fact(
    "Карта может быть переключена с «МИР (Продвинутая)» на Mir Supreme при "
    "активном сервисе Premium 32 дня подряд и покупках от 137 000 ₽ за "
    "последние три календарных месяца",
    _TBANK_PREMIUM_TARIFF,
    "Официальные условия сервиса Premium, пункт 6.8")

_TBANK_BRONZE_ENTRY = _fact(
    "Premium Bronze доступен любому клиенту за 2 990 ₽ в месяц",
    _TBANK_PREMIUM_TERMS,
    "Официальная справка Т-Банка: у Bronze нет условия входа через акции; "
    "вариант «5 000 акций» из PBI не применяется",
    date_checked="2026-07-23")

_TBANK_BRONZE_POSITIONING = _fact(
    "Premium Bronze — платный базовый уровень сервиса Premium, доступный "
    "любому клиенту Т-Банка",
    _TBANK_PREMIUM_TERMS,
    "Официальная справка Т-Банка; условие через акции отсутствует",
    date_checked="2026-07-23")

_TBANK_BRONZE_SERVICE_COST = _fact(
    "2 990 ₽ в месяц",
    _TBANK_PREMIUM_TERMS,
    "Официальная справка Т-Банка, стоимость Premium Bronze",
    date_checked="2026-07-23")

_TBANK_SILVER_ENTRY = _fact(
    "3 млн ₽ на счетах; или 1 млн ₽ на счетах и траты 200 тыс ₽ в месяц; "
    "или зарплата 400 тыс ₽ в текущем месяце или в среднем за три "
    "предыдущих календарных месяца",
    _TBANK_PREMIUM_ACCESS,
    "Официальная справка Т-Банка, условия бесплатного уровня Premium Silver",
    date_checked="2026-07-21")

_TBANK_PRIVATE_TRANSFERS = _fact(
    "Лимит бесплатных переводов с расчётной карты Т-Банка на карту другого "
    "банка через сервисы Т-Банка — 500 000 ₽ в расчётном периоде по всем "
    "счетам. Лимит бесплатных переводов с кредитной карты Т-Банка — "
    "500 000 ₽ в расчётном периоде по всем кредитным картам, кроме тарифных "
    "планов кредитных карт из линейки 11.X",
    _TBANK_PRIVATE_TARIFF,
    "Официальные условия сервиса Private, раздел «Тарифы Сервиса»")

_TBANK_PRIVATE_CASH_WITHDRAWAL = _fact(
    "Снятие наличных по расчётным картам: в банкоматах Т-Банка — бесплатно; "
    "в других банкоматах — бесплатно в расчётном периоде в 10 раз больше "
    "относительно суммы, указанной в тарифе карты в рублях РФ, или в 2 раза "
    "больше относительно суммы, указанной в тарифе карты в иностранной валюте, "
    "без ограничения по минимальной сумме операции",
    _TBANK_PRIVATE_TARIFF,
    "Официальные условия сервиса Private, раздел «Тарифы Сервиса»")

_TBANK_PRIVATE_SUPREME = _fact(
    "Карта может быть переключена с «МИР (Продвинутая)» на Mir Supreme при "
    "активном сервисе Private 32 дня подряд и покупках от 137 000 ₽ за "
    "последние три календарных месяца; обратное переключение — при отключении "
    "сервиса Private",
    _TBANK_PRIVATE_TARIFF,
    "Официальные условия сервиса Private, пункт 4.6")


def _tbank_private_restaurants(pbi_url):
    return _fact(
        "Безлимитные компенсации: до 5 000 ₽ на один посадочный талон в "
        "России и до 50 $ за границей. Только в ресторане аэропорта вылета, "
        "не более чем за сутки до вылета; компенсация по кнопке в приложении "
        "или через чат, чек разбивать не требуется",
        pbi_url,
        "Лимит 5 000 ₽ применяется к одному посадочному талону, а не к месяцу; "
        "месячного и годового денежного лимита источник не указывает",
        date_checked="2026-07-21")

_TBANK_SHARED = {
    "concierge": _fact(
        "Есть — круглосуточная консьерж-служба с личным ассистентом "
        "(бронирования, билеты, подбор специалистов) + премиальная "
        "поддержка выделенной командой",
        _TBANK_PREMIUM,
        "Ложное «нет» из автопарсинга ПБИ исправлено по официальному сайту"),
    "cashback": _fact(
        "Базовая программа кэшбэка Т-Банка (1–30% по категориям и партнёрам); "
        "с Premium лимит кэшбэка повышен до 60 000 ₽/мес по картам Black Premium",
        _TBANK_PREMIUM,
        "Лимит без Premium — 30 000 ₽/мес"),
    "card_terms": _fact(
        "Металлическая дебетовая карта Black Premium для клиентов Premium. "
        "Снятие наличных: в банкоматах Т-Банка без ограничений, в чужих — "
        "до 500 000 ₽ за расчётный период без комиссии",
        _TBANK_CARD, ""),
    "auto": _fact(
        "— (автоуслуги не входят в состав сервиса Premium по официальному "
        "перечню услуг)",
        _TBANK_SERVICES, "Отсутствие по официальным условиям"),
    "addons": _fact(
        "— (докупаемых опций нет: Premium — единая подписка, уровни статуса "
        "определяются остатком/активами)",
        _TBANK_PREMIUM, "Отсутствие по официальным условиям"),
}

_TBANK_PREMIUM_SHARED = {
    **_TBANK_SHARED,
    "deposits": _fact(
        "Накопительный счёт — 9% годовых с сервисом Premium",
        _TBANK_SAVINGS,
        "Официальная страница накопительного счёта: 9% с Premium, "
        "6% без подписки и премиального сервиса",
        date_checked="2026-07-23"),
    "transfers_payments": _TBANK_PREMIUM_TRANSFERS,
    "cash_withdrawal": _TBANK_PREMIUM_CASH_WITHDRAWAL,
    "supreme": _TBANK_PREMIUM_SUPREME,
}

_TBANK_PRIVATE_SHARED = {
    **_TBANK_SHARED,
    "deposits": _fact(
        "Накопительный счёт — 10% годовых с сервисом Private",
        _TBANK_PRIVATE_BANKING,
        "Официальная страница банковских услуг T-Private",
        date_checked="2026-07-23"),
    "transfers_payments": _TBANK_PRIVATE_TRANSFERS,
    "cash_withdrawal": _TBANK_PRIVATE_CASH_WITHDRAWAL,
    "supreme": _TBANK_PRIVATE_SUPREME,
}

# ---------- ВТБ (Привилегия, уровни 1–4) ----------
_VTB_SERVICES = "https://www.vtb.ru/privilegia/premialnye-servisy/"
_VTB_CARD = ("https://www.vtb.ru/privilegia/karty/debetovye/"
             "privilegiya-mir-supreme/")
_VTB_MAIN = "https://www.vtb.ru/privilegia/"
_VTB_UPDATE_2026 = "https://www.vtb.ru/promo/rsvtb-pv-2/"
_VTB_SBP = "https://www.vtb.ru/personal/online-servisy/perevody-sbp/"
_VTB_RKO_TARIFF = (
    "https://www.vtb.ru/media-files/vtb.ru/sitepages/tarify/"
    "chastnim-licam/t_rko.xlsx"
)
_VTB_TRANSFERS = "https://www.vtb.ru/personal/online-servisy/perevody/"
_VTB_CASH_QR = (
    "https://www.vtb.ru/personal/online-servisy/snyatie-nalichnyh-po-qr/"
)
_VTB_PRIVATE_CARDS = "https://private.vtb.ru/bankovskie-uslugi/karty/"
_VTB_PRIVATE_CASHBACK = "https://private.vtb.ru/bankovskie-uslugi/cashback/"
_VTB_PRIME_OPERATIONS_TARIFF = (
    "https://h.vtb.ru/projects/tbcv_dgto/files/prime_pictures/"
    "vtb_tarif_prime.pdf"
)
_VTB_CHECKED = "2026-07-15"
_VTB_UPDATE_CHECKED = "2026-07-28"

_VTB_PRIVILEGE_1_ENTRY = _fact(
    "3 990 ₽ в месяц; или траты 150 тыс ₽ в месяц; или зарплата 300 тыс ₽ "
    "в месяц; или зарплата 700 тыс ₽ суммарно за три полных последовательных "
    "календарных месяца; или 9 000 акций банка ВТБ",
    _VTB_MAIN,
    "Официальная страница ВТБ; добавлен отдельный трёхмесячный зарплатный "
    "критерий, не выделенный в PBI",
    date_checked="2026-07-21")

_VTB_CASHBACK = _fact(
    "Кэшбэк рублями по карте ВТБ «Привилегия Mir Supreme»: до 30 000 ₽ "
    "в месяц за покупки в выбранных категориях; 3 категории из 9 "
    "ежемесячно, плюс 1 категория для зарплатных клиентов; отдельные "
    "категории могут иметь собственные лимиты",
    _VTB_CARD,
    "Официальная страница карты ВТБ «Привилегия Mir Supreme»: кэшбэк "
    "рублями до 30 000 ₽, 3 категории из 9 + 1 для зарплатных клиентов",
    _VTB_CHECKED)

_VTB_PRIVILEGE_CASHBACK_2026 = _fact(
    "С 31 июля 2026 года — 5 категорий кэшбэка вместо 3; категории "
    "выбираются ежемесячно с 26-го числа в разделе «Расти с ВТБ», "
    "максимальный кэшбэк — до 30 000 ₽ в месяц. Первый выбор пяти "
    "категорий откроется 26 августа",
    _VTB_UPDATE_2026,
    "Официальный лендинг обновления ВТБ «Привилегия»; изменение относится "
    "к четырём уровням Привилегии, но не переносится на Prime+",
    date_checked=_VTB_UPDATE_CHECKED)

_VTB_LEVEL_ENTRIES_2026 = {
    "vtb_privilege_1": _fact(
        "Уровень «Изумруд» с 31 июля 2026 года: активы в ВТБ до 2,5 млн ₽ "
        "для Москвы и Московской области; до 2 млн ₽ для других регионов",
        _VTB_UPDATE_2026,
        "Первый уровень будет назначен 1 сентября по оценке периода "
        "31 июля — 30 августа",
        date_checked=_VTB_UPDATE_CHECKED),
    "vtb_privilege_2": _fact(
        "Уровень «Сапфир» с 31 июля 2026 года. Москва и Московская область: "
        "активы от 2,5 млн ₽ либо активы от 1,5 млн ₽ и покупки картой "
        "от 125 000 ₽ в месяц. Другие регионы: активы от 2 млн ₽ либо "
        "активы от 1,5 млн ₽ и покупки картой от 100 000 ₽ в месяц",
        _VTB_UPDATE_2026,
        "Первый уровень будет назначен 1 сентября по оценке периода "
        "31 июля — 30 августа",
        date_checked=_VTB_UPDATE_CHECKED),
    "vtb_privilege_3": _fact(
        "Уровень «Рубин» с 31 июля 2026 года: активы в ВТБ от 6 млн ₽ "
        "для Москвы, Московской области и других регионов",
        _VTB_UPDATE_2026,
        "Первый уровень будет назначен 1 сентября по оценке периода "
        "31 июля — 30 августа",
        date_checked=_VTB_UPDATE_CHECKED),
    "vtb_privilege_4": _fact(
        "Уровень «Бриллиант» с 31 июля 2026 года: активы в ВТБ от 10 млн ₽ "
        "для Москвы, Московской области и других регионов",
        _VTB_UPDATE_2026,
        "Первый уровень будет назначен 1 сентября по оценке периода "
        "31 июля — 30 августа",
        date_checked=_VTB_UPDATE_CHECKED),
}


def _vtb_preference_fields_2026(monthly_count: int) -> dict:
    timing = (
        "Новые правила действуют с 31 июля 2026 года; первое начисление "
        "по ним — 1 сентября за период 31 июля — 30 августа"
    )
    preference_word = "преференции" if monthly_count == 2 else "преференций"
    pool = (
        f"{monthly_count} {preference_word} в месяц из общего баланса; "
        "1 преференция = 1 использование выбранного сервиса"
    )
    return {
        "lounge_access": _fact(
            f"До {monthly_count} проходов в месяц, если направить весь общий "
            f"баланс ({pool}) на бизнес-залы. Более 900 бизнес-залов в "
            "аэропортах и на вокзалах через ON·PASS и ON·PASS PREMIUM",
            _VTB_UPDATE_2026,
            f"{timing}; проходы делят баланс с такси, ресторанами, упаковкой "
            "багажа и приоритетной регистрацией",
            date_checked=_VTB_UPDATE_CHECKED),
        "taxi": _fact(
            f"До {monthly_count} компенсаций поездок на такси в месяц; "
            "до 1 000 ₽ за один чек. Используется общий баланс: "
            f"{pool}; поездки делят его с другими сервисами",
            _VTB_UPDATE_2026,
            f"{timing}; отдельный годовой лимит на лендинге обновления "
            "не опубликован",
            date_checked=_VTB_UPDATE_CHECKED),
        "restaurants": _fact(
            f"До {monthly_count} компенсаций чеков в ресторанах аэропортов "
            "России в месяц; до 2 500 ₽ за один чек. Используется общий "
            f"баланс: {pool}; рестораны делят его с другими сервисами",
            _VTB_UPDATE_2026,
            f"{timing}; отдельный годовой лимит на лендинге обновления "
            "не опубликован",
            date_checked=_VTB_UPDATE_CHECKED),
        "selectable_options": _fact(
            "Преференции на выбор: бизнес-залы ON·PASS и ON·PASS PREMIUM | "
            "такси до 1 000 ₽ за чек | рестораны аэропортов РФ до 2 500 ₽ "
            "за чек | упаковка багажа | приоритетная регистрация в аэропорту",
            _VTB_UPDATE_2026,
            timing,
            date_checked=_VTB_UPDATE_CHECKED),
        "selection_rules": _fact(
            f"{pool}. Проверка условий — с последнего дня предыдущего месяца "
            "по предпоследний день текущего; начисление — 1-го числа; "
            "использовать преференции можно до конца месяца начисления",
            _VTB_UPDATE_2026,
            timing,
            date_checked=_VTB_UPDATE_CHECKED),
        "last_change_date": _fact(
            "31.07.2026 — запуск уровней «Расти с ВТБ»; первое назначение "
            "уровня и начисление преференций — 01.09.2026",
            _VTB_UPDATE_2026,
            timing,
            date_checked=_VTB_UPDATE_CHECKED),
    }

_VTB_DEPOSITS = _fact(
    "Накопительный ВТБ-Счёт до 13,6% годовых; повышенная ставка за "
    "покупки по дебетовой карте, проценты начисляются на минимальный / "
    "ежедневный остаток",
    _VTB_MAIN,
    "Официальная страница ВТБ «Привилегия»: доходность по новому "
    "накопительному ВТБ-Счёту до 13,6%",
    _VTB_CHECKED)

_VTB_PRIVILEGE_TRANSFERS = _fact(
    "Переводы через СБП на счета третьих лиц — без комиссии: до 1 млн ₽ "
    "за один перевод и в сутки, до 10 млн ₽ в месяц. Переводы через СБП "
    "на свои счета в других банках — без комиссии до 30 млн ₽ в месяц",
    _VTB_SBP,
    "Официальная страница СБП ВТБ: отдельная стоимость для владельцев ПУ "
    "«Привилегия Мультикарта» и операционные лимиты. Перепроверено по "
    f"официальному сборнику РКО {_VTB_RKO_TARIFF}: раздел 3, пп. "
    "3.1.4.1.1 и 3.1.4.2.3",
    date_checked="2026-07-24")

_VTB_PRIME_TRANSFERS = _fact(
    "Переводы внутри ВТБ — до 1 млн ₽ в сутки, без ограничения в месяц. "
    "Через СБП на счета третьих лиц — до 1 млн ₽ в сутки и до 10 млн ₽ "
    "в месяц. По реквизитам в другие банки на счета третьих лиц — до "
    "10 млн ₽ в сутки и до 10 млн ₽ в месяц. На собственные счета в "
    "других банках — бесплатно до 30 млн ₽ в месяц",
    _VTB_TRANSFERS,
    "Официальная страница ВТБ прямо называет ПУ «Прайм+» для лимитов "
    "СБП и переводов по реквизитам; лимиты действуют совокупно по всем "
    "дебетовым картам клиента",
    date_checked="2026-08-05")

_VTB_PRIME_CASH_WITHDRAWAL = _fact(
    "Снятие наличных по дебетовым картам Прайм+: до 1,2 млн ₽ в сутки "
    "и до 37,2 млн ₽ в месяц совокупно по всем дебетовым картам. В "
    "банкоматах ВТБ и банков группы — без комиссии; в банкоматах других "
    "банков — 1%, минимум 300 ₽ / 6 $ / 6 €. Для снятия в банкомате ВТБ "
    "по QR действует отдельный технический лимит 500 000 ₽ в сутки",
    _VTB_PRIME_OPERATIONS_TARIFF,
    "Официальный тариф для владельцев ПУ «Прайм+», раздел 8, пункты "
    "8.1 и 8.3. Технический QR-лимит дополнительно подтверждён текущей "
    f"страницей ВТБ {_VTB_CASH_QR}",
    date_checked="2026-08-05")

_VTB_PRIME_CASHBACK = _fact(
    "Кешбэк рублями до 100 000 ₽ в месяц: 3 категории на выбор из 10, "
    "ещё 1 категория — при получении зарплаты на карту ВТБ. Если категории "
    "не выбраны, начисляется 1,5% на все покупки. Новым клиентам в первый "
    "месяц — 2% на все покупки; кешбэк начисляется за каждые 100 ₽ и "
    "зачисляется рублями на мастер-счёт до 20-го числа следующего месяца",
    _VTB_PRIVATE_CASHBACK,
    "Официальная страница ВТБ Private Banking для дебетовой карты пакета "
    "Прайм+: лимит до 100 000 ₽ в месяц и правила выбора категорий. "
    f"Связь карты с пакетом Прайм+ подтверждена карточным каталогом "
    f"{_VTB_PRIVATE_CARDS}",
    date_checked="2026-08-05")

_VTB_PRIME_OPERATION_COMPONENTS = {
    "internal_transfers": _scoped_fact(
        "Переводы физическим лицам внутри ВТБ: до 1 млн ₽ в сутки; "
        "месячный лимит не установлен",
        _VTB_TRANSFERS,
        "Официальные лимиты переводов ВТБ для ПУ «Прайм+»",
        "Внутри ВТБ — до 1 млн ₽ в сутки, без ограничения в месяц",
        recipient="физическое лицо — клиент ВТБ",
        channel="ВТБ Онлайн",
        technical_limit="1 000 000 ₽ в сутки",
        period="сутки",
        date_checked="2026-08-05",
    ),
    "sbp_transfers": _scoped_fact(
        "Переводы через СБП на счета третьих лиц: до 1 млн ₽ в сутки "
        "и до 10 млн ₽ в месяц",
        _VTB_TRANSFERS,
        "Официальные лимиты переводов ВТБ для ПУ «Прайм+»",
        "Прайм+: 1 млн ₽ в сутки и 10 млн ₽ в месяц через СБП",
        recipient="третье лицо",
        channel="СБП",
        free_limit="10 000 000 ₽",
        technical_limit="1 000 000 ₽ в сутки",
        period="месяц",
        over_limit_fee="не опубликована",
        date_checked="2026-08-05",
    ),
    "interbank_transfers_remote": _scoped_fact(
        "Переводы по реквизитам в другие банки на счета третьих лиц: "
        "до 10 млн ₽ в сутки и до 10 млн ₽ в месяц",
        _VTB_TRANSFERS,
        "Официальные лимиты переводов ВТБ для ПУ «Прайм+»",
        "Прайм+: 10 млн ₽ в сутки и 10 млн ₽ в месяц по реквизитам",
        recipient="третье лицо в другом банке",
        channel="ВТБ Онлайн, перевод по реквизитам",
        free_limit="10 000 000 ₽",
        technical_limit="10 000 000 ₽ в сутки",
        period="месяц",
        date_checked="2026-08-05",
    ),
    "atm_free_withdrawal": _scoped_fact(
        "Снятие наличных в банкоматах ВТБ и банков группы — без комиссии "
        "в пределах операционных лимитов",
        _VTB_PRIME_OPERATIONS_TARIFF,
        "Тариф для владельцев ПУ «Прайм+»",
        "Раздел 8, п. 8.1: выдача наличных в ВТБ и банках группы без комиссии",
        channel="банкоматы ВТБ и банков группы",
        free_limit="без опубликованного отдельного комиссионного лимита",
        technical_limit="1 200 000 ₽ в сутки; 37 200 000 ₽ в месяц",
        date_checked="2026-08-05",
    ),
    "cash_monthly_operational_limit": _scoped_fact(
        "До 37,2 млн ₽ в месяц совокупно по всем дебетовым картам Прайм+",
        _VTB_PRIME_OPERATIONS_TARIFF,
        "Тариф для владельцев ПУ «Прайм+»",
        "Раздел 8, п. 8.3: 37 200 000 ₽ в месяц",
        channel="выдача наличных по дебетовым картам",
        technical_limit="37 200 000 ₽",
        period="месяц",
        date_checked="2026-08-05",
    ),
    "atm_daily_limit": _scoped_fact(
        "До 1,2 млн ₽ в сутки совокупно по всем дебетовым картам Прайм+",
        _VTB_PRIME_OPERATIONS_TARIFF,
        "Тариф для владельцев ПУ «Прайм+»",
        "Раздел 8, п. 8.3: 1 200 000 ₽ в сутки",
        channel="банкоматы, дебетовые карты",
        technical_limit="1 200 000 ₽",
        period="сутки",
        note=(
            "Для снятия по QR действует отдельный технический лимит "
            f"500 000 ₽ в сутки: {_VTB_CASH_QR}"
        ),
        date_checked="2026-08-05",
    ),
}

_VTB_PRIVILEGE_SHARED = {
    "concierge": _fact(
        "Есть — круглосуточный консьерж-сервис, бесплатно для всех клиентов "
        "«Привилегии»: юридическая, деловая и медицинская поддержка, "
        "путешествия/досуг, детский консьерж",
        _VTB_SERVICES, ""),
    "cashback": _VTB_PRIVILEGE_CASHBACK_2026,
    "deposits": _VTB_DEPOSITS,
    "transfers_payments": _VTB_PRIVILEGE_TRANSFERS,
    "card_terms": _fact(
        "Карта «Привилегия Mir Supreme» (есть цифровая версия). Снятие без "
        "комиссии в банкоматах ВТБ и партнёров группы: до 350 000 ₽/день, "
        "до 2 млн ₽/мес",
        _VTB_CARD, ""),
    "cash_withdrawal": _fact(
        "Снятие без комиссии в банкоматах ВТБ и партнёров группы: "
        "до 350 000 ₽ в день, до 2 млн ₽ в месяц",
        _VTB_CARD, ""),
    "supreme": _fact(
        "Карта «Привилегия Mir Supreme»; есть цифровая версия",
        _VTB_CARD, ""),
    "auto": _fact(
        "Есть — «Помощь на дорогах»: эвакуатор, техническая и юридическая "
        "поддержка (для поездок на личном автомобиле)",
        _VTB_SERVICES, ""),
}

_VTB_PRIME_CONCIERGE = _fact(
    "АМА консьерж включён в пакет Прайм+ и доступен круглосуточно (24/7)",
    f"{_VTB_MAIN}; https://premiumbanking.info/vtb",
    "Страницы каждого уровня Прайм+ подтверждают АМА консьерж в составе "
    "привилегий; официальный сайт ВТБ описывает консьерж-сервис как помощь "
    "24/7",
    date_checked="2026-07-24")


def _vtb_prime_roadside(pbi_url: str) -> dict:
    return _fact(
        "Помощь на дорогах — консультации, подвоз топлива, эвакуатор",
        pbi_url,
        "Услуга опубликована для конкретного уровня Прайм+ в блоке "
        "«Другие привилегии» и нормализована в отдельное поле «Авто»",
        date_checked="2026-08-05")

# ---------- Озон Банк (Ultra) ----------
_OZON_PRODUCTS = "https://finance.ozon.ru/products"
_OZON_HELP = "https://help-bank.ozon.ru/individuals/bonuses-and-promotions"
_OZON_SAVINGS = "https://finance.ozon.ru/promo/savings/landing"
_OZON_DEPOSIT = "https://finance.ozon.ru/promo/deposit/landing"
_OZON_ULTRA_TARIFF = (
    "https://cdn1.ozone.ru/s3/ob-landing/static/docs/ecom/products/rules/"
    "2026.05.18%20-%20Тариф%20Ultra.pdf")

_OZON_DEPOSITS_FACT = _fact(
    "Накопительный счёт: до 15,1% годовых для новых клиентов до 2 месяцев, "
    "далее 12,5% при выполнении условий или 8% базовая ставка; вклад: "
    "до 13,5% годовых с ежемесячной капитализацией",
    _OZON_DEPOSIT,
    "Официальные страницы Ozon Банка: вклад до 13,5%; накопительный счёт "
    f"до 15,1% / 12,5% / 8% ({_OZON_SAVINGS})")

_OZON_ULTRA_TRANSFERS = _fact(
    "Пополнение через сервис пополнения по карте — бесплатно. Перевод "
    "денежных средств с использованием реквизитов карты через сторонние "
    "сервисы переводов при MCC 6538 — бесплатно; отдельный лимит по этой "
    "строке тарифа Ultra не указан",
    _OZON_ULTRA_TARIFF,
    "Официальный тариф Ultra, раздел операций по карте")

_OZON_ULTRA_SUPREME = _fact(
    "Карта категории Mir Supreme: пластиковая карта — выпуск/перевыпуск "
    "не более 1 карты бесплатно, обслуживание на период действия тарифа "
    "Ultra бесплатно; металлическая карта Mir Supreme — выпуск/перевыпуск "
    "не более 1 карты бесплатно, обслуживание на период действия тарифа "
    "Ultra бесплатно",
    _OZON_ULTRA_TARIFF,
    "Официальный тариф Ultra, блок «Карта категории Mir Supreme»")


def _ozon_ultra_cash_withdrawal(renewal_limit: str) -> dict:
    return _fact(
        "Выдача наличных по карте (снятие в банкоматах и т.д.) — бесплатно "
        "во всех банкоматах на территории РФ в рамках лимитов. При первичном "
        "подключении тарифа Ultra: 3 000 000 ₽ дневной / 3 000 000 ₽ месячный "
        f"лимит. При продлении тарифа Ultra: {renewal_limit} дневной / "
        f"{renewal_limit} месячный лимит",
        _OZON_ULTRA_TARIFF,
        "Официальный тариф Ultra, блок выдачи наличных")


_OZONBANK_SHARED = {
    "cashback": _fact(
        "Кэшбэк рублями: общий лимит для Ultra до 50 000 ₽/мес, до 10 "
        "категорий на выбор ежемесячно (лимит по одной категории 10 000 "
        "₽/мес), «1% на всё» в рамках общего лимита. Выплата реальными "
        "рублями (можно снять/перевести)",
        _OZON_HELP, ""),
    "card_terms": _fact(
        "Карта Ozon: для Ultra повышенный лимит на снятие наличных без "
        "комиссии в любых банкоматах и увеличенный лимит по счёту "
        "(конкретные суммы по уровням — в тарифах)",
        _OZON_PRODUCTS, ""),
    "transfers_payments": _OZON_ULTRA_TRANSFERS,
    "supreme": _OZON_ULTRA_SUPREME,
    "deposits": _OZON_DEPOSITS_FACT,
    "auto": _fact(
        "— (автоуслуги не входят в состав Ultra по официальному описанию "
        "программы: менеджер, поддержка, страховка, бизнес-залы, "
        "Ozon Premium, кэшбэк, лимиты)",
        _OZON_PRODUCTS, "Отсутствие по официальным условиям"),
    "concierge": _fact(
        "— (консьерж-сервис не заявлен в составе Ultra; вместо него — "
        "персональный менеджер и круглосуточная поддержка)",
        _OZON_PRODUCTS, "Отсутствие по официальному составу программы"),
    "addons": _fact(
        "— (докупаемых опций нет: уровни Ultra определяются остатком, "
        "подписка Ozon Premium уже включена)",
        _OZON_PRODUCTS, "Отсутствие по официальным условиям"),
}

# ---------- Газпромбанк ----------
_GPB_BONUS = "https://www.gazprombank.ru/premium/gazprom-bonus/"
_GPB_PREMIUM = "https://www.gazprombank.ru/premium/special/pu-premium/"
_GPB_PREMIUM_TARIFF = (
    "https://www.gazprombank.ru/upload/files/iblock/e97/"
    "h038o8uoge7g8zucvs80yz2sy8r9gejz/"
    "Tarif-Gazprombank.Premium-s-22.07.2026.pdf"
)
_GPB_PREMIUM_CASHBACK = (
    "https://www.gazprombank.ru/upload/files/iblock/474/"
    "102zjqtow8yzfiixl6bvikr0khvb3g51/"
    "Programma-loyalnosti-Banka-GPB-_AO_-po-nachisleniyu-keshbeka-"
    "_deystvuet-s-01.06.2026_.pdf"
)
_GPB_PRIVATE = "https://www.gazprombank.ru/private/"
_GPB_PRIVATE_PACKAGE = "https://www.gazprombank.ru/private/package-of-services/"
_GPB_PRIVATE_TRANSFERS = "https://www.gazprombank.ru/download/8091775/"
_GPB_PRIVATE_DEPOSITS_PAGE = "https://www.gazprombank.ru/private/deposits/"

_GPB_PREMIUM_1_ENTRY = _fact(
    "2,5 млн ₽ среднемесячных остатков; или траты 150 тыс ₽ в месяц; или "
    "1 млн ₽ среднемесячных остатков и траты 100 тыс ₽ в месяц; или "
    "зарплата 250 тыс ₽ и траты 50 тыс ₽ в месяц; или 2 990 ₽ в месяц",
    _GPB_BONUS,
    "Официальная страница условий бесплатности Газпром Бонус «Премиум»",
    date_checked="2026-07-21")

_GPB_PREMIUM_2_ENTRY = _fact(
    "6 млн ₽ среднемесячных остатков; или зарплата 750 тыс ₽ и траты "
    "100 тыс ₽ в месяц",
    "https://premiumbanking.info/gazprombank/2",
    "Точное условие уровня 2 подтверждено в профильном источнике; на "
    "официальной странице отдельная граница уровня не выделена",
    date_checked="2026-07-21")

_GPB_PREMIUM_DEPOSITS = _fact(
    "Надбавки по вкладам и накопительным счетам; доход по вкладам до 13,6%",
    _GPB_PREMIUM,
    "Официальная страница премиальной карты Газпромбанка")

_GPB_PREMIUM_TRANSFERS = _fact(
    "Переводы другим людям в любые банки РФ через СБП бесплатно до "
    "200 000 ₽ в месяц; переводы по номеру карты бесплатно до 50 000 ₽ "
    "в месяц. Общий технический лимит переводов через СБП или по номеру "
    "карты — до 10 млн ₽ в месяц",
    _GPB_PREMIUM,
    "Официальная страница премиальной карты Газпромбанка; бесплатные лимиты "
    "и общий операционный лимит показаны раздельно",
    date_checked="2026-07-24")

_GPB_PREMIUM_CASH = _fact(
    "При выполнении условий пакета снятие наличных без комиссии в банкоматах "
    "и пунктах выдачи наличных Газпромбанка и сторонних банков в России и "
    "за рубежом. Без выполнения условий: в Газпромбанке до 1 000 000 ₽ в "
    "месяц бесплатно; в сторонних банках России до 100 000 ₽ в месяц "
    "бесплатно; за рубежом — 450 ₽ за операцию",
    _GPB_PREMIUM_TARIFF,
    "Официальный тариф пакета с 22.07.2026, раздел III, пункты 4.1–4.4",
    date_checked="2026-07-24")

_GPB_PREMIUM_SUPREME = _fact(
    "Премиальная карта Газпромбанка на платёжной системе МИР Supreme; "
    "можно оформить до 4 дополнительных карт Mir Supreme бесплатно",
    _GPB_PREMIUM_TARIFF,
    "Официальный тариф пакета с 22.07.2026, разделы I и III",
    date_checked="2026-07-24")

_GPB_PREMIUM_CASHBACK_FACT = _fact(
    "Кэшбэк по программе Газпромбанка: до 6% в топ-категориях; с сервисом "
    "Газпром Бонус «Премиум» лимит до 40 000 бонусных баллов в месяц, "
    "1 бонусный балл = 1 ₽",
    _GPB_PREMIUM_CASHBACK,
    "Официальная программа лояльности с 01.06.2026 по 31.07.2026; таблица "
    "ставок и лимита для сервиса Газпром Бонус «Премиум»",
    date_checked="2026-07-24")

_GPB_PRIVATE_DEPOSITS = _fact(
    "Вклады Private: фиксированная ставка до 13,65% годовых; плавающая "
    "ставка до 16,85% годовых; накопительные счета до 13,30% годовых",
    _GPB_PRIVATE_DEPOSITS_PAGE,
    "Официальная страница вкладов и накопительных счетов Газпромбанк Private",
    date_checked="2026-07-24")

_GPB_PRIVATE_CASHBACK = _fact(
    "Кэшбэк в рублях: до 15% в основной категории; до 20% на здоровье или "
    "путешествия",
    _GPB_PRIVATE_PACKAGE,
    "Официальная страница пакета услуг Газпромбанк Private",
    date_checked="2026-07-24")

_GPB_PRIVATE_TRANSFERS_FACT = _fact(
    "Переводы со счёта внутри Газпромбанка — без комиссии; перевод со счёта "
    "физическому лицу в другой банк в пределах РФ и стран СНГ — 2% от суммы "
    "(минимум 200 ₽, максимум 1 500 ₽)",
    _GPB_PRIVATE_TRANSFERS,
    "Официальные тарифы переводов для клиентов сегментов «ВИП» и "
    "«Частно-банковский бизнес» с 01.06.2026",
    date_checked="2026-07-24")

_GPB_PRIVATE_PRIME = _fact(
    "Премиальная карта PRIME для клиентов Private; доступны пластиковая и "
    "моментальная карты, платёжный стикер и кольцо. По карте PRIME заявлены "
    "скидки до 30% в отелях и ресторанах",
    _GPB_PRIVATE_PACKAGE,
    "Официальная страница пакета услуг Газпромбанк Private",
    date_checked="2026-07-24")

# ---------- Альфа-Банк ----------
_ALFA_ONLY = "https://alfabank.ru/everyday/alfa-only/"
_ALFA_ONLY_DEPOSIT = "https://alfabank.ru/everyday/package/premium/vklad/"
_ALFA_ONLY_SUPREME_PAGE = (
    "https://alfabank.ru/everyday/debit-cards/mir-supreme-short/"
)
_ALFA_ONLY_LOYALTY_RULES = (
    "https://alfabank.servicecdn.ru/site-upload/27/2a/2366/prog_loyal_v46.pdf"
)
_ALFA_ACLUB_DEPOSIT_RATES = (
    "https://alfabank.servicecdn.ru/site-upload/06/72/2363/"
    "deposits_alfa_fin_club_26062026.pdf"
)
_ALFA_ONLY_SALARY = (
    "https://alfabank.ru/everyday/debit-cards/premium/zarplatnaya-karta/"
)
_ALFA_ACLUB_OFFICIAL = "https://alfabank.ru/a-club/"
_ALFA_CONCIERGE = "https://alfabank.ru/everyday/package/premium/konserzh-servis/"
_PBI_ACLUB = "https://premiumbanking.info/alfabank/5"
_ALFA_ONLY_CARD_TARIFFS = (
    "https://alfabank.servicecdn.ru/site-upload/c1/65/275/"
    "Tariffs_Alfa_Only_Card.pdf"
)
_ALFA_RETAIL_TARIFFS = (
    "https://alfabank.servicecdn.ru/site-upload/58/51/1869/"
    "all_tariffs_1082026.pdf"
)
_ALFA_CASH_LIMITS_OFFICIAL = (
    "https://alfabank.ru/help/articles/debit-cards/"
    "kak-snimat-dengi-s-karty-v-bankomate/"
)

_ALFA_CONCIERGE_FACT = _fact(
    "Есть — консьерж-сервис для клиентов Alfa Only (официальная страница "
    "«Консьерж-сервис — премиум-услуги для клиентов Alfa Only»)",
    _ALFA_CONCIERGE,
    "Ложное «нет» из автопарсинга ПБИ исправлено по официальному сайту")

_ALFA_ONLY_1_ENTRY = _fact(
    "2 990 ₽ в месяц; или зарплата 400 тыс ₽ в месяц через зарплатный "
    "сервис Альфа-Банка",
    _ALFA_ONLY_SALARY,
    "Официальная зарплатная страница подтверждает порог; привязка к "
    "базовому уровню Alfa Only подтверждена PBI",
    date_checked="2026-07-21")

_ALFA_ADDONS_ABSENT = _fact(
    "— (докупаемых опций нет: набор привилегий Alfa Only фиксированный — "
    "Lounge, металлическая карта, партнёрские программы, премиальный вклад, "
    "привилегии в ресторанах)",
    _ALFA_ONLY, "Отсутствие по официальному составу пакета")

_ALFA_ONLY_CASHBACK = _fact(
    "Кэшбэк по карте Alfa Only: 7% в 5 категориях либо 7% в 4 категориях "
    "+ 1% на всё; максимальный месячный лимит кэшбэка 30 000 ₽; "
    "суперкэшбэк до 100% как отдельная промо-механика; категории выбираются "
    "ежемесячно",
    _ALFA_ONLY_CARD_TARIFFS,
    "Официальный PDF Tariffs_Alfa_Only_Card.pdf; суперкэшбэк не трактуется "
    "как стандартный кэшбэк на все покупки")

_ALFA_ONLY_CARD_FREE = _fact(
    "Карта Alfa Only обслуживается бесплатно",
    _ALFA_ONLY_CARD_TARIFFS,
    "Официальный тарифный PDF по карте Alfa Only")

_ALFA_ONLY_TRANSFERS = _fact(
    "Через приложение Альфа-Банка или Альфа-Онлайн бесплатно: пополнение "
    "с карты другого банка, перевод клиенту банка, оплата коммунальных услуг, "
    "мобильной связи и штрафов ГИБДД, переводы по реквизитам счёта в рублях "
    "и валюте, перевод по номеру телефона. Перевод на карту другого банка "
    "по номеру карты — бесплатно до 100 000 ₽ в месяц; при превышении лимита "
    "и остатках до 12 млн ₽ — комиссия 1,95%, минимум 49 ₽; при остатках "
    "от 12 млн ₽ — без комиссии и ограничений",
    _ALFA_ONLY_CARD_TARIFFS,
    "Официальный тарифный PDF по карте Alfa Only, раздел 6")

_ALFA_ONLY_CASH_WITHDRAWAL = _fact(
    "Премиальные карты Alfa Only: снятие наличных — до 1,5 млн ₽ в сутки "
    "и до 3 млн ₽ в месяц; в банкоматах других банков по миру — бесплатно",
    f"{_ALFA_CASH_LIMITS_OFFICIAL}; {_ALFA_ONLY_CARD_TARIFFS}",
    "Числовые лимиты подтверждены официальной справочной статьёй "
    "Альфа-Банка; бесплатное снятие в сторонних банкоматах — официальным "
    "тарифным PDF Alfa Only, пункт 3. Фактический клиентский лимит общий "
    "для карт и счетов и может быть изменён банком; актуальное значение "
    "показывается в приложении",
    date_checked="2026-07-27")

_ALFA_ONLY_OPERATION_FACTS = {
    "internal_transfers": _scoped_fact(
        "Через приложение Альфа-Банка или Альфа-Онлайн перевод клиенту "
        "Альфа-Банка, в том числе юридическому лицу, — бесплатно",
        _ALFA_ONLY_CARD_TARIFFS,
        "Карта Alfa Only — тарифы",
        "6.2. Перевод клиенту банка, в том числе, юридическому лицу — Бесплатно",
        channel="Альфа-Мобайл / Альфа-Онлайн",
        free_limit="без опубликованного лимита",
        period="не указан",
        pdf_page="1",
        date_checked="2026-08-05",
    ),
    "interbank_transfers_remote": _scoped_fact(
        "Через приложение или Альфа-Онлайн перевод в другой банк по "
        "реквизитам счёта в рублях и иностранной валюте — бесплатно",
        _ALFA_ONLY_CARD_TARIFFS,
        "Карта Alfa Only — тарифы",
        "6.5–6.6. Перевод в другой банк по реквизитам счёта — Бесплатно",
        channel="Альфа-Мобайл / Альфа-Онлайн",
        free_limit="без опубликованного лимита",
        period="не указан",
        pdf_page="1",
        date_checked="2026-08-05",
    ),
    "card_to_card_transfers": _scoped_fact(
        "Перевод на карту другого банка по номеру карты — бесплатно до "
        "100 000 ₽ в месяц; сверх лимита при остатках до 12 млн ₽ — 1,95%, "
        "минимум 49 ₽; при остатках от 12 млн ₽ — без комиссии и ограничений",
        _ALFA_ONLY_CARD_TARIFFS,
        "Карта Alfa Only — тарифы",
        "6.4. Бесплатно до 100 000 ₽ в месяц; сверх — 1,95% мин. 49 ₽; "
        "от 12 млн ₽ без комиссии и ограничений",
        channel="Альфа-Мобайл / Альфа-Онлайн",
        free_limit="100 000 ₽ в месяц; без ограничений при остатках от 12 млн ₽",
        period="месяц",
        over_limit_fee="1,95%, минимум 49 ₽ при остатках до 12 млн ₽",
        pdf_page="1",
        date_checked="2026-08-05",
    ),
    "sbp_transfers": _scoped_fact(
        "Перевод в рублях в другой банк по номеру телефона через приложение "
        "или Альфа-Онлайн — бесплатно; отдельный лимит в описании карты не указан",
        _ALFA_ONLY_CARD_TARIFFS,
        "Карта Alfa Only — тарифы",
        "6.7. Перевод в рублях в другой банк по номеру телефона — Бесплатно",
        channel="Альфа-Мобайл / Альфа-Онлайн",
        free_limit="без опубликованного лимита",
        period="не указан",
        pdf_page="1",
        date_checked="2026-08-05",
    ),
    "legal_entity_payments": _scoped_fact(
        "Перевод клиенту Альфа-Банка, включая юридическое лицо, а также "
        "оплата коммунальных услуг, мобильной связи и штрафов ГИБДД — бесплатно",
        _ALFA_ONLY_CARD_TARIFFS,
        "Карта Alfa Only — тарифы",
        "6.2–6.3. Перевод юридическому лицу и платежи — Бесплатно",
        channel="Альфа-Мобайл / Альфа-Онлайн",
        free_limit="без опубликованного лимита",
        period="не указан",
        pdf_page="1",
        date_checked="2026-08-05",
    ),
    "atm_free_withdrawal": _scoped_fact(
        "Снятие наличных в банкоматах Альфа-Банка, банков-партнёров и "
        "других банков по миру — бесплатно",
        f"{_ALFA_CASH_LIMITS_OFFICIAL}; {_ALFA_ONLY_CARD_TARIFFS}",
        "Карта Alfa Only — тарифы и справка о снятии",
        "С премиальным платёжным средством снятие наличных бесплатное в любых банкоматах",
        channel="банкоматы Альфа-Банка и сторонних банков",
        free_limit="в пределах технических лимитов карты",
        period="сутки / месяц",
        pdf_page="1",
        date_checked="2026-08-05",
    ),
    "cash_monthly_operational_limit": _scoped_fact(
        "Максимум 3 000 000 ₽ в месяц по премиальным картам Alfa Only",
        _ALFA_CASH_LIMITS_OFFICIAL,
        "Как снимать деньги с карты в банкомате",
        "С премиальных карт ... в месяц — 3 млн ₽",
        channel="банкоматы",
        technical_limit="3 000 000 ₽",
        period="месяц",
        date_checked="2026-08-05",
    ),
    "atm_daily_limit": _scoped_fact(
        "Максимум 1 500 000 ₽ в сутки по премиальным картам Alfa Only",
        _ALFA_CASH_LIMITS_OFFICIAL,
        "Как снимать деньги с карты в банкомате",
        "С премиальных карт максимальная сумма снятия в сутки составляет 1,5 млн ₽",
        channel="банкоматы",
        technical_limit="1 500 000 ₽",
        period="сутки",
        date_checked="2026-08-05",
    ),
}

_ALFA_ACLUB_OPERATION_FACTS = {
    "transfers_payments": _scoped_fact(
        "A-Club: в стоимость пакета включены внутрибанковские переводы, "
        "рублёвые переводы через приложение и отделение, переводы в иностранной "
        "валюте через отделение и Альфа-Мобайл; СБП физлицам бесплатно до "
        "100 000 ₽ в месяц; платежи по СБП юридическим лицам и ИП — бесплатно",
        _ALFA_RETAIL_TARIFFS,
        "Тарифы Альфа-Банка по Договору КБО, редакция от 01.08.2026",
        "В стоимость Пакета услуг «А-Клуб» включены стоимости переводов; "
        "не установлена плата за переводы, перечисленные на стр. 117–118",
        pdf_page="116–118",
        date_checked="2026-08-05",
    ),
    "internal_transfers": _scoped_fact(
        "Внутрибанковские переводы физическим и юридическим лицам на счета "
        "Альфа-Банка включены в стоимость пакета A-Club",
        _ALFA_RETAIL_TARIFFS,
        "Тарифы Альфа-Банка по Договору КБО, редакция от 01.08.2026",
        "внутрибанковского перевода ... в пользу физических и юридических лиц",
        channel="Альфа-Мобайл / Альфа-Клик / отделение",
        free_limit="без опубликованного лимита",
        period="не указан",
        pdf_page="117",
        date_checked="2026-08-05",
    ),
    "interbank_transfers_remote": _scoped_fact(
        "Переводы в рублях через Альфа-Мобайл/Альфа-Клик и переводы в "
        "иностранной валюте через Альфа-Мобайл на основании проекта в чате "
        "включены в стоимость A-Club; трансграничные рублёвые переводы исключены",
        _ALFA_RETAIL_TARIFFS,
        "Тарифы Альфа-Банка по Договору КБО, редакция от 01.08.2026",
        "переводов ... в валюте РФ ... через Интернет Банк / Альфа-Мобайл; "
        "переводов в иностранной валюте ... посредством Альфа-Мобайл",
        channel="Альфа-Мобайл / Альфа-Клик",
        free_limit="без опубликованного лимита; кроме трансграничных переводов в рублях",
        period="не указан",
        pdf_page="117",
        date_checked="2026-08-05",
    ),
    "interbank_transfers_office": _scoped_fact(
        "Переводы в рублях и иностранной валюте по поручению через отделение "
        "включены в стоимость пакета A-Club",
        _ALFA_RETAIL_TARIFFS,
        "Тарифы Альфа-Банка по Договору КБО, редакция от 01.08.2026",
        "переводов по поручениям ... в валюте РФ / иностранной валюте, "
        "поданным через Отделение",
        channel="отделение",
        free_limit="без опубликованного лимита",
        period="не указан",
        pdf_page="117",
        date_checked="2026-08-05",
    ),
    "sbp_transfers": _scoped_fact(
        "Переводы через СБП на счета физлиц в Альфа-Банке и других банках — "
        "бесплатно до 100 000 ₽ за календарный месяц; трансграничные переводы "
        "в рублях не входят",
        _ALFA_RETAIL_TARIFFS,
        "Тарифы Альфа-Банка по Договору КБО, редакция от 01.08.2026",
        "не установлена плата ... если общая сумма переводов не превышает "
        "100 000 рублей за календарный месяц",
        channel="Альфа-Мобайл / Альфа-Клик",
        free_limit="100 000 ₽",
        period="месяц",
        pdf_page="117–118",
        date_checked="2026-08-05",
    ),
    "legal_entity_payments": _scoped_fact(
        "Платежи по СБП в пользу юридических лиц и ИП, а также оплата товаров, "
        "работ и услуг по QR-коду/платёжной ссылке — бесплатно",
        _ALFA_RETAIL_TARIFFS,
        "Тарифы Альфа-Банка по Договору КБО, редакция от 01.08.2026",
        "не установлена плата ... в пользу юридических лиц и индивидуальных предпринимателей",
        channel="СБПэй / Альфа-Мобайл / Альфа-Клик",
        free_limit="без опубликованного лимита",
        period="не указан",
        pdf_page="118",
        date_checked="2026-08-05",
    ),
    "cash_withdrawal": _scoped_fact(
        "A-Club: снятие без конвертации в банкоматах и кассах Альфа-Банка, "
        "сторонних банкоматах и пунктах выдачи наличных — бесплатно; выдача "
        "наличных в отделении включена в пакет. При снятии с конвертацией в "
        "банкомате Альфа-Банка комиссия 1,5%",
        _ALFA_RETAIL_TARIFFS,
        "Тарифы Альфа-Банка по Договору КБО, редакция от 01.08.2026",
        "Для A-Club не установлены стоимости выдачи наличных без конвертации; "
        "с конвертацией — 1,5%",
        pdf_page="116, 118, 147",
        date_checked="2026-08-05",
    ),
    "atm_free_withdrawal": _scoped_fact(
        "Снятие без конвертации через банкоматы Альфа-Банка и сторонних банков, "
        "а также пункты выдачи наличных — бесплатно; опубликованный числовой "
        "лимит для A-Club в тарифе не указан",
        _ALFA_RETAIL_TARIFFS,
        "Тарифы Альфа-Банка по Договору КБО, редакция от 01.08.2026",
        "Для A-Club не установлены стоимости выдачи наличных ... через банкомат "
        "или пункт выдачи наличных стороннего банка",
        channel="банкоматы Альфа-Банка и сторонних банков / ПВН",
        free_limit="без опубликованного числового лимита",
        period="не указан",
        pdf_page="118",
        date_checked="2026-08-05",
    ),
}

_ALFA_ONLY_SUPREME = _fact(
    "Дебетовая Альфа-Карта МИР Supreme доступна клиентам Alfa Only",
    _ALFA_ONLY_SUPREME_PAGE,
    "Официальная страница заявки на дебетовую Альфа-Карту МИР Supreme; "
    "условие действует для сервиса Alfa Only на всех его уровнях",
    date_checked="2026-07-24")

_ALFA_ONLY_SIMPLE_PRIVE = _fact(
    "Сервис SimplePrivé: статус Silver, персональный менеджер и специальные "
    "условия в SimpleWine",
    _ALFA_ONLY_LOYALTY_RULES,
    "Официальные правила программы Alfa Only, п. 6.3: статус Silver доступен "
    "участникам всех уровней Alfa Only; точные скидки не добавлены, поскольку "
    "в правилах банка они не зафиксированы",
    date_checked="2026-07-24")


def _alfa_only_ecosystem(level: int, include_rbc: bool = False) -> dict:
    items = [
        "Консультации с юристом и бухгалтером",
        "Альфа-Мобайл — 10 ГБ, 300 минут и 30 SMS",
        "Саммари от Smart Reading",
    ]
    if include_rbc:
        items.append("Подписка РБК")
    items.extend([
        "Alfa Only Лаундж в SVO, терминал C",
        "Сервис SimplePrivé: статус Silver, персональный менеджер и "
        "специальные условия в SimpleWine",
    ])
    return _fact(
        " | ".join(items),
        f"https://premiumbanking.info/alfabank/{level}; "
        f"{_ALFA_ONLY_LOYALTY_RULES}",
        "Состав уровня — ПБИ; SimplePrivé Silver для всех уровней Alfa Only — "
        "официальные правила программы, п. 6.3",
        date_checked="2026-07-24",
    )

_ALFA_ONLY_DEPOSITS = _fact(
    "Премиум-вклад Alfa Only: до 13,8% годовых в рублях или до 4% годовых "
    "в юанях; минимальная сумма 10 000 ₽ или 500 ¥; срок от 2 месяцев до "
    "3 лет; с капитализацией процентов или без неё",
    _ALFA_ONLY_DEPOSIT,
    "Официальная продуктовая страница подтверждает условия для клиентов "
    "Alfa Only без разделения по уровням",
    date_checked="2026-07-21")

_ALFA_ACLUB_DEPOSITS = _fact(
    "Альфа-Вклад «Новые деньги» для А-Клуба: до 14% годовых с "
    "капитализацией; минимальная сумма 10 000 ₽",
    _ALFA_ACLUB_DEPOSIT_RATES,
    "Официальная таблица ставок А-Клуба, действует с 26 июня 2026 года",
    date_checked="2026-07-24")

_ALFA_ACLUB_SUPREME = _fact(
    "Доступны продукты МИР Supreme: кредитная Alfa Travel Мир Supreme и "
    "платёжные кольца с привилегиями Мир Supreme",
    _ALFA_ACLUB_OFFICIAL,
    "Текущая официальная страница А-Клуба, раздел «Платёжные аксессуары»",
    date_checked="2026-07-24")

# ---------- Райффайзен ----------
_RAIF_PREMIUM = "https://www.raiffeisen.ru/premium/"

_RAIF_ADDONS_ABSENT = _fact(
    "— (докупаемых опций нет: Premium — фиксированный пакет, различаются "
    "только способы бесплатного входа: плата/траты/остаток)",
    _RAIF_PREMIUM, "Отсутствие по официальным условиям")

_RAIF_PREMIUM_4_ECOSYSTEM = _fact(
    "Автоконсьерж | Сервис «Лучи»: медицинские онлайн-консультации, "
    "10 посещений по ДМС «Лучи» на тарифе «Бизнес» и компенсация чекапа "
    "за рубежом и чекап «Здоровый образ жизни» | Акция «Привилегии на "
    "выбор»: промокоды на 2 000 ₽ от Яндекс Еды, Яндекс Go и Детского "
    "Мира, безлимитные проходы в бизнес-залы, сертификаты на 7 000 ₽ "
    "в отдельные рестораны Москвы и Санкт-Петербурга",
    "https://premiumbanking.info/raiffeisen/4",
    "Профильный источник уровня 5 млн ₽, актуальность июль 2026; "
    "официальная страница Райффайзен не раскрывает состав акции по уровням",
    date_checked="2026-07-24")

# ---------- Инго Premium ----------
_INGO_PREMIUM = "https://ingobank.ru/premium/"
_INGO_PREMIUM_TARIFF = "https://cdn.ingos.ru/docs/cards/Tarif_7.pdf"

_INGO_ENTRY_CONDITIONS = _fact(
    "Премиальная карта доступна с платным обслуживанием либо бесплатно при "
    "выполнении одного из условий в течение расчётного периода: остатки на "
    "всех счетах от 1,5 млн ₽; остатки от 1 млн ₽ и покупки от 75 000 ₽; "
    "зачисления от 300 000 ₽ и покупки от 75 000 ₽",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф «Премиальная ИнгоКарта», пункты 1.3.1–1.3.4",
    date_checked="2026-07-28")

_INGO_SERVICE_COST = _fact(
    "Первый календарный месяц бесплатно; далее 0 ₽ при выполнении одного "
    "из условий бесплатности, иначе 2 500 ₽ в месяц",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф «Премиальная ИнгоКарта», пункты 1.2–1.3.4",
    date_checked="2026-07-28")

_INGO_LOUNGES = _fact(
    "Ежемесячный общий лимит с ресторанами: 2 привилегии в месяц при остатках от "
    "1,5 млн ₽ либо остатках от 1 млн ₽ и покупках от 75 000 ₽; "
    "15 привилегий в месяц при остатках от 5 млн ₽ либо остатках от 3 млн ₽ и "
    "покупках от 75 000 ₽. Одна привилегия — один проход ON PASS, один "
    "проход в премиальный бизнес-зал ON PASS Premium или одна скидка "
    "ON FOOD; услуга для каждого сопровождающего списывается отдельно",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, пункт 10.2 и примечание 12; общий лимит нельзя "
    "одновременно трактовать как отдельный лимит залов и ресторанов",
    date_checked="2026-07-28")

_INGO_RESTAURANTS = _fact(
    "Скидка в партнёрских ресторанах ON FOOD расходует общий месячный лимит "
    "привилегий с бизнес-залами: 2 привилегии в месяц при остатках от 1,5 млн ₽ "
    "либо от 1 млн ₽ и покупках от 75 000 ₽; 15 привилегий в месяц при остатках "
    "от 5 млн ₽ либо от 3 млн ₽ и покупках от 75 000 ₽. Одна скидка "
    "ON FOOD считается одной привилегией",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, пункт 10.2 и примечание 12; размер скидки в самом "
    "тарифе не указан",
    date_checked="2026-07-28")

_INGO_TAXI = _fact(
    "Компенсация 1 поездки на такси в месяц — до 1 500 Ингорублей "
    "(курс 1:1). Условия: остатки от 5 млн ₽ либо остатки от 3 млн ₽ и "
    "покупки от 75 000 ₽ в месяц; поездка должна быть оплачена картой "
    "Мир Supreme",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, пункт 10.3 и примечание 13; аренда автомобилей "
    "и каршеринг не входят",
    date_checked="2026-07-28")

_INGO_INSURANCE = _fact(
    "Страхование путешествующих: стандартная программа — бесплатно; "
    "расширенная программа — бесплатно при выполнении одного из условий "
    "в предыдущем месяце: остатки от 5 млн ₽ либо остатки от 3 млн ₽ и "
    "покупки от 75 000 ₽",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, пункт 10.1 и примечания 10–11; конкретные риски, "
    "страховая сумма и срок поездки в тарифе не раскрыты",
    date_checked="2026-07-28")

_INGO_CASHBACK = _fact(
    "Без подписки «ИНГО Премиум»: 5% за полисы Ингосстраха без лимита; "
    "5% в 3 выбранных категориях из 8 (до 1 500 Ингорублей на категорию); "
    "1,5–2% в топ-категории (до 1 500); 1% на всё; общий лимит "
    "15 000 Ингорублей в месяц. С подпиской: 10% за полисы Ингосстраха; "
    "7–10% в 4 выбранных категориях из 9 (до 3 000 на категорию); "
    "5% в топ-категории (до 3 000); 1,5% на всё; общий лимит "
    "20 000 Ингорублей в месяц",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, разделы 8–9 и примечание 9; цена подписки в этом "
    "документе не указана",
    date_checked="2026-07-28")

_INGO_CARD_TERMS = _fact(
    "Выпуск Премиальной ИнгоКарты — бесплатно. Первая дополнительная карта "
    "на срок действия основной — бесплатно, последующие — 2 500 ₽ в год",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, пункты 1.1 и 1.4",
    date_checked="2026-07-28")

_INGO_CASH_WITHDRAWAL = _fact(
    "Снятие наличных в банкоматах и пунктах выдачи Инго Банка и сторонних "
    "банков — без комиссии; лимиты: до 1 млн ₽ в день и до 3 млн ₽ в месяц",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, раздел 3 и примечание 2",
    date_checked="2026-07-28")

_INGO_TRANSFERS = _fact(
    "По номеру карты: до 50 000 ₽ в месяц бесплатно, далее 1,5% "
    "(минимум 50 ₽). СБП другим людям: до 150 000 ₽ в месяц без подписки "
    "и до 250 000 ₽ с подпиской «ИНГО Премиум», далее 0,5% "
    "(максимум 1 500 ₽); технический лимит — 750 000 ₽ за операцию/сутки "
    "без подписки и 900 000 ₽ с подпиской. Переводы на собственные счета "
    "в других банках — до 30 млн ₽ в месяц без комиссии",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, разделы 4 и 6, примечания 3, 4 и 7",
    date_checked="2026-07-28")

_INGO_SUPREME = _fact(
    "Премиальные привилегии бизнес-залов, ресторанов и компенсации такси "
    "предоставляются держателям карты категории Мир Supreme",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, пункт 10.2 и примечания 12–13",
    date_checked="2026-07-28")

_INGO_SELECTABLE = _fact(
    "В общем месячном лимите можно использовать привилегии на выбор: "
    "проход ON PASS, скидку ON FOOD или проход ON PASS Premium",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, примечание 12",
    date_checked="2026-07-28")

_INGO_SELECTION_RULES = _fact(
    "Доступно 2 либо 15 привилегий в месяц в зависимости от остатков и "
    "покупок; каждый проход или скидка списывает одну привилегию, а услуга "
    "для каждого сопровождающего учитывается отдельно",
    _INGO_PREMIUM_TARIFF,
    "Официальный тариф, примечание 12",
    date_checked="2026-07-28")

# ---------- Lifestyle ----------
_OZON_PREMIUM_DOCS = ("https://docs.ozon.ru/common/pravila-prodayoi-i-rekvizity/"
                      "usloviya-podpiski-na-ozon-premium/")
_WB_CLUB_NEWS = "https://oborot.ru/news/chto-takoe-wb-klub-razbiraemsya-chto-daet-podpiska-za-199-rublej-v-mesyac-pokupatelyam-wildberries-i222045.html"
_YANDEX_PLUS_SUPPORT = "https://yandex.ru/support/plus-ru/ru/cashback"

_COMPETITOR_FACTS = {
    # ----- Т-Банк -----
    "tbank_bronze": {
        **_TBANK_PREMIUM_SHARED,
        "positioning": _TBANK_BRONZE_POSITIONING,
        "entry_conditions": _TBANK_BRONZE_ENTRY,
        "service_cost": _TBANK_BRONZE_SERVICE_COST,
    },
    "tbank_silver": {**_TBANK_PREMIUM_SHARED,
                     "entry_conditions": _TBANK_SILVER_ENTRY,
                     "service_cost": _free_on_conditions(
                         "https://premiumbanking.info/tbank/2")},
    "tbank_gold": {**_TBANK_PREMIUM_SHARED,
                   "service_cost": _free_on_conditions(
                       "https://premiumbanking.info/tbank/3")},
    "tbank_diamond": {**_TBANK_PREMIUM_SHARED,
                      "service_cost": _free_on_conditions(
                          "https://premiumbanking.info/tbank/4")},
    "tbank_private_30": {**_TBANK_PRIVATE_SHARED,
                         "restaurants": _tbank_private_restaurants(
                             "https://premiumbanking.info/tbank/5"),
                         "service_cost": _free_on_conditions(
                             "https://premiumbanking.info/tbank/5")},
    "tbank_private_55": {**_TBANK_PRIVATE_SHARED,
                         "restaurants": _tbank_private_restaurants(
                             "https://premiumbanking.info/tbank/6"),
                         "service_cost": _free_on_conditions(
                             "https://premiumbanking.info/tbank/6")},
    "tbank_private_100": {**_TBANK_PRIVATE_SHARED,
                          "restaurants": _tbank_private_restaurants(
                              "https://premiumbanking.info/tbank/7"),
                          "service_cost": _free_on_conditions(
                              "https://premiumbanking.info/tbank/7")},
    # ----- ВТБ: Привилегия 1–4; Prime+ получает только общие банковские
    # условия ВТБ по карте/сбережениям, явно опубликованные на официальных
    # страницах ВТБ. Не переносить сюда уникальные сервисы без tier-source.
    "vtb_privilege_1": {
        **_VTB_PRIVILEGE_SHARED,
        "entry_conditions": _VTB_LEVEL_ENTRIES_2026["vtb_privilege_1"],
        "last_change_date": _fact(
            "31.07.2026 — запуск уровней «Расти с ВТБ»; первое назначение "
            "уровня — 01.09.2026",
            _VTB_UPDATE_2026,
            "Официальный лендинг не публикует количество преференций для "
            "уровня «Изумруд», поэтому оно не добавлено в curated-данные",
            date_checked=_VTB_UPDATE_CHECKED),
    },
    "vtb_privilege_2": {**_VTB_PRIVILEGE_SHARED,
                        "entry_conditions":
                            _VTB_LEVEL_ENTRIES_2026["vtb_privilege_2"],
                        **_vtb_preference_fields_2026(2),
                        "service_cost": _free_on_conditions(
                            "https://premiumbanking.info/vtb/2")},
    "vtb_privilege_3": {**_VTB_PRIVILEGE_SHARED,
                        "entry_conditions":
                            _VTB_LEVEL_ENTRIES_2026["vtb_privilege_3"],
                        **_vtb_preference_fields_2026(6),
                        "service_cost": _free_on_conditions(
                            "https://premiumbanking.info/vtb/3")},
    "vtb_privilege_4": {**_VTB_PRIVILEGE_SHARED,
                        "entry_conditions":
                            _VTB_LEVEL_ENTRIES_2026["vtb_privilege_4"],
                        **_vtb_preference_fields_2026(10),
                        "service_cost": _free_on_conditions(
                            "https://premiumbanking.info/vtb/4")},
    "vtb_prime_5": {
        **_VTB_PRIME_OPERATION_COMPONENTS,
        "concierge": _VTB_PRIME_CONCIERGE,
        "auto": _vtb_prime_roadside("https://premiumbanking.info/vtb/5"),
        "cashback": _VTB_PRIME_CASHBACK,
        "deposits": _VTB_DEPOSITS,
        "transfers_payments": _VTB_PRIME_TRANSFERS,
        "cash_withdrawal": _VTB_PRIME_CASH_WITHDRAWAL,
        "supreme": _VTB_PRIVILEGE_SHARED["supreme"],
    },
    "vtb_prime_6": {
        **_VTB_PRIME_OPERATION_COMPONENTS,
        "concierge": _VTB_PRIME_CONCIERGE,
        "auto": _vtb_prime_roadside("https://premiumbanking.info/vtb/6"),
        "cashback": _VTB_PRIME_CASHBACK,
        "deposits": _VTB_DEPOSITS,
        "transfers_payments": _VTB_PRIME_TRANSFERS,
        "cash_withdrawal": _VTB_PRIME_CASH_WITHDRAWAL,
        "supreme": _VTB_PRIVILEGE_SHARED["supreme"],
        "service_cost": _free_on_conditions("https://premiumbanking.info/vtb/6"),
    },
    "vtb_prime_7": {
        **_VTB_PRIME_OPERATION_COMPONENTS,
        "concierge": _VTB_PRIME_CONCIERGE,
        "auto": _vtb_prime_roadside("https://premiumbanking.info/vtb/7"),
        "cashback": _VTB_PRIME_CASHBACK,
        "deposits": _VTB_DEPOSITS,
        "transfers_payments": _VTB_PRIME_TRANSFERS,
        "cash_withdrawal": _VTB_PRIME_CASH_WITHDRAWAL,
        "supreme": _VTB_PRIVILEGE_SHARED["supreme"],
        "service_cost": _free_on_conditions("https://premiumbanking.info/vtb/7"),
    },
    "vtb_prime_8": {
        **_VTB_PRIME_OPERATION_COMPONENTS,
        "concierge": _VTB_PRIME_CONCIERGE,
        "auto": _vtb_prime_roadside("https://premiumbanking.info/vtb/8"),
        "cashback": _VTB_PRIME_CASHBACK,
        "deposits": _VTB_DEPOSITS,
        "transfers_payments": _VTB_PRIME_TRANSFERS,
        "cash_withdrawal": _VTB_PRIME_CASH_WITHDRAWAL,
        "supreme": _VTB_PRIVILEGE_SHARED["supreme"],
        "service_cost": _free_on_conditions("https://premiumbanking.info/vtb/8"),
    },
    # ----- Озон Банк -----
    "ozonbank_ultra_bronze": {
        **_OZONBANK_SHARED,
        "cash_withdrawal": _ozon_ultra_cash_withdrawal("3 000 000 ₽"),
    },
    "ozonbank_ultra_silver": {**_OZONBANK_SHARED,
                              "cash_withdrawal": _ozon_ultra_cash_withdrawal(
                                  "6 000 000 ₽"),
                              "service_cost": _free_on_conditions(
                                  "https://premiumbanking.info/ozon/2")},
    "ozonbank_ultra_gold": {**_OZONBANK_SHARED,
                            "cash_withdrawal": _ozon_ultra_cash_withdrawal(
                                "12 000 000 ₽"),
                            "service_cost": _free_on_conditions(
                                "https://premiumbanking.info/ozon/3")},
    "ozonbank_ultra_platinum": {**_OZONBANK_SHARED,
                                "cash_withdrawal": _ozon_ultra_cash_withdrawal(
                                    "30 000 000 ₽"),
                                "service_cost": _free_on_conditions(
                                    "https://premiumbanking.info/ozon/4")},
    # ----- Газпромбанк Premium -----
    "gpb_premium_1": {
        "entry_conditions": _GPB_PREMIUM_1_ENTRY,
        "deposits": _GPB_PREMIUM_DEPOSITS,
        "cashback": _GPB_PREMIUM_CASHBACK_FACT,
        "transfers_payments": _GPB_PREMIUM_TRANSFERS,
        "cash_withdrawal": _GPB_PREMIUM_CASH,
        "supreme": _GPB_PREMIUM_SUPREME,
    },
    "gpb_premium_2": {
        "entry_conditions": _GPB_PREMIUM_2_ENTRY,
        "deposits": _GPB_PREMIUM_DEPOSITS,
        "cashback": _GPB_PREMIUM_CASHBACK_FACT,
        "transfers_payments": _GPB_PREMIUM_TRANSFERS,
        "cash_withdrawal": _GPB_PREMIUM_CASH,
        "supreme": _GPB_PREMIUM_SUPREME,
        "service_cost": _free_on_conditions(
            "https://premiumbanking.info/gazprombank/2"),
    },
    "gpb_premium_3": {
        "deposits": _GPB_PREMIUM_DEPOSITS,
        "cashback": _GPB_PREMIUM_CASHBACK_FACT,
        "transfers_payments": _GPB_PREMIUM_TRANSFERS,
        "cash_withdrawal": _GPB_PREMIUM_CASH,
        "supreme": _GPB_PREMIUM_SUPREME,
        "service_cost": _free_on_conditions(
            "https://premiumbanking.info/gazprombank/3"),
    },
    # ----- Газпромбанк Private -----
    "gpb_private": {
        "service_cost": _free_on_conditions(
            "https://premiumbanking.info/gazprombank/4"),
        "deposits": _GPB_PRIVATE_DEPOSITS,
        "cashback": _GPB_PRIVATE_CASHBACK,
        "transfers_payments": _GPB_PRIVATE_TRANSFERS_FACT,
        "supreme": _GPB_PRIVATE_PRIME,
    },
    # ----- Альфа-Банк -----
    "alfa_only_1": {**_ALFA_ONLY_OPERATION_FACTS,
                    "entry_conditions": _ALFA_ONLY_1_ENTRY,
                    "addons": _ALFA_ADDONS_ABSENT,
                    "concierge": _ALFA_CONCIERGE_FACT,
                    "ecosystem": _ALFA_ONLY_SIMPLE_PRIVE,
                    "cashback": _ALFA_ONLY_CASHBACK,
                    "card_terms": _ALFA_ONLY_CARD_FREE,
                    "transfers_payments": _ALFA_ONLY_TRANSFERS,
                    "cash_withdrawal": _ALFA_ONLY_CASH_WITHDRAWAL,
                    "supreme": _ALFA_ONLY_SUPREME,
                    "deposits": _ALFA_ONLY_DEPOSITS},
    "alfa_only_2": {**_ALFA_ONLY_OPERATION_FACTS,
                    "addons": _ALFA_ADDONS_ABSENT,
                    "concierge": _ALFA_CONCIERGE_FACT,
                    "ecosystem": _alfa_only_ecosystem(2),
                    "cashback": _ALFA_ONLY_CASHBACK,
                    "card_terms": _ALFA_ONLY_CARD_FREE,
                    "transfers_payments": _ALFA_ONLY_TRANSFERS,
                    "cash_withdrawal": _ALFA_ONLY_CASH_WITHDRAWAL,
                    "supreme": _ALFA_ONLY_SUPREME,
                    "deposits": _ALFA_ONLY_DEPOSITS,
                    "service_cost": _free_on_conditions(
                        "https://premiumbanking.info/alfabank/2")},
    "alfa_only_3": {**_ALFA_ONLY_OPERATION_FACTS,
                    "addons": _ALFA_ADDONS_ABSENT,
                    "concierge": _ALFA_CONCIERGE_FACT,
                    "ecosystem": _alfa_only_ecosystem(3, include_rbc=True),
                    "cashback": _ALFA_ONLY_CASHBACK,
                    "card_terms": _ALFA_ONLY_CARD_FREE,
                    "transfers_payments": _ALFA_ONLY_TRANSFERS,
                    "cash_withdrawal": _ALFA_ONLY_CASH_WITHDRAWAL,
                    "supreme": _ALFA_ONLY_SUPREME,
                    "deposits": _ALFA_ONLY_DEPOSITS,
                    "service_cost": _free_on_conditions(
                        "https://premiumbanking.info/alfabank/3")},
    "alfa_only_4": {**_ALFA_ONLY_OPERATION_FACTS,
                    "addons": _ALFA_ADDONS_ABSENT,
                    "concierge": _ALFA_CONCIERGE_FACT,
                    "ecosystem": _alfa_only_ecosystem(4, include_rbc=True),
                    "cashback": _ALFA_ONLY_CASHBACK,
                    "card_terms": _ALFA_ONLY_CARD_FREE,
                    "transfers_payments": _ALFA_ONLY_TRANSFERS,
                    "cash_withdrawal": _ALFA_ONLY_CASH_WITHDRAWAL,
                    "supreme": _ALFA_ONLY_SUPREME,
                    "deposits": _ALFA_ONLY_DEPOSITS,
                    "service_cost": _free_on_conditions(
                        "https://premiumbanking.info/alfabank/4")},
    "alfa_aclub": {
        **_ALFA_ACLUB_OPERATION_FACTS,
        "entry_conditions": _fact(
            "30 млн ₽ на счетах",
            _ALFA_ACLUB_OFFICIAL,
            "Актуальный единый порог входа в A-Club; прежнее разделение на "
            "60 млн ₽ для Москвы и 30 млн ₽ для регионов больше не применяется",
            date_checked="2026-07-21"),
        "lounge_access": _fact(
            "Бизнес-залы — безлимит",
            _PBI_ACLUB,
            "Fallback после недоступности официальной страницы A-Club"),
        "restaurants": _fact(
            "Рестораны — безлимит по 2 500 ₽; один чек за одну дату до "
            "5 000 ₽ списывает две компенсации по 2 500 ₽; доступно при "
            "вылете и прилёте, в дату поездки и один календарный день до "
            "или после неё; общий лимит с бизнес-залами",
            _PBI_ACLUB,
            "Fallback после недоступности официальной страницы A-Club"),
        "taxi": _fact(
            "Такси — 3 раза в месяц, 15 раз в год, до 5 000 ₽",
            _PBI_ACLUB,
            "Fallback после недоступности официальной страницы A-Club"),
        "insurance": _fact(
            "Страхование — €650 тыс, 90 дней, ассистанс Class Assistance",
            _PBI_ACLUB,
            "Fallback после недоступности официальной страницы A-Club"),
        "concierge": _fact(
            "Есть — консьерж-сервис PRIME",
            _PBI_ACLUB,
            "Не переносим консьерж-сервис Alfa Only в A-Club"),
        "ecosystem": _fact(
            "Консультации с юристом, бухгалтером; Альфа-Мобайл (50 ГБ, "
            "500 минут, 50 SMS); Alfa Only Lounge в SVO терминал C; "
            "А-Клуб Lounge в SVO терминал B; "
            "Закрытый винный клуб SimplePrivé — статус Gold, персональный "
            "сомелье и скидка 30% на основной ассортимент; "
            "Медицинский консьерж — организация обследований и лечения "
            "в лучших клиниках в России и за рубежом",
            _ALFA_ACLUB_OFFICIAL,
            "Постоянные привилегии A-Club: часть подтверждена ПБИ /alfabank/5; "
            "SimplePrivé и медицинский консьерж — по официальной странице A-Club "
            "(страница зарегистрирована, но при автоматической проверке может "
            "возвращать 403)"),
        "cashback": _fact(
            "не найдено",
            _PBI_ACLUB,
            "Постоянная программа кэшбэка A-Club в доступных источниках "
            "не подтверждена; временные акции не используются как тарифный факт"),
        "deposits": _ALFA_ACLUB_DEPOSITS,
        "supreme": _ALFA_ACLUB_SUPREME,
        "card_terms": _fact(
            "не найдено",
            _PBI_ACLUB,
            "Карточные лимиты именно A-Club в доступных источниках не подтверждены; "
            "данные Alfa Only не переносятся"),
        "addons": _fact(
            "— (докупаемые опции A-Club в доступных источниках не заявлены)",
            _PBI_ACLUB,
            "Не переносим состав докупаемых опций Alfa Only"),
        "service_cost": _free_on_conditions(_PBI_ACLUB),
    },
    # ----- Райффайзен -----
    "raif_premium_1": {"addons": _RAIF_ADDONS_ABSENT},
    "raif_premium_2": {"addons": _RAIF_ADDONS_ABSENT,
                       "service_cost": _free_on_conditions(
                           "https://premiumbanking.info/raiffeisen/2")},
    "raif_premium_3": {"addons": _RAIF_ADDONS_ABSENT,
                       "service_cost": _free_on_conditions(
                           "https://premiumbanking.info/raiffeisen/3")},
    "raif_premium_4": {"addons": _RAIF_ADDONS_ABSENT,
                       "ecosystem": _RAIF_PREMIUM_4_ECOSYSTEM,
                       "service_cost": _free_on_conditions(
                           "https://premiumbanking.info/raiffeisen/4")},
    # ----- Инго Premium -----
    "ingo_premium": {
        "positioning": _fact(
            "Премиальная ИнгоКарта с платным или бесплатным обслуживанием "
            "по остаткам, зачислениям и покупкам",
            _INGO_PREMIUM_TARIFF,
            "Официальный тарифный план 3.1.1.1.2.2",
            date_checked="2026-07-28"),
        "entry_conditions": _INGO_ENTRY_CONDITIONS,
        "service_cost": _INGO_SERVICE_COST,
        "lounge_access": _INGO_LOUNGES,
        "cashback": _INGO_CASHBACK,
        "card_terms": _INGO_CARD_TERMS,
        "transfers_payments": _INGO_TRANSFERS,
        "cash_withdrawal": _INGO_CASH_WITHDRAWAL,
        "supreme": _INGO_SUPREME,
        "insurance": _INGO_INSURANCE,
        "taxi": _INGO_TAXI,
        "restaurants": _INGO_RESTAURANTS,
        "selectable_options": _INGO_SELECTABLE,
        "selection_rules": _INGO_SELECTION_RULES,
    },
    # ----- Lifestyle -----
    "yandex_plus_main": {
        "delivery": _fact(
            "Бесплатная доставка из Яндекс Лавки; кэшбэк баллами 5% на "
            "Маркете (1 балл = 1 ₽ в сервисах Яндекса)",
            _YANDEX_PLUS_SUPPORT, ""),
        "taxi": _fact(
            "Кэшбэк баллами 5% в Яндекс Такси (Go), 10% в Еде, 5% в Лавке; "
            "баллы тратятся в такси и других сервисах",
            _YANDEX_PLUS_SUPPORT, ""),
    },
    "ozon_premium_main": {
        "price": _fact(
            "199 ₽/мес при помесячной оплате; 1 490 ₽/год (≈124 ₽/мес) при "
            "годовой. Периоды подписки: 30/91/182/365 дней",
            _OZON_PREMIUM_DOCS, "Сайт ozon.ru закрыт антиботом — данные из "
                                "официальных условий подписки (docs.ozon.ru)"),
        "delivery": _fact(
            "Бесплатная курьерская доставка без минимальной суммы заказа; "
            "увеличенный срок возврата до 60 дней; приоритетная поддержка; "
            "ранний доступ к распродажам и закрытые скидки",
            _OZON_PREMIUM_DOCS, ""),
        "cashback": _fact(
            "— (кэшбэк-механика не заявлена в официальных условиях подписки; "
            "денежная выгода — через закрытые скидки и ранний доступ к "
            "распродажам)",
            _OZON_PREMIUM_DOCS, "Отсутствие по официальным условиям"),
        "entertainment": _fact(
            "— (развлекательные сервисы не входят в состав Ozon Premium по "
            "официальным условиям подписки)",
            _OZON_PREMIUM_DOCS, "Отсутствие по официальным условиям"),
        "taxi": _fact(
            "— (такси/транспорт не входят в состав Ozon Premium)",
            _OZON_PREMIUM_DOCS, "Отсутствие по официальным условиям"),
        "bank_overlap": _fact(
            "доставка товаров без мин. суммы (vs возмещение Самоката и опций "
            "доставки); закрытые скидки/ранние распродажи (vs кэшбэк "
            "банковских пакетов)",
            _OZON_PREMIUM_DOCS, "Оценка пересечений по составу подписки"),
    },
    "wb_club": {
        "price": _fact(
            "199 ₽/мес (первый месяц 1 ₽); годовая — 159 ₽/мес "
            "(1 908 ₽/год)",
            _WB_CLUB_NEWS, "Сайт wildberries.ru закрыт антиботом — данные "
                           "из публичных материалов о запуске WB Клуба"),
        "cashback": _fact(
            "Механика скидок вместо кэшбэка: дополнительные скидки до 31% "
            "на товары, суммируются с персональными предложениями и акциями",
            _WB_CLUB_NEWS, ""),
        "entertainment": _fact(
            "— (развлекательные сервисы не входят в состав WB Клуба)",
            _WB_CLUB_NEWS, "Отсутствие по официальным условиям"),
        "taxi": _fact(
            "— (такси/транспорт не входят в состав WB Клуба)",
            _WB_CLUB_NEWS, "Отсутствие по официальным условиям"),
        "bank_overlap": _fact(
            "скидки на повседневные покупки (vs кэшбэк банковских пакетов); "
            "приоритетная поддержка (vs премиальная линия банка)",
            _WB_CLUB_NEWS, "Оценка пересечений по составу подписки"),
    },
}

CURATED_FACTS.update(_COMPETITOR_FACTS)

# ============================================================================
# DIGITAL-FIRST НЕОБАНКИ — Revolut, N26, Wise, Monzo (проверено 2026-07-02).
# Требование блока: НИ ОДНОГО «не найдено» — каждое поле либо заполнено с
# source_url, либо «—» с пометкой «не предусмотрено моделью продукта».
# Линейки сверены с официальными сайтами: у Monzo текущие планы —
# Extra/Perks/Max (Plus/Premium из вводной упразднены в 2024), у N26 тир
# You переименован в Go. Цены — в валюте страны (UK £ / ЕС €).
# ============================================================================

_NA = "— (не предусмотрено моделью продукта)"


def _na(url, note="Категория не применима к модели продукта"):
    return _fact(_NA, url, note)


def _ref_dashes(url):
    """Справочные поля для digital-блока: ПБИ их не покрывает."""
    return {
        "aggregator_value": _fact("— (ПБИ не покрывает международные необанки)",
                                  url, "Справочное поле"),
        "other_notes": _fact("—", url, "Справочное поле"),
        "last_change_date": _fact("— (история изменений не отслеживается "
                                  "для международного блока)", url,
                                  "Справочное поле"),
    }


# ---------- Revolut ----------
_REV_PRICING = "https://www.revolut.com/our-pricing-plans/"
_REV_PREMIUM = "https://www.revolut.com/revolut-premium/"
_REV_ULTRA = "https://www.revolut.com/ultra-plan/"
_REV_LOUNGES = "https://www.revolut.com/lounges/"

_REV_SHARED = {
    "concierge": _na(_REV_PRICING, "Консьерж-сервис не входит ни в один "
                                   "план Revolut"),
    "auto": _na(_REV_PRICING),
    "taxi_restaurants": _na(_REV_PRICING, "Компенсации такси/ресторанов "
                                          "не предусмотрены моделью"),
    "addons": _fact(
        "Разовые платные сервисы в приложении (например, lounge-пассы "
        "DragonPass); пакетных докупаемых опций нет — вместо этого апгрейд "
        "на следующий план",
        _REV_LOUNGES, ""),
    **_ref_dashes(_REV_PRICING),
}

_DIGITAL_REVOLUT = {
    "revolut_premium": {
        **_REV_SHARED,
        "positioning": _fact(
            "Первый платный уровень Revolut — travel/daily-banking подписка "
            "для активно путешествующего массового клиента",
            _REV_PREMIUM, ""),
        "entry_conditions": _fact(
            "Подписка без требований к остатку: £7,99/мес или £80/год (UK; "
            "тарифы зависят от страны)", _REV_PREMIUM, ""),
        "service_cost": _fact("£7,99/мес или £80/год (UK)", _REV_PREMIUM, ""),
        "lounge_access": _fact(
            "Проходы DragonPass покупаются со скидкой в приложении + "
            "SmartDelay: бесплатный доступ в зал при задержке рейса от 1 часа",
            _REV_LOUNGES, "Бесплатных визитов в пакете нет"),
        "cashback": _fact(
            "Баллы RevPoints за покупки по повышенному курсу относительно "
            "Standard (точный курс — в приложении; максимум по линейке — "
            "1 балл/£1 на Ultra); обмен на мили и перки",
            _REV_PRICING, ""),
        "card_terms": _fact(
            "Дебетовая карта премиального дизайна; лимит бесплатных снятий "
            "в банкоматах до £400/мес (далее комиссия); виртуальные и "
            "одноразовые карты",
            _REV_PREMIUM, ""),
        "deposits": _fact(
            "Savings-счета: ставка зависит от плана и валюты — линейка от "
            "~2,9% (Standard) до 4% годовых (Ultra); Premium — промежуточная "
            "ставка, точное значение в приложении на дату",
            _REV_PRICING, "Ставки плавающие"),
        "insurance": _fact(
            "Страхование путешествий входит начиная с Premium (медицинские "
            "расходы, задержки рейса/багажа); детали в Insurance Policy плана",
            _REV_PREMIUM, ""),
        "ecosystem": _fact(
            "Мультивалютный обмен по выгодным лимитам, международные "
            "переводы, партнёрские перки и скидки в приложении",
            _REV_PREMIUM, ""),
    },
    "revolut_metal": {
        **_REV_SHARED,
        "positioning": _fact(
            "Средний платный уровень Revolut — расширенный travel-пакет с "
            "металлической картой", _REV_PRICING, ""),
        "entry_conditions": _fact(
            "Подписка без требований к остатку: £14,99/мес (UK)",
            _REV_PRICING, ""),
        "service_cost": _fact("£14,99/мес (UK)", _REV_PRICING, ""),
        "lounge_access": _fact(
            "Проходы DragonPass со скидкой + SmartDelay (бесплатный зал при "
            "задержке рейса)", _REV_LOUNGES, ""),
        "cashback": _fact(
            "Баллы RevPoints по курсу выше, чем на Premium (точный курс в "
            "приложении); обмен на мили и перки", _REV_PRICING, ""),
        "card_terms": _fact(
            "Металлическая карта (эксклюзив уровня, одна на клиента); лимит "
            "бесплатных снятий ×4 от Standard-плана",
            "https://help.revolut.com/en-US/help/profile-and-plan/my-plan-benefits/revolut-plans1/metal-plan/",
            ""),
        "deposits": _fact(
            "Savings-счета со ставкой выше Premium (линейка до 4% на Ultra; "
            "точная ставка в приложении)", _REV_PRICING, "Ставки плавающие"),
        "insurance": _fact(
            "Расширенное страхование путешествий (медицина, задержки, багаж) "
            "— шире пакета Premium", _REV_PRICING, ""),
        "ecosystem": _fact(
            "Всё из Premium + расширенные партнёрские перки",
            _REV_PRICING, ""),
    },
    "revolut_ultra": {
        **_REV_SHARED,
        "positioning": _fact(
            "Топ-план Revolut для affluent-клиента: платиновое покрытие "
            "карты, максимальные лимиты, перки «стоимостью до £4 290/год»",
            _REV_ULTRA, ""),
        "entry_conditions": _fact(
            "Подписка без требований к остатку: £55/мес или £540/год (UK)",
            _REV_ULTRA, ""),
        "service_cost": _fact("£55/мес или £540/год (UK)", _REV_ULTRA, ""),
        "lounge_access": _fact(
            "SmartDelay (бесплатный зал при задержке рейса) + проходы "
            "DragonPass в приложении; безлимитный доступ в залы в пакете "
            "не заявлен", _REV_LOUNGES, ""),
        "cashback": _fact(
            "RevPoints: 1 балл за £1 трат — максимальный курс линейки; "
            "обмен на мили авиакомпаний и перки", _REV_ULTRA, ""),
        "card_terms": _fact(
            "Карта с платиновым покрытием (эксклюзив Ultra); снятие в "
            "банкоматах без комиссии до £2 000/мес", _REV_ULTRA, ""),
        "deposits": _fact(
            "Savings-счета до 4% годовых (максимум линейки; ставка зависит "
            "от валюты)", _REV_PRICING, "Ставки плавающие"),
        "insurance": _fact(
            "Максимальный пакет: глобальная медицина, отмена поездок и "
            "мероприятий, franchise аренды авто, зимний спорт, задержка "
            "рейса, багаж, личная ответственность", _REV_ULTRA, ""),
        "ecosystem": _fact(
            "Партнёрские подписки и travel/lifestyle-перки суммарной "
            "стоимостью до £4 290/год", _REV_ULTRA, ""),
    },
}

# ---------- N26 ----------
_N26_GO = "https://n26.com/en-eu/you-bank-account-with-travel-insurance"
_N26_METAL = "https://n26.com/en-eu/metal"
_N26_PLANS = "https://n26.com/en-eu/plans"

_N26_SHARED = {
    "concierge": _na(_N26_PLANS, "Консьерж не входит ни в один план N26"),
    "auto": _na(_N26_PLANS),
    "taxi_restaurants": _na(_N26_PLANS),
    "addons": _na(_N26_PLANS, "Докупаемых опций нет — апгрейд плана"),
    "ecosystem": _fact(
        "Партнёрские предложения и скидки в приложении; Spaces "
        "(суб-счета-конверты) для управления деньгами", _N26_PLANS, ""),
    **_ref_dashes(_N26_PLANS),
}

_DIGITAL_N26 = {
    "n26_go": {
        **_N26_SHARED,
        "positioning": _fact(
            "Средний платный план N26 (экс-You, переименован в Go) — счёт "
            "с travel-страховками для путешествующих", _N26_GO, ""),
        "entry_conditions": _fact(
            "Подписка без требований к остатку: €9,90/мес", _N26_GO, ""),
        "service_cost": _fact("€9,90/мес", _N26_GO, ""),
        "lounge_access": _fact(
            "Скидочные lounge-пассы покупаются в приложении; бесплатных "
            "визитов в пакете нет", "https://n26.com/en-eu/travel-benefits", ""),
        "cashback": _fact(
            "— (кэшбэк не предусмотрен на уровне Go; 1% за платежи за "
            "границей — только на Metal)", _N26_PLANS,
            "Отсутствие по официальной линейке планов"),
        "card_terms": _fact(
            "Цветная дебетовая Mastercard; 5 бесплатных снятий в еврозоне/мес; "
            "бесплатные снятия в иностранной валюте", _N26_GO, ""),
        "deposits": _fact(
            "Накопительный счёт N26 Instant Savings (ставка зависит от плана, "
            "максимум на Metal — 1,5% p.a.; гибкий cash fund до 2,31%)",
            _N26_PLANS, "Ставки плавающие (ЕЦБ)"),
        "insurance": _fact(
            "Travel-страховки Allianz: медицина в поездках, отмена поездки, "
            "багаж (лимиты ниже пакета Metal)", _N26_GO, ""),
    },
    "n26_metal": {
        **_N26_SHARED,
        "positioning": _fact(
            "Топ-план N26 — премиальный счёт со стальной картой и "
            "максимальными ставками/страховками; немецкая лицензия BaFin, "
            "защита депозитов €100 000", _N26_METAL, ""),
        "entry_conditions": _fact(
            "Подписка без требований к остатку: €16,90/мес", _N26_METAL, ""),
        "service_cost": _fact("€16,90/мес", _N26_METAL, ""),
        "lounge_access": _fact(
            "Скидочные lounge-пассы в приложении; бесплатных визитов нет",
            "https://n26.com/en-eu/travel-benefits", ""),
        "cashback": _fact(
            "1% кэшбэка за платежи картой вне EEA/UK/Швейцарии, без лимита "
            "суммы", _N26_METAL, ""),
        "card_terms": _fact(
            "Стальная Mastercard 18 г; 8 бесплатных снятий в еврозоне/мес "
            "(далее €2/снятие); безлимитные бесплатные снятия вне еврозоны",
            _N26_METAL, ""),
        "deposits": _fact(
            "N26 Instant Savings 1,5% p.a. + гибкий cash fund до 2,31% p.a. "
            "— максимальные ставки линейки", _N26_METAL, "Ставки плавающие"),
        "insurance": _fact(
            "Пакет Allianz: медицина до €1 млн/поездка, отмена поездки до "
            "€10 000, багаж до €2 000, смартфон до €2 000 (кража/повреждение), "
            "purchase protection", _N26_METAL, ""),
    },
}

# ---------- Wise ----------
_WISE_PRICING = "https://wise.com/us/pricing/"
_WISE_CARD = "https://wise.com/us/card/"

_DIGITAL_WISE = {
    "wise_main": {
        "positioning": _fact(
            "Мультивалютный счёт без подписки — конкурент за multi-currency "
            "lifestyle-сценарий состоятельного клиента: 40+ валют, карта, "
            "международные переводы по mid-market курсу", _WISE_CARD, ""),
        "entry_conditions": _fact(
            "Подписки и требований к остатку нет — модель pay-per-use "
            "(оплата за операции)", _WISE_PRICING, ""),
        "service_cost": _fact(
            "0/мес — без абонентской платы; выпуск карты €5 разово "
            "(замена €7)", _WISE_PRICING, ""),
        "lounge_access": _na(_WISE_PRICING, "Бизнес-залы не предусмотрены "
                                            "моделью продукта"),
        "concierge": _na(_WISE_PRICING),
        "cashback": _fact(
            "— (кэшбэк не предусмотрен моделью — ценность продукта в "
            "mid-market курсе конвертации без наценки)", _WISE_PRICING,
            "Отсутствие по модели продукта"),
        "card_terms": _fact(
            "Дебетовая карта: оплата в 40+ валютах, 160+ стран; снятия: "
            "первые 2 снятия или £200/мес бесплатно, далее ~1,75% + £1 "
            "(правила с мая 2026); конвертация 0,35–1,5% от mid-market",
            _WISE_CARD, ""),
        "deposits": _fact(
            "Wise Interest (opt-in, остатки EUR/USD/GBP): ~3,55% на EUR "
            "(май 2026, зависит от ставки ЕЦБ); Jars для хранения валют",
            _WISE_PRICING, "Ставки плавающие"),
        "insurance": _na(_WISE_PRICING, "Страхование не предусмотрено "
                                        "моделью продукта"),
        "auto": _na(_WISE_PRICING),
        "taxi_restaurants": _na(_WISE_PRICING),
        "ecosystem": _fact(
            "Международные переводы по mid-market курсу (комиссия 0,35–1,5% "
            "по паре валют, без наценки выходного дня); мультивалютные "
            "реквизиты локальных счетов (IBAN/sort code/routing)",
            _WISE_PRICING, ""),
        "addons": _na(_WISE_PRICING, "Опций нет — pay-per-use за операции"),
        **_ref_dashes(_WISE_PRICING),
    },
}

# ---------- Monzo ----------
_MONZO_PLANS = "https://monzo.com/current-account/plans"
_MONZO_PERKS = "https://monzo.com/current-account/perks"
_MONZO_MAX = "https://monzo.com/help/monzo-max/monzo-max-what"
_MONZO_LOUNGE = "https://monzo.com/help/monzo-premium/how-to-airport-lounge"

_MONZO_SHARED = {
    "concierge": _na(_MONZO_PLANS, "Консьерж не входит ни в один план Monzo"),
    "taxi_restaurants": _na(_MONZO_PLANS),
    "addons": _fact(
        "Max можно расширить пакетом Family (+£5/мес: страховки на членов "
        "семьи); других докупаемых опций нет", _MONZO_MAX, ""),
    "card_terms": _fact(
        "Стандартная дебетовая карта Monzo (премиальных носителей в линейке "
        "Extra/Perks/Max нет); лимиты бесплатных снятий за границей выше на "
        "платных планах (детали в Help Centre)", _MONZO_PLANS, ""),
    **_ref_dashes(_MONZO_PLANS),
}

_DIGITAL_MONZO = {
    "monzo_extra": {
        **_MONZO_SHARED,
        "positioning": _fact(
            "Начальный платный план Monzo (линейка Extra/Perks/Max заменила "
            "Plus/Premium в 2024)", _MONZO_PLANS, ""),
        "entry_conditions": _fact(
            "Подписка без требований к остатку: £3/мес", _MONZO_PLANS, ""),
        "service_cost": _fact("£3/мес (£36/год)", _MONZO_PLANS, ""),
        "lounge_access": _na(_MONZO_PLANS, "Lounge-доступ — только на Max"),
        "cashback": _fact(
            "Billsback: возврат по оплате счетов — шанс получить счёт "
            "оплаченным до £150/счёт в месяц (механика розыгрыша, не "
            "фиксированный процент)", _MONZO_PLANS, ""),
        "deposits": _fact(
            "Сберегательные счета: стандартные ставки 2,75% AER (Instant "
            "Access) / 3,15% AER (Select Access) — буст ставок начинается "
            "с Perks", _MONZO_PLANS, "Ставки плавающие"),
        "insurance": _na(_MONZO_PLANS, "Страховки — только на Max"),
        "auto": _na(_MONZO_PLANS, "Breakdown cover — только на Max"),
        "ecosystem": _fact(
            "Connected banks (агрегация чужих счетов), credit insights, "
            "Billsback", _MONZO_PLANS, ""),
    },
    "monzo_perks": {
        **_MONZO_SHARED,
        "positioning": _fact(
            "Средний план Monzo — lifestyle-перки повседневного использования",
            _MONZO_PERKS, ""),
        "entry_conditions": _fact(
            "Подписка без требований к остатку: £7/мес", _MONZO_PERKS, ""),
        "service_cost": _fact("£7/мес (£84/год)", _MONZO_PERKS, ""),
        "lounge_access": _na(_MONZO_PLANS, "Lounge-доступ — только на Max"),
        "cashback": _fact(
            "Billsback до £150/счёт в месяц + натуральные перки: еженедельный "
            "Greggs, годовой Railcard, ежемесячный билет Vue, подписка "
            "Uber One", _MONZO_PERKS, ""),
        "deposits": _fact(
            "Буст ставок +0,50% AER: 3,25% AER Instant Access / до 3,65% "
            "AER Select Access", _MONZO_PERKS, "Ставки плавающие"),
        "insurance": _na(_MONZO_PLANS, "Страховки — только на Max"),
        "auto": _na(_MONZO_PLANS, "Breakdown cover — только на Max"),
        "ecosystem": _fact(
            "Всё из Extra + Greggs/Railcard/Vue/Uber One — прямая аналогия "
            "механики «опций» рублёвых банков", _MONZO_PERKS, ""),
    },
    "monzo_max": {
        **_MONZO_SHARED,
        "positioning": _fact(
            "Топ-план Monzo — страховой пакет + travel-перки (аналог "
            "packaged account)", _MONZO_MAX, ""),
        "entry_conditions": _fact(
            "Подписка без требований к остатку: £17/мес (Max) или £22/мес "
            "(Max with Family)", _MONZO_MAX, ""),
        "service_cost": _fact("£17/мес (£204/год); Family — £22/мес",
                              _MONZO_MAX, ""),
        "lounge_access": _fact(
            "Скидочный доступ LoungeKey: 1 100+ залов по фиксированной цене "
            "£24/чел/визит (бесплатных визитов нет)", _MONZO_LOUNGE, ""),
        "cashback": _fact(
            "Billsback до £150/счёт в месяц + перки Perks (Greggs, Railcard, "
            "Vue, Uber One)", _MONZO_MAX, ""),
        "deposits": _fact(
            "Бустнутые ставки: 3,25% AER Instant Access / до 3,65% AER "
            "Select Access", _MONZO_MAX, "Ставки плавающие"),
        "insurance": _fact(
            "Worldwide travel insurance + страховка телефона; членов семьи "
            "можно добавить за +£5/мес", _MONZO_MAX, ""),
        "auto": _fact(
            "Breakdown cover UK & Europe (помощь на дорогах — эвакуация/"
            "техпомощь) — входит в Max", _MONZO_MAX, ""),
        "ecosystem": _fact(
            "Всё из Extra и Perks + страховой пакет; connected banks, "
            "credit insights", _MONZO_MAX, ""),
    },
}

CURATED_FACTS.update(_DIGITAL_REVOLUT)
CURATED_FACTS.update(_DIGITAL_N26)
CURATED_FACTS.update(_DIGITAL_WISE)
CURATED_FACTS.update(_DIGITAL_MONZO)

# Official analogs that are explicitly published for every named tier below.
# Absence from this block means "not confirmed", never a negative fact.
for _vtb_tier_id in (
    "vtb_privilege_1", "vtb_privilege_2",
    "vtb_privilege_3", "vtb_privilege_4",
):
    CURATED_FACTS[_vtb_tier_id]["sbp_transfers"] = _scoped_fact(
        _VTB_PRIVILEGE_TRANSFERS["value"],
        _VTB_SBP,
        "Переводы через СБП — ВТБ Привилегия",
        _VTB_PRIVILEGE_TRANSFERS["value"],
        recipient="третье лицо / собственный счёт в другом банке",
        channel="СБП",
        free_limit="10 000 000 ₽ третьим лицам / 30 000 000 ₽ себе",
        technical_limit="1 000 000 ₽ за операцию и в сутки третьим лицам",
        period="месяц",
        date_checked="2026-07-24",
    )
    CURATED_FACTS[_vtb_tier_id]["roadside_option"] = _scoped_fact(
        _VTB_PRIVILEGE_SHARED["auto"]["value"],
        _VTB_SERVICES,
        "Премиальные сервисы ВТБ",
        _VTB_PRIVILEGE_SHARED["auto"]["value"],
        channel="включённый сервис",
        date_checked="2026-07-15",
    )
    CURATED_FACTS[_vtb_tier_id]["atm_daily_limit"] = _scoped_fact(
        "350 000 ₽ в сутки в банкоматах ВТБ и партнёров группы",
        _VTB_CARD,
        "Карта ВТБ «Привилегия Mir Supreme»",
        "до 350 000 ₽ в день",
        channel="банкоматы ВТБ и партнёров группы",
        technical_limit="350 000 ₽",
        period="сутки",
        date_checked="2026-07-15",
    )
    CURATED_FACTS[_vtb_tier_id]["cash_monthly_operational_limit"] = _scoped_fact(
        "2 000 000 ₽ в месяц в банкоматах ВТБ и партнёров группы",
        _VTB_CARD,
        "Карта ВТБ «Привилегия Mir Supreme»",
        "до 2 000 000 ₽ в месяц",
        channel="банкоматы ВТБ и партнёров группы",
        technical_limit="2 000 000 ₽",
        period="месяц",
        date_checked="2026-07-15",
    )

_ALFA_ONLY_METAL_SOURCE = "https://t.me/aaa_only/1434"
for _alfa_tier_id in (
    "alfa_only_1", "alfa_only_2", "alfa_only_3", "alfa_only_4",
):
    CURATED_FACTS[_alfa_tier_id]["metal_card"] = _scoped_fact(
        "Металлическая карта Alfa Only доступна бесплатно всем клиентам Alfa Only независимо от суммы на счетах",
        _ALFA_ONLY_METAL_SOURCE,
        "Официальный канал Alfa Only — металлическая карта",
        "Металлическая карта доступна всем клиентам Alfa Only — бесплатно и независимо от суммы на счетах",
        channel="основная/дополнительная карта не уточнена",
        date_checked="2026-07-30",
    )


def curated_for(tier_id: str) -> dict:
    return CURATED_FACTS.get(tier_id, {})
