# Add Ingo Premium to the competitor comparison

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. This plan follows `PLANS.md` in the repository root.

## Purpose / Big Picture

After this change, a user can select Ingo Bank in the existing Sber-versus-competitors landing and compare the Ingo Premium package with Sber tiers and other banks. Every displayed Ingo value must come from the official Ingo Premium landing or the official tariff PDF supplied by the user. Information hidden behind landing-page information icons, arrows, sliders, or tabs must be inspected before the values are curated. Missing or ambiguous facts must remain `Не найдено в доступных источниках`.

## Progress

- [x] (2026-07-28) Read the repository rules, source policy, browser workflow, and PDF workflow.
- [ ] Inspect all interactive elements on the Ingo Premium landing and record the visible evidence. The landing is open but blocked by CAPTCHA pending user completion.
- [x] (2026-07-28) Download, extract, render, and visually inspect both pages of the official tariff PDF.
- [x] (2026-07-28) Register Ingo Bank, its Premium tier, and authoritative URLs in `scanner/sources.py`.
- [x] (2026-07-28) Add verified tier-specific tariff facts with provenance in `scanner/curated.py`.
- [x] (2026-07-28) Add focused regression tests covering registration, provenance, exact limits, and compensation scoring.
- [ ] Rebuild the comparison JSON and Sber-versus-banks landing, then perform final visual and functional verification. A preliminary rebuild and Sber-versus-Ingo interaction pass; final rebuild must include facts found behind landing controls.

## Surprises & Discoveries

The working tree already contains unrelated user changes and generated artifacts. They must be preserved. This implementation will touch only the smallest overlapping regions needed for the new bank and will not revert or rewrite unrelated work.

The generic compensation evaluator initially treated Ingo eligibility thresholds such as 5 million rubles of balances as taxi or restaurant compensation amounts. The evaluator now removes qualification clauses before extracting benefit amounts. A browser check changed the false taxi summary from 5 million rubles per month to the official 1,500 rubles per month.

## Decision Log

- Decision: Treat the supplied Ingo landing and `Tarif_7.pdf` as authoritative sources.
  Rationale: Both are official-domain sources and therefore outrank aggregators under `SOURCE_POLICY.md`.
  Date/Author: 2026-07-28 / Codex

- Decision: Model Ingo Premium as one concrete tier unless the official sources explicitly expose multiple premium levels.
  Rationale: The repository forbids inventing or splitting tiers without direct source confirmation.
  Date/Author: 2026-07-28 / Codex

- Decision: Keep the 2/15 lounge and restaurant privileges as one shared pool and say so in both category values.
  Rationale: Official tariff note 12 explicitly states that one ON PASS visit, one ON FOOD discount, or one ON PASS Premium visit each consume one privilege; separate category limits would overstate the package.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

Ingo Bank is already selectable in the local rebuilt landing and its PDF-backed categories render with official provenance. The work remains incomplete only because the live landing’s interactive controls cannot be inspected until the user completes CAPTCHA.

## Context and Orientation

`scanner/sources.py` defines banks, tiers, and the list of URLs scanned for each tier. `scanner/curated.py` contains manually verified facts with their source URL and check date. `main.py` merges scanned and curated facts and writes `output/comparison_data.json`. `landing/sber_vs.py` reads only that JSON and generates `output/sber_vs_banks.html`. Tests live in `tests/`.

The existing comparison uses a concrete tier identifier for every row. The new identifier will be `ingo_premium`, attached to bank identifier `ingo`, only if source inspection confirms a single premium package.

## Plan of Work

First, inspect every clickable information icon, arrow, carousel control, and tab on the official landing. Capture exact wording and distinguish general marketing statements from tariff conditions. Then download the official PDF into `tmp/pdfs/`, extract its text for searching, render all pages to PNG, and visually verify the relevant tariff rows.

Next, register the official URLs and the new bank in `scanner/sources.py`. Add only verified facts in `scanner/curated.py`; anything not found stays absent so the merge layer publishes the project’s standard missing-value marker. Add focused tests that prove Ingo is registered, uses official sources, appears in comparison JSON, and does not inherit facts from another bank.

Finally, run the source listing, focused tests, a targeted Ingo scan if the source is accessible, and rebuild the Sber comparison landing. Open the generated HTML locally and verify bank selection, category rendering, source links, and comparison scoring.

## Concrete Steps

Work from `/Users/ilyashmarov/Documents/analyst/bank_analyst`.

Inspect sources:

    Open https://ingobank.ru/premium/
    Inspect every information icon, arrow, carousel, and tab.
    Download https://cdn.ingos.ru/docs/cards/Tarif_7.pdf
    Render and inspect all PDF pages.

Validate implementation:

    .venv/bin/python main.py --list-sources
    .venv/bin/python -m unittest tests.test_premium_structured tests.test_source_policy
    .venv/bin/python main.py --scan-bank ingo
    .venv/bin/python main.py --build-sber-vs

The expected observable result is that `Инго Банк` appears in the bank selector and `Инго Premium` is available as its tier. Its conditions, lounges, restaurants, taxi, insurance, card, cashback, transfers, and other fields either show verified official values or the standard missing-value text.

## Validation and Acceptance

Acceptance requires all focused tests to pass, `--list-sources` to list the new bank, the generated comparison JSON to contain `ingo_premium`, and the generated HTML to allow comparison against that tier. Source URLs and reliability metadata must be present for every published Ingo fact. No field may be copied from another tier, bank, aggregator, or historical news post.

## Idempotence and Recovery

All build and test commands are safe to rerun. Existing dirty-worktree changes belong to the user and must not be reset. If the live landing is blocked by CAPTCHA, do not bypass it; record the source as unavailable and rely only on official content the user can explicitly authorize or on the supplied official PDF. If the targeted scan cannot fetch the landing, curated official PDF facts still allow the comparison to render with provenance.

## Artifacts and Notes

The authoritative URLs are:

    https://ingobank.ru/premium/
    https://cdn.ingos.ru/docs/cards/Tarif_7.pdf

Temporary PDF renders belong in `tmp/pdfs/` and are not final project data.

## Interfaces and Dependencies

No new runtime dependency is expected. Existing `requests`, PDF extraction tools, the curated-fact format, JSON writer, and landing builder are sufficient. The new bank object must follow the existing `BANKS` structure, and every curated fact must follow `_fact(value, source_url, note, date_checked=...)`.

Revision note (2026-07-28): Initial executable plan created before source inspection and implementation.

Revision note (2026-07-28): Recorded completed PDF integration, the compensation-scoring correction, the preliminary landing rebuild, and the CAPTCHA blocker.
