from typing import Dict, List

from src.adapters.base_adapter import discover_base_candidates
from src.adapters.ethereum_adapter import discover_ethereum_candidates
from src.adapters.solana_adapter import discover_solana_candidates
from src.config import MAX_PER_DAY, TODAY_UTC
from src.models import dedupe_candidates
from src.pipeline.aggregate import rank_and_limit, summarize_actions
from src.pipeline.enrich import enrich_candidate
from src.pipeline.filtering import apply_filters
from src.pipeline.momentum import apply_momentum
from src.pipeline.name_quality import assess_name_quality
from src.pipeline.project_cluster import apply_project_cluster
from src.pipeline.scoring import score_item
from src.pipeline.socials import enrich_socials
from src.pipeline.storage import store_snapshot, update_seen_ids
from src.utils import load_json


def discover_all_candidates(target_date: str) -> List[Dict]:
    candidates: List[Dict] = []

    candidates.extend(discover_base_candidates(target_date))
    candidates.extend(discover_ethereum_candidates(target_date))
    candidates.extend(discover_solana_candidates(target_date))

    return dedupe_candidates(candidates)


def process_candidate(item: Dict, target_date: str) -> Dict:
    item = enrich_candidate(item)
    item = assess_name_quality(item)
    item = apply_project_cluster(item)
    item = enrich_socials(item)
    item = apply_filters(item)
    item = apply_momentum(item, target_date)
    item = score_item(item)

    item["labels"] = sorted(set(item.get("labels", [])))
    item["why_kept"] = list(dict.fromkeys(item.get("why_kept", [])))
    item["why_flagged"] = list(dict.fromkeys(item.get("why_flagged", [])))

    if "raw" in item:
        item["raw"] = {
            "source": item.get("source"),
            "project_signal_count": item["raw"].get("project_signal_count"),
            "hard_ignore": item["raw"].get("hard_ignore"),
            "social_count": item["raw"].get("social_count"),
            "discovery_bucket": item["raw"].get("discovery_bucket"),
            "solana_activity_source": item["raw"].get("solana_activity_source"),
            "score_components": item["raw"].get("score_components"),
            "volume_liquidity_ratio": item["raw"].get("volume_liquidity_ratio"),
            "has_any_social": item["raw"].get("has_any_social"),
            "dex_tx_count_1h": item["raw"].get("dex_tx_count_1h"),
        }

    return item


def run_daily_for_date(target_date: str, store: bool = True) -> List[Dict]:
    seen_ids = set(load_json("state/seen_ids.json", []))

    candidates = discover_all_candidates(target_date)
    processed: List[Dict] = []

    for item in candidates:
        try:
            item = process_candidate(item, target_date)

            if item.get("id") in seen_ids:
                item["labels"].append("seen_before")

            processed.append(item)

        except Exception as exc:
            item.setdefault("why_flagged", [])
            item.setdefault("labels", [])
            item.setdefault("raw", {})

            item["why_flagged"].append(f"processing_error={type(exc).__name__}")
            item["labels"].append("processing_error")
            item["action"] = "ignore"
            item["raw"]["processing_error"] = str(exc)[:300]

            processed.append(item)

    ranked = rank_and_limit(processed, limit=MAX_PER_DAY)

    if store:
        store_snapshot(target_date, ranked)
        update_seen_ids(ranked)

    print(
        {
            "date": target_date,
            "discovered": len(candidates),
            "stored": len(ranked),
            "actions": summarize_actions(ranked),
        }
    )

    return ranked


def run() -> List[Dict]:
    return run_daily_for_date(TODAY_UTC, store=True)


if __name__ == "__main__":
    run()
