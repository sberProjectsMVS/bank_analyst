# Build a broad multi-source premium banking news monitor

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. This document is maintained in accordance with `PLANS.md`.

## Purpose / Big Picture

The current landing depends mainly on PremiumBanking.info and therefore can miss or delay official announcements. After this change, every scanner run also checks registered official bank newsrooms and selected industry feeds, identifies publications about premium or private banking, preserves their provenance, and adds them to a separate chronological “Все новости” feed. The bank-grouped “Изменения условий” feed remains limited to actual product-condition changes. A separate `--scan-news` command performs the same monitoring and rebuilds the landings without running the full banking-data scan.

The monitor cannot guarantee coverage of every page on the internet. It provides a broad, explicit source registry that can be audited and extended, respects robots.txt, and reports unavailable sources rather than bypassing restrictions.

## Progress

- [x] (2026-07-28 08:35Z) Read `AGENTS.md`, `PLANS.md`, `SOURCE_POLICY.md`, the current PBI feed, editorial import, scanner flow, and publication flow.
- [x] (2026-07-28 08:35Z) Verified that Bankinform allows `/news` in robots.txt and exposes current news links in static HTML.
- [x] (2026-07-28 08:35Z) Located official news or client-update pages for the seven Russian banks currently compared by the landing.
- [x] (2026-07-28 08:40Z) Registered the monitoring sources in `scanner/sources.py`.
- [x] (2026-07-28 08:46Z) Implemented fetch, relevance filtering, date parsing, persistence, and conservative deduplication.
- [x] (2026-07-28 08:48Z) Added monitored records and visible source provenance to the existing changes landing.
- [x] (2026-07-28 08:49Z) Added `--scan-news` and invoked the monitor from every normal scanner run.
- [x] (2026-07-28 08:55Z) Passed focused tests, completed a live nine-source scan with zero source failures, rebuilt both landings, verified the VTB update, and published the main landing.
- [x] (2026-07-28 09:16Z) Replaced the generic premium-only match with bank-specific package aliases, added inflection and typography normalization, rejected cross-card contamination, passed 15 focused tests, and republished the cleaned landing.
- [x] (2026-07-28 09:35Z) Expanded discovery beyond compared banks: added official Telegram parsing, Ingo Bank and its 2024 premium launch, customer events and benefits, conservative discovery of unknown bank names, explicit business-news exclusions, 14-source live validation, 19 focused tests, and publication.
- [x] (2026-07-28 09:43Z) Added the dedicated SberPremier channel, Sber's main channel, and Raiffeisen's official channel; completed a 17-source live scan with zero failures, manually reviewed the 13 retained monitored cards, and republished a 65-card feed covering eight banks.
- [x] (2026-07-28 09:52Z) Removed SberPremier lifestyle contamination: channel branding no longer supplies relevance, long editorial introductions are clipped before display, two personal-life cards were removed, 21 focused tests passed, and the corrected 63-card landing was republished.
- [x] (2026-07-28 10:10Z) Split condition changes from monitored news, added the chronological “Все новости” tab, required a premium/package signal and concrete action in the same or adjacent sentence, restricted the historical Ingo import to its launch post, shortened source excerpts, passed 26 focused tests, visually verified both tabs, and published the 52-change/4-news landing.
- [x] (2026-07-28 10:35Z) Replaced the mistaken two-tab design with one complete chronological feed and bank/period/event-type filters; merged strict monitored records back with PBI and editorial changes.
- [x] (2026-07-28 10:48Z) Expanded the official registry from newsrooms and Telegram to premium product landings and dated tariff/document links for the compared banks plus Ingo, Uralsib, Sovcombank, MKB, Bank DOM.RF, and Russian Standard.
- [x] (2026-07-28 11:00Z) Re-ran live discovery across 36 registered sources, retained 13 strict monitored records, verified the VTB 31 July update in the unified feed, tested all filters and browser logs, rebuilt both landings, and published.
- [x] (2026-07-29 00:00Z) Expanded the Telegram registry from the user-provided TrendsFactory examples, classified benefits/lifestyle/market/rumor items, detected banks per industry post, and rendered the landing as bank-ranked sections.
- [x] (2026-07-29 00:00Z) Completed a live 51-source scan: 48 sources succeeded, 3 reported access failures, 32 monitored records were retained, both HTML outputs were rebuilt, and 32 focused tests passed.
- [x] (2026-07-29 00:00Z) Replaced the bank-section interpretation with one global reverse-chronological feed embedded in the main landing; verified 84 cards, one timeline, no bank sections, and 32 passing focused tests.
- [ ] Publish the rebuilt main landing after the user explicitly authorizes the configured workflow to commit, pull, and push the neighboring GitHub Pages repository.

