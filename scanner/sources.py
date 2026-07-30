# -*- coding: utf-8 -*-
"""
Реестр источников: банки, тиры, экосистемные подписки и URL для скана.

Мультиисточниковая модель:
  - у каждого тира есть список источников (`sources`): официальный сайт банка,
    premiumbanking.info (ПБИ) и т.д. Каждый источник скачивается и парсится
    отдельно, данные сливаются в merge.py с фиксацией, откуда взята каждая цифра;
  - у банка могут быть `extra_sources` (Banki.ru, Sravni.ru, Bankiros) —
    страницы уровня банка, применяются ко всем его тирам как кросс-проверка;
  - внутри одного источника несколько URL — это fallback-цепочка (пробуем
    по порядку до первого успешного). Комплементарные страницы (например,
    отдельная страница вкладов) оформляются отдельным источником.

Приоритет источников при слиянии — см. SOURCE_META и scanner/merge.py.

`segment` — сегмент капитала по классификации premiumbanking.info
(0–3, 3–10, 10–25, 25–100 млн ₽): конфигурация раскладки сводной таблицы,
сверена с порогами входа на июль 2026.
"""

# Пауза между HTTP-запросами, сек (rate limiting)
REQUEST_PAUSE = 2.5

# Таймаут одного запроса, сек
REQUEST_TIMEOUT = 20

NOT_FOUND = "не найдено"
NOT_FOUND_AVAILABLE = "Не найдено в доступных источниках"

# Справочные поля: не участвуют в контуре «дозаполнить или отправить в
# ручную проверку» (не являются привилегиями)
REFERENCE_FIELDS = {
    "aggregator_value",
    "other_notes",
    "last_change_date",
    # Backward-compatible scoring field; user-facing reports use taxi/restaurants.
    "taxi_restaurants",
    "always_included_options",
    "selectable_options",
    "selection_rules",
    "auto",
    "ecosystem",
}

# Сегменты капитала в порядке отображения в сводной таблице
SEGMENTS = ["0–3 млн ₽", "3–10 млн ₽", "10–25 млн ₽", "25–100 млн ₽"]

# Международный блок — digital-first необанки (Revolut, N26, Wise, Monzo):
# конкуренты за lifestyle/multi-currency сценарий состоятельного клиента.
# Пороги/цены в валюте страны; в балльную оценку не входят (сопоставление
# 1:1 с рублёвым рынком вводит в заблуждение — см. лист «Методика оценки»)
INTL_SEGMENTS = ["digital-first (межд.)"]

# Источники данных. priority: меньше = приоритетнее при слиянии.
# Source policy: official -> premiumbanking.info -> other. curated сохраняется
# как приоритет 0 только для вручную проверенных фактов с source_url и датой.
SOURCE_PRIORITY_ORDER = ["curated", "official", "pbi", "other"]
SOURCE_META = {
    "curated": {
        "name": "Ручная проверка (первоисточник)",
        "priority": 0,
        "source_type": "curated",
    },
    "official": {
        "name": "Официальный сайт банка",
        "priority": 1,
        "source_type": "official",
    },
    "pbi": {
        "name": "premiumbanking.info",
        "priority": 2.1,
        "source_type": "premiumbanking.info",
    },
    "pbi_level": {
        "name": "premiumbanking.info (страница уровня)",
        "priority": 2,
        "source_type": "premiumbanking.info",
    },
    "banki_ru": {"name": "Banki.ru", "priority": 3, "source_type": "other"},
    "sravni_ru": {"name": "Sravni.ru", "priority": 3, "source_type": "other"},
    "bankiros": {"name": "Bankiros.ru", "priority": 3, "source_type": "other"},
    "frankrg": {"name": "Frank RG", "priority": 3, "source_type": "other"},
}


def source_priority_rank(source_id: str) -> int:
    return SOURCE_META.get(source_id, {"priority": 99})["priority"]

# Поля, которые собираем по каждому банковскому тиру.
# keywords — маркеры для извлечения релевантных фрагментов текста страницы.
BANK_FIELDS = {
    "positioning": {
        "label": "Позиционирование (на кого рассчитан)",
        "keywords": ["для клиентов", "капитал", "состоятельн", "премиальн",
                     "privat", "уровень дохода", "статус",
                     "wealth", "private bank"],
    },
    "entry_conditions": {
        "label": "Условия входа / поддержания уровня",
        "keywords": ["остаток", "оборот", "баланс", "бесплатное обслуживание",
                     "условия обслуживания", "суммарный", "среднемесячн",
                     "minimum balance", "eligibility", "qualify", "relationship balance", "investable assets"],
    },
    "service_cost": {
        "label": "Стоимость обслуживания",
        "keywords": ["стоимость обслуживания", "плата за обслуживание",
                     "руб/мес", "₽/мес", "рублей в месяц", "ежемесячная плата",
                     "monthly fee", "monthly service fee", "fee waived", "annual fee"],
    },
    "lounge_access": {
        "label": "Бизнес-залы (визиты, спутники)",
        "keywords": ["бизнес-зал", "бизнес зал", "lounge", "проход",
                     "аэропорт", "mir pass", "every lounge",
                     "priority pass", "airport lounge"],
    },
    "concierge": {
        "label": "Консьерж-сервис",
        "keywords": ["консьерж", "concierge", "личный помощник", "ассистент"],
    },
    "cashback": {
        "label": "Кэшбэк (ставка, категории, механика)",
        "keywords": ["кэшбэк", "кешбэк", "cashback", "бонус", "баллы",
                     "категори", "спасибо",
                     "rewards", "points", "cash back"],
    },
    "card_terms": {
        "label": "Карты (тип, лимиты переводов/снятия, выпуск)",
        "keywords": ["металлическ", "лимит на перевод", "переводы до",
                     "переводы без комиссии", "снятие наличн", "снять наличн",
                     "перевыпуск", "выпуск карты", "пластиков", "премиальная карта",
                     "лимитированн",
                     "metal card", "debit card", "withdrawal limit"],
    },
    "transfers_payments": {
        "label": "Переводы и платежи без комиссии",
        "keywords": ["переводы без комиссии", "платежи без комиссии",
                     "бесплатные переводы", "бесплатные платежи",
                     "лимит на перевод", "переводы до", "переводить без комиссии",
                     "free transfers", "fee-free transfers", "payments without fee"],
    },
    "cash_withdrawal": {
        "label": "Снятие наличных",
        "keywords": ["снятие наличных", "снять наличные", "снимать наличные",
                     "снятие без комиссии", "банкомат", "банкоматы",
                     "cash withdrawal", "atm withdrawal", "withdrawal limit"],
    },
    "supreme": {
        "label": "Supreme",
        "keywords": ["supreme", "мир supreme", "mir supreme"],
    },
    "deposits": {
        "label": "Вклады / накопительные счета",
        "keywords": ["вклад", "накопительн", "ставка", "процент годовых",
                     "% годовых", "надбавка",
                     "interest rate", "savings rate", "apy"],
    },
    "insurance": {
        "label": "Страхование",
        "keywords": ["страхов", "взр", "путешеств", "медицинск", "телемедицин",
                     "чекап", "check-up",
                     "travel insurance", "medical cover"],
    },
    "taxi": {
        "label": "Такси",
        "keywords": ["такси", "трансфер", "аэропорт", "вокзал"],
    },
    "restaurants": {
        "label": "Рестораны",
        "keywords": ["ресторан", "кафе", "чек", "вылет", "прилёт", "прилет"],
    },
    "auto": {
        "label": "Автоуслуги",
        "keywords": ["авто", "каршеринг", "парковк", "водитель",
                     "помощь на дорог"],
    },
    "taxi_restaurants": {
        "label": "Такси и рестораны (совместимость скоринга)",
        "keywords": ["такси", "ресторан", "трансфер", "кафе"],
    },
    "ecosystem": {
        "label": "Экосистемные привилегии (доставка, подписки)",
        "keywords": ["подписк", "доставк", "самокат", "афиша", "плюс",
                     "premium", "кино", "музыка", "экосистем"],
    },
    "other_benefits": {
        "label": "Другие привилегии",
        "keywords": [],
    },
    "always_included_options": {
        "label": "Постоянно включённые привилегии",
        "keywords": ["всегда включ", "включено", "входит", "бессрочно"],
    },
    "selectable_options": {
        "label": "Опции на выбор",
        "keywords": ["опция", "на выбор", "можно выбрать", "выбор"],
    },
    "selection_rules": {
        "label": "Условия выбора опций",
        "keywords": ["можно выбрать", "выбрать", "раз в месяц", "менять",
                     "опция из", "опции из", "на выбор"],
    },
    "addons": {
        "label": "Докупаемые опции и их цена",
        "keywords": ["опци", "докупить", "дополнительный пакет",
                     "подключить за", "стоимость опции"],
    },
    "aggregator_value": {
        "label": "Оценка ценности пакета в год (ПБИ, справочно)",
        "keywords": ["ценность"],
    },
    "other_notes": {
        "label": "Прочее (из источника)",
        "keywords": [],
    },
    "last_change_date": {
        "label": "Дата последнего изменения условий",
        "keywords": ["изменени", "вступает в силу", "обновлено", "действует с"],
    },
}

