# Complete Gazprombank card facts and traffic-light comparisons

This ExecPlan is a living document maintained in accordance with `PLANS.md`. It covers the current Gazprombank facts for transfers and payments, cashback, cash withdrawal, and premium cards across Premium levels 1–3 and Private.

## Purpose / Big Picture

After this change, the Gazprombank comparison will no longer show missing cashback for Premium levels 1–3, will show the current official cash-withdrawal conditions instead of a vague statement, and will show the officially confirmed PRIME card and current cashback terms for Private. Every populated fact will retain its exact source URL, source type, check date, and raw evidence. The traffic lights will use the confirmed percentages and limits rather than treating missing text as a weak tariff.

## Progress

- [x] (2026-07-24) Inspected the current comparison records and identified which fields are missing.
- [x] (2026-07-24) Verified the current official Premium package tariff, cashback rules, Premium card page, Private package page, and Private transfer tariff.
- [x] (2026-07-24) Rendered and visually inspected the relevant Premium tariff and cashback PDF pages.
- [x] (2026-07-24) Updated the Gazprombank source registry and curated facts without transferring conditions between Premium and Private.
- [x] (2026-07-24) Added regression tests for values, provenance, effective versions, and comparison metrics.
- [x] (2026-07-24) Rescanned Gazprombank, rebuilt and published the landing, and verified the rendered traffic lights for Premium levels 1–3 and Private.
- [x] (2026-07-24) Rechecked the official Private transfer documents after the same-bank comparison displayed Private as weaker; confirmed that the documents describe account transfers rather than the Premium card/SBP channels.
- [x] (2026-07-24) Added and verified a narrowly scoped same-bank hierarchy fallback for Gazprombank transfers when Private and Premium channels are not directly comparable.

## Surprises & Discoveries

- Observation: The configured Gazprom Bonus Premium PDF dated 27 January 2026 is superseded.
  Evidence: the current official Premium page links a package tariff effective 22 July 2026, service conditions effective 6 July 2026, and cashback rules effective 1 June through 31 July 2026.
- Observation: Premium transfers, cash withdrawal, and Mir Supreme were already present in curated data, but cashback was missing and cash withdrawal lacked the published thresholds.
  Evidence: `output/comparison_data.json` contains the three existing fields for `gpb_premium_1` through `gpb_premium_3`, while cashback is `не найдено`.
- Observation: The public Private package page confirms cashback and the PRIME card family but does not publish a comparable ATM withdrawal limit.
  Evidence: the page states cashback up to 15% in the main category and up to 20% for health or travel, and lists plastic and instant cards, a sticker, a ring, and PRIME card discounts. No cash-withdrawal limit appears on that page.
- Observation: The current Private transfer tariff cannot be ranked numerically against Premium's card transfers.
  Evidence: the Private document effective 1 June 2026 publishes commissions for transfers from a bank account, while Premium publishes fee-free limits for SBP and card-number transfers. The previous generic fallback reduced the Private text to a presence score and therefore painted the senior package red.

## Decision Log

- Decision: Use only documents effective on 24 July 2026 for current Premium values.
  Rationale: The source policy requires current official values to win over older official documents.
  Date/Author: 2026-07-24 / Codex
- Decision: Do not copy Premium cash-withdrawal or Mir Supreme terms into Private.
  Rationale: Premium and Private are separate products and the source policy explicitly forbids transferring facts between levels or products.
  Date/Author: 2026-07-24 / Codex
- Decision: Populate Private PRIME and cashback from the official Private package page, but leave Private cash withdrawal missing unless a direct source is found.
  Rationale: A visible missing fact is preferable to an invented or transferred condition.
  Date/Author: 2026-07-24 / Codex
- Decision: In a comparison containing only Gazprombank levels, rank Private above Premium for the transfers row only when the published transfer channels are not directly comparable.
  Rationale: This preserves the sourced text and does not invent a free limit, while preventing a generic fallback score from presenting the senior Private package as definitively worse. The cell explanation must disclose that package hierarchy was used because the channels differ.
  Date/Author: 2026-07-24 / Codex

## Outcomes & Retrospective

The current official Gazprombank card facts are now present in the comparison with provenance. Premium levels 1–3 show cashback up to 6% with a 40,000-point monthly cap, free SBP transfers up to 200,000 ₽, free card-number transfers up to 50,000 ₽, conditional fee-free cash withdrawal in all banks' ATMs, and Mir Supreme with four free additional cards. Private shows cashback up to 20%, the published account-transfer tariff, and the PRIME card family. Its cash-withdrawal field remains explicitly missing because no comparable public official limit was found.

