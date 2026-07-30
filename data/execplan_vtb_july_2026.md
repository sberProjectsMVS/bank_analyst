# Update VTB Privilege levels effective 31 July 2026

This ExecPlan is a living document maintained according to `PLANS.md`.

## Purpose / Big Picture

The comparison currently shows the older generic VTB Privilege levels even though VTB has published a new four-level system effective 31 July 2026. After this change, the landing will show the official names Emerald, Sapphire, Ruby, and Diamond, their Moscow and regional asset thresholds, the corresponding monthly Preference balances, five cashback categories, and the current list of services that consume Preferences.

## Progress

- [x] (2026-07-28) Opened the official VTB update landing and inspected both Moscow and regional tabs plus all visible FAQ answers.
- [x] (2026-07-28) Registered the update landing as an authoritative comparison source.
- [x] (2026-07-28) Mapped the four published statuses to the existing stable tier identifiers.
- [x] (2026-07-28) Added source-backed curated facts and regression tests.
- [x] (2026-07-28) Ran a targeted VTB scan, rebuilt the landing, and verified the VTB comparison locally.
- [x] (2026-07-28) Published the verified landing to GitHub Pages and confirmed the new VTB values on the public URL.

## Surprises & Discoveries

The update page is already present in the news monitor but was not registered as a tier-level comparison source. Therefore the news appeared while the comparison continued to use prior curated and PremiumBanking.info values.

The new status rules begin on 31 July 2026, but the first status assignment and first new Preference credit occur on 1 September after measuring 31 July through 30 August. User-facing values must retain this timing rather than present the September allocation as already credited.

## Decision Log

- Decision: Preserve the stable identifiers `vtb_privilege_1` through `vtb_privilege_4`, but rename their displayed tiers to Изумруд, Сапфир, Рубин, and Бриллиант.
  Rationale: This preserves scan history and existing links while reflecting the official product names.
  Date/Author: 2026-07-28 / Codex

- Decision: Treat the Preference balance as a shared pool across lounges, taxi, restaurants, baggage wrapping, and priority airport check-in.
  Rationale: The official page states that one Preference equals one use of any service chosen by the client; separate category limits would overstate the package.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

The generated and published landing now shows all four new VTB Privilege
status names and their official entry rules. Sapphire, Ruby, and Diamond show
2, 6, and 10 shared Preferences respectively; cashback shows five categories;
taxi and restaurant receipt limits remain visible in the compact cells.
Browser verification confirmed these values and the corrected upper-bound
label for Emerald on both the local build and the public GitHub Pages URL.

## Context and Orientation

`scanner/sources.py` defines the VTB bank and four Privilege tiers. `scanner/curated.py` supplies verified values that override lower-priority sources. `output/comparison_data.json` is generated from scan history, and `landing/sber_vs.py` builds `output/sber_vs_banks.html` from that JSON.

The authoritative update source is `https://www.vtb.ru/promo/rsvtb-pv-2/`.

## Plan of Work

Add the promo URL to the official source registry and every VTB Privilege tier. Rename the four tier display names while retaining their IDs. Curate level entry thresholds and Preference counts, then update shared cashback and selection rules from the same page. Keep Prime+ tiers unchanged because the promo explicitly describes VTB Privilege, not Prime+.

Add tests for the four names, Moscow and regional thresholds, monthly Preference counts, five cashback categories, and the effective/first-credit dates. Run only the VTB scan, rebuild the comparison, inspect the generated VTB rows in a browser, and publish the rebuilt file to the existing GitHub Pages repository.

## Concrete Steps

Run from `/Users/ilyashmarov/Documents/analyst/bank_analyst`:

    .venv/bin/python -m unittest tests.test_vtb_july_2026
    .venv/bin/python main.py --list-sources
    .venv/bin/python main.py --scan-bank vtb
    .venv/bin/python main.py --build-sber-vs

## Validation and Acceptance

The bank picker must still show VTB once. Its four Privilege levels must be named Изумруд, Сапфир, Рубин, and Бриллиант. Sapphire must show the distinct Moscow and regional thresholds and two Preferences; Ruby six; Diamond ten. Cashback must show five categories and a 30,000-ruble monthly cap. No VTB balance threshold may be scored as a taxi or restaurant reimbursement.

## Idempotence and Recovery

The scan and build commands are safe to repeat. Existing dirty-worktree changes belong to the user and must not be reset. Stable tier IDs keep history migration unnecessary.

## Artifacts and Notes

The official page states that the update begins 31 July 2026, the first measurement period is 31 July through 30 August, the first level is assigned 1 September, and Preferences credited on 1 September can be used through 30 September.

## Interfaces and Dependencies

No new dependency is required. Existing source registration, curated-fact merge, comparison JSON, and landing generation interfaces remain unchanged.

Revision note (2026-07-28): Initial plan created after complete interactive inspection of the official VTB update landing.

Revision note (2026-07-28): Recorded completed implementation, scan, tests, and local browser verification; publication is the only remaining step.

Revision note (2026-07-28): Marked publication complete after confirming the new VTB values on the live site.