# Поля для экосистемных подписок (lifestyle-конкуренты)
LIFESTYLE_FIELDS = {
    "price": {
        "label": "Стоимость подписки",
        "keywords": ["₽ в месяц", "руб/мес", "рублей в месяц", "в год",
                     "стоимость", "цена подписки", "первые 30 дней", "бесплатно"],
    },
    "cashback": {
        "label": "Кэшбэк / баллы",
        "keywords": ["кэшбэк", "кешбэк", "баллы", "cashback", "возврат"],
    },
    "delivery": {
        "label": "Доставка",
        "keywords": ["доставк", "бесплатная доставка", "экспресс"],
    },
    "entertainment": {
        "label": "Развлечения (кино, музыка, контент)",
        "keywords": ["кино", "музыка", "кинопоиск", "сериал", "книги", "контент"],
    },
    "taxi": {
        "label": "Такси / транспорт",
        "keywords": ["такси", "драйв", "самокат", "транспорт"],
    },
}

# Джобы, по которым lifestyle-подписки пересекаются с банковскими привилегиями.
LIFESTYLE_BANK_OVERLAP_JOBS = {
    "cashback": "кэшбэк на повседневные покупки (vs кэшбэк банковских пакетов)",
    "delivery": "доставка продуктов/товаров (vs возмещение Самоката и опций доставки)",
    "entertainment": "развлечения и контент (vs возмещения Афиши, консьерж-букинг)",
    "taxi": "такси и городской транспорт (vs компенсация такси в аэропорт/на ЖД)",
}


def _src(source_id, *urls):
    return {"source_id": source_id, "urls": list(urls)}


# Официальные страницы Сбера (проверены 2026-07-02)
_SBER_PREMIER_OFFICIAL = "https://www.sberbank.com/ru/person/sb_premier_new"
_SBER_FIRST_OFFICIAL = "https://www.sberbank.com/ru/person/new_sb1"
_SBER_PREMIUM_OFFICIAL = "https://www.sberbank.ru/ru/person/premium"
_SBER_PREMIUM_VKLAD = "https://www.sberbank.ru/ru/person/premium/premium_vklad"
_SBER_FIRST_VKLADY = "https://www.sberbank.ru/ru/person/sb1/vklad/vse_vklady"
# Тарифы Премиальной СберКарты — первоисточник карточных лимитов всех уровней
_SBER_CARD_OFFICIAL = "https://www.sberbank.ru/ru/person/bank_cards/debit/sberkarta_premium"
_SBER_PREMIUM_TARIFF_PDF = "https://www.sberbank.ru/common/img/uploaded/files/pdf/tarif_premobsl_06032026.pdf"
_SBER_PRIVATE_TARIFF_PDF = "https://www.sberbank.ru/common/img/uploaded/redirected/private/assets/tariff_sb_pb.pdf"
_TBANK_PREMIUM_TARIFF_PDF = "https://cdn.tbank.ru/static/documents/docs-terms-of-service-premium.pdf"
_TBANK_PRIVATE_TARIFF_PDF = "https://cdn.tbank.ru/static/documents/docs-terms-of-service-private.pdf"
_TBANK_PREMIUM_OFFICIAL = "https://www.tbank.ru/tinkoff-premium/"
_TBANK_PREMIUM_ACCESS_OFFICIAL = (
    "https://www.tbank.ru/bank/help/general/premium/access/what-is/"
)
_TBANK_PREMIUM_TERMS_OFFICIAL = (
    "https://www.tbank.ru/bank/help/general/premium/access/terms/"
)
_TBANK_PRIVATE_OFFICIAL = "https://www.tbank.ru/private/"
_OZON_ULTRA_TARIFF_PDF = "https://cdn1.ozone.ru/s3/ob-landing/static/docs/ecom/products/rules/2026.05.18%20-%20Тариф%20Ultra.pdf"
_OZON_PRODUCTS_OFFICIAL = "https://finance.ozon.ru/products"
_OZON_SAVINGS_OFFICIAL = "https://finance.ozon.ru/promo/savings/landing"
_OZON_DEPOSIT_OFFICIAL = "https://finance.ozon.ru/promo/deposit/landing"
_VTB_PRIVILEGE_TARIFF_PDF = "https://www.vtb.ru/media-files/vtb.ru/sitepages/tarify/chastnim-licam/t-priv_pbu.pdf"
_VTB_RKO_TARIFF_XLSX = "https://www.vtb.ru/media-files/vtb.ru/sitepages/tarify/chastnim-licam/t_rko.xlsx"
_VTB_PRIME_PLUS_TARIFF_PDF = "https://private.vtb.ru/media-files/private.vtb.ru/sitepages/promo/new-pu-pm/tarify_praym_plyus_01.10.2025.pdf"
_VTB_PRIVILEGE_OFFICIAL = "https://www.vtb.ru/privilegia/"
_VTB_PRIVILEGE_UPDATE_2026 = "https://www.vtb.ru/promo/rsvtb-pv-2/"
_VTB_PRIME_PLUS_OFFICIAL = "https://www.vtb.ru/privilegia/paket-prime/"
_VTB_PRIVILEGE_CARD = "https://www.vtb.ru/privilegia/karty/debetovye/privilegiya-mir-supreme/"
_VTB_SBP_OFFICIAL = "https://www.vtb.ru/personal/online-servisy/perevody-sbp/"
_RAIF_PACKAGE_TARIFF_PDF = "https://www.raiffeisen.ru/common/img/uploaded/files/retail/package/tariffs_pakety_uslug.pdf"
_RAIF_PREMIUM_OFFICIAL = "https://www.raiffeisen.ru/premium/"
_GPB_PREMIUM_TARIFF_PDF = (
    "https://www.gazprombank.ru/upload/files/iblock/e97/"
    "h038o8uoge7g8zucvs80yz2sy8r9gejz/"
    "Tarif-Gazprombank.Premium-s-22.07.2026.pdf"
)
_GPB_PREMIUM_BONUS_TARIFF_PDF = (
    "https://www.gazprombank.ru/upload/files/iblock/a37/"
    "pdmoo1wsztjxq7zl1zsl7xa8v7wpuj0z/"
    "Usloviya-predostavleniya-fizicheskim-litsam-klientam-Banka-GPB-_AO_-"
    "servisa-Gazprom-Bonus-Premium-_deystvuet-s-06.07.2026_.pdf"
)
_GPB_PREMIUM_CASHBACK_PDF = (
    "https://www.gazprombank.ru/upload/files/iblock/474/"
    "102zjqtow8yzfiixl6bvikr0khvb3g51/"
    "Programma-loyalnosti-Banka-GPB-_AO_-po-nachisleniyu-keshbeka-"
    "_deystvuet-s-01.06.2026_.pdf"
)
_GPB_PREMIUM_OFFICIAL = "https://www.gazprombank.ru/premium/special/pu-premium/"
_GPB_PREMIUM_BONUS_OFFICIAL = "https://www.gazprombank.ru/premium/gazprom-bonus/"
_GPB_PRIVATE_OFFICIAL = "https://www.gazprombank.ru/private/"
_GPB_PRIVATE_PACKAGE_OFFICIAL = (
    "https://www.gazprombank.ru/private/package-of-services/"
)
_GPB_PRIVATE_TRANSFERS_PDF = "https://www.gazprombank.ru/download/8091775/"
_ALFA_ONLY_CARD_TARIFFS = (
    "https://alfabank.servicecdn.ru/site-upload/c1/65/275/"
    "Tariffs_Alfa_Only_Card.pdf"
)
_ALFA_CASH_LIMITS_OFFICIAL = (
    "https://alfabank.ru/help/articles/debit-cards/"
    "kak-snimat-dengi-s-karty-v-bankomate/"
)
_ALFA_ONLY_OFFICIAL = "https://alfabank.ru/everyday/package/premium/"
_ALFA_ONLY_DEPOSIT_OFFICIAL = (
    "https://alfabank.ru/everyday/package/premium/vklad/"
)
_ALFA_ONLY_SALARY_OFFICIAL = (
    "https://alfabank.ru/everyday/debit-cards/premium/zarplatnaya-karta/"
)
_ALFA_ACLUB_OFFICIAL = "https://alfabank.ru/a-club/"
_INGO_PREMIUM_OFFICIAL = "https://ingobank.ru/premium/"
_INGO_PREMIUM_TARIFF_PDF = "https://cdn.ingos.ru/docs/cards/Tarif_7.pdf"