The rendered comparison was exercised again after the follow-up correction. In a Gazprombank Premium 1 / Premium 3 / Private comparison, the transfer cells now have CSS classes `rank-low`, `rank-low`, and `rank-best`. The visible explanation says that Private is the senior level and that the transfer channels differ. No factual limit was copied or invented. Private cash withdrawal still has no traffic-light class because there is no sourced value. The full structured test suite passes (85 tests), source listing succeeds, and the landing is ready for republication.

## Context and Orientation

`scanner/sources.py` is the registry of monitored URLs. `scanner/curated.py` contains manually verified facts, each carrying a value, source URL, source name, raw text, check date, source type, and reliability. `output/comparison_data.json` is the only user-facing data source for `landing/sber_vs.py`. The landing converts cashback rates, transfer limits, cash limits, and card availability into structured metrics used by the red-yellow-green traffic lights.

The Premium package and Private package are different products. A fact confirmed for Premium levels 1–3 cannot be copied to Private. PremiumBanking.info may be used only as fallback when the official source is missing, and it must not override an official value.

## Plan of Work

First save and render the relevant official PDF pages to confirm that extracted table rows have been read in the correct columns. Then replace the stale Gazprombank source URLs in `scanner/sources.py` with the current package, service, and cashback documents, while assigning Private its own package and transfer sources. In `scanner/curated.py`, add a shared current Premium cashback fact, expand the Premium cash-withdrawal fact with the confirmed thresholds, and add official Private cashback and PRIME facts. Add tests in `tests/test_premium_structured.py` that assert both the displayed facts and the numerical comparison metrics. Finally run a Gazprombank scan, rebuild the landing, and exercise the comparison in a browser.

For the follow-up transfer correction, preserve all factual values and provenance unchanged. Add the tier identifier and bank identity to browser ranking entries. When all selected products are Gazprombank products, the row is `transfers_payments`, and Private's structured evaluation is not directly comparable with Premium because the channels differ, use two hierarchy groups: every `gpb_premium_*` level is equal and `gpb_private` is the senior group. Do not apply this rule across banks, to other fields, or when directly comparable transfer limits are available.

## Concrete Steps

From `/Users/ilyashmarov/Documents/analyst/bank_analyst`, render the Premium tariff pages containing card issue, cash withdrawal, and transfers, and the cashback table pages containing the premium service cap. Edit only `scanner/`, `landing/` if comparison parsing requires it, `tests/`, generated `data/` and `output/` files. Run:

    .venv/bin/python -m unittest tests.test_premium_structured
    .venv/bin/python main.py --scan-bank gazprombank
    .venv/bin/python main.py --build-sber-vs
    .venv/bin/python main.py --list-sources

## Validation and Acceptance

Premium levels 1–3 must show current cashback up to 6%, a monthly cashback cap of 40,000, free transfers of 200,000 by phone and 50,000 by card, detailed free cash-withdrawal conditions, and Mir Supreme with four free additional cards. When levels 1–3 are compared, equal financial conditions should receive equal middle traffic lights rather than missing or weak states. Private must show the official cashback up to 15% in the main category and up to 20% for health or travel, and must show the PRIME card offering. In a same-bank Gazprombank comparison containing Private, the transfer row must show Private as the senior green group and disclose that hierarchy was used because the source texts cover different transfer channels. A Private field without a direct source must remain `Не найдено в доступных источниках`.

## Idempotence and Recovery

The scan and landing build are deterministic and safe to repeat. PDF files and rendered PNGs are temporary research artifacts under `tmp/pdfs/` and must be removed after visual verification. Generated output may be rebuilt repeatedly from history and curated facts.

## Artifacts and Notes

The primary deliverables are `output/comparison_data.json` and `output/sber_vs_banks.html`. The official package tariff effective 22 July 2026 is the evidence for Premium card, transfer, and cash terms. The official cashback program effective 1 June 2026 is current through 31 July 2026. The official Private package page is the evidence for Private cashback and PRIME.

## Interfaces and Dependencies

Keep the existing `_fact()` provenance structure in `scanner/curated.py`. Keep `_attr_metric()` and the landing evaluation shape stable. Any comparison parser change must preserve the fields `status`, `method`, `metrics`, `directions`, `scope`, `summary`, and `reason`.

Revision note: initial plan created after verifying that the user-provided January PDF is superseded and separating confirmed Premium facts from incomplete Private facts. Progress and the Premium 6% acceptance value were corrected after the scan confirmed the current official cashback rules.
Revision note: completed after scan, browser-level traffic-light verification, full tests, and publication.
Revision note: reopened after the user identified that a generic fallback made Gazprombank Private red in a same-bank transfer comparison; research confirmed that the compared texts cover different transfer channels.
Revision note: follow-up completed with a Gazprombank-only transfer hierarchy fallback, browser verification of the exact color classes, and a repeat full test run.