## Surprises & Discoveries

- Observation: The current changes landing fetches PBI directly during every build, while official bank newsrooms are not part of the news pipeline at all.
  Evidence: `landing/premium_changes.py::collect_premium_updates()` combines only `fetch_pbi_updates()` and `load_editorial_news()`.

- Observation: The VTB announcement supplied by the user is a future-dated official product update that starts on 31 July 2026 and is not represented by the current PBI updates feed.
  Evidence: `https://www.vtb.ru/promo/rsvtb-pv-2/` states “Улучшаем ВТБ «Привилегию» с 31 июля”.

- Observation: Bankinform publishes a static current-news listing and its robots.txt permits the base `/news` URL while disallowing selected query variants.
  Evidence: `https://bankinform.ru/robots.txt` disallows `/news*skip*`, `/news*f=*`, and `/news*t=*`, not `/news`.

- Observation: The first live scan found two qualifying source-derived records in the lookback window: the official VTB update and Ozon Bank's official premium-service launch.
  Evidence: `data/monitored_premium_news.json`; all nine registered sources completed successfully on the final run.

- Observation: Press-release pages alone miss customer activities and even
  product launches that banks announce in public Telegram channels.
  Evidence: the official Ingo Bank post `https://t.me/ingobankru/630`
  announces the premium-service launch; recent official posts also expose a
  premium office and a travel-insurance benefit.

- Observation: A bare word “Премиум” is unsafe because it also appears in
  unrelated partner products such as “Магнит Плюс Премиум”.
  Evidence: the first expanded live run admitted the VTB partner-subscription
  post; phrase-level premium-service matching and package aliases removed it.

- Observation: A dedicated premium channel can still publish general lifestyle
  editorial, and its footer can mention the package on every post.
  Evidence: two SberPremier posts about divorce and family rituals entered only
  because the footer said “СберПремьер в МАКС”; removing the footer before
  relevance evaluation rejects both.

- Observation: Requiring premium language anywhere in a long post is still too
  permissive: a generic referral, restaurant joke, personal-manager story, or
  office advert can contain both premium language and an unrelated action.
  Evidence: the user-supplied Sber, Alfa, Gazprombank, and Ingo examples.
  Sentence-local matching rejects those false associations while retaining a
  real launch, an explicit condition update, or a new premium office.

- Observation: The TrendsFactory examples expose repeated stories from
  different Telegram channels and a much broader editorial scope than tariff
  changes alone: benefits, customer events, brand lifestyle, and HNWI research.
  Evidence: the user supplied examples from AlfaBank, Alfa Only, T-Bank,
  PremiumBanking.info, Bankinform, Frank RG, BankBlog, Banksta, and lifestyle
  channels on 2026-07-29.

## Decision Log

- Decision: Official bank newsrooms have higher display and deduplication priority than PremiumBanking.info and industry feeds.
  Rationale: This matches `SOURCE_POLICY.md`; an aggregator may discover a story but must not supersede official conditions.
  Date/Author: 2026-07-28 / Codex

