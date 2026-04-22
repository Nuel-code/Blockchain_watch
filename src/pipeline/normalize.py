from src.models import empty_socials, make_id
from src.utils import first_non_empty


def normalize_candidate(candidate: dict, best_pair: dict, target_date: str) -> dict:
    chain = candidate["chain"]
    address = candidate["token_address"]
    base_token = best_pair.get("baseToken", {}) if best_pair else {}
    quote_token = best_pair.get("quoteToken", {}) if best_pair else {}

    base_address = (base_token.get("address") or "").lower()

    name = first_non_empty(
        base_token.get("name"),
        candidate.get("profile", {}).get("description"),
        "Unknown",
    )
    symbol = first_non_empty(base_token.get("symbol"), "UNKNOWN")

    object_type = "token"

    normalized = {
        "id": make_id(chain, object_type, address),
        "object_type": object_type,
        "chain": chain,
        "address": address,
        "pair_address": best_pair.get("pairAddress"),
        "name": name,
        "symbol": symbol,
        "first_seen": target_date,
        "snapshot_date": target_date,
        "quote_symbol": quote_token.get("symbol"),
        "quote_address": quote_token.get("address"),
        "dex_id": best_pair.get("dexId"),
        "recognized_factory": best_pair.get("dexId"),
        "liquidity_usd": 0.0,
        "tx_count_1h": 0,
        "unique_external_wallets_1h": 0,
        "volume_usd_24h": 0.0,
        "price_usd": 0.0,
        "socials": empty_socials(),
        "signals": {},
        "risk_scores": {},
        "scores": {},
        "labels": [],
        "action": "ignore",
        "why_kept": [],
        "why_flagged": [],
        "source": candidate.get("source"),
        "discovery_meta": {
            "bucket": candidate.get("discovery_bucket"),
            "profile_url": candidate.get("profile", {}).get("url"),
            "base_token_matches_candidate": base_address == address.lower() if base_address else None,
        },
        "raw": {
            "profile": candidate.get("profile", {}),
            "pair": best_pair or {},
        },
    }
    return normalized
