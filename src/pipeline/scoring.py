import math
from typing import Dict

from src.pipeline.fodder_filter import count_project_signals
from src.utils import clamp01


def _log_scaled(value: float, cap: float) -> float:
    if value <= 0:
        return 0.0

    if value >= cap:
        return 1.0

    return clamp01(math.log1p(value) / math.log1p(cap))


def _social_score(socials: Dict) -> float:
    if not socials:
        return 0.0

    weights = {
        "website": 0.28,
        "twitter_x": 0.22,
        "telegram": 0.14,
        "discord": 0.12,
        "github": 0.12,
        "docs": 0.12,
    }

    return clamp01(sum(weight for key, weight in weights.items() if socials.get(key)))


def score_item(item: Dict) -> Dict:
    contract = item.get("contract_signals", {})
    activity = item.get("activity_signals", {})
    market = item.get("market_signals", {})
    socials = item.get("socials", {})

    signal_count = count_project_signals(item)

    verified_score = 1.0 if contract.get("verified_contract") else 0.0
    metadata_score = 1.0 if contract.get("has_metadata") else 0.0

    standard_score = 0.0
    if contract.get("erc20"):
        standard_score = max(standard_score, 0.9)
    if contract.get("erc721") or contract.get("erc1155"):
        standard_score = max(standard_score, 0.75)
    if item.get("chain") == "solana" and contract.get("bytecode_known"):
        standard_score = max(standard_score, 0.55)

    unique_wallets = max(
        activity.get("unique_wallets", 0) or 0,
        activity.get("unique_wallets_sample", 0) or 0,
    )

    tx_count = max(
        activity.get("transfer_count", 0) or 0,
        activity.get("tx_count_sample", 0) or 0,
        market.get("dex_tx_count_1h", 0) or 0,
    )

    wallet_score = _log_scaled(unique_wallets, 150)
    tx_score = _log_scaled(tx_count, 300)

    liquidity_score = _log_scaled(market.get("liquidity_usd", 0) or 0, 100_000)
    volume_score = _log_scaled(market.get("volume_usd_24h", 0) or 0, 500_000)
    dex_score = 1.0 if market.get("dex_listed") else 0.0
    recognized_dex_score = 1.0 if market.get("recognized_dex") else 0.0

    socials_score = _social_score(socials)
    momentum_score = clamp01(item.get("scores", {}).get("momentum_score", 0.0))

    project_signal_score = clamp01(signal_count / 7.0)

    economic_activity_score = clamp01(
        0.35 * wallet_score
        + 0.25 * tx_score
        + 0.20 * liquidity_score
        + 0.10 * volume_score
        + 0.10 * dex_score
    )

    spam_risk_score = 0.0

    if contract.get("generic_name_risk"):
        spam_risk_score += 0.16

    if not contract.get("verified_contract") and item.get("chain") in {"base", "ethereum"}:
        spam_risk_score += 0.12

    if not contract.get("has_metadata"):
        spam_risk_score += 0.14

    if unique_wallets <= 1:
        spam_risk_score += 0.18

    if tx_count <= 1:
        spam_risk_score += 0.14

    if not market.get("dex_listed"):
        spam_risk_score += 0.08

    if socials_score == 0:
        spam_risk_score += 0.14

    if activity.get("deployer_only") is True:
        spam_risk_score += 0.18

    if item.get("raw", {}).get("hard_ignore"):
        spam_risk_score += 0.4

    spam_risk_score = clamp01(spam_risk_score)

    project_likelihood_score = clamp01(
        0.16 * verified_score
        + 0.13 * metadata_score
        + 0.12 * standard_score
        + 0.16 * wallet_score
        + 0.12 * tx_score
        + 0.13 * socials_score
        + 0.08 * dex_score
        + 0.05 * recognized_dex_score
        + 0.05 * project_signal_score
        + 0.05 * momentum_score
        - 0.28 * spam_risk_score
    )

    confidence_score = clamp01(
        0.22 * project_signal_score
        + 0.18 * wallet_score
        + 0.14 * socials_score
        + 0.12 * metadata_score
        + 0.12 * verified_score
        + 0.12 * economic_activity_score
        + 0.10 * (1.0 - spam_risk_score)
    )

    if item.get("raw", {}).get("hard_ignore"):
        action = "ignore"
    elif project_likelihood_score >= 0.72 and confidence_score >= 0.62:
        action = "watch_now"
    elif project_likelihood_score >= 0.46 and confidence_score >= 0.42:
        action = "research"
    else:
        action = "ignore"

    item["scores"].update(
        {
            "project_likelihood_score": round(project_likelihood_score, 4),
            "economic_activity_score": round(economic_activity_score, 4),
            "social_presence_score": round(socials_score, 4),
            "spam_risk_score": round(spam_risk_score, 4),
            "momentum_score": round(momentum_score, 4),
            "confidence_score": round(confidence_score, 4),
        }
    )

    item["raw"]["score_components"] = {
        "verified_score": round(verified_score, 4),
        "metadata_score": round(metadata_score, 4),
        "standard_score": round(standard_score, 4),
        "wallet_score": round(wallet_score, 4),
        "tx_score": round(tx_score, 4),
        "liquidity_score": round(liquidity_score, 4),
        "volume_score": round(volume_score, 4),
        "dex_score": round(dex_score, 4),
        "recognized_dex_score": round(recognized_dex_score, 4),
        "project_signal_score": round(project_signal_score, 4),
    }

    item["action"] = action

    if action == "watch_now":
        item["labels"].append("watch_now")
    elif action == "research":
        item["labels"].append("research_candidate")
    else:
        item["labels"].append("ignored_by_score")

    item["labels"] = sorted(set(item.get("labels", [])))

    return item