- Decision: Monitor a finite explicit registry instead of claiming to crawl the whole internet.
  Rationale: The registry is testable, respects source policies, and can report coverage. “All internet sources” is not a verifiable or safe crawler boundary.
  Date/Author: 2026-07-28 / Codex

- Decision: Store only source-derived titles and relevant source snippets, without generative rewriting.
  Rationale: The project must not invent or infer banking facts. Exact source text remains auditable.
  Date/Author: 2026-07-28 / Codex

- Decision: Treat the registered package names as premium signals even when a
  publication never uses the word “премиум”.
  Rationale: “СберПремьер”, “СберПервый”, “ВТБ Привилегия”, Alfa Only,
  A-Club, Ozon Ultra, and tier names such as Premium Diamond are product names
  for the monitored premium lines. Bank-specific matching avoids interpreting
  a generic word such as “привилегии” as premium news for every bank.
  Date/Author: 2026-07-28 / Codex

- Decision: Parse each Telegram post as an isolated source item and accept
  customer events, meetings, invitations, launches, and benefits when the same
  post identifies premium service or a registered premium package.
  Rationale: This widens coverage without letting a premium post elsewhere on a
  channel make unrelated acquiring, mortgage, or corporate posts relevant.
  Date/Author: 2026-07-28 / Codex

- Decision: Channel name and footer are provenance, not relevance evidence.
  Rationale: A post must mention a concrete premium condition, benefit, service,
  package, or customer event in its own body. When a relevant fact follows a
  lifestyle introduction, only the source-derived premium fragment is displayed.
  Date/Author: 2026-07-28 / Codex

- Decision: Keep monitored news in a separate atomic JSON cache.
  Rationale: A source outage must not erase previously discovered news or break the landing, and rollback stays isolated from banking facts.
  Date/Author: 2026-07-28 / Codex

- Decision: Do not merge monitored posts into bank-grouped condition changes.
  Rationale: A factual bank announcement can be useful market intelligence
  without representing a tariff or benefit change. Mixing the two makes the
  “Последние изменения” section noisy and misleading.
  Date/Author: 2026-07-28 / Codex

- Decision: Display monitored posts in one chronological “Все новости” stream,
  with bank and provenance badges, and cap source-derived excerpts at 360
  characters without generative rewriting.
  Rationale: The user needs broad discovery and quick scanning, while exact
  condition changes must remain a stricter, separate product.
  Date/Author: 2026-07-28 / Codex

- Decision: Supersede the two-tab design with one chronological feed containing
  both condition changes and strict monitored news.
  Rationale: The user asked for “Все новости” to mean the complete list, not a
  separate destination. Bank, period, and event-type filters provide the needed
  control without hiding VTB or any other monitored record behind a tab.
  Date/Author: 2026-07-28 / Codex

- Decision: Present the complete feed as bank sections ranked by newest
  publication, then by event importance, while preserving bank/type/date
  filters.
  Rationale: The user wants a bank-oriented competitive radar. Grouping prevents
  important condition changes from being lost in a single mixed timeline, while
  the event priority keeps tariffs and conditions above lifestyle material.
  Date/Author: 2026-07-29 / Codex

- Decision: Supersede the bank-section layout with one reverse-chronological
  feed across all banks, retaining bank/type/date filters.
  Rationale: The user clarified that reading every old item for one bank before
  reaching a new item from another bank is unusable. The main landing must show
  all news in time order and must not introduce a new destination.
  Date/Author: 2026-07-29 / Codex

- Decision: Industry Telegram channels do not supply a bank identity by
  themselves. Each accepted post must name a recognized bank or package; an
  ambiguous premium-service brand remains excluded.
  Rationale: This preserves SOURCE_POLICY.md strict bank binding and prevents
  SimplePrivé or other shared service brands from being silently assigned to
  the wrong bank.
  Date/Author: 2026-07-29 / Codex

## Outcomes & Retrospective

