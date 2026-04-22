from typing import Any, Dict, List, Set, Tuple

from src.clients.dexscreener import latest_token_boosts, latest_token_profiles, top_token_boosts


def discover_ethereum_candidates(target_date: str) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    for bucket_name, items in [
        ("profiles", latest_token_profiles()),
        ("boosts_latest", latest_token_boosts()),
        ("boosts_top", top_token_boosts()),
    ]:
        for item in items:
            chain = (item.get("chainId") or "").lower()
            address = item.get("tokenAddress")
            if chain != "ethereum" or not address:
                continue

            key = (chain, address.lower())
            if key in seen:
                continue
            seen.add(key)

            candidates.append(
                {
                    "source": "dexscreener",
                    "discovery_bucket": bucket_name,
                    "target_date": target_date,
                    "chain": "ethereum",
                    "token_address": address,
                    "profile": item,
                }
            )

    return candidates
