from typing import Dict, List

from src.adapters.base_adapter import discover_base_candidates
from src.adapters.dune_adapter import discover_dune_candidates
from src.adapters.ethereum_adapter import discover_ethereum_candidates
from src.adapters.solana_adapter import discover_solana_candidates
from src.config import (
    ENABLE_DUNE_DISCOVERY,
    ENABLE_HEAVY_ENRICHMENT,
    ENABLE_LEGACY_DISCOVERY,
    MAX_HEAVY_ENRICH_CANDIDATES,
    MAX_PER_DAY,
    TODAY_UTC,
)
from src.models import dedupe_candidates
from src.pipeline.aggregate import rank_and_limit, summarize_actions
from src.pipeline.enrich import enrich_candidate
from src.pipeline.filtering import apply_filters
from src.pipeline.momentum import apply_momentum
from src.pipeline.name_quality import assess_name_quality
from src.pipeline.project_cluster import apply_project_cluster
from src.pipeline.project_identity import assess_project_identity
from src.pipeline.scoring import score_item
from src.pipeline.socials import enrich_socials
from src.pipeline.storage import store_snapshot, update_seen_ids
from src.utils import load_json, safe_float, safe_int


def _dune_pre_rank_key(item: Dict):
    activity = item.get("activity_signals", {}) or {}
    market = item.get("market_signals", {}) or {}

    return (
        safe_int(activity.get("unique_wallets"), 0),
        safe_int(activity.get("transfer_count"), 0),
        safe_float(market.get("volume_usd_24h"), 0.0),
    )


def discover_all_candidates(target_date: str) -> List[Dict]:
    candidates: List[Dict] = []

    print(
        {
            "ENABLE_DUNE_DISCOVERY": ENABLE_DUNE_DISCOVERY,
            "ENABLE_LEGACY_DISCOVERY": ENABLE_LEGACY_DISCOVERY,
            "ENABLE_HEAVY_ENRICHMENT": ENABLE_HEAVY_ENRICHMENT,
            "MAX_HEAVY_ENRICH_CANDIDATES": MAX_HEAVY_ENRICH_CANDIDATES,
            "target_date": target_date,
        }
    )

    if ENABLE_DUNE_DISCOVERY:
        dune_candidates = discover_dune_candidates(target_date)
        print({"dune_candidates": len(dune_candidates)})
        candidates.extend(dune_candidates)

    if ENABLE_LEGACY_DISCOVERY:
        legacy_candidates: List[Dict] = []
        legacy_candidates.extend(discover_base_candidates(target_date))
        legacy_candidates.extend(discover_ethereum_candidates(target_date))
        legacy_candidates.extend(discover_solana_candidates(target_date))
        print({"legacy_candidates": len(legacy_candidates)})
        candidates.extend(legacy_candidates)
    else:
        print({"legacy_candidates": "skipped"})

    candidates = dedupe_candidates(candidates)
    candidates = sorted(candidates, key=_dune_pre_rank_key, reverse=True)

    print({"total_candidates_after_dedupe": len(candidates)})

    return candidates


def _trim_raw(item: Dict) -> Dict:
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
            "dune_discovery_source": item["raw"].get("discovery_source"),
            "heavy_enriched": item["raw"].get("heavy_enriched"),
        }

    return item


def process_candidate(item: Dict, target_date: str, heavy_enrich: bool = False) -> Dict:
    """
    Fast path:
      Dune discovery + local name/description/filter/score.

    Heavy path:
      Adds DexScreener/Etherscan/social/cluster enrichment.
      Used only for top Dune candidates so backfill stays fast.
    """
    item.setdefault("raw", {})
    item["raw"]["heavy_enriched"] = heavy_enrich

    if heavy_enrich:
        item = enrich_candidate(item)
        item = apply_project_cluster(item)
        item = enrich_socials(item)

    item = assess_name_quality(item)
    item = assess_project_identity(item)
    item = apply_filters(item)
    item = apply_momentum(item, target_date)
    item = score_item(item)

    item["labels"] = sorted(set(item.get("labels", [])))
    item["why_kept"] = list(dict.fromkeys(item.get("why_kept", [])))
    item["why_flagged"] = list(dict.fromkeys(item.get("why_flagged", [])))

    return _trim_raw(item)


def run_daily_for_date(target_date: str, store: bool = True) -> List[Dict]:
    seen_ids = set(load_json("state/seen_ids.json", []))

    candidates = discover_all_candidates(target_date)
    processed: List[Dict] = []

    for idx, item in enumerate(candidates):
        try:
            heavy_enrich = ENABLE_HEAVY_ENRICHMENT and idx < MAX_HEAVY_ENRICH_CANDIDATES

            item = process_candidate(
                item,
                target_date,
                heavy_enrich=heavy_enrich,
            )

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
