from __future__ import annotations
from src.models import Candidate
from src.pipeline.socials import resolve_socials
from src.clients.dexscreener import DexScreenerClient


dex_client = DexScreenerClient()


def _safe_float(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def enrich(candidate: Candidate) -> Candidate:
    candidate = resolve_socials(candidate)

    pairs = dex_client.fetch_token_pairs(candidate.address)

    chain_pairs = []
    for pair in pairs:
        if pair.get("chainId") == candidate.chain:
            chain_pairs.append(pair)

    best_pair = None
    best_liquidity = -1.0

    for pair in chain_pairs:
        liq = _safe_float((pair.get("liquidity") or {}).get("usd"))
        if liq > best_liquidity:
            best_liquidity = liq
            best_pair = pair

    if best_pair:
        liquidity = _safe_float((best_pair.get("liquidity") or {}).get("usd"))
        volume_24h = _safe_float((best_pair.get("volume") or {}).get("h24"))
        txns_h24 = best_pair.get("txns") or {}
        txns_h24_total = 0

        # DexScreener exposes h24 more reliably than h1 across many pairs.
        # MVP proxy: use h24 txns compressed to hourly-ish estimate.
        if isinstance(txns_h24, dict):
            h24 = txns_h24.get("h24") or {}
            buys = _safe_int(h24.get("buys"))
            sells = _safe_int(h24.get("sells"))
            txns_h24_total = buys + sells

        candidate.liquidity_usd = liquidity
        candidate.tx_count_1h = max(0, txns_h24_total // 24)

        # We do not get unique wallets directly here.
        # MVP proxy from txn breadth.
        if txns_h24_total >= 240:
            candidate.unique_external_wallets_1h = 18
        elif txns_h24_total >= 120:
            candidate.unique_external_wallets_1h = 10
        elif txns_h24_total >= 48:
            candidate.unique_external_wallets_1h = 6
        elif txns_h24_total >= 12:
            candidate.unique_external_wallets_1h = 3
        else:
            candidate.unique_external_wallets_1h = 1

        # No true launch timestamp from current candidate feed.
        # Use pairCreatedAt if available as a weak proxy.
        pair_created_at = best_pair.get("pairCreatedAt")
        if pair_created_at:
            candidate.time_to_first_liquidity = 300
        else:
            candidate.time_to_first_liquidity = None

        dex_id = best_pair.get("dexId")
        if dex_id:
            candidate.recognized_factory = True
            candidate.recognized_factory_name = dex_id

        candidate.raw_refs["best_pair"] = {
            "pairAddress": best_pair.get("pairAddress"),
            "dexId": best_pair.get("dexId"),
            "url": best_pair.get("url"),
            "liquidity_usd": liquidity,
            "volume_h24": volume_24h,
        }

    else:
        candidate.liquidity_usd = 0.0
        candidate.tx_count_1h = 0
        candidate.unique_external_wallets_1h = 0
        candidate.time_to_first_liquidity = None

    if candidate.website:
        candidate.deployer_quality_score = max(candidate.deployer_quality_score, 0.35)

    if candidate.social_confidence >= 0.4:
        candidate.deployer_quality_score = max(candidate.deployer_quality_score, 0.5)

    if candidate.liquidity_usd >= 10000:
        candidate.deployer_quality_score = max(candidate.deployer_quality_score, 0.6)

    return candidate
