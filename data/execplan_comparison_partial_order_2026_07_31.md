# Make premium-bank comparisons evidence-safe

This ExecPlan is a living document maintained in accordance with `PLANS.md`.

## Purpose / Big Picture

After this change the comparison page will distinguish a proven disadvantage from missing evidence. Lounge access, cashback, transfers, cash withdrawal, travel insurance, standalone options, metal cards, and personal banking support will be represented as separate facts where their scopes differ. A user can rebuild `output/sber_vs_banks.html`, compare Sber Premier level 2 with VTB Privilege Sapphire, and see equal lounge access and no false cashback loser.

## Progress

- [x] (2026-07-31 11:20 MSK) Read the complete request, `PLANS.md`, `AGENTS.md`, and `SOURCE_POLICY.md`.
- [x] (2026-07-31 11:30 MSK) Located normalization and ranking code in `landing/sber_vs.py`, curated facts in `scanner/curated.py`, source registration in `scanner/sources.py`, and regression coverage in `tests/`.
- [x] (2026-07-31 13:05 MSK) Replaced forced total-order fallbacks with evidence-safe partial-order results and added the P0 regressions.
- [x] (2026-07-31 14:10 MSK) Added scoped transfer, withdrawal, insurance, option, metal-card, and personal-support fields without cross-tier inference.
- [x] (2026-07-31 15:05 MSK) Rebuilt JSON/Excel/HTML and ran targeted plus project self-checks.
- [x] (2026-07-31 15:30 MSK) Verified desktop/mobile rendering and captured the required comparison screenshot. The PDF button is present and its DOM-based export path includes the new rows, but an automated browser download timed out and was not counted as a passed download test.
- [x] (2026-07-31 15:45 MSK) Recorded unconfirmed official facts and final outcomes.
- [x] (2026-07-31 16:05 MSK) Corrected Sber transfer channels from the 07.07.2026 tariff, consolidated VZR to one visible row, removed standalone-option duplication, and limited visible ranking badges/colors to proven stronger/weaker outcomes.
- [x] (2026-07-31 16:35 MSK) Compacted the five transfer/payment rows and five cash-withdrawal rows into two presentation-only summary rows while retaining every structured fact in JSON and Excel.
- [x] (2026-07-31 22:35 MSK) Normalized entry thresholds, cashback caps, and explicit daily/monthly operation limits after focused user-visible regressions.
- [ ] (2026-07-31 22:45 MSK) Replace false yellow equality with category-specific taxi, restaurant, and insurance comparisons; audit every resulting equal outcome and republish.

## Surprises & Discoveries

- Observation: The browser currently falls back to lexicographic vectors whenever one structured pair is incomparable.
  Evidence: `rankEvaluations` calls `fallbackRankVector` after any `compareEvaluations` result with `order: null`.
- Observation: Lounge access programs currently break ties after visit counts.
  Evidence: `compareLounges` compares `access_programs` after `visits_monthly`, contrary to the requested informational-only treatment.
- Observation: Cashback fallback gives a known maximum rate a leading binary advantage.
  Evidence: `fallbackRankVector` begins the cashback vector with `rateKnown`.
- Observation: The project source registry contains 8 banks and 39 package levels, while official tier-specific evidence for the newly split P2 fields is uneven.
  Evidence: Sber’s requested tariff/insurance facts are tier-bound and VTB/Alfa have selected official analogs; the other new cells remain `Не найдено в доступных источниках` rather than inheriting adjacent-tier data.
- Observation: The bundled workbook renderer cannot load its signed `skia-canvas` binary in this macOS process.
  Evidence: artifact-tool import fails with a Team ID code-signature mismatch; structural workbook checks use the project’s read-only `openpyxl` dependency instead.
- Observation: A server-side landing override reintroduced Health, Pets, Samokat, and Auto into `Другие привилегии` after JSON normalization had removed them.
  Evidence: the published payload contained the duplicate items even though `output/comparison_data.json` was clean; removing `other_benefits_by_tier` made the public payload match JSON.

## Decision Log

- Decision: Keep the landing’s current evaluation envelope but extend statuses and comparison results rather than building a second ranking system.
  Rationale: This fixes the root comparison behavior while preserving current rendering and PDF export.
  Date/Author: 2026-07-31 / Codex
- Decision: Treat missing metrics as absent evidence, never as numeric zero, and use only common, scope-compatible metrics for dominance.
  Rationale: This is the project’s source policy and the user’s principal acceptance rule.
  Date/Author: 2026-07-31 / Codex