PRIORITY_SOURCE_URLS = {
    "official": {
        "sber_premium": _SBER_PREMIUM_TARIFF_PDF,
        "sber_private": _SBER_PRIVATE_TARIFF_PDF,
        "tbank_premium": _TBANK_PREMIUM_TARIFF_PDF,
        "tbank_private": _TBANK_PRIVATE_TARIFF_PDF,
        "ozon_ultra": _OZON_ULTRA_TARIFF_PDF,
        "vtb_privilege": _VTB_PRIVILEGE_TARIFF_PDF,
        "vtb_rko": _VTB_RKO_TARIFF_XLSX,
        "vtb_prime_plus": _VTB_PRIME_PLUS_TARIFF_PDF,
        "raiffeisen": _RAIF_PACKAGE_TARIFF_PDF,
        "gazprombank": _GPB_PREMIUM_TARIFF_PDF,
        "alfa_only": _ALFA_ONLY_CARD_TARIFFS,
        "alfa_aclub": _ALFA_ACLUB_OFFICIAL,
        "ingo_premium": _INGO_PREMIUM_TARIFF_PDF,
    },
    "official_landing": {
        "sber_premium_levels": _SBER_PREMIUM_OFFICIAL,
        "sber_premier": _SBER_PREMIER_OFFICIAL,
        "sber_first": _SBER_FIRST_OFFICIAL,
        "sber_private": "https://sberpb.ru/",
        "tbank_premium": _TBANK_PREMIUM_OFFICIAL,
        "tbank_premium_access": _TBANK_PREMIUM_ACCESS_OFFICIAL,
        "tbank_premium_terms": _TBANK_PREMIUM_TERMS_OFFICIAL,
        "tbank_private": _TBANK_PRIVATE_OFFICIAL,
        "ozon_products": _OZON_PRODUCTS_OFFICIAL,
        "vtb_privilege": _VTB_PRIVILEGE_OFFICIAL,
        "vtb_privilege_update_2026": _VTB_PRIVILEGE_UPDATE_2026,
        "vtb_sbp": _VTB_SBP_OFFICIAL,
        "vtb_prime_plus": _VTB_PRIME_PLUS_OFFICIAL,
        "raiffeisen": _RAIF_PREMIUM_OFFICIAL,
        "gazprombank_premium": _GPB_PREMIUM_OFFICIAL,
        "gazprombank_premium_bonus": _GPB_PREMIUM_BONUS_OFFICIAL,
        "gazprombank_private": _GPB_PRIVATE_OFFICIAL,
        "alfa_only": _ALFA_ONLY_OFFICIAL,
        "alfa_only_deposit": _ALFA_ONLY_DEPOSIT_OFFICIAL,
        "alfa_only_salary": _ALFA_ONLY_SALARY_OFFICIAL,
        "alfa_aclub": _ALFA_ACLUB_OFFICIAL,
        "ingo_premium": _INGO_PREMIUM_OFFICIAL,
    },
    "pbi": {
        "sber": "https://premiumbanking.info/sber",
        "alfabank": "https://premiumbanking.info/alfabank",
        "vtb": "https://premiumbanking.info/vtb",
        "gazprombank": "https://premiumbanking.info/gazprombank",
        "ozon": "https://premiumbanking.info/ozon",
        "raiffeisen": "https://premiumbanking.info/raiffeisen",
        "tbank": "https://premiumbanking.info/tbank",
    },
}

REQUIRED_PRIORITY_URLS = frozenset(
    url
    for group in PRIORITY_SOURCE_URLS.values()
    for url in group.values()
)
AUTHORITATIVE_SOURCE_URLS = REQUIRED_PRIORITY_URLS


def is_authoritative_url(url: str) -> bool:
    return str(url or "").strip().split("?", 1)[0] in AUTHORITATIVE_SOURCE_URLS
_PBI_SBER = PRIORITY_SOURCE_URLS["pbi"]["sber"]
_PBI_TBANK = PRIORITY_SOURCE_URLS["pbi"]["tbank"]
_PBI_ALFABANK = PRIORITY_SOURCE_URLS["pbi"]["alfabank"]
_PBI_VTB = PRIORITY_SOURCE_URLS["pbi"]["vtb"]
_PBI_GAZPROMBANK = PRIORITY_SOURCE_URLS["pbi"]["gazprombank"]
_PBI_OZON = PRIORITY_SOURCE_URLS["pbi"]["ozon"]
_PBI_RAIFFEISEN = PRIORITY_SOURCE_URLS["pbi"]["raiffeisen"]

