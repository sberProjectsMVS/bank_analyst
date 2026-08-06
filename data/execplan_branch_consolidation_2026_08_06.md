# Consolidate development into one protected main branch

This ExecPlan is a living document maintained in accordance with `PLANS.md`.

## Purpose / Big Picture

The repository will end with `main` as its only active working branch, while every file from the current `develop` tip remains recoverable from a pushed safety tag. The published landing and its retained news will be fingerprinted before and after consolidation so branch cleanup cannot silently replace or erase the user-visible site.

## Progress

- [x] (2026-08-06 16:20+03:00) Confirmed a clean `develop` worktree at commit `6291073` and authenticated GitHub CLI access.
- [x] (2026-08-06 16:20+03:00) Recorded matching SHA-256 fingerprints for `output/sber_vs_banks.html` and the published repository's `index.html`.
- [x] (2026-08-06 16:25+03:00) Pushed permanent tag `pre-main-consolidation-2026-08-06` resolving to `6291073`.
- [x] (2026-08-06 16:27+03:00) Fetched `origin/main` at `1a8d26c` and audited scratch files versus service data.
- [x] (2026-08-06 16:33+03:00) Removed only `tmp/vtb_prime` and `tmpt43w8f1a`, added ignore rules, and validated retained data and outputs.
- [ ] Commit and push cleanup, merge `develop` into `main` through a pull request, and wait for Actions.
- [ ] Verify the public landing and retained news, then delete `develop` locally and remotely.

## Surprises & Discoveries

- Observation: The current `develop` snapshot includes approximately 47 MiB of newly pushed objects and a 51.52 MiB `data/history.json`.
  Evidence: GitHub accepted commit `6291073` but warned that the history file exceeds its recommended 50 MiB size.
- Observation: The current local and publication HTML files are byte-identical.
  Evidence: both files have SHA-256 `6c688168d5156f05f845891bc9041e981f109324d3d180c65369e5d9959f9ae0`.
- Observation: `tmp/vtb_prime` and `tmpt43w8f1a` total approximately 78 MiB and no runtime source references either path.
  Evidence: `du -sh` reports 74 MiB and 3.9 MiB respectively; focused `rg` over runtime directories returns no references.
- Observation: The full test discovery is not hermetic and stalled in a live Google Sheets TLS handshake after exposing one previously known assertion failure.
  Evidence: interruption stack ended in `scanner/editorial_news.py` via `requests.get(..., timeout=30)` from `test_balanced_parentheses_all_banks`; the isolated 56-test retention, publisher, and alignment suite passes.

## Decision Log

- Decision: Preserve commit `6291073` with a pushed annotated tag before removing any tracked scratch file.
  Rationale: A tag makes every current file recoverable even after the short-lived `develop` branch is deleted.
  Date/Author: 2026-08-06 / Codex
- Decision: Keep service data, generated public outputs, research provenance, and source code; remove only reproducible temporary directories and dependency caches.
  Rationale: The user explicitly requires no loss above or below the landing.
  Date/Author: 2026-08-06 / Codex
- Decision: Merge through a pull request and require successful Actions plus a live landing fingerprint before branch deletion.
  Rationale: Branch deletion is safe only after both repository and deployed-site outcomes are observable.
  Date/Author: 2026-08-06 / Codex

## Outcomes & Retrospective

Implementation is in progress.

## Context and Orientation

`develop` is the current working branch and contains commit `6291073`, including the news-retention and verified-publication fixes. `main` is the GitHub Actions branch. The separate sibling repository `../bank_cite` contains the GitHub Pages `index.html`. Temporary inspection directories were accidentally included in `6291073`; they are not runtime inputs, but the full commit will remain accessible by safety tag.

## Plan of Work

Create and push an annotated safety tag at `6291073`. Fetch the latest `origin/main`, inventory the files introduced by the latest commit, and confirm runtime references with `rg`. Remove only dependency caches, screenshots, and one-off temporary workspaces that the application never reads; extend `.gitignore` to prevent recurrence. Run the focused news and publisher tests, the source-list self-check, and HTML builds. Commit and push the cleanup on `develop`, open a pull request to `main`, merge it after checks, update the local `main`, and compare the deployed build marker and news count. Delete `develop` only after all checks pass.

## Concrete Steps

From `/Users/ilyashmarov/Documents/analyst/bank_analyst`, use `git`, `/opt/homebrew/bin/gh`, and the project's `.venv/bin/python`. Expected final evidence includes a clean `main`, no remote `develop`, a successful `Scan and update site` run, and a public news count no lower than the pre-merge count.

## Validation and Acceptance

The focused unit tests must pass. `.venv/bin/python main.py --list-sources` must exit zero. The generated and published landing must retain the expected build marker and at least 87 news publications. The safety tag must resolve to `6291073`, `main` must contain the consolidation commits, and `git ls-remote --heads origin develop` must return no branch after deletion.

## Idempotence and Recovery

The safety tag is additive and never rewritten. Cleanup is committed separately, so it can be reverted. The `develop` branch remains until the merged `main`, Actions run, and public landing are verified. If any validation fails, stop before deletion and recover individual files from the safety tag.

## Artifacts and Notes

Initial fingerprints:

    develop: 6291073a785e821d002e11d648a57f600ad68a31
    bank_cite: e7ac2cd8f189e2d97a06387e2e5d976d69f14041
    landing sha256: 6c688168d5156f05f845891bc9041e981f109324d3d180c65369e5d9959f9ae0

Pre-commit validation:

    Ran 56 tests in 1.132s
    OK (skipped=1)
    comparison audit: 15600 pairs, 1063 metric mutations, 0 violations
    premium_changes_cache records: 87
    monitored_premium_news records: 27

## Interfaces and Dependencies

No runtime interface is intentionally changed by branch consolidation. GitHub CLI manages the pull request and checks; ordinary `git` manages commits, tags, branch updates, and deletion. GitHub Actions remains responsible for the scheduled full scan and copying the generated landing into `bank_cite`.

Revision note (2026-08-06): Created before the first branch or file mutation so the full consolidation remains restartable and auditable.
