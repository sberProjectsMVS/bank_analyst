from pathlib import Path

from report.json_writer import write_comparison_json
from scanner import sources
from scanner.curated import curated_for
from scanner.diff import load_history, save_history
from scanner.merge import merge_tier_fields
from scanner.publication import apply_publication_gate


ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = ROOT / "data" / "history.json"
COMPARISON_PATH = ROOT / "output" / "comparison_data.json"
TIER_IDS = ("vtb_prime_5", "vtb_prime_6", "vtb_prime_7", "vtb_prime_8")
FIELD_IDS = (
    "internal_transfers",
    "interbank_transfers_remote",
    "sbp_transfers",
    "atm_free_withdrawal",
    "cash_monthly_operational_limit",
    "atm_daily_limit",
)


history = load_history(HISTORY_PATH)
latest = history["scans"][-1]
scan_date = latest.get("date", "2026-08-05")

for tier_id in TIER_IDS:
    merged = merge_tier_fields(
        [],
        curated_for(tier_id),
        list(sources.BANK_FIELDS),
        scan_date,
        bank_id="vtb",
        tier_id=tier_id,
    )
    gated = apply_publication_gate(merged)
    target = latest["results"][tier_id]["fields"]
    for field_id in FIELD_IDS:
        target[field_id] = gated[field_id]

save_history(history, HISTORY_PATH)
write_comparison_json(history, COMPARISON_PATH)
print("Updated:", ", ".join(TIER_IDS))