# Структура тиров сверена с premiumbanking.info (июль 2026):
# у Сбера 6 уровней, у ВТБ 8 (Привилегия 1–4 + Прайм+ 5–8), у Т-Банка
# статусы Bronze/Silver/Gold/Diamond, у Озон Банка — линейка Ultra.
BANKS = [
    # ---------- НАША ЛИНЕЙКА ----------
    {
        "id": "sber",
        "name": "Сбер",
        "type": "our",
        "extra_sources": [
            _src("banki_ru", "https://www.banki.ru/banks/bank/sberbank/"),
            _src("sravni_ru",
                 "https://www.sravni.ru/enciklopediya/info/sberbank-premer-chto-ehto-takoe/"),
            _src("bankiros", "https://bankiros.ru/bank/sberbank"),
        ],
        "tiers": [
            {
                "tier_id": "sber_premier_1",
                "tier_name": "СберПремьер — уровень 1",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _SBER_PREMIUM_OFFICIAL),
                    _src("official", _SBER_PREMIER_OFFICIAL),
                    _src("official", _SBER_PREMIUM_TARIFF_PDF),
                    _src("official", _SBER_PREMIUM_VKLAD),
                    _src("official", _SBER_CARD_OFFICIAL),
                    _src("pbi", _PBI_SBER, f"{_PBI_SBER}/1"),
                ],
            },
            {
                "tier_id": "sber_premier_2",
                "tier_name": "СберПремьер — уровень 2",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _SBER_PREMIUM_OFFICIAL),
                    _src("official", _SBER_PREMIER_OFFICIAL),
                    _src("official", _SBER_PREMIUM_TARIFF_PDF),
                    _src("official", _SBER_PREMIUM_VKLAD),
                    _src("official", _SBER_CARD_OFFICIAL),
                    _src("pbi", _PBI_SBER, f"{_PBI_SBER}/2"),
                ],
            },
            {
                "tier_id": "sber_premier_3",
                "tier_name": "СберПремьер — уровень 3",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _SBER_PREMIUM_OFFICIAL),
                    _src("official", _SBER_PREMIER_OFFICIAL),
                    _src("official", _SBER_PREMIUM_TARIFF_PDF),
                    _src("official", _SBER_PREMIUM_VKLAD),
                    _src("official", _SBER_CARD_OFFICIAL),
                    _src("pbi", _PBI_SBER, f"{_PBI_SBER}/3"),
                ],
            },
            {
                "tier_id": "sber_first_4",
                "tier_name": "СберПервый — уровень 4",
                "segment": "10–25 млн ₽",
                "sources": [
                    _src("official", _SBER_PREMIUM_OFFICIAL),
                    _src("official", _SBER_FIRST_OFFICIAL),
                    _src("official", _SBER_PREMIUM_TARIFF_PDF),
                    _src("official", _SBER_FIRST_VKLADY),
                    _src("official", _SBER_CARD_OFFICIAL),
                    _src("pbi", _PBI_SBER, f"{_PBI_SBER}/4"),
                ],
            },
            {
                "tier_id": "sber_first_5",
                "tier_name": "СберПервый — уровень 5",
                "segment": "25–100 млн ₽",
                "sources": [
                    _src("official", _SBER_PREMIUM_OFFICIAL),
                    _src("official", _SBER_FIRST_OFFICIAL),
                    _src("official", _SBER_PREMIUM_TARIFF_PDF),
                    _src("official", _SBER_FIRST_VKLADY),
                    _src("official", _SBER_CARD_OFFICIAL),
                    _src("pbi", _PBI_SBER, f"{_PBI_SBER}/5"),
                ],
            },
            {
                "tier_id": "sber_private_6",
                "tier_name": "Sber Private Banking — уровень 6",
                "segment": "25–100 млн ₽",
                "sources": [
                    _src("official", "https://sberpb.ru/", _SBER_PREMIUM_OFFICIAL),
                    _src("official", _SBER_PRIVATE_TARIFF_PDF),
                    _src("official", _SBER_CARD_OFFICIAL),
                    _src("pbi", _PBI_SBER, f"{_PBI_SBER}/6"),
                ],
            },
        ],
    },
    # ---------- ПРЯМЫЕ КОНКУРЕНТЫ ----------
    {
        "id": "tbank",
        "name": "Т-Банк",
        "type": "bank",
        "extra_sources": [
            _src("banki_ru", "https://www.banki.ru/banks/bank/tinkoff/",
                 "https://www.banki.ru/banks/bank/t-bank/"),
        ],
        "tiers": [
            {
                "tier_id": "tbank_bronze",
                "tier_name": "Premium Bronze",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _TBANK_PREMIUM_OFFICIAL),
                    _src("official", _TBANK_PREMIUM_TERMS_OFFICIAL),
                    _src("official", _TBANK_PREMIUM_TARIFF_PDF),
                    _src("pbi", _PBI_TBANK, f"{_PBI_TBANK}/1"),
                ],
            },
            {
                "tier_id": "tbank_silver",
                "tier_name": "Premium Silver",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _TBANK_PREMIUM_OFFICIAL),
                    _src("official", _TBANK_PREMIUM_ACCESS_OFFICIAL),
                    _src("official", _TBANK_PREMIUM_TARIFF_PDF),
                    _src("pbi", _PBI_TBANK, f"{_PBI_TBANK}/2"),
                ],
            },
            {
                "tier_id": "tbank_gold",
                "tier_name": "Premium Gold",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _TBANK_PREMIUM_OFFICIAL),
                    _src("official", _TBANK_PREMIUM_TARIFF_PDF),
                    _src("pbi", _PBI_TBANK, f"{_PBI_TBANK}/3"),
                ],
            },
            {
                "tier_id": "tbank_diamond",
                "tier_name": "Premium Diamond",
                "segment": "10–25 млн ₽",
                "sources": [
                    _src("official", _TBANK_PRIVATE_OFFICIAL),
                    _src("official", _TBANK_PRIVATE_TARIFF_PDF),
                    _src("pbi", _PBI_TBANK, f"{_PBI_TBANK}/4"),
                ],
            },
            {
                "tier_id": "tbank_private_30",
                "tier_name": "Private — 30 млн ₽",
                "segment": "25–50 млн ₽",
                "sources": [
                    _src("official", _TBANK_PRIVATE_OFFICIAL),
                    _src("official", _TBANK_PRIVATE_TARIFF_PDF),
                    _src("pbi", _PBI_TBANK, f"{_PBI_TBANK}/5"),
                ],
            },
            {
                "tier_id": "tbank_private_55",
                "tier_name": "Private — 55 млн ₽",
                "segment": "50–100 млн ₽",
                "sources": [
                    _src("official", _TBANK_PRIVATE_OFFICIAL),
                    _src("official", _TBANK_PRIVATE_TARIFF_PDF),
                    _src("pbi", _PBI_TBANK, f"{_PBI_TBANK}/6"),
                ],
            },
            {
                "tier_id": "tbank_private_100",
                "tier_name": "Private — 100 млн ₽",
                "segment": "100+ млн ₽",
                "sources": [
                    _src("official", _TBANK_PRIVATE_OFFICIAL),
                    _src("official", _TBANK_PRIVATE_TARIFF_PDF),
                    _src("pbi", _PBI_TBANK, f"{_PBI_TBANK}/7"),
                ],
            },
        ],
    },
    {
        "id": "alfa",
        "name": "Альфа-Банк",
        "type": "bank",
        "extra_sources": [
            _src("banki_ru", "https://www.banki.ru/banks/bank/alfabank/"),
            _src("bankiros", "https://bankiros.ru/bank/alfa-bank"),
        ],
        "tiers": [
            {
                "tier_id": "alfa_only_1",
                "tier_name": "Alfa Only — уровень 1",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _ALFA_ONLY_OFFICIAL),
                    _src("official", _ALFA_ONLY_SALARY_OFFICIAL),
                    _src("official", _ALFA_ONLY_DEPOSIT_OFFICIAL),
                    _src("official", _ALFA_ONLY_CARD_TARIFFS),
                    _src("official", _ALFA_CASH_LIMITS_OFFICIAL),
                    _src("pbi", _PBI_ALFABANK, f"{_PBI_ALFABANK}/1"),
                ],
            },
            {
                "tier_id": "alfa_only_2",
                "tier_name": "Alfa Only — уровень 2",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _ALFA_ONLY_OFFICIAL),
                    _src("official", _ALFA_ONLY_DEPOSIT_OFFICIAL),
                    _src("official", _ALFA_ONLY_CARD_TARIFFS),
                    _src("official", _ALFA_CASH_LIMITS_OFFICIAL),
                    _src("pbi", _PBI_ALFABANK, f"{_PBI_ALFABANK}/2"),
                ],
            },
            {
                "tier_id": "alfa_only_3",
                "tier_name": "Alfa Only — уровень 3",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _ALFA_ONLY_OFFICIAL),
                    _src("official", _ALFA_ONLY_DEPOSIT_OFFICIAL),
                    _src("official", _ALFA_ONLY_CARD_TARIFFS),
                    _src("official", _ALFA_CASH_LIMITS_OFFICIAL),
                    _src("pbi", _PBI_ALFABANK, f"{_PBI_ALFABANK}/3"),
                ],
            },
            {
                "tier_id": "alfa_only_4",
                "tier_name": "Alfa Only — уровень 4",
                "segment": "10–25 млн ₽",
                "sources": [
                    _src("official", _ALFA_ONLY_OFFICIAL),
                    _src("official", _ALFA_ONLY_DEPOSIT_OFFICIAL),
                    _src("official", _ALFA_ONLY_CARD_TARIFFS),
                    _src("official", _ALFA_CASH_LIMITS_OFFICIAL),
                    _src("pbi", _PBI_ALFABANK, f"{_PBI_ALFABANK}/4"),
                ],
            },
            {
                "tier_id": "alfa_aclub",
                "tier_name": "A-Club (private)",
                "segment": "25–100 млн ₽",
                "sources": [
                    _src("official", _ALFA_ACLUB_OFFICIAL,
                         "https://alfabank.ru/aclub/",
                         "https://www.aclub.ru/"),
                    _src("pbi", _PBI_ALFABANK, f"{_PBI_ALFABANK}/5"),
                ],
            },
        ],
    },
    {
        "id": "vtb",
        "name": "ВТБ",
        "type": "bank",
        "extra_sources": [
            _src("banki_ru", "https://www.banki.ru/banks/bank/vtb/"),
            _src("bankiros", "https://bankiros.ru/bank/vtb"),
        ],
        "tiers": [
            {
                "tier_id": "vtb_privilege_1",
                "tier_name": "Привилегия — Изумруд",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _VTB_PRIVILEGE_UPDATE_2026),
                    _src("official", _VTB_PRIVILEGE_OFFICIAL),
                    _src("official", _VTB_PRIVILEGE_TARIFF_PDF),
                    _src("official", _VTB_RKO_TARIFF_XLSX),
                    _src("official", _VTB_SBP_OFFICIAL),
                    _src("pbi", _PBI_VTB, f"{_PBI_VTB}/1"),
                ],
            },
            {
                "tier_id": "vtb_privilege_2",
                "tier_name": "Привилегия — Сапфир",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _VTB_PRIVILEGE_UPDATE_2026),
                    _src("official", _VTB_PRIVILEGE_OFFICIAL),
                    _src("official", _VTB_PRIVILEGE_TARIFF_PDF),
                    _src("official", _VTB_RKO_TARIFF_XLSX),
                    _src("official", _VTB_SBP_OFFICIAL),
                    _src("pbi", _PBI_VTB, f"{_PBI_VTB}/2"),
                ],
            },
            {
                "tier_id": "vtb_privilege_3",
                "tier_name": "Привилегия — Рубин",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _VTB_PRIVILEGE_UPDATE_2026),
                    _src("official", _VTB_PRIVILEGE_OFFICIAL),
                    _src("official", _VTB_PRIVILEGE_TARIFF_PDF),
                    _src("official", _VTB_RKO_TARIFF_XLSX),
                    _src("official", _VTB_SBP_OFFICIAL),
                    _src("pbi", _PBI_VTB, f"{_PBI_VTB}/3"),
                ],
            },
            {
                "tier_id": "vtb_privilege_4",
                "tier_name": "Привилегия — Бриллиант",
                "segment": "10–25 млн ₽",
                "sources": [
                    _src("official", _VTB_PRIVILEGE_UPDATE_2026),
                    _src("official", _VTB_PRIVILEGE_OFFICIAL),
                    _src("official", _VTB_PRIVILEGE_TARIFF_PDF),
                    _src("official", _VTB_RKO_TARIFF_XLSX),
                    _src("official", _VTB_SBP_OFFICIAL),
                    _src("pbi", _PBI_VTB, f"{_PBI_VTB}/4"),
                ],
            },
            {
                "tier_id": "vtb_prime_5",
                "tier_name": "Прайм+ — уровень 5",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _VTB_PRIME_PLUS_OFFICIAL),
                    _src("official", _VTB_PRIME_PLUS_TARIFF_PDF),
                    _src("official", _VTB_PRIVILEGE_CARD),
                    _src("official", _VTB_PRIVILEGE_OFFICIAL),
                    _src("pbi", _PBI_VTB, f"{_PBI_VTB}/5"),
                ],
            },
            {
                "tier_id": "vtb_prime_6",
                "tier_name": "Прайм+ — уровень 6",
                "segment": "10–25 млн ₽",
                "sources": [
                    _src("official", _VTB_PRIME_PLUS_OFFICIAL),
                    _src("official", _VTB_PRIME_PLUS_TARIFF_PDF),
                    _src("official", _VTB_PRIVILEGE_CARD),
                    _src("official", _VTB_PRIVILEGE_OFFICIAL),
                    _src("pbi", _PBI_VTB, f"{_PBI_VTB}/6"),
                ],
            },
            {
                "tier_id": "vtb_prime_7",
                "tier_name": "Прайм+ — уровень 7",
                "segment": "25–100 млн ₽",
                "sources": [
                    _src("official", _VTB_PRIME_PLUS_OFFICIAL),
                    _src("official", _VTB_PRIME_PLUS_TARIFF_PDF),
                    _src("official", _VTB_PRIVILEGE_CARD),
                    _src("official", _VTB_PRIVILEGE_OFFICIAL),
                    _src("pbi", _PBI_VTB, f"{_PBI_VTB}/7"),
                ],
            },
            {
                "tier_id": "vtb_prime_8",
                "tier_name": "Прайм+ — уровень 8",
                "segment": "25–100 млн ₽",
                "sources": [
                    _src("official", _VTB_PRIME_PLUS_OFFICIAL),
                    _src("official", _VTB_PRIME_PLUS_TARIFF_PDF),
                    _src("official", _VTB_PRIVILEGE_CARD),
                    _src("official", _VTB_PRIVILEGE_OFFICIAL),
                    _src("pbi", _PBI_VTB, f"{_PBI_VTB}/8"),
                ],
            },
        ],
    },
    {
        "id": "gazprombank",
        "name": "Газпромбанк",
        "type": "bank",
        "extra_sources": [
            _src("banki_ru", "https://www.banki.ru/banks/bank/gazprombank/"),
            _src("bankiros", "https://bankiros.ru/bank/gazprombank"),
        ],
        "tiers": [
            {
                "tier_id": "gpb_premium_1",
                "tier_name": "Премиум — уровень 1",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _GPB_PREMIUM_OFFICIAL),
                    _src("official", _GPB_PREMIUM_BONUS_OFFICIAL),
                    _src("official", _GPB_PREMIUM_TARIFF_PDF),
                    _src("official", _GPB_PREMIUM_BONUS_TARIFF_PDF),
                    _src("official", _GPB_PREMIUM_CASHBACK_PDF),
                    _src("pbi", _PBI_GAZPROMBANK, f"{_PBI_GAZPROMBANK}/1"),
                ],
            },
            {
                "tier_id": "gpb_premium_2",
                "tier_name": "Премиум — уровень 2",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _GPB_PREMIUM_OFFICIAL),
                    _src("official", _GPB_PREMIUM_TARIFF_PDF),
                    _src("official", _GPB_PREMIUM_BONUS_TARIFF_PDF),
                    _src("official", _GPB_PREMIUM_CASHBACK_PDF),
                    _src("pbi", _PBI_GAZPROMBANK, f"{_PBI_GAZPROMBANK}/2"),
                ],
            },
            {
                "tier_id": "gpb_premium_3",
                "tier_name": "Премиум — уровень 3",
                "segment": "10–25 млн ₽",
                "sources": [
                    _src("official", _GPB_PREMIUM_OFFICIAL),
                    _src("official", _GPB_PREMIUM_TARIFF_PDF),
                    _src("official", _GPB_PREMIUM_BONUS_TARIFF_PDF),
                    _src("official", _GPB_PREMIUM_CASHBACK_PDF),
                    _src("pbi", _PBI_GAZPROMBANK, f"{_PBI_GAZPROMBANK}/3"),
                ],
            },
            {
                "tier_id": "gpb_private",
                "tier_name": "Private Banking",
                "segment": "25–100 млн ₽",
                "sources": [
                    _src("official", _GPB_PRIVATE_OFFICIAL),
                    _src("official", _GPB_PRIVATE_PACKAGE_OFFICIAL),
                    _src("official", _GPB_PRIVATE_TRANSFERS_PDF),
                    _src("pbi", _PBI_GAZPROMBANK, f"{_PBI_GAZPROMBANK}/4"),
                ],
            },
        ],
    },
    {
        "id": "ozonbank",
        "name": "Озон Банк",
        "type": "bank",
        "extra_sources": [],
        "tiers": [
            {
                "tier_id": "ozonbank_ultra_bronze",
                "tier_name": "Ultra Bronze",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _OZON_PRODUCTS_OFFICIAL),
                    _src("official", _OZON_ULTRA_TARIFF_PDF),
                    _src("official", _OZON_SAVINGS_OFFICIAL),
                    _src("official", _OZON_DEPOSIT_OFFICIAL),
                    _src("pbi", _PBI_OZON, f"{_PBI_OZON}/1"),
                ],
            },
            {
                "tier_id": "ozonbank_ultra_silver",
                "tier_name": "Ultra Silver",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _OZON_PRODUCTS_OFFICIAL),
                    _src("official", _OZON_ULTRA_TARIFF_PDF),
                    _src("official", _OZON_SAVINGS_OFFICIAL),
                    _src("official", _OZON_DEPOSIT_OFFICIAL),
                    _src("pbi", _PBI_OZON, f"{_PBI_OZON}/2"),
                ],
            },
            {
                "tier_id": "ozonbank_ultra_gold",
                "tier_name": "Ultra Gold",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _OZON_PRODUCTS_OFFICIAL),
                    _src("official", _OZON_ULTRA_TARIFF_PDF),
                    _src("official", _OZON_SAVINGS_OFFICIAL),
                    _src("official", _OZON_DEPOSIT_OFFICIAL),
                    _src("pbi", _PBI_OZON, f"{_PBI_OZON}/3"),
                ],
            },
            {
                "tier_id": "ozonbank_ultra_platinum",
                "tier_name": "Ultra Platinum",
                "segment": "10–25 млн ₽",
                "sources": [
                    _src("official", _OZON_PRODUCTS_OFFICIAL),
                    _src("official", _OZON_ULTRA_TARIFF_PDF),
                    _src("official", _OZON_SAVINGS_OFFICIAL),
                    _src("official", _OZON_DEPOSIT_OFFICIAL),
                    _src("pbi", _PBI_OZON, f"{_PBI_OZON}/4"),
                ],
            },
        ],
    },
    {
        "id": "raiffeisen",
        "name": "Райффайзен Банк",
        "type": "bank",
        "extra_sources": [
            _src("banki_ru", "https://www.banki.ru/banks/bank/raiffeisen/"),
        ],
        "tiers": [
            {
                "tier_id": "raif_premium_1",
                "tier_name": "Premium — платное обслуживание",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _RAIF_PREMIUM_OFFICIAL),
                    _src("official", _RAIF_PACKAGE_TARIFF_PDF),
                    _src("pbi", _PBI_RAIFFEISEN, f"{_PBI_RAIFFEISEN}/1"),
                ],
            },
            {
                "tier_id": "raif_premium_2",
                "tier_name": "Premium — по обороту покупок",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _RAIF_PREMIUM_OFFICIAL),
                    _src("official", _RAIF_PACKAGE_TARIFF_PDF),
                    _src("pbi", _PBI_RAIFFEISEN, f"{_PBI_RAIFFEISEN}/2"),
                ],
            },
            {
                "tier_id": "raif_premium_3",
                "tier_name": "Premium — от 1.5 млн ₽",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _RAIF_PREMIUM_OFFICIAL),
                    _src("official", _RAIF_PACKAGE_TARIFF_PDF),
                    _src("pbi", _PBI_RAIFFEISEN, f"{_PBI_RAIFFEISEN}/3"),
                ],
            },
            {
                "tier_id": "raif_premium_4",
                "tier_name": "Premium — от 5 млн ₽",
                "segment": "3–10 млн ₽",
                "sources": [
                    _src("official", _RAIF_PREMIUM_OFFICIAL),
                    _src("official", _RAIF_PACKAGE_TARIFF_PDF),
                    _src("pbi", _PBI_RAIFFEISEN, f"{_PBI_RAIFFEISEN}/4"),
                ],
            },
        ],
    },
    {
        "id": "ingo",
        "name": "Инго Банк",
        "type": "bank",
        "extra_sources": [],
        "tiers": [
            {
                "tier_id": "ingo_premium",
                "tier_name": "Инго Premium",
                "segment": "0–3 млн ₽",
                "sources": [
                    _src("official", _INGO_PREMIUM_OFFICIAL),
                    _src("official", _INGO_PREMIUM_TARIFF_PDF),
                ],
            },
        ],
    },
    # ---------- МЕЖДУНАРОДНЫЕ DIGITAL-FIRST БАНКИ (type="intl") ----------
    # Схема атрибутов та же (BANK_FIELDS). Линейки сверены с официальными
    # сайтами (июль 2026): у Monzo вместо Plus/Premium действуют
    # Extra/Perks/Max, у N26 тир You переименован в Go. Wise — без тиров.
    {
        "id": "revolut",
        "name": "Revolut",
        "type": "intl",
        "tiers": [
            {
                "tier_id": "revolut_premium",
                "tier_name": "Premium",
                "segment": "digital-first (межд.)",
                "sources": [
                    _src("official", "https://www.revolut.com/revolut-premium/",
                         "https://help.revolut.com/help/profile-and-plan/my-plan-benefits/revolut-plans1/premium-plan/"),
                ],
            },
            {
                "tier_id": "revolut_metal",
                "tier_name": "Metal",
                "segment": "digital-first (межд.)",
                "sources": [
                    _src("official", "https://www.revolut.com/our-pricing-plans/",
                         "https://help.revolut.com/en-US/help/profile-and-plan/my-plan-benefits/revolut-plans1/metal-plan/"),
                ],
            },
            {
                "tier_id": "revolut_ultra",
                "tier_name": "Ultra",
                "segment": "digital-first (межд.)",
                "sources": [
                    _src("official", "https://www.revolut.com/ultra-plan/",
                         "https://help.revolut.com/help/profile-and-plan/my-plan-benefits/revolut-plans1/ultra-plan1/"),
                ],
            },
        ],
    },
    {
        "id": "n26",
        "name": "N26",
        "type": "intl",
        "tiers": [
            {
                "tier_id": "n26_go",
                "tier_name": "Go (экс-You)",
                "segment": "digital-first (межд.)",
                "sources": [
                    _src("official", "https://n26.com/en-eu/you-bank-account-with-travel-insurance",
                         "https://n26.com/en-eu/plans"),
                ],
            },
            {
                "tier_id": "n26_metal",
                "tier_name": "Metal",
                "segment": "digital-first (межд.)",
                "sources": [
                    _src("official", "https://n26.com/en-eu/metal",
                         "https://n26.com/en-eu/plans"),
                ],
            },
        ],
    },
    {
        "id": "wise",
        "name": "Wise",
        "type": "intl",
        "tiers": [
            {
                # Wise без тиров — фиксируем как единый multi-currency продукт
                "tier_id": "wise_main",
                "tier_name": "Wise (multi-currency, без тиров)",
                "segment": "digital-first (межд.)",
                "sources": [
                    _src("official", "https://wise.com/us/pricing/",
                         "https://wise.com/us/card/"),
                ],
            },
        ],
    },
    {
        "id": "monzo",
        "name": "Monzo",
        "type": "intl",
        "tiers": [
            {
                "tier_id": "monzo_extra",
                "tier_name": "Extra",
                "segment": "digital-first (межд.)",
                "sources": [
                    _src("official", "https://monzo.com/current-account/plans",
                         "https://monzo.com/help/monzo-extra/monzo-extra-what"),
                ],
            },
            {
                "tier_id": "monzo_perks",
                "tier_name": "Perks",
                "segment": "digital-first (межд.)",
                "sources": [
                    _src("official", "https://monzo.com/current-account/perks",
                         "https://monzo.com/help/monzo-perks/monzo-perks-what"),
                ],
            },
            {
                "tier_id": "monzo_max",
                "tier_name": "Max",
                "segment": "digital-first (межд.)",
                "sources": [
                    _src("official", "https://monzo.com/help/monzo-max/monzo-max-what",
                         "https://monzo.com/current-account/plans"),
                ],
            },
        ],
    },
    # ---------- LIFESTYLE-КОНКУРЕНТЫ ----------
    {
        "id": "yandex_plus",
        "name": "Яндекс Плюс",
        "type": "lifestyle",
        "tiers": [
            {
                "tier_id": "yandex_plus_main",
                "tier_name": "Яндекс Плюс",
                "segment": None,
                "sources": [_src("official", "https://plus.yandex.ru/")],
            },
        ],
    },
    {
        "id": "ozon_premium",
        "name": "Ozon Premium",
        "type": "lifestyle",
        "tiers": [
            {
                "tier_id": "ozon_premium_main",
                "tier_name": "Ozon Premium",
                "segment": None,
                "sources": [
                    _src("official", "https://www.ozon.ru/premium/",
                         "https://www.ozon.ru/landing/premium/"),
                ],
            },
        ],
    },
    {
        "id": "wildberries",
        "name": "Wildberries (Клуб покупателей)",
        "type": "lifestyle",
        "tiers": [
            {
                "tier_id": "wb_club",
                "tier_name": "WB Клуб",
                "segment": None,
                "sources": [
                    _src("official", "https://www.wildberries.ru/services/wb-club",
                         "https://www.wildberries.ru/"),
                ],
            },
        ],
    },
]

