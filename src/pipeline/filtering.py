from src.config import (
    MIN_LIQUIDITY_USD,
    MIN_TX_COUNT_1H,
    MIN_UNIQUE_WALLETS_1H,
    RECOGNIZED_FACTORIES,
)
from src.utils import count_non_empty


def apply_filters(item: dict) -> dict:
    chain = item["chain"]
    dex_id = (item.get("recognized_factory") or "").lower()
    socials = item.get("socials", {})

    social_count = count_non_empty(socials.values())

    keep = True
    why_kept = []
    why_flagged = []
    labels = []

    if item["liquidity_usd"] >= MIN_LIQUIDITY_USD:
        why_kept.append(f"liquidity_usd={item['liquidity_usd']:.2f}")
        labels.append("liquid")
    else:
        why_flagged.append("low_liquidity")
        keep = False

    if item["tx_count_1h"] >= MIN_TX_COUNT_1H:
        why_kept.append(f"tx_count_1h={item['tx_count_1h']}")
        labels.append("active")
    else:
        why_flagged.append("low_activity")
        keep = False

    if item["unique_external_wallets_1h"] >= MIN_UNIQUE_WALLETS_1H:
        why_kept.append(f"unique_external_wallets_1h={item['unique_external_wallets_1h']}")
        labels.append("multi_wallet")
    else:
        why_flagged.append("few_unique_wallets")

    if dex_id in RECOGNIZED_FACTORIES.get(chain, set()):
        why_kept.append(f"recognized_factory={dex_id}")
        labels.append("dex_listed")
    else:
        why_flagged.append("unrecognized_factory")

    if social_count > 0:
        why_kept.append(f"social_count={social_count}")
        labels.append("socially_present")
    else:
        why_flagged.append("no_socials")

    if socials.get("website"):
        labels.append("has_website")

    item["why_kept"] = why_kept
    item["why_flagged"] = why_flagged
    item["labels"] = labels
    item["signals"]["social_count"] = social_count
    item["signals"]["keep_gate_passed"] = keep

    return item
