import unittest

from landing.sber_vs import _compensation_evaluation
from scanner.curated import curated_for
from scanner.sources import (
    AUTHORITATIVE_SOURCE_URLS,
    BANKS,
    PRIORITY_SOURCE_URLS,
    is_authoritative_url,
)


class IngoPremiumTests(unittest.TestCase):
    def setUp(self):
        self.bank = next(bank for bank in BANKS if bank["id"] == "ingo")
        self.tier = self.bank["tiers"][0]
        self.facts = curated_for("ingo_premium")

    def test_ingo_premium_is_registered_as_one_concrete_tier(self):
        self.assertEqual(self.bank["name"], "Инго Банк")
        self.assertEqual(len(self.bank["tiers"]), 1)
        self.assertEqual(self.tier["tier_id"], "ingo_premium")
        self.assertEqual(self.tier["tier_name"], "Инго Premium")
        self.assertEqual(self.tier["segment"], "0–3 млн ₽")

    def test_landing_and_tariff_are_authoritative_sources(self):
        expected = {
            "https://ingobank.ru/premium/",
            "https://cdn.ingos.ru/docs/cards/Tarif_7.pdf",
        }
        configured = {
            url
            for source in self.tier["sources"]
            for url in source["urls"]
        }

        self.assertEqual(configured, expected)
        self.assertTrue(expected <= AUTHORITATIVE_SOURCE_URLS)
        self.assertEqual(
            PRIORITY_SOURCE_URLS["official"]["ingo_premium"],
            "https://cdn.ingos.ru/docs/cards/Tarif_7.pdf",
        )
        for url in expected:
            self.assertTrue(is_authoritative_url(url))

    def test_curated_tariff_facts_keep_official_provenance(self):
        expected_fields = {
            "entry_conditions",
            "service_cost",
            "lounge_access",
            "restaurants",
            "taxi",
            "insurance",
            "cashback",
            "card_terms",
            "transfers_payments",
            "cash_withdrawal",
            "supreme",
            "selectable_options",
            "selection_rules",
        }
        self.assertTrue(expected_fields <= self.facts.keys())

        for field_id in expected_fields:
            with self.subTest(field_id=field_id):
                fact = self.facts[field_id]
                self.assertEqual(
                    fact["source_url"],
                    "https://cdn.ingos.ru/docs/cards/Tarif_7.pdf",
                )
                self.assertEqual(fact["date_checked"], "2026-07-28")

    def test_exact_official_limits_are_not_lost(self):
        self.assertIn("2 500 ₽ в месяц", self.facts["service_cost"]["value"])
        self.assertIn("300 000 ₽", self.facts["entry_conditions"]["value"])
        self.assertIn("2 привилегии", self.facts["lounge_access"]["value"])
        self.assertIn("15 привилегий", self.facts["lounge_access"]["value"])
        self.assertIn("общий", self.facts["restaurants"]["value"].lower())
        self.assertIn("1 поездки", self.facts["taxi"]["value"])
        self.assertIn("1 500", self.facts["taxi"]["value"])
        self.assertIn("1 млн ₽ в день", self.facts["cash_withdrawal"]["value"])
        self.assertIn("3 млн ₽ в месяц", self.facts["cash_withdrawal"]["value"])

    def test_subscription_is_not_confused_with_card_service_cost(self):
        self.assertNotIn("подписк", self.facts["service_cost"]["value"].lower())
        self.assertIn("Без подписки", self.facts["cashback"]["value"])
        self.assertIn("С подпиской", self.facts["cashback"]["value"])

    def test_eligibility_thresholds_are_not_scored_as_compensation(self):
        taxi = _compensation_evaluation(self.facts["taxi"]["value"], "taxi")
        restaurants = _compensation_evaluation(
            self.facts["restaurants"]["value"], "restaurants"
        )

        self.assertEqual(taxi["metrics"]["monthly_count"], 1)
        self.assertEqual(taxi["metrics"]["per_use_limit"], 1500)
        self.assertEqual(taxi["metrics"]["monthly_total"], 1500)
        self.assertNotIn(5_000_000, taxi["metrics"].values())
        self.assertEqual(restaurants["metrics"]["monthly_count"], 2)
        self.assertNotIn("monthly_total", restaurants["metrics"])
        self.assertNotIn("per_use_limit", restaurants["metrics"])


if __name__ == "__main__":
    unittest.main()
