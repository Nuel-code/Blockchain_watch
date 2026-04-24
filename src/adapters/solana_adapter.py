from typing import Any, Dict, List, Set

from src.clients.dexscreener import collect_visible_candidates_for_chain
from src.clients.helius import (
    estimate_activity_with_helius,
    extract_asset_metadata,
    get_asset,
    has_helius_key,
)
from src.clients.solana_rpc import estimate_recent_activity, verify_account_exists
from src.pipeline.classify import classify_solana_object
from src.pipeline.normalize import normalize_visible_token_candidate


def _verify_and_enrich_solana_candidate(item: Dict[str, Any]) -> Dict[str, Any]:
    address = item["address"]

    account_exists = verify_account_exists(address)
    item["raw"]["solana_account_exists"] = account_exists

    metadata = {}

    if has_helius_key():
        asset = get_asset(address)
        metadata = extract_asset_metadata(asset) if asset else {}
        item["raw"]["helius_asset"] = asset

        activity = estimate_activity_with_helius(address, limit=25)
        item["activity_signals"].update(
            {
                "tx_count_sample": activity.get("tx_count_sample", 0),
                "unique_wallets_sample": activity.get("unique_wallets_sample", 0),
                "transfer_count": activity.get("tx_count_sample", 0),
                "unique_wallets": activity.get("unique_wallets_sample", 0),
                "deployer_only": activity.get("unique_wallets_sample", 0) <= 1
                if activity.get("tx_count_sample", 0) > 0
                else None,
            }
        )
        item["raw"]["solana_activity_source"] = "helius"
        item["raw"]["solana_activity"] = activity

    else:
        activity = estimate_recent_activity(address, limit=20)
        item["activity_signals"].update(
            {
                "tx_count_sample": activity.get("tx_count_sample", 0),
                "unique_wallets_sample": activity.get("unique_wallets_sample", 0),
                "transfer_count": activity.get("tx_count_sample", 0),
                "unique_wallets": activity.get("unique_wallets_sample", 0),
                "deployer_only": activity.get("unique_wallets_sample", 0) <= 1
                if activity.get("tx_count_sample", 0) > 0
                else None,
            }
        )
        item["raw"]["solana_activity_source"] = "public_rpc"
        item["raw"]["solana_activity"] = activity

    item = classify_solana_object(item, metadata=metadata)

    if account_exists:
        item["why_kept"].append("solana_account_exists")
    else:
        item["why_flagged"].append("solana_account_not_verified")

    if metadata.get("name") or metadata.get("symbol"):
        item["why_kept"].append("solana_metadata_found")
        item["labels"].append("has_solana_metadata")

    return item


def discover_solana_candidates(target_date: str) -> List[Dict[str, Any]]:
    """
    Solana free MVP strategy:

    Candidate-first funnel:
      1. collect visible Solana candidates from DexScreener public launch/visibility surfaces
      2. verify account existence using public RPC
      3. use Helius if available for better metadata/activity
      4. fallback to public RPC if no Helius key

    This is not pretending to scan all Solana mints from genesis.
    That requires a heavier indexer.
    """
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for raw in collect_visible_candidates_for_chain("solana", target_date):
        address = raw.get("address")
        if not address:
            continue

        key = address.lower()
        if key in seen:
            continue
        seen.add(key)

        item = normalize_visible_token_candidate(raw, target_date)
        item["labels"].append("solana_visible_candidate")
        item = _verify_and_enrich_solana_candidate(item)

        out.append(item)

    return out[:500]