The multi-source monitor is operational and published. Normal scans now check the
news registry automatically, while `--scan-news` provides a fast news-only path.
The final live run checked 17 sources: 16 completed and the Alfa press page
returned HTTP 403; its official Telegram source still completed. Four strict
records were retained. The landing contains 52 bank-grouped condition changes
and a separate chronological stream of four monitored news items. The personal
life stories, generic referral offer, thin restaurant line, Ingo travel-insurance
promotion, and unrelated Ingo archive posts are absent. Focused news/editorial
tests pass (26 tests), both tabs were verified in the browser, and the browser
console contained no warnings or errors.

The final user-requested interface supersedes that interim result. There is now
one chronological feed containing 65 publications across nine banks, including
13 strict monitored records. It has bank, period, and event-type filters. The
official VTB 31 July update is the second card and includes the five cashback
categories plus taxi and airport-restaurant compensation limits. Uralsib was
newly discovered with its 1 August condition changes, 1 June package-line
changes, and dated premium tariff. The live registry checked 36 sources:
32 succeeded and four were unavailable (two Alfa pages returned 403,
Sovcombank returned 401, and the Bank DOM.RF premium-news listing returned an
incomplete response). Other official sources for those banks remain registered
and successful where available. Twenty-seven focused tests pass, the VTB filter
shows only nine VTB cards, the document filter shows only document cards, and
the browser console is clean.

The 2026-07-29 extension adds the user-provided Telegram source families and
renders one newest-first feed in the main landing with filters for bank, period,
and event type.
Official sources remain visibly distinguished from industry sources. Multi-bank
roundups are assigned to `Рынок` instead of being falsely attributed to the
first bank mentioned, and unconfirmed reports have their own `Не подтверждено`
label. The live scan retained 32 monitored records from 48 successful sources;
three bank pages remained unavailable because of HTTP access restrictions. The
standalone and embedded HTML files were rebuilt locally. Publication remains
pending because the configured publisher would commit, pull, and push a
neighboring GitHub Pages repository and requires explicit user authorization.

## Context and Orientation

`scanner/sources.py` is the required registry for all monitored URLs. `scanner/premium_news.py` will implement the new monitor. `landing/premium_changes.py` renders PBI and editorial items; it will additionally load the monitor cache. `main.py::run_scan()` is the normal scanner entry point and will call the monitor before rebuilding outputs. The cache will be `data/monitored_premium_news.json`. Service failures continue to be recorded in `data/service_log.json`.

A listing source is a page containing links to many announcements. A direct source is a known announcement page, such as the VTB update supplied by the user. Relevance filtering requires premium/private product language and change or benefit language; generic corporate, mortgage, business, survey, and sponsorship news must not enter the landing.

## Plan of Work

Add `PREMIUM_NEWS_SOURCES` to `scanner/sources.py`. Include official pages for Sber, Alfa-Bank, VTB, Gazprombank, Ozon Bank, Raiffeisen Bank, and T-Bank, the exact VTB announcement, and Bankinform. Each record contains a stable id, source name, source type, bank when fixed, URL, and source kind.

Create `scanner/premium_news.py`. It checks robots.txt, fetches each listing, discovers same-site article links, extracts nearby dates, detects the bank, applies relevance rules, and fetches a relevant detail page only when needed. It normalizes each item into the existing landing shape while retaining source type, URL, raw text, check date, reliability status, and a stable fingerprint. Cache writes are atomic and merge with previous records.

Update `landing/premium_changes.py` to render cached monitored records in a
separate chronological “Все новости” tab, prefer each monitored item’s concrete
source URL, and show bank and provenance badges. Do not merge these cards into
the bank-grouped condition changes.

Update `main.py` with `--scan-news`. Normal `--scan-all`, `--scan-bank`, and `--scan-lifestyle` runs invoke the news monitor automatically. The fast command scans news, appends source failures to the service log, rebuilds the standalone changes page and the main comparison landing, and uses the existing publication path.

