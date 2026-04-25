from typing import Dict

from src.config import (
    EXTREME_STALE_VOLUME_LIQUIDITY_RATIO,
    MIN_WATCH_RECENT_DEX_TX_1H,
    MIN_WATCH_VOLUME_USD_24H,
    STALE_LIQUIDITY_CHECK_MIN_USD,
    STALE_VOLUME_LIQUIDITY_RATIO,
    SUSPICIOUS_TOKEN_NAME_TERMS,
)
from src.pipeline.fodder_filter import apply_fodder_filter, count_project_signals
from src.utils import safe_float


def _has_any_social(item: Dict) -> bool:
    socials = item.get("socials", {}) or {}
    return any(bool(v) for v in socials.values())


def _volume_liquidity_ratio(item: Dict) -> float:
    market = item.get("market_signals", {}) or {}
    volume = safe_float(market.get("volume_usd_24h"), 0.0)
    liquidity = safe_float(market.get("liquidity_usd"), 0.0)

    if liquidity <= 0:
        return 0.0

    return volume / liquidity


def _has_suspicious_name(item: Dict) -> bool:
    name = (item.get("name") or "").lower()
    symbol = (item.get("symbol") or "").lower()
    text = f"{name} {symbol}"

    return any(term in text for term in SUSPICIOUS_TOKEN_NAME_TERMS)


def apply_filters(item: Dict) -> Dict:
    """
    Filtering philosophy:
    - Do not require liquidity.
    - Do not instantly delete early projects.
    - Aggressively flag obvious fodder.
    - Let scoring decide final action.
    """
    item = apply_fodder_filter(item)

    signal_count = count_project_signals(item)
    contract = item.get("contract_signals", {}) or {}
    activity = item.get("activity_signals", {}) or {}
    market = item.get("market_signals", {}) or {}
    socials = item.get("socials", {}) or {}

    hard_ignore = False

    volume = safe_float(market.get("volume_usd_24h"), 0.0)
    liquidity = safe_float(market.get("liquidity_usd"), 0.0)
    dex_tx_count_1h = int(market.get("dex_tx_count_1h") or 0)
    vl_ratio = _volume_liquidity_ratio(item)
    has_social = _has_any_social(item)

    item.setdefault("raw", {})
    item["raw"]["volume_liquidity_ratio"] = round(vl_ratio, 6)

    # True trash profile:
    # generic/unverified/no metadata/no activity/no market/no socials.
    if (
        contract.get("generic_name_risk")
        and not contract.get("verified_contract")
        and not contract.get("has_metadata")
        and activity.get("unique_wallets", 0) <= 1
        and activity.get("unique_wallets_sample", 0) <= 1
        and not market.get("dex_listed")
        and not has_social
    ):
        hard_ignore = True
        item["why_flagged"].append("hard_ignore_generic_unverified_dead_object")

    if signal_count <= 0:
        hard_ignore = True
        item["why_flagged"].append("hard_ignore_zero_project_signals")

    # Identity + market safety flags.
    if not has_social:
        item["labels"].append("identity_missing")
        item["why_flagged"].append("no_project_identity_links")

    if volume < MIN_WATCH_VOLUME_USD_24H:
        item["labels"].append("low_volume")
        item["why_flagged"].append(f"volume_below_{int(MIN_WATCH_VOLUME_USD_24H)}")

    if dex_tx_count_1h == 0:
        item["labels"].append("zero_recent_dex_tx")
        item["why_flagged"].append("zero_recent_dex_tx")

    elif dex_tx_count_1h < MIN_WATCH_RECENT_DEX_TX_1H:
        item["labels"].append("weak_recent_dex_tx")
        item["why_flagged"].append("weak_recent_dex_tx")

    if liquidity >= STALE_LIQUIDITY_CHECK_MIN_USD and vl_ratio < EXTREME_STALE_VOLUME_LIQUIDITY_RATIO:
        item["labels"].append("extremely_stale_liquidity")
        item["why_flagged"].append("extremely_stale_liquidity")

    elif liquidity >= STALE_LIQUIDITY_CHECK_MIN_USD and vl_ratio < STALE_VOLUME_LIQUIDITY_RATIO:
        item["labels"].append("stale_liquidity")
        item["why_flagged"].append("stale_liquidity")

    if _has_suspicious_name(item):
        item["labels"].append("suspicious_name_pattern")
        item["why_flagged"].append("suspicious_name_pattern")

    # Combination block: no identity + no recent DEX activity is not watchable.
    if not has_social and dex_tx_count_1h == 0:
        item["labels"].append("watch_block_no_identity_no_recent_dex")
        item["why_flagged"].append("watch_block_no_identity_no_recent_dex")

    item["raw"]["hard_ignore"] = hard_ignore
    item["raw"]["project_signal_count"] = signal_count
    item["raw"]["has_any_social"] = has_social
    item["raw"]["dex_tx_count_1h"] = dex_tx_count_1h
    item["raw"]["volume_usd_24h"] = volume
    item["raw"]["liquidity_usd"] = liquidity

    item["labels"] = sorted(set(item.get("labels", [])))
    item["why_kept"] = list(dict.fromkeys(item.get("why_kept", [])))
    item["why_flagged"] = list(dict.fromkeys(item.get("why_flagged", [])))

    return item
