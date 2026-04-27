from typing import Any, Dict, List, Optional, Set

from src.clients.defillama import get_protocols
from src.clients.dexscreener import collect_visible_candidates_for_chain, search_pairs
from src.clients.github_search import search_recent_crypto_repos
from src.clients.helius import (
    estimate_activity_with_helius,
    extract_asset_metadata,
    get_asset,
    has_helius_key,
)
from src.clients.solana_rpc import estimate_recent_activity, verify_account_exists
from src.pipeline.classify import classify_solana_object
from src.pipeline.normalize import normalize_visible_token_candidate
from src.utils import first_non_empty


def _pair_to_visible_candidate(
    *,
    pair: Dict[str, Any],
    target_date: str,
    source: str,
    discovery_bucket: str,
    description: Optional[str] = None,
    project_url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    base = pair.get("baseToken") or {}
    address = base.get("address")

    if not address:
        return None

    profile = {
        "name": base.get("name"),
        "symbol": base.get("symbol"),
        "description": description or base.get("name"),
        "url": project_url or pair.get("url"),
        "links": [],
        "pair": pair,
    }

    return {
        "source": source,
        "discovery_bucket": discovery_bucket,
        "target_date": target_date,
        "chain": "solana",
        "address": address,
        "object_type_hint": "token",
        "raw": profile,
    }


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

    if metadata.get("name") or metadata.get("symbol") or metadata.get("description"):
        item["why_kept"].append("solana_metadata_found")
        item["labels"].append("has_solana_metadata")

    return item


def _project_seed_candidates(target_date: str, seen: Set[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    # GitHub project-like repos resolved to Solana DEX candidates.
    for repo in search_recent_crypto_repos()[:20]:
        query = first_non_empty(repo.get("name"), repo.get("full_name"))
        if not query:
            continue

        for pair in search_pairs(query)[:10]:
            if (pair.get("chainId") or "").lower() != "solana":
                continue

            candidate = _pair_to_visible_candidate(
                pair=pair,
                target_date=target_date,
                source="github_project_seed",
                discovery_bucket="github_search_resolved_to_solana_pair",
                description=repo.get("description"),
                project_url=repo.get("url"),
            )

            if not candidate:
                continue

            key = candidate["address"].lower()
            if key in seen:
                continue

            seen.add(key)
            item = normalize_visible_token_candidate(candidate, target_date)
            item["labels"].append("project_seed_github")
            item["raw"]["github_seed"] = repo
            item["raw"]["dexscreener_pair_seed"] = pair
            item = _verify_and_enrich_solana_candidate(item)
            out.append(item)

    # DeFiLlama Solana protocols resolved to Solana pair candidates.
    for protocol in get_protocols()[:2500]:
        chains = [str(c).lower() for c in protocol.get("chains") or []]
        if "solana" not in chains:
            continue

        query = protocol.get("name")
        if not query:
            continue

        for pair in search_pairs(query)[:10]:
            if (pair.get("chainId") or "").lower() != "solana":
                continue

            candidate = _pair_to_visible_candidate(
                pair=pair,
                target_date=target_date,
                source="defillama_project_seed",
                discovery_bucket="defillama_resolved_to_solana_pair",
                description=protocol.get("description") or protocol.get("category"),
                project_url=protocol.get("url"),
            )

            if not candidate:
                continue

            key = candidate["address"].lower()
            if key in seen:
                continue

            seen.add(key)
            item = normalize_visible_token_candidate(candidate, target_date)
            item["labels"].append("project_seed_defillama")
            item["raw"]["defillama_seed"] = protocol
            item["raw"]["dexscreener_pair_seed"] = pair
            item = _verify_and_enrich_solana_candidate(item)
            out.append(item)

    return out


def discover_solana_candidates(target_date: str) -> List[Dict[str, Any]]:
    """
    Solana strategy:
      1. project-first seeds from GitHub/DeFiLlama resolved through public DEX visibility
      2. fallback visible candidates from DexScreener
      3. Helius/public-RPC verification

    Still not a perfect full Solana mint indexer.
    But it is now less memecoin-first.
    """
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    # 1. Project-first Solana discovery.
    out.extend(_project_seed_candidates(target_date, seen))

    # 2. Fallback token/DEX visible surface.
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
        item["labels"].append("token_surface_only")
        item = _verify_and_enrich_solana_candidate(item)

        out.append(item)

    return out[:500]