## Concrete Steps

From `/Users/ilyashmarov/Documents/analyst/bank_analyst`, run:

    .venv/bin/python -m unittest tests.test_premium_news tests.test_editorial_news
    .venv/bin/python main.py --list-sources
    .venv/bin/python main.py --scan-news
    .venv/bin/python main.py --build-premium-changes
    .venv/bin/python main.py --build-sber-vs

The live scan should report each newsroom as successful, blocked, or unavailable; report a nonzero count of retained premium-banking publications; and preserve previous cached records if one source fails.

## Validation and Acceptance

A synthetic listing test must prove that a premium-service change is accepted while a mortgage, corporate survey, or unrelated bank story is rejected. A source-priority test must prove that an official duplicate wins over an industry duplicate. A robots test must prove that a disallowed source is marked unavailable without being fetched.

After a live scan, “Все новости” must contain the official 31 July “Улучшаем
Привилегию” announcement with the exact VTB URL. Bankinform items, when
relevant, must point to their Bankinform article and be visibly identified as an
industry source. Existing PBI and Google Sheets condition changes must remain in
the bank-grouped tab.

`--scan-news` must not update the banking fact history or Excel workbook. A normal full scan must invoke the news monitor before building the landing.

## Idempotence and Recovery

Stable record fingerprints make repeat scans idempotent. The cache is written through a temporary file and atomically replaced only after parsing completes. Individual source failures retain the last successful records. Removing the monitor call and cache loader restores the old PBI plus Google Sheets behavior without touching bank facts.

## Artifacts and Notes

Every monitored item carries at least:

    bank
    dateSort
    text
    sourcePage
    source_name
    source_type
    date_checked
    raw_text
    reliability_status
    record_id

Official items use `reliability_status = "official"`. Bankinform items use `reliability_status = "industry"` and remain subordinate to an official duplicate.

## Interfaces and Dependencies

`scanner.premium_news.sync_premium_news_sources(bank_id: str | None = None) -> dict` scans the registry, merges records, writes the cache, and returns `records`, `discovered`, `duplicates`, `sources_ok`, and `sources_failed`.

`scanner.premium_news.load_monitored_premium_news() -> list[dict]` safely returns cached records.

No new Python dependency is needed. The implementation uses existing `requests` and `beautifulsoup4`.

Plan update note (2026-07-28): Created after repository and live-source research to replace the narrow PBI-only news path with an auditable multi-source monitor.

Plan update note (2026-07-28): Expanded relevance matching after user feedback
that package brands, rather than the literal word “премиум”, identify many
premium-service announcements. Added a regression test for shared listing-page
wrappers after a live Ozon page initially contaminated unrelated B2B cards.

Plan update note (2026-07-28): Expanded the monitor from product-change headlines
to market-wide premium-service intelligence. Official Telegram posts are now
first-class sources, unknown banks can be discovered from launch headlines, and
business-only topics such as acquiring are explicitly rejected.

Plan update note (2026-07-28): Split broad monitored news from strict condition
changes after user review exposed misleading mixed cards. Relevance is now
sentence-local, the historical Ingo source is allowlisted to its actual launch,
and long source text is presented as a compact non-generative excerpt.

Plan update note (2026-07-28): Replaced the interim split-feed interpretation
with the requested single complete feed. Added filters and official landing/
document discovery, expanded coverage to five additional Russian premium banks,
restored the full VTB update to the default view, and published after live and
visual validation.

Plan update note (2026-07-29): Began the bank-ranked Telegram expansion from the
user's TrendsFactory examples. The change keeps source text and provenance,
adds no inferred tariff facts, and treats ambiguous service-only mentions as
unassigned rather than guessing a bank.

Plan update note (2026-07-29): Corrected the UI interpretation after user
feedback: the news remains inside the main landing as one newest-first stream;
bank grouping is available only as a filter, not as sequential sections.
