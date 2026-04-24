from typing import Any, Dict, List, Optional

from src.utils import request_json


BASE = "https://api.dexscreener.com"


def latest_token_profiles() -> List[Dict[str, Any]]:
    try:
        data = request_json("GET", f"{BASE}/token-profiles/latest/v1", timeout=20, retries=1)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def latest_token_boosts() -> List[Dict[str, Any]]:
    try:
        data = request_json("GET", f"{BASE}/token-boosts/latest/v1", timeout=20, retries=1)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def top_token_boosts() -> List[Dict[str, Any]]:
    try:
        data = request_json("GET", f"{BASE}/token-boosts/top/v1", timeout=20, retries=1)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def token_pairs(chain_id: str, token_address: str) -> List[Dict[str, Any]]:
    try:
        data = request_json(
            "GET",
            f"{BASE}/token-pairs/v1/{chain_id}/{token_address}",
            timeout=20,
            retries=1,
        )
        return data if isinstance(data, list) else []
    except Exception:
        return []


def pair_by_pair_address(chain_id: str, pair_address: str) -> List[Dict[str, Any]]:
    try:
        data = request_json(
            "GET",
            f"{BASE}/latest/dex/pairs/{chain_id}/{pair_address}",
            timeout=20,
            retries=1,
        )
        return data.get("pairs", []) if isinstance(data, dict) else []
    except Exception:
        return []


def search_pairs(query: str) -> List[Dict[str, Any]]:
    try:
        data = request_json(
            "GET",
            f"{BASE}/latest/dex/search",
            params={"q": query},
            timeout=20,
            retries=1,
        )
        return data.get("pairs", []) if isinstance(data, dict) else []
    except Exception:
        return []


def orders_for_token(chain_id: str, token_address: str) -> List[Dict[str, Any]]:
    try:
        data = request_json(
            "GET",
            f"{BASE}/orders/v1/{chain_id}/{token_address}",
            timeout=20,
            retries=0,
        )
        return data if isinstance(data, list) else []
    except Exception:
        return []


def get_best_pair_for_token(chain_id: str, token_address: str) -> Optional[Dict[str, Any]]:
    pairs = token_pairs(chain_id, token_address)
    if not pairs:
        return None

    def score_pair(pair: Dict[str, Any]) -> float:
        liquidity = 0.0
        volume = 0.0
        tx_count = 0.0

        try:
            liquidity = float((pair.get("liquidity") or {}).get("usd") or 0)
        except Exception:
            pass

        try:
            volume = float((pair.get("volume") or {}).get("h24") or 0)
        except Exception:
            pass

        try:
            txns = pair.get("txns", {}).get("h1", {})
            tx_count = float(txns.get("buys") or 0) + float(txns.get("sells") or 0)
        except Exception:
            pass

        return liquidity + (volume * 0.15) + (tx_count * 20)

    return sorted(pairs, key=score_pair, reverse=True)[0]


def collect_visible_candidates_for_chain(chain_id: str, target_date: str) -> List[Dict[str, Any]]:
    """
    Candidate-first discovery surface.

    This is especially useful for Solana and also useful as enrichment/discovery backup
    for Base/Ethereum.
    """
    out: List[Dict[str, Any]] = []
    seen = set()

    buckets = [
        ("token_profiles_latest", latest_token_profiles()),
        ("token_boosts_latest", latest_token_boosts()),
        ("token_boosts_top", top_token_boosts()),
    ]

    for bucket_name, rows in buckets:
        for row in rows:
            row_chain = (row.get("chainId") or "").lower()
            token_address = row.get("tokenAddress")

            if row_chain != chain_id or not token_address:
                continue

            key = f"{row_chain}:{token_address.lower()}"
            if key in seen:
                continue

            seen.add(key)

            out.append(
                {
                    "source": "dexscreener_visible_candidate",
                    "discovery_bucket": bucket_name,
                    "target_date": target_date,
                    "chain": chain_id,
                    "address": token_address,
                    "object_type_hint": "token",
                    "raw": row,
                }
            )

    return out