- Decision: Remove the obsolete fallback-vector and Gazprombank package-hierarchy functions entirely.
  Rationale: Dead fallback code could be reintroduced accidentally and contradicted the evidence-safe partial-order rule.
  Date/Author: 2026-07-31 / Codex
- Decision: Publish only the official analogs actually verified during this change and leave all other new fields explicitly unavailable.
  Rationale: Completion of the data schema must not be confused with confirmation of every bank/tier fact.
  Date/Author: 2026-07-31 / Codex
- Decision: Render every comparison outcome with the user-defined traffic-light contract: green for stronger, red for weaker, and yellow for equal or not safely rankable.
  Rationale: The user explicitly restored the earlier color rule. One confirmed value against missing evidence is green/red; two missing values are yellow; exact numeric equality is yellow. No 10% tolerance is applied.
  Date/Author: 2026-07-31 / Codex
- Decision: Aggregate transfer and cash facts only in the landing payload, not in the source schema.
  Rationale: The user gets a compact table, while channel, period, fee, provenance, and technical-limit fields remain separately auditable and cannot be accidentally compared across scopes.
  Date/Author: 2026-07-31 / Codex
- Decision: Reserve the yellow `равно` badge for a proven equality result (`order === 0`).
  Rationale: Rendering incomparable or structurally incomplete conditions as equal is factually misleading. Such cases keep their audit reason but receive no visible result until a category-specific comparison can prove an order.
  Date/Author: 2026-07-31 / Codex
- Decision: Compare compensation services lexicographically by monthly total, monthly uses, per-use limit, annual total, then availability; compare insurance first by CBR-normalized maximum coverage, then owner coverage, territory breadth, family coverage, and trip duration.
  Rationale: These priorities match the customer value of each category and avoid letting a missing secondary field cancel a clear advantage in the primary confirmed metric.
  Date/Author: 2026-07-31 / Codex

## Outcomes & Retrospective

The P0 defect is fixed: Sber Premier level 2 and VTB Privilege Sapphire show equal lounge access at two uses per month, and cashback is neutral/ambiguous with the requested explanation. Ranking now uses only scope-compatible confirmed metrics; equality, ambiguity, and insufficient evidence are visible states.

The data model, JSON writer, Excel report, and landing now keep transfer channels, cash limits, insurance details, standalone options, metal cards, and personal support separate. Exact requested Sber facts are attached only to their confirmed levels. Selected official VTB and Alfa analogs were also added. A complete official-source fill for every new field across all 39 package levels was not possible in this pass, so remaining cells are deliberately marked unavailable.

Targeted tests pass with 27,300 actual pair comparisons and 827 monotonic metric mutations, with zero violations. Desktop and 390 px mobile rendering pass without horizontal page overflow. The required screenshot is saved in `output/`. Publication to the sibling `bank_cite` repository was blocked by the workspace boundary and was not forced.

Follow-up publication succeeded after a targeted Sber scan. The public page now uses the official tariff wording for internal, interbank remote, interbank office, and legal-entity transfers; VZR appears as one row; Health, Pets, and Auto appear once each and are absent from `Другие привилегии`; neutral outcomes have no color or visible badge.

The landing now displays one `Переводы и платежи` row and one `Снятие наличных` row per package. Their values use compact semicolon-separated limits and fees; missing subfacts are listed once at the end of the cell. The underlying JSON/Excel fields remain separate.

The comparison colors now follow the strict final rule: green means objectively stronger, red means weaker or uniquely missing, and yellow means exactly equal or not safely rankable. Composite transfer/cash rows compare their source-bound components separately and never compare daily against monthly limits. Entry conditions additionally account for required `И` combinations and alternative `ИЛИ` routes.

Visible result badges are restricted to three words: `сильнее`, `слабее`, and `равно`. Internal ambiguous/insufficient statuses remain available for audit explanations but are displayed as the yellow `равно` outcome rather than separate user-facing labels.

Entry-condition ranking uses a normalized standalone asset threshold across generic and regional wording. It excludes reduced thresholds that require spending via `И`, uses the strictest published regional standalone threshold, and compares that common metric before secondary structural attributes. This prevents Sber `3 млн ₽` versus VTB Sapphire `2,5 млн ₽` from being mislabeled as equal.

