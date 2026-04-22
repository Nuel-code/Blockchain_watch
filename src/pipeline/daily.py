from src.adapters.base_adapter import discover_base_candidates
from src.adapters.ethereum_adapter import discover_ethereum_candidates
from src.adapters.solana_adapter import discover_solana_candidates
from src.config import MAX_PER_DAY, TODAY_UTC
from src.pipeline.aggregate import rank_and_limit
from src.pipeline.enrich import enrich_market_data, select_best_pair
from src.pipeline.filtering import apply_filters
from src.pipeline.momentum import apply_momentum
from src.pipeline.normalize import normalize_candidate
from src.pipeline.scoring import score_item
from src.pipeline.socials import enrich_socials
from src.pipeline.storage import store_snapshot, update_seen_ids
from src.utils import load_json


def run_daily_for_date(target_date: str) -> list:
    seen_ids = set(load_json("state/seen_ids.json", []))

    candidates = []
    candidates.extend(discover_solana_candidates(target_date))
    candidates.extend(discover_base_candidates(target_date))
    candidates.extend(discover_ethereum_candidates(target_date))

    processed = []

    for candidate in candidates:
        chain = candidate["chain"]
        token_address = candidate["token_address"]

        best_pair = select_best_pair(chain, token_address)
        if not best_pair:
            continue

        item = normalize_candidate(candidate, best_pair, target_date)
        item = enrich_market_data(item)
        item = enrich_socials(item)
        item = apply_filters(item)
        item = apply_momentum(item, target_date)
        item = score_item(item)

        # global dedupe: don't store repeat ids again in all.json history, but do allow daily snapshot refresh
        if item["id"] in seen_ids:
            item["labels"].append("seen_before")

        processed.append(item)

    processed = rank_and_limit(processed, limit=MAX_PER_DAY)
    store_snapshot(target_date, processed)
    update_seen_ids(processed)
    return processed


def run():
    return run_daily_for_date(TODAY_UTC)


if __name__ == "__main__":
    run()