# Новостные страницы премиального и private banking. Они проверяются быстрым
# монитором при каждом запуске скана; факты из отраслевых лент не заменяют
# официальные банковские условия.
PREMIUM_NEWS_SOURCES = [
    {
        "id": "sber_press",
        "name": "Пресс-релизы Сбера",
        "bank_id": "sber",
        "bank": "Сбер",
        "source_type": "official",
        "kind": "listing",
        "url": "https://www.sberbank.com/ru/news-and-media/press-releases",
    },
    {
        "id": "alfa_press",
        "name": "Пресс-релизы Альфа-Банка",
        "bank_id": "alfa",
        "bank": "Альфа-Банк",
        "source_type": "official",
        "kind": "listing",
        "url": "https://alfabank.ru/news/",
    },
    {
        "id": "vtb_press",
        "name": "Пресс-релизы ВТБ",
        "bank_id": "vtb",
        "bank": "ВТБ",
        "source_type": "official",
        "kind": "listing",
        "url": "https://www.vtb.ru/about/press/",
    },
    {
        "id": "vtb_privilege_update_2026",
        "name": "ВТБ: обновление «Привилегии»",
        "bank_id": "vtb",
        "bank": "ВТБ",
        "source_type": "official",
        "kind": "direct",
        "url": "https://www.vtb.ru/promo/rsvtb-pv-2/",
    },
    {
        "id": "sber_premium_landing",
        "name": "Сбер: премиальные лендинги и документы",
        "bank_id": "sber",
        "bank": "Сбер",
        "source_type": "official",
        "kind": "landing",
        "allowed_hosts": ["www.sberbank.ru", "sberbank.ru"],
        "url": "https://www.sberbank.com/ru/person/sb_premier_new",
    },
    {
        "id": "alfa_only_landing",
        "name": "Альфа-Банк: Alfa Only и документы",
        "bank_id": "alfa",
        "bank": "Альфа-Банк",
        "source_type": "official",
        "kind": "landing",
        "allowed_hosts": ["alfabank.servicecdn.ru"],
        "url": "https://alfabank.ru/everyday/package/premium/",
    },
    {
        "id": "vtb_privilege_landing",
        "name": "ВТБ: Привилегия и документы",
        "bank_id": "vtb",
        "bank": "ВТБ",
        "source_type": "official",
        "kind": "landing",
        "allowed_hosts": ["private.vtb.ru"],
        "url": "https://www.vtb.ru/privilegia/",
    },
    {
        "id": "gazprombank_premium_landing",
        "name": "Газпромбанк: Премиум и документы",
        "bank_id": "gazprombank",
        "bank": "Газпромбанк",
        "source_type": "official",
        "kind": "landing",
        "allowed_hosts": ["cdn.gpb.ru"],
        "url": "https://www.gazprombank.ru/premium/",
    },
    {
        "id": "ozon_ultra_landing",
        "name": "Ozon Банк: Ultra и документы",
        "bank_id": "ozonbank",
        "bank": "Озон Банк",
        "source_type": "official",
        "kind": "landing",
        "allowed_hosts": ["cdn1.ozone.ru"],
        "url": "https://finance.ozon.ru/products",
    },
    {
        "id": "raiffeisen_premium_landing",
        "name": "Райффайзен Банк: Premium и документы",
        "bank_id": "raiffeisen",
        "bank": "Райффайзен Банк",
        "source_type": "official",
        "kind": "landing",
        "url": "https://www.raiffeisen.ru/premium/",
    },
    {
        "id": "tbank_premium_landing",
        "name": "Т-Банк: Т-Премиум и документы",
        "bank_id": "tbank",
        "bank": "Т-Банк",
        "source_type": "official",
        "kind": "landing",
        "allowed_hosts": ["cdn.tbank.ru"],
        "url": "https://www.tbank.ru/tinkoff-premium/",
    },
    {
        "id": "ingo_premium_landing",
        "name": "Инго Банк: премиальное обслуживание",
        "bank_id": "ingo",
        "bank": "Инго Банк",
        "source_type": "official",
        "kind": "landing",
        "url": "https://ingobank.ru/premium/",
    },
    {
        "id": "uralsib_premium_landing",
        "name": "Уралсиб: Премиум и документы",
        "bank_id": "uralsib",
        "bank": "Уралсиб",
        "source_type": "official",
        "kind": "landing",
        "url": "https://uralsib.ru/premium",
    },
    {
        "id": "uralsib_august_2026",
        "name": "Уралсиб: изменения с 1 августа 2026",
        "bank_id": "uralsib",
        "bank": "Уралсиб",
        "source_type": "official",
        "kind": "direct",
        "url": "https://uralsib.ru/blog/izmeneniya-v-usloviyakh-obsluzhivaniya-paketov-uslug-dlya-fizicheskikh-lits-s-1-avgusta-2026-goda",
    },
    {
        "id": "uralsib_june_2026",
        "name": "Уралсиб: изменения с 1 июня 2026",
        "bank_id": "uralsib",
        "bank": "Уралсиб",
        "source_type": "official",
        "kind": "direct",
        "url": "https://uralsib.ru/blog/izmeneniya-v-lineyke-paketov-uslug-dlya-fizicheskikh-lits-s-1-iyunya-2026-g",
    },
    {
        "id": "sovcombank_premium_landing",
        "name": "Совкомбанк: Xalva Premium и документы",
        "bank_id": "sovcombank",
        "bank": "Совкомбанк",
        "source_type": "official",
        "kind": "landing",
        "allowed_hosts": ["prod-api.sovcombank.ru"],
        "url": "https://sovcombank.ru/premium",
    },
    {
        "id": "mkb_premium_landing",
        "name": "МКБ: Премиум и документы",
        "bank_id": "mkb",
        "bank": "МКБ",
        "source_type": "official",
        "kind": "landing",
        "url": "https://mkb.ru/premium",
    },
    {
        "id": "domrf_premium_landing",
        "name": "Банк ДОМ.РФ: Премиум и документы",
        "bank_id": "domrf",
        "bank": "Банк ДОМ.РФ",
        "source_type": "official",
        "kind": "landing",
        "url": "https://domrfbank.ru/premium/",
    },
    {
        "id": "domrf_premium_news",
        "name": "Банк ДОМ.РФ: новости премиальным клиентам",
        "bank_id": "domrf",
        "bank": "Банк ДОМ.РФ",
        "source_type": "official",
        "kind": "listing",
        "url": "https://domrfbank.ru/press/premium-customers/",
    },
    {
        "id": "uralsib_blog",
        "name": "Уралсиб: новости и изменения",
        "bank_id": "uralsib",
        "bank": "Уралсиб",
        "source_type": "official",
        "kind": "listing",
        "url": "https://uralsib.ru/blog",
    },
    {
        "id": "mkb_news",
        "name": "МКБ: новости",
        "bank_id": "mkb",
        "bank": "МКБ",
        "source_type": "official",
        "kind": "listing",
        "url": "https://mkb.ru/news",
    },
    {
        "id": "rsb_news",
        "name": "Русский Стандарт: новости",
        "bank_id": "rsb",
        "bank": "Русский Стандарт",
        "source_type": "official",
        "kind": "listing",
        "url": "https://www.rsb.ru/press-center/publications/",
    },
    {
        "id": "rsb_premium_landing",
        "name": "Русский Стандарт: Премиум и документы",
        "bank_id": "rsb",
        "bank": "Русский Стандарт",
        "source_type": "official",
        "kind": "landing",
        "url": "https://www.rsb.ru/LP/premium/",
    },
    {
        "id": "gazprombank_press",
        "name": "Пресс-релизы Газпромбанка",
        "bank_id": "gazprombank",
        "bank": "Газпромбанк",
        "source_type": "official",
        "kind": "listing",
        "url": "https://www.gazprombank.ru/press/press/",
    },
    {
        "id": "ozonbank_news",
        "name": "Новости Ozon Банка",
        "bank_id": "ozonbank",
        "bank": "Озон Банк",
        "source_type": "official",
        "kind": "listing",
        "url": "https://finance.ozon.ru/blog/news",
    },
    {
        "id": "raiffeisen_client_news",
        "name": "Новости для клиентов Райффайзен Банка",
        "bank_id": "raiffeisen",
        "bank": "Райффайзен Банк",
        "source_type": "official",
        "kind": "listing",
        "url": "https://www.raiffeisen.ru/about/press/news/",
    },
    {
        "id": "tbank_news",
        "name": "Новости Т-Банка",
        "bank_id": "tbank",
        "bank": "Т-Банк",
        "source_type": "official",
        "kind": "listing",
        "url": "https://www.tbank.ru/about/news-archive/",
    },
    {
        "id": "bankinform_news",
        "name": "БанкИнформСервис",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "listing",
        "url": "https://bankinform.ru/news",
    },
    {
        "id": "ingo_telegram",
        "name": "Официальный канал Инго Банка",
        "bank_id": "ingo",
        "bank": "Инго Банк",
        "source_type": "official",
        "kind": "telegram",
        "url": "https://t.me/s/ingobankru",
    },
    {
        "id": "ingo_premium_launch",
        "name": "Инго Банк: запуск премиального обслуживания",
        "bank_id": "ingo",
        "bank": "Инго Банк",
        "source_type": "official",
        "kind": "telegram",
        "historical": True,
        "include_urls": ["https://t.me/ingobankru/630"],
        "url": "https://t.me/s/ingobankru?before=637",
    },
    {
        "id": "vtb_telegram",
        "name": "Официальный канал ВТБ",
        "bank_id": "vtb",
        "bank": "ВТБ",
        "source_type": "official",
        "kind": "telegram",
        "url": "https://t.me/s/bankvtb",
    },
    {
        "id": "alfa_telegram",
        "name": "Официальный канал Альфа-Банка",
        "bank_id": "alfa",
        "bank": "Альфа-Банк",
        "source_type": "official",
        "kind": "telegram",
        "url": "https://t.me/s/AlfaBank",
    },
    {
        "id": "alfa_only_telegram",
        "name": "Alfa Only",
        "bank_id": "alfa",
        "bank": "Альфа-Банк",
        "source_type": "official",
        "kind": "telegram",
        "url": "https://t.me/s/aaa_only",
    },
    {
        "id": "gazprombank_telegram",
        "name": "Официальный канал Газпромбанка",
        "bank_id": "gazprombank",
        "bank": "Газпромбанк",
        "source_type": "official",
        "kind": "telegram",
        "url": "https://t.me/s/gazprombank",
    },
    {
        "id": "sber_telegram",
        "name": "Официальный канал Сбера",
        "bank_id": "sber",
        "bank": "Сбер",
        "source_type": "official",
        "kind": "telegram",
        "url": "https://t.me/s/sberbank",
    },
    {
        "id": "sberpremier_telegram",
        "name": "Официальный канал СберПремьер",
        "bank_id": "sber",
        "bank": "Сбер",
        "source_type": "official",
        "kind": "telegram",
        "url": "https://t.me/s/sberpremiernew",
    },
    {
        "id": "raiffeisen_telegram",
        "name": "Официальный канал Райффайзен Банка",
        "bank_id": "raiffeisen",
        "bank": "Райффайзен Банк",
        "source_type": "official",
        "kind": "telegram",
        "url": "https://t.me/s/Raiffeisenbankrus",
    },
    {
        "id": "tbank_telegram",
        "name": "Официальный канал Т-Банка",
        "bank_id": "tbank",
        "bank": "Т-Банк",
        "source_type": "official",
        "kind": "telegram",
        "url": "https://t.me/s/tbank",
    },
    {
        "id": "premiumbankinginfo_telegram",
        "name": "Премиум Банкинг Инфо",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/premiumbankinginfo",
    },
    {
        "id": "bankinform_telegram",
        "name": "БанкИнформСервис",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/bankinform_ru",
    },
    {
        "id": "frank_rg_telegram",
        "name": "Frank RG",
        "bank_id": "",
        "bank": "Рынок",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/frank_rg",
    },
    {
        "id": "bank_blog_telegram",
        "name": "БанкБлог",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/bank_blog",
    },
    {
        "id": "blogbankir_telegram",
        "name": "Дайджест банковских новостей",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/blogbankir",
    },
    {
        "id": "banksta_telegram",
        "name": "Банкста",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/banksta",
    },
    {
        "id": "profitanet_telegram",
        "name": "Профита нет. А если найду?",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/profitanet",
    },
    {
        "id": "mediyca_telegram",
        "name": "Медийка",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/mediyca",
    },
    {
        "id": "theblueprint_telegram",
        "name": "The Blueprint",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/theblueprintru",
    },
    {
        "id": "okeymood_telegram",
        "name": "МУД",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/okeymood",
    },
    {
        "id": "fashion_mur_telegram",
        "name": "MUR",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/fashion_mur",
    },
    {
        "id": "ksenia_solovieva_telegram",
        "name": "Ксения Соловьёва",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/ksenia_solovieva",
    },
    {
        "id": "darkmgimo_telegram",
        "name": "Бахчисарайские гвоздики",
        "bank_id": "",
        "bank": "",
        "source_type": "industry",
        "kind": "telegram",
        "url": "https://t.me/s/darkmgimo",
    },
]

