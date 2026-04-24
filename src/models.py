from typing import Any, Dict, List, Optional


def make_id(chain: str, object_type: str, address: str) -> str:
    return f"{chain}:{object_type}:{(address or '').lower()}"


def empty_socials() -> Dict[str, Optional[str]]:
    return {
        "website": None,
        "twitter_x": None,
        "telegram": None,
        "discord": None,
        "github": None,
        "docs": None,
    }


def empty_contract_signals() -> Dict[str, Any]:
    return {
        "verified_contract": False,
        "contract_name": None,
        "is_proxy": False,
        "implementation": None,
        "erc20": False,
        "erc721": False,
        "erc1155": False,
        "has_metadata": False,
        "bytecode_known": False,
        "generic_name_risk": False,
    }


def empty_activity_signals() -> Dict[str, Any]:
    return {
        "transfer_count": 0,
        "unique_wallets": 0,
        "deployer_only": None,
        "tx_count_sample": 0,
        "unique_wallets_sample": 0,
        "activity_continues": False,
    }


def empty_market_signals() -> Dict[str, Any]:
    return {
        "dex_listed": False,
        "dex_id": None,
        "pair_address": None,
        "liquidity_usd": 0.0,
        "volume_usd_24h": 0.0,
        "price_usd": 0.0,
        "recognized_dex": False,
    }


def base_candidate(
    *,
    chain: str,
    address: str,
    object_type: str = "unknown_contract",
    snapshot_date: str,
    source: str,
) -> Dict[str, Any]:
    return {
        "id": make_id(chain, object_type, address),
        "chain": chain,
        "object_type": object_type,
        "address": address,
        "creator": None,
        "creation_tx": None,
        "created_at": None,
        "created_block": None,
        "first_seen": snapshot_date,
        "snapshot_date": snapshot_date,
        "name": None,
        "symbol": None,
        "description": None,
        "contract_signals": empty_contract_signals(),
        "activity_signals": empty_activity_signals(),
        "market_signals": empty_market_signals(),
        "socials": empty_socials(),
        "scores": {
            "project_likelihood_score": 0.0,
            "economic_activity_score": 0.0,
            "social_presence_score": 0.0,
            "spam_risk_score": 1.0,
            "momentum_score": 0.0,
            "confidence_score": 0.0,
        },
        "labels": [],
        "action": "ignore",
        "why_kept": [],
        "why_flagged": [],
        "source": source,
        "raw": {},
    }


def dedupe_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []

    for item in candidates:
        key = item.get("id") or f"{item.get('chain')}:{item.get('object_type')}:{item.get('address')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    return out
