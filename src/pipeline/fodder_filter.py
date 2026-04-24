from typing import Any, Dict

from src.config import MIN_SIGNAL_COUNT_FOR_PROJECT_LIKE
from src.utils import count_non_empty


def count_project_signals(item: Dict[str, Any]) -> int:
    contract = item.get("contract_signals", {})
    activity = item.get("activity_signals", {})
    market = item.get("market_signals", {})
    socials = item.get("socials", {})

    signal_count = 0

    if contract.get("verified_contract"):
        signal_count += 1

    if contract.get("has_metadata"):
        signal_count += 1

    if contract.get("erc20") or contract.get("erc721") or contract.get("erc1155"):
        signal_count += 1

    if activity.get("unique_wallets", 0) >= 2 or activity.get("unique_wallets_sample", 0) >= 2:
        signal_count += 1

    if activity.get("transfer_count", 0) >= 2 or activity.get("tx_count_sample", 0) >= 2:
        signal_count += 1

    if market.get("dex_listed"):
        signal_count += 1

    if market.get("liquidity_usd", 0) > 0:
        signal_count += 1

    if count_non_empty(socials.values()) > 0:
        signal_count += 1

    if socials.get("website"):
        signal_count += 1

    return signal_count


def apply_fodder_filter(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Not a brutal liquidity gate.

    This detects obvious garbage, then leaves scoring to rank the survivors.
    """
    why_kept = item.get("why_kept", [])
    why_flagged = item.get("why_flagged", [])
    labels = item.get("labels", [])

    contract = item.get("contract_signals", {})
    activity = item.get("activity_signals", {})
    market = item.get("market_signals", {})
    socials = item.get("socials", {})

    signal_count = count_project_signals(item)
    item.setdefault("raw", {})
    item["raw"]["project_signal_count"] = signal_count

    if signal_count >= MIN_SIGNAL_COUNT_FOR_PROJECT_LIKE:
        labels.append("project_like_signal_bundle")
        why_kept.append(f"project_signal_count={signal_count}")
    else:
        why_flagged.append(f"low_project_signal_count={signal_count}")

    if contract.get("generic_name_risk"):
        labels.append("generic_name_risk")
        why_flagged.append("generic_or_test_like_name")

    if activity.get("deployer_only") is True:
        labels.append("deployer_only_risk")
        why_flagged.append("deployer_only_activity")

    if not contract.get("has_metadata"):
        why_flagged.append("missing_metadata")

    if count_non_empty(socials.values()) == 0:
        why_flagged.append("no_socials_found")

    if market.get("dex_listed"):
        labels.append("dex_visible")
        why_kept.append(f"dex_listed={market.get('dex_id')}")

    if market.get("liquidity_usd", 0) > 0:
        labels.append("has_liquidity")
        why_kept.append(f"liquidity_usd={market.get('liquidity_usd')}")

    if activity.get("unique_wallets", 0) >= 2 or activity.get("unique_wallets_sample", 0) >= 2:
        labels.append("multi_wallet_activity")
        why_kept.append(
            f"wallets={max(activity.get('unique_wallets', 0), activity.get('unique_wallets_sample', 0))}"
        )

    item["labels"] = sorted(set(labels))
    item["why_kept"] = list(dict.fromkeys(why_kept))
    item["why_flagged"] = list(dict.fromkeys(why_flagged))

    return item