# Агрегаторы рыночного уровня — сканируются в --scan-all, raw-снимок для аудита
# Обзорные страницы premiumbanking.info по банкам держим здесь, а не в sources
# конкретных тиров: на одной странице смешаны уровни, для фактов тира
# используются точные URL вида /bank/N.
AGGREGATORS = [
    {
        "id": "premiumbanking_info",
        "name": "premiumbanking.info (обзорная)",
        "urls": ["https://premiumbanking.info/"],
    },
    {
        "id": "pbi_sber",
        "name": "premiumbanking.info — Сбер",
        "urls": ["https://premiumbanking.info/sber"],
    },
    {
        "id": "pbi_alfabank",
        "name": "premiumbanking.info — Альфа-Банк",
        "urls": ["https://premiumbanking.info/alfabank"],
    },
    {
        "id": "pbi_vtb",
        "name": "premiumbanking.info — ВТБ",
        "urls": ["https://premiumbanking.info/vtb"],
    },
    {
        "id": "pbi_gazprombank",
        "name": "premiumbanking.info — Газпромбанк",
        "urls": ["https://premiumbanking.info/gazprombank"],
    },
    {
        "id": "pbi_ozon",
        "name": "premiumbanking.info — Озон Банк",
        "urls": ["https://premiumbanking.info/ozon"],
    },
    {
        "id": "pbi_raiffeisen",
        "name": "premiumbanking.info — Райффайзен Банк",
        "urls": ["https://premiumbanking.info/raiffeisen"],
    },
    {
        "id": "pbi_tbank",
        "name": "premiumbanking.info — Т-Банк",
        "urls": ["https://premiumbanking.info/tbank"],
    },
    {
        "id": "frankrg",
        "name": "Frank RG (рейтинги Premium/Private Banking)",
        "urls": ["https://frankrg.com/"],
    },
]


