from typing import Dict

from src.pipeline.fodder_filter import apply_fodder_filter, count_project_signals


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
    contract = item.get("contract_signals", {})
    activity = item.get("activity_signals", {})
    market = item.get("market_signals", {})
    socials = item.get("socials", {})

    hard_ignore = False

    # True trash profile:
    # generic/unverified/no metadata/no activity/no market/no socials.
    if (
        contract.get("generic_name_risk")
        and not contract.get("verified_contract")
        and not contract.get("has_metadata")
        and activity.get("unique_wallets", 0) <= 1
        and activity.get("unique_wallets_sample", 0) <= 1
        and not market.get("dex_listed")
        and not any(socials.values())
    ):
        hard_ignore = True
        item["why_flagged"].append("hard_ignore_generic_unverified_dead_object")

    # If zero project-like signals, this is almost certainly fodder.
    if signal_count <= 0:
        hard_ignore = True
        item["why_flagged"].append("hard_ignore_zero_project_signals")

    item["raw"]["hard_ignore"] = hard_ignore
    item["raw"]["project_signal_count"] = signal_count

    item["labels"] = sorted(set(item.get("labels", [])))
    item["why_kept"] = list(dict.fromkeys(item.get("why_kept", [])))
    item["why_flagged"] = list(dict.fromkeys(item.get("why_flagged", [])))

    return item
