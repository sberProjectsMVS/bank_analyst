import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from landing.sber_vs import (
    CANONICAL_SITE_URL,
    FRESHNESS_INTERVAL_MS,
    _JS,
    _lounge_evaluation,
    _entry_evaluation,
    _compensation_evaluation,
    _insurance_evaluation,
    _sport_beauty_evaluation,
    build_payload,
    build_sber_vs_landing,
    load_summary_rows,
)


def _field(value):
    return {"display_value": value, "value": value, "raw_text": value}


class SberVsAlignmentTests(unittest.TestCase):
    def test_sport_beauty_highlights_direct_access_over_selectable_option(self):
        selectable = _sport_beauty_evaluation(
            "Опция «Спорт и красота» (6000 бонусных рублей Фитмост)"
        )
        direct = _sport_beauty_evaluation(
            "5 тыс баллов в год в сервисе appoint — включено постоянно"
        )

        self.assertEqual(selectable["status"], "comparable")
        self.assertEqual(direct["status"], "comparable")
        self.assertLess(
            selectable["metrics"]["service_rank"],
            direct["metrics"]["service_rank"],
        )
        self.assertIn("не сопоставляются", direct["reason"])

    def _write_fixture(self, tmp):
        rows = []
        banks = [
            (
                "bank_one",
                "Банк Один",
                ("2 млн ₽", "3 млн ₽", "6 млн ₽", "100 млн ₽"),
            ),
            (
                "bank_two",
                "Банк Два с очень длинным названием программы",
                ("2 млн ₽", "6 млн ₽", "10 млн ₽", "30 млн ₽", "100 млн ₽"),
            ),
            (
                "bank_three",
                "Банк Три",
                ("2,5 млн ₽", "6 млн ₽", "12 млн ₽"),
            ),
        ]
        for bank_no, (bank_id, bank_name, thresholds) in enumerate(banks, start=1):
            for level_no, threshold in enumerate(thresholds, start=1):
                rows.append({
                    "bank_id": bank_id,
                    "bank": bank_name,
                    "tier_id": f"{bank_id}_{level_no}",
                    "tier": (
                        f"Премиальная программа с длинным названием — уровень {level_no}"
                    ),
                    "segment": "0–3 млн ₽",
                    "scan_date": "2026-07-17T00:00:00",
                    "sources_ok": 1,
                    "score": {"total": bank_no + level_no / 10, "breakdown": {}},
                    "fields": {
                        "entry_conditions": _field(threshold),
                        "service_cost": _field(f"{level_no} 990 ₽ в месяц"),
                        "lounge_access": _field(f"{level_no} посещений в месяц"),
                    },
                })
        comparison_json = Path(tmp) / "comparison_data.json"
        comparison_json.write_text(
            json.dumps({"schema_version": 1, "rows": rows}, ensure_ascii=False),
            encoding="utf-8",
        )
        output = Path(tmp) / "sber_vs.html"
        with patch("landing.sber_vs.premium_changes.load_changes", return_value=[]):
            build_sber_vs_landing(comparison_json, output)
        return output

    def test_generated_html_uses_bank_vs_bank_level_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = self._write_fixture(tmp)
            html = output.read_text(encoding="utf-8")

        self.assertEqual(html.count('class="picker" data-side='), 2)
        self.assertNotIn("Банк 3", html)
        self.assertNotIn('id="recommendations"', html)
        self.assertIn('id="pair-list" class="pair-list"', html)
        self.assertIn('id="expand-all"', html)
        self.assertIn('id="collapse-all"', html)
        self.assertIn("Выгрузить PDF этого уровня", html)
        self.assertIn("function exportLevelPdf(", html)
        self.assertIn("html2canvas(pairElement", html)
        self.assertIn("function alignLevels(", html)
        self.assertIn("function levelCompatibility(", html)
        self.assertIn("relativeDistance > 0.5", html)
        self.assertIn("--compare-level-count: 2", html)
        self.assertIn("grid-template-columns: var(--compare-grid-template);", html)
        self.assertNotIn("renderRecommendations()", html)

    def test_generated_html_avoids_stale_github_pages_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = self._write_fixture(tmp)
            html = output.read_text(encoding="utf-8")

        self.assertIn(
            '<meta http-equiv="Cache-Control" '
            'content="no-cache, no-store, must-revalidate">',
            html,
        )
        self.assertIn(f'<link rel="canonical" href="{CANONICAL_SITE_URL}">', html)
        self.assertIn(f"const intervalMs = {FRESHNESS_INTERVAL_MS};", html)
        self.assertIn("url.searchParams.set('_fresh', currentBucket);", html)
        self.assertIn("if (event.persisted) refreshStalePage();", html)

    def test_payload_keeps_all_banks_levels_and_long_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = self._write_fixture(tmp)
            html = output.read_text(encoding="utf-8")
            payload = re.search(
                r'<script id="data" type="application/json">(.*?)</script>',
                html,
                flags=re.S,
            ).group(1)
            data = json.loads(payload)

        levels_by_bank = {
            bank["bank"]: len(bank["levels"])
            for bank in data
        }
        self.assertEqual(levels_by_bank, {
            "Банк Один": 4,
            "Банк Два с очень длинным названием программы": 5,
            "Банк Три": 3,
        })
        self.assertTrue(all(
            level["entry_match"]["eligible"]
            for bank in data for level in bank["levels"]
        ))
        bank_one = next(bank for bank in data if bank["bank"] == "Банк Один")
        self.assertEqual(
            bank_one["levels"][1]["entry_match"]["min_amount"],
            3_000_000,
        )
        self.assertIn("очень длинным названием", html)

    def test_alignment_pairs_each_level_at_most_once(self):
        if not shutil.which("node"):
            self.skipTest("Node.js is unavailable")
        algorithm = _JS.split("SIDES.forEach", 1)[0]
        algorithm = algorithm.replace(
            "const DATA = JSON.parse(document.getElementById('data').textContent);",
            "const DATA = [];",
        ).replace(
            "document.documentElement.classList.add('js-ready');",
            "",
        )
        scenario = r"""
function fixtureLevel(id, amount) {
  return {
    tier_id: id,
    entry_match: {
      eligible: true,
      min_amount: amount,
      max_amount: amount,
      label: String(amount)
    }
  };
}
const leftFixture = [
  fixtureLevel('a2', 2000000),
  fixtureLevel('a3', 3000000),
  fixtureLevel('a6', 6000000),
  fixtureLevel('a100', 100000000)
];
const rightFixture = [
  fixtureLevel('b2', 2000000),
  fixtureLevel('b6', 6000000),
  fixtureLevel('b10', 10000000),
  fixtureLevel('b30', 30000000),
  fixtureLevel('b100', 100000000)
];
const alignedFixture = alignLevels(leftFixture, rightFixture);
console.log(JSON.stringify(alignedFixture.map((pair) => ({
  left: pair.left && pair.left.tier_id,
  right: pair.right && pair.right.tier_id,
  kind: pair.match && pair.match.id
}))));
"""
        result = subprocess.run(
            ["node"],
            input=algorithm + scenario,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        pairs = json.loads(result.stdout)
        used_left = [pair["left"] for pair in pairs if pair["left"]]
        used_right = [pair["right"] for pair in pairs if pair["right"]]
        self.assertEqual(used_left, ["a2", "a3", "a6", "a100"])
        self.assertEqual(used_right, ["b2", "b6", "b10", "b30", "b100"])
        self.assertEqual(len(used_left), len(set(used_left)))
        self.assertEqual(len(used_right), len(set(used_right)))
        exact_pairs = {
            (pair["left"], pair["right"])
            for pair in pairs
            if pair["kind"] == "exact"
        }
        self.assertEqual(exact_pairs, {
            ("a2", "b2"),
            ("a6", "b6"),
            ("a100", "b100"),
        })

    def test_access_program_count_is_informational_when_visits_are_equal(self):
        if not shutil.which("node"):
            self.skipTest("Node.js is unavailable")
        left = _lounge_evaluation(
            "Включено постоянно: безлимит. Доступ через Mir Pass, "
            "ON·PASS, Частично и ON·PASS Premium."
        )
        right = _lounge_evaluation(
            "безлимит. Доступ через MILE·ON·AIR, ON·PASS, ON·PASS Premium, "
            "Phoenix Pass, Phoenix Pass Exclusive, Grey Wall и Persona.aero."
        )
        self.assertEqual(left["metrics"]["access_programs"], 4)
        self.assertEqual(right["metrics"]["access_programs"], 7)

        algorithm = _JS.split("SIDES.forEach", 1)[0]
        algorithm = algorithm.replace(
            "const DATA = JSON.parse(document.getElementById('data').textContent);",
            "const DATA = [];",
        ).replace(
            "document.documentElement.classList.add('js-ready');",
            "",
        )
        scenario = f"""
const loungeEntries = [
  {{ side: 'a', attr: {{ id: 'lounge_access', score: null, value: 'безлимит' }},
     evaluation: {json.dumps(left, ensure_ascii=False)} }},
  {{ side: 'b', attr: {{ id: 'lounge_access', score: null, value: 'безлимит' }},
     evaluation: {json.dumps(right, ensure_ascii=False)} }}
];
console.log(JSON.stringify(rankEvaluations(loungeEntries)));
"""
        result = subprocess.run(
            ["node"],
            input=algorithm + scenario,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ranks = {item["side"]: item for item in json.loads(result.stdout)}
        self.assertEqual(
            {side: item["status"] for side, item in ranks.items()},
            {"a": "equal", "b": "equal"},
        )
        self.assertTrue(all(
            item["cls"] == "rank-mid" and item["label"] == "равно"
            for item in ranks.values()
        ))

    def test_two_preferences_normalize_to_two_lounge_visits(self):
        evaluation = _lounge_evaluation(
            "До 2 проходов в месяц, если направить весь общий баланс "
            "(2 преференции в месяц из общего баланса; "
            "1 преференция = 1 использование выбранного сервиса) "
            "на бизнес-залы."
        )
        self.assertEqual(evaluation["metrics"]["visits_monthly"], 2)
        self.assertEqual(evaluation["metrics"]["shared_preference_pool"], 1)
        self.assertIn("общего баланса", evaluation["reason"])

    def test_entry_evaluation_accounts_for_and_or_structure(self):
        single = _entry_evaluation("3 млн ₽ на счетах")
        combined = _entry_evaluation("2 млн ₽ на счетах и траты 100 тыс ₽ в месяц")
        alternatives = _entry_evaluation(
            "3 млн ₽ на счетах или 2 млн ₽ на счетах и траты 100 тыс ₽ в месяц"
        )
        self.assertEqual(single["metrics"]["mandatory_count"], 1)
        self.assertEqual(combined["metrics"]["mandatory_count"], 2)
        self.assertEqual(alternatives["metrics"]["alternative_count"], 2)
        self.assertEqual(alternatives["directions"]["alternative_count"], "higher")
        self.assertIn("«И»", alternatives["reason"])

        sber = _entry_evaluation(
            "3 млн ₽; или траты 200 тыс ₽; или 8000 акций (≈2,200,000₽)"
        )
        vtb = _entry_evaluation(
            "Москва: активы от 2,5 млн ₽ либо активы от 1,5 млн ₽ и "
            "покупки от 125 000 ₽ в месяц. Другие регионы: активы от "
            "2 млн ₽ либо активы от 1,5 млн ₽ и покупки от 100 000 ₽ в месяц"
        )
        self.assertEqual(sber["metrics"]["standalone_capital_threshold"], 3_000_000)
        self.assertEqual(vtb["metrics"]["standalone_capital_threshold"], 2_500_000)

    def test_vtb_sapphire_entry_threshold_ranks_stronger_than_sber_level_2(self):
        if not shutil.which("node"):
            self.skipTest("Node.js is unavailable")
        sber = _entry_evaluation(
            "3 млн ₽; или траты 200 тыс ₽; или 8000 акций (≈2,200,000₽)"
        )
        vtb = _entry_evaluation(
            "Москва: активы от 2,5 млн ₽ либо активы от 1,5 млн ₽ и "
            "покупки от 125 000 ₽ в месяц. Другие регионы: активы от "
            "2 млн ₽ либо активы от 1,5 млн ₽ и покупки от 100 000 ₽ в месяц"
        )
        algorithm = _JS.split("SIDES.forEach", 1)[0]
        algorithm = algorithm.replace(
            "const DATA = JSON.parse(document.getElementById('data').textContent);",
            "const DATA = [];",
        ).replace(
            "document.documentElement.classList.add('js-ready');", "",
        )
        scenario = f"""
const entryRanks = rankEvaluations([
  {{side:'a',attr:{{id:'entry_conditions',value:'Сбер'}},
    evaluation:{json.dumps(sber, ensure_ascii=False)}}},
  {{side:'b',attr:{{id:'entry_conditions',value:'ВТБ'}},
    evaluation:{json.dumps(vtb, ensure_ascii=False)}}}
]);
console.log(JSON.stringify(entryRanks));
"""
        result = subprocess.run(
            ["node"], input=algorithm + scenario, text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ranks = json.loads(result.stdout)
        self.assertEqual(
            [(item["cls"], item["label"]) for item in ranks],
            [("rank-low", "слабее"), ("rank-best", "сильнее")],
        )
        self.assertIn("3 млн ₽ против 2,5 млн ₽", ranks[0]["reason"])

    def test_sber_vtb_lounges_equal_and_vtb_cashback_cap_is_stronger(self):
        if not shutil.which("node"):
            self.skipTest("Node.js is unavailable")
        algorithm = _JS.split("SIDES.forEach", 1)[0]
        algorithm = algorithm.replace(
            "const DATA = JSON.parse(document.getElementById('data').textContent);",
            "const DATA = [];",
        ).replace(
            "document.documentElement.classList.add('js-ready');",
            "",
        )
        sber_lounge = _lounge_evaluation(
            "2 посещения в месяц. Доступ через Mir Pass."
        )
        vtb_lounge = _lounge_evaluation(
            "До 2 проходов в месяц из общего баланса: 2 преференции в месяц; "
            "1 преференция = 1 использование выбранного сервиса. "
            "Доступ через ON·PASS и ON·PASS Premium."
        )
        scenario = f"""
const lounge = rankEvaluations([
  {{side:'a', bank:'Сбер', tierId:'sber_premier_2',
    attr:{{id:'lounge_access', value:'2 посещения'}},
    evaluation:{json.dumps(sber_lounge, ensure_ascii=False)}}},
  {{side:'b', bank:'ВТБ', tierId:'vtb_privilege_2',
    attr:{{id:'lounge_access', value:'2 прохода'}},
    evaluation:{json.dumps(vtb_lounge, ensure_ascii=False)}}}
]);
const cashback = rankEvaluations([
  {{side:'a', bank:'Сбер', tierId:'sber_premier_2',
    attr:{{id:'cashback', value:'до 10%, 5 категорий, 20 000 бонусов'}},
    evaluation:{{status:'comparable', method:'cashback',
      metrics:{{max_rate:10,categories:5,monthly_bonus_cap:20000}},
      directions:{{max_rate:'higher',categories:'higher',monthly_bonus_cap:'higher'}},
      scope:{{}}, summary:'до 10%'}}}},
  {{side:'b', bank:'ВТБ', tierId:'vtb_privilege_2',
    attr:{{id:'cashback', value:'5 категорий, до 30 000 ₽'}},
    evaluation:{{status:'comparable', method:'cashback',
      metrics:{{categories:5,monthly_cap:30000}},
      directions:{{categories:'higher',monthly_cap:'higher'}},
      scope:{{}}, summary:'ставка не опубликована'}}}}
]);
console.log(JSON.stringify({{lounge, cashback}}));
"""
        result = subprocess.run(
            ["node"], input=algorithm + scenario, text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            [item["status"] for item in report["lounge"]],
            ["equal", "equal"],
        )
        self.assertEqual(
            [item["status"] for item in report["cashback"]],
            ["comparable", "comparable"],
        )
        self.assertTrue(all(item["cls"] == "rank-mid" for item in report["lounge"]))
        self.assertEqual(
            [item["label"] for item in report["lounge"]],
            ["равно", "равно"],
        )
        self.assertEqual(
            [item["label"] for item in report["cashback"]],
            ["слабее", "сильнее"],
        )
        self.assertIn(
            "20 тыс ₽ против 30 тыс ₽",
            report["cashback"][0]["reason"],
        )

    def test_taxi_restaurants_and_insurance_are_not_false_equals(self):
        if not shutil.which("node"):
            self.skipTest("Node.js is unavailable")
        evaluations = {
            "sber_taxi": _compensation_evaluation(
                "1 посещение в месяц по 1000 ₽ — опция на выбор", "taxi"
            ),
            "vtb_taxi": _compensation_evaluation(
                "До 2 компенсаций поездок на такси в месяц; до 1000 ₽ за чек",
                "taxi",
            ),
            "sber_restaurants": _compensation_evaluation(
                "1 посещение в месяц на 2000 ₽ — опция на выбор", "restaurants"
            ),
            "vtb_restaurants": _compensation_evaluation(
                "До 2 компенсаций чеков в месяц; до 2500 ₽ за один чек",
                "restaurants",
            ),
            "sber_insurance": _insurance_evaluation(
                "30 000 евро в РФ и 100 000 евро за рубежом; до 90 дней"
            ),
            "vtb_insurance": _insurance_evaluation(
                "Страховое покрытие: $100 тыс для владельца / "
                "$100 тыс для члена семьи, 90 дней"
            ),
        }
        algorithm = _JS.split("SIDES.forEach", 1)[0]
        algorithm = algorithm.replace(
            "const DATA = JSON.parse(document.getElementById('data').textContent);",
            "const DATA = [];",
        ).replace(
            "document.documentElement.classList.add('js-ready');", "",
        )
        scenario = f"""
function pair(left, right, id) {{
  return rankEvaluations([
    {{side:'a',attr:{{id,value:'Сбер'}},evaluation:left}},
    {{side:'b',attr:{{id,value:'ВТБ'}},evaluation:right}}
  ]);
}}
const evaluations = {json.dumps(evaluations, ensure_ascii=False)};
const report = {{
  taxi: pair(evaluations.sber_taxi, evaluations.vtb_taxi, 'taxi'),
  restaurants: pair(evaluations.sber_restaurants,
    evaluations.vtb_restaurants, 'restaurants'),
  insurance: pair(evaluations.sber_insurance,
    evaluations.vtb_insurance, 'insurance'),
  incomparable: pair(
    {{status:'incomparable',method:'none',metrics:{{}},directions:{{}},
      scope:{{}},summary:'разные условия',reason:'Нет общей метрики'}},
    {{status:'incomparable',method:'none',metrics:{{}},directions:{{}},
      scope:{{}},summary:'другие условия',reason:'Нет общей метрики'}},
    'other_benefits')
}};
console.log(JSON.stringify(report));
"""
        result = subprocess.run(
            ["node"], input=algorithm + scenario, text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            [(item["cls"], item["label"]) for item in report["taxi"]],
            [("rank-low", "слабее"), ("rank-best", "сильнее")],
        )
        self.assertEqual(
            [(item["cls"], item["label"]) for item in report["restaurants"]],
            [("rank-low", "слабее"), ("rank-best", "сильнее")],
        )
        self.assertEqual(
            [(item["cls"], item["label"]) for item in report["insurance"]],
            [("rank-best", "сильнее"), ("rank-low", "слабее")],
        )
        self.assertTrue(all(
            not item["cls"] and not item["label"]
            for item in report["incomparable"]
        ))

    def test_missing_equal_and_composite_values_use_red_green_yellow(self):
        if not shutil.which("node"):
            self.skipTest("Node.js is unavailable")
        algorithm = _JS.split("SIDES.forEach", 1)[0]
        algorithm = algorithm.replace(
            "const DATA = JSON.parse(document.getElementById('data').textContent);",
            "const DATA = [];",
        ).replace(
            "document.documentElement.classList.add('js-ready');", "",
        )
        equal_limit = {
            "status": "comparable", "method": "limit",
            "metrics": {"unlimited": False, "limits": [
                {"amount": 1_000_000, "period": "month"}
            ]},
            "directions": {}, "scope": {"operation_scope": "general_cash"},
            "summary": "1 000 000 ₽ в месяц", "reason": "",
        }
        composite_left = {
            "status": "comparable", "method": "composite",
            "metrics": {"components": {
                "internal": {"label": "Внутри банка", "present": True,
                             "evaluation": equal_limit},
                "sbp": {"label": "СБП", "present": True,
                        "evaluation": equal_limit},
            }},
            "directions": {}, "scope": {"group": "transfers"},
            "summary": "", "reason": "",
        }
        composite_right = json.loads(json.dumps(composite_left))
        composite_right["metrics"]["components"]["sbp"]["present"] = False
        composite_right["metrics"]["components"]["sbp"]["evaluation"] = {
            "status": "missing", "method": "none", "metrics": {},
            "directions": {}, "scope": {}, "summary": "Нет данных", "reason": "",
        }
        scenario = f"""
const missing = rankEvaluations([
  {{side:'a', attr:{{id:'x',value:'Есть'}}, evaluation:{{status:'comparable',
    method:'ordinal',metrics:{{service_rank:1}},directions:{{service_rank:'higher'}},
    scope:{{}},summary:'Есть',reason:''}}}},
  {{side:'b', attr:{{id:'x',value:'Не найдено в доступных источниках'}},
    evaluation:{{status:'missing',method:'none',metrics:{{}},directions:{{}},
    scope:{{}},summary:'Нет данных',reason:''}}}}
]);
const bothMissing = rankEvaluations([
  {{side:'a',attr:{{id:'x',value:'Не найдено в доступных источниках'}},
    evaluation:{{status:'missing',method:'none',metrics:{{}},directions:{{}},
    scope:{{}},summary:'Нет данных',reason:''}}}},
  {{side:'b',attr:{{id:'x',value:'Нет данных'}},
    evaluation:{{status:'missing',method:'none',metrics:{{}},directions:{{}},
    scope:{{}},summary:'Нет данных',reason:''}}}}
]);
const equal = rankEvaluations([
  {{side:'a',attr:{{id:'cash',value:'1 млн ₽/мес'}},
    evaluation:{json.dumps(equal_limit, ensure_ascii=False)}}},
  {{side:'b',attr:{{id:'cash',value:'1 млн ₽/мес'}},
    evaluation:{json.dumps(equal_limit, ensure_ascii=False)}}}
]);
const composite = rankEvaluations([
  {{side:'a',attr:{{id:'transfers_summary',value:'данные'}},
    evaluation:{json.dumps(composite_left, ensure_ascii=False)}}},
  {{side:'b',attr:{{id:'transfers_summary',value:'данные'}},
    evaluation:{json.dumps(composite_right, ensure_ascii=False)}}}
]);
console.log(JSON.stringify({{missing,bothMissing,equal,composite}}));
"""
        result = subprocess.run(
            ["node"], input=algorithm + scenario, text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            [(item["cls"], item["label"]) for item in report["missing"]],
            [("rank-best", "сильнее"), ("rank-low", "слабее")],
        )
        self.assertEqual(
            [(item["cls"], item["label"]) for item in report["bothMissing"]],
            [("rank-mid", "равно"), ("rank-mid", "равно")],
        )
        self.assertEqual(
            [(item["cls"], item["label"]) for item in report["equal"]],
            [("rank-mid", "равно"), ("rank-mid", "равно")],
        )
        self.assertEqual(
            [(item["cls"], item["label"]) for item in report["composite"]],
            [("rank-best", "сильнее"), ("rank-low", "слабее")],
        )

    def test_rank_bruteforce_all_actual_pairs_is_symmetric_and_deterministic(self):
        if not shutil.which("node"):
            self.skipTest("Node.js is unavailable")
        project_root = Path(__file__).resolve().parent.parent
        payload = build_payload(
            load_summary_rows(project_root / "output" / "comparison_data.json")
        )
        algorithm = _JS.split("SIDES.forEach", 1)[0]
        algorithm = algorithm.replace(
            "const DATA = JSON.parse(document.getElementById('data').textContent);",
            "const DATA = [];",
        ).replace(
            "document.documentElement.classList.add('js-ready');",
            "",
        )
        scenario = f"""
const auditPayload = {json.dumps(payload, ensure_ascii=False)};
const auditLevels = auditPayload.flatMap((bank) => bank.levels.map(
  (level) => ({{ bank: bank.bank, level }})
));
const auditFields = [...new Set(auditLevels.flatMap(
  (item) => item.level.attrs.map((attr) => attr.id)
))].sort();
const violations = [];
let checked = 0;
let monotonicChecked = 0;

function auditEntry(item, field, side) {{
  const attr = item.level.attrs.find((candidate) => candidate.id === field);
  return {{
    side,
    bank: item.bank,
    tierId: item.level.tier_id,
    attr,
    evaluation: attr.evaluation
  }};
}}

function resultSignature(result) {{
  return {{
    status: result.status || null,
    label: result.label || null,
    cls: result.cls || null
  }};
}}

function resultFor(results, side) {{
  return resultSignature(results.find((item) => item.side === side));
}}

for (const field of auditFields) {{
  const candidates = auditLevels.filter(
    (item) => item.level.attrs.some((attr) => attr.id === field)
  );
  for (let i = 0; i < candidates.length; i += 1) {{
    for (let j = i; j < candidates.length; j += 1) {{
      const left = auditEntry(candidates[i], field, 'a');
      const right = auditEntry(candidates[j], field, 'b');
      const direct = rankEvaluations([left, right]);
      const repeat = rankEvaluations([left, right]);
      const swapped = rankEvaluations([
        auditEntry(candidates[j], field, 'a'),
        auditEntry(candidates[i], field, 'b')
      ]);
      checked += 1;
      if (!deepEqual(direct.map(resultSignature), repeat.map(resultSignature))) {{
        violations.push({{ kind: 'nondeterministic', field, i, j }});
      }}
      if (!deepEqual(resultFor(direct, 'a'), resultFor(swapped, 'b'))
          || !deepEqual(resultFor(direct, 'b'), resultFor(swapped, 'a'))) {{
        violations.push({{ kind: 'asymmetric', field, i, j }});
      }}
      if (i === j
          && !deepEqual(resultFor(direct, 'a'), resultFor(direct, 'b'))) {{
        violations.push({{ kind: 'not_reflexive', field, i, j }});
      }}
    }}
  }}
}}

for (const item of auditLevels) {{
  for (const attr of item.level.attrs) {{
    const evaluation = attr.evaluation || {{}};
    if (evaluation.status !== 'comparable') continue;
    for (const [key, direction] of Object.entries(evaluation.directions || {{}})) {{
      const original = Number((evaluation.metrics || {{}})[key]);
      if (!Number.isFinite(original) || !['higher', 'lower'].includes(direction)) continue;
      const delta = Math.max(1, Math.abs(original) * 0.1);
      const improvedValue = direction === 'higher'
        ? original + delta
        : original - delta;
      const improvedEvaluation = {{
        ...evaluation,
        metrics: {{ ...evaluation.metrics, [key]: improvedValue }}
      }};
      const baselineEntry = {{
        side: 'a', bank: item.bank, tierId: item.level.tier_id,
        attr, evaluation
      }};
      const improvedEntry = {{
        ...baselineEntry, side: 'b', evaluation: improvedEvaluation
      }};
      monotonicChecked += 1;
      const structured = compareEvaluations(improvedEvaluation, evaluation);
      if (structured.order !== null && structured.order < 0) {{
        violations.push({{
          kind: 'reversed_structured_metric', field: attr.id, metric: key,
          bank: item.bank, tier: item.level.tier_id
        }});
      }}
    }}
  }}
}}
console.log(JSON.stringify({{
  checked,
  monotonicChecked,
  fields: auditFields.length,
  levels: auditLevels.length,
  violations: violations.slice(0, 20),
  violationCount: violations.length
}}));
"""
        result = subprocess.run(
            ["node"],
            input=algorithm + scenario,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        print(
            "comparison audit: "
            f"{report['checked']} pairs, "
            f"{report['monotonicChecked']} metric mutations, "
            f"{report['violationCount']} violations"
        )
        self.assertGreater(report["checked"], 9_000)
        self.assertGreater(report["monotonicChecked"], 100)
        self.assertEqual(report["fields"], len({
            field
            for bank in payload
            for level in bank["levels"]
            for field in (attr["id"] for attr in level["attrs"])
        }))
        self.assertEqual(report["violationCount"], 0, report["violations"])

    def test_level_map_is_unique_expandable_and_responsive_if_browser_available(self):
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        with tempfile.TemporaryDirectory() as tmp:
            output = self._write_fixture(tmp)
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    try:
                        page = browser.new_page(viewport={"width": 1440, "height": 900})
                        page.goto(output.as_uri())
                        page.wait_for_load_state("networkidle")
                        page.locator('.picker[data-side="a"]').get_by_role(
                            "button", name="Банк Один", exact=True
                        ).click()
                        page.locator('.picker[data-side="b"]').get_by_role(
                            "button",
                            name="Банк Два с очень длинным названием программы",
                            exact=True,
                        ).click()
                        page.locator("#compare").wait_for(state="visible")

                        tier_ids = page.locator(
                            "#pair-list .pair-level[data-tier-id]"
                        ).evaluate_all(
                            "(nodes) => nodes.map((node) => node.dataset.tierId)"
                        )
                        self.assertEqual(len(tier_ids), 9)
                        self.assertEqual(len(set(tier_ids)), 9)
                        self.assertEqual(
                            page.locator("#pair-list .level-pair").count(), 6
                        )
                        self.assertEqual(
                            page.locator(".match-badge.exact").count(), 3
                        )
                        self.assertEqual(
                            page.locator(".match-badge.unmatched").count(), 3
                        )
                        self.assertIn(
                            "9 уровней · 3 сопоставленных пар · "
                            "3 без прямого аналога",
                            page.locator("#map-summary").inner_text(),
                        )

                        first_pair = page.locator(".level-pair").first
                        first_pair.locator("summary").click()
                        self.assertTrue(first_pair.evaluate("(node) => node.open"))
                        first_pair.locator(".cmp-table").wait_for(state="visible")
                        self._assert_detail_alignment(page)

                        page.locator("#expand-all").click()
                        self.assertTrue(page.locator(".level-pair").evaluate_all(
                            "(nodes) => nodes.every((node) => node.open)"
                        ))
                        page.locator("#collapse-all").click()
                        self.assertTrue(page.locator(".level-pair").evaluate_all(
                            "(nodes) => nodes.every((node) => !node.open)"
                        ))

                        page.set_viewport_size({"width": 390, "height": 900})
                        page.locator(".level-pair").first.locator("summary").click()
                        has_overflow = page.locator("main.page").evaluate(
                            "(node) => node.scrollWidth > node.clientWidth"
                        )
                        self.assertFalse(has_overflow)
                        widths = page.locator(
                            ".level-pair"
                        ).first.locator(".cmp-table tbody tr").first.locator(
                            "td"
                        ).evaluate_all(
                            "(cells) => cells.map((cell) => "
                            "Math.round(cell.getBoundingClientRect().width))"
                        )
                        self.assertEqual(len(set(widths)), 1)
                    finally:
                        browser.close()
            except PlaywrightError as exc:
                self.skipTest(f"Playwright browser is unavailable: {exc}")

    def _assert_detail_alignment(self, page):
        boxes = page.evaluate(
            """
            () => {
              const pair = document.querySelector('.level-pair');
              const heads = [...pair.querySelectorAll('.cmp-table thead th')].slice(1)
                .map((node) => node.getBoundingClientRect());
              const cells = [...pair.querySelectorAll('.cmp-table tbody tr:first-child td')]
                .slice(1)
                .map((node) => node.getBoundingClientRect());
              return heads.map((head, i) => ({
                headLeft: head.left,
                headWidth: head.width,
                cellLeft: cells[i].left,
                cellWidth: cells[i].width
              }));
            }
            """
        )
        for box in boxes:
            self.assertLess(abs(box["headLeft"] - box["cellLeft"]), 1)
            self.assertLess(abs(box["headWidth"] - box["cellWidth"]), 1)


if __name__ == "__main__":
    unittest.main()