def tier_sources(bank: dict, tier: dict) -> list:
    """Все источники тира: собственные + банковские extra_sources."""
    sources = []
    for src in list(tier.get("sources", [])) + list(bank.get("extra_sources", [])):
        if src.get("source_id") == "pbi" and len(src.get("urls", [])) > 1:
            urls = src["urls"]
            sources.append({"source_id": "pbi", "urls": [urls[0]]})
            sources.extend(
                {"source_id": "pbi_level", "urls": [url]}
                for url in urls[1:]
            )
        else:
            sources.append(src)
    return sorted(sources, key=lambda src: source_priority_rank(src["source_id"]))


def registered_source_urls() -> set:
    urls = set()
    for bank in BANKS:
        for source in bank.get("extra_sources", []):
            urls.update(source.get("urls", []))
        for tier in bank.get("tiers", []):
            for source in tier.get("sources", []):
                urls.update(source.get("urls", []))
    for source in AGGREGATORS:
        urls.update(source.get("urls", []))
    for source in PREMIUM_NEWS_SOURCES:
        urls.add(source["url"])
    return urls


def get_bank(bank_id: str):
    for bank in BANKS:
        if bank["id"] == bank_id:
            return bank
    return None


def bank_ids():
    return [b["id"] for b in BANKS]
