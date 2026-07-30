import unittest

from scanner.curated import curated_for
from scanner.sources import BANKS, is_authoritative_url
from landing.sber_vs import _entry_match_from_text


VTB_UPDATE = "https://www.vtb.ru/promo/rsvtb-pv-2/"


class VtbJuly2026Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vtb = next(bank for bank in BANKS if bank["id"] == "vtb")
        cls.tiers = {
            tier["tier_id"]: tier for tier in cls.vtb["tiers"]
        }

    def test_privilege_level_names_and_official_source(self):
        expected = {
            "vtb_privilege_1": "Привилегия — Изумруд",
            "vtb_privilege_2": "Привилегия — Сапфир",
            "vtb_privilege_3": "Привилегия — Рубин",
            "vtb_privilege_4": "Привилегия — Бриллиант",
        }
        for tier_id, tier_name in expected.items():
            with self.subTest(tier_id=tier_id):
                tier = self.tiers[tier_id]
                self.assertEqual(tier["tier_name"], tier_name)
                self.assertEqual(tier["sources"][0]["urls"], [VTB_UPDATE])
                self.assertTrue(is_authoritative_url(VTB_UPDATE))

    def test_level_entry_conditions_match_official_landing(self):
        emerald = curated_for("vtb_privilege_1")["entry_conditions"]
        sapphire = curated_for("vtb_privilege_2")["entry_conditions"]
        ruby = curated_for("vtb_privilege_3")["entry_conditions"]
        diamond = curated_for("vtb_privilege_4")["entry_conditions"]

        self.assertIn("до 2,5 млн ₽", emerald["value"])
        self.assertIn("до 2 млн ₽", emerald["value"])
        for marker in (
            "от 2,5 млн ₽",
            "от 1,5 млн ₽",
            "от 125 000 ₽",
            "от 2 млн ₽",
            "от 100 000 ₽",
        ):
            self.assertIn(marker, sapphire["value"])
        self.assertIn("от 6 млн ₽", ruby["value"])
        self.assertIn("от 10 млн ₽", diamond["value"])

        for fact in (emerald, sapphire, ruby, diamond):
            self.assertEqual(fact["source_url"], VTB_UPDATE)
            self.assertEqual(fact["date_checked"], "2026-07-28")

    def test_preference_counts_and_shared_pool(self):
        for tier_id, count in (
            ("vtb_privilege_2", 2),
            ("vtb_privilege_3", 6),
            ("vtb_privilege_4", 10),
        ):
            facts = curated_for(tier_id)
            with self.subTest(tier_id=tier_id):
                preference_word = (
                    "преференции" if count == 2 else "преференций"
                )
                self.assertIn(
                    f"{count} {preference_word} в месяц",
                    facts["selection_rules"]["value"],
                )
                self.assertIn(
                    f"До {count} проходов в месяц",
                    facts["lounge_access"]["value"],
                )
                self.assertIn(
                    f"До {count} компенсаций поездок",
                    facts["taxi"]["value"],
                )
                self.assertIn(
                    f"До {count} компенсаций чеков",
                    facts["restaurants"]["value"],
                )
                self.assertIn(
                    "1 преференция = 1 использование",
                    facts["selection_rules"]["value"],
                )
                self.assertIn("до 1 000 ₽", facts["taxi"]["value"])
                self.assertIn("до 2 500 ₽", facts["restaurants"]["value"])

    def test_sapphire_card_uses_standalone_regional_asset_thresholds(self):
        value = curated_for("vtb_privilege_2")["entry_conditions"]["value"]
        match = _entry_match_from_text(value)

        self.assertTrue(match["eligible"])
        self.assertEqual(match["min_amount"], 2_000_000)
        self.assertEqual(match["max_amount"], 2_500_000)
        self.assertEqual(match["label"], "2–2,5 млн ₽ по региону")

    def test_emerald_card_is_an_upper_bound_not_an_entry_minimum(self):
        value = curated_for("vtb_privilege_1")["entry_conditions"]["value"]
        match = _entry_match_from_text(value)

        self.assertTrue(match["eligible"])
        self.assertEqual(match["min_amount"], 0)
        self.assertEqual(match["max_amount"], 2_500_000)
        self.assertEqual(match["label"], "до 2–2,5 млн ₽ по региону")

    def test_new_cashback_applies_to_privilege_but_not_prime_plus(self):
        privilege = curated_for("vtb_privilege_2")["cashback"]
        prime = curated_for("vtb_prime_5")["cashback"]

        self.assertIn("5 категорий", privilege["value"])
        self.assertIn("30 000 ₽", privilege["value"])
        self.assertIn("26 августа", privilege["value"])
        self.assertEqual(privilege["source_url"], VTB_UPDATE)

        self.assertIn("3 категории", prime["value"])
        self.assertNotEqual(prime["source_url"], VTB_UPDATE)

    def test_emerald_does_not_invent_preference_count(self):
        facts = curated_for("vtb_privilege_1")
        self.assertNotIn("selection_rules", facts)
        self.assertNotIn("lounge_access", facts)
        self.assertNotIn("taxi", facts)
        self.assertNotIn("restaurants", facts)


if __name__ == "__main__":
    unittest.main()