Compact transfer and cash rows spell out every confirmed period instead of abbreviating it: `лимит за перевод`, `лимит в сутки`, and `лимит в месяц`. A single SBP cell can therefore show operation, daily, third-party monthly, and own-account monthly limits without creating extra table rows.

Cashback comparison normalizes ruble and bonus monthly caps into one `effective_monthly_cap` metric. When both caps are confirmed, the higher cap determines the result even if one bank has not published its maximum rate; therefore VTB `30 000 ₽` ranks above Sber `20 000` bonuses for the shown pair.

## Context and Orientation

`scanner/sources.py` defines available fields and source URLs. `scanner/parse.py` extracts source text. `scanner/curated.py` stores manually verified facts with provenance. `report/json_writer.py` writes `output/comparison_data.json`, which is the sole user-facing source for `landing/sber_vs.py`. That module builds both the HTML and embedded JavaScript comparison engine. A “partial order” means two offers are ranked only when one is no worse on every comparable confirmed metric and better on at least one; split advantages are ambiguous and missing key evidence is insufficient data.

## Plan of Work

First, change lounge normalization to recognize preference-to-use equivalence and shared preference pools. Make access-system count informational. Replace cashback and generic dominance behavior with common-metric comparison that returns equal, better, ambiguous, or insufficient-data outcomes without falling back to unknown-as-zero vectors. Update visual classes and explanations.

Second, extend the field catalog and curated model with separately scoped operations: internal transfers, interbank remote transfers, interbank office transfers, Faster Payments System transfers, legal-entity payments, free ATM withdrawal, aggregate monthly cash limit, ATM daily limit, cash-desk daily limit, and over-limit fee. Add structured travel-insurance details, standalone Sber-style options, metal card, and personal banking support. Every added fact must retain tier, URL, source type, checked date, raw text, effective date where known, and channel/region scope.

Third, add automatic pairwise invariants and focused regressions, rebuild artifacts, inspect the actual Sber/VTB pair in a browser at desktop and mobile widths, test PDF preparation, and save a screenshot under `output/`.

## Concrete Steps

Run from `/Users/ilyashmarov/Documents/analyst/bank_analyst`:

    .venv/bin/python -m unittest tests.test_sber_vs_alignment tests.test_premium_structured
    .venv/bin/python main.py --list-sources
    .venv/bin/python main.py --build-sber-vs

Use the generated `output/sber_vs_banks.html` for browser verification. The expected P0 result is lounge status `равно` for Sber Premier level 2 versus VTB Sapphire and a neutral `неоднозначно` cashback result explaining the confirmed 10% rate versus 30,000/20,000 monthly limits and missing VTB maximum rate.

## Validation and Acceptance

Tests must prove preference-to-pass normalization, unknown cashback rate preservation, no fallback total order for split or missing evidence, channel/period separation, and symmetric/reflexive pair comparisons. The generated page must retain the current responsive design, detail expansion, and PDF export while displaying neutral ambiguous/insufficient states. All published facts must come from `comparison_data.json`.

## Idempotence and Recovery

Build and tests are repeatable. Generated JSON and HTML may be regenerated safely. Curated values are additive and source-bound; they must not overwrite unrelated user changes or synthesize missing facts. No destructive command is needed.

## Artifacts and Notes

Primary artifacts are `output/comparison_data.json`, `output/sber_vs_banks.html`, the updated test suite, and a screenshot of the Sber Premier level 2 / VTB Sapphire comparison.

## Interfaces and Dependencies

Keep `_category_evaluation(field, raw_value, display_value, row) -> dict` and the JavaScript evaluation object keys `status`, `method`, `metrics`, `directions`, `scope`, `summary`, and `reason`. New structured fact fields must use the existing provenance shape and be registered in `scanner/sources.py` before publication.

Revision note: initial plan created after reading the complete request and mapping the existing data-to-landing pipeline. Updated after implementation and validation with completed milestones, renderer/publication constraints, and the explicit remaining evidence gaps.

Revision note: updated after the focused transfers/options/ranking follow-up to record the removed landing override, the latest visible-status rule, and successful GitHub Pages publication.

Revision note: updated after compacting transfers and cash withdrawal to record the presentation-only aggregation and preservation of structured source facts.

Revision note: updated after the final traffic-light clarification to record strict equality, two-sided missing behavior, context-aware composite comparisons, and AND/OR entry-condition structure.

Revision note: updated after the false-equality audit to reserve visible equality for proven equality and introduce category-specific priorities for compensation services and insurance.
