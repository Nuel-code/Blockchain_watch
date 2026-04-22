from src.config import RECOGNIZED_FACTORIES
from src.utils import clamp01


def _log_scaled(x: float, cap: float) -> float:
    if x <= 0:
        return 0.0
    if x >= cap:
        return 1.0
    # simple nonlinear-ish scale without importing math? no, let's use math.
    import math
    return clamp01(math.log1p(x) / math.log1p(cap))


def score_item(item: dict) -> dict:
    liquidity_score = _log_scaled(item["liquidity_usd"], 100_000)
    activity_score = _log_scaled(item["tx_count_1h"], 200)
    wallet_score = _log_scaled(item["unique_external_wallets_1h"], 100)
    volume_score = _log_scaled(item["volume_usd_24h"], 500_000)

    social_count = item["signals"].get("social_count", 0)
    social_score = clamp01(social_count / 5.0)

    recognized = (item.get("recognized_factory") or "").lower() in RECOGNIZED_FACTORIES.get(item["chain"], set())
    factory_score = 1.0 if recognized else 0.2

    momentum_score = clamp01(item.get("signals", {}).get("momentum_score", 0.0))

    spam_penalty = 0.0
    if item["liquidity_usd"] <= 0:
        spam_penalty += 0.35
    if item["tx_count_1h"] <= 1:
        spam_penalty += 0.2
    if item["unique_external_wallets_1h"] <= 1:
        spam_penalty += 0.2
    if social_count == 0:
        spam_penalty += 0.15
    if not recognized:
        spam_penalty += 0.1

    relevance_score = (
        0.23 * liquidity_score
        + 0.18 * activity_score
        + 0.16 * wallet_score
        + 0.16 * social_score
        + 0.10 * factory_score
        + 0.07 * volume_score
        + 0.10 * momentum_score
    ) - spam_penalty * 0.35

    confidence_score = (
        0.18 * liquidity_score
        + 0.14 * activity_score
        + 0.20 * wallet_score
        + 0.22 * social_score
        + 0.16 * factory_score
        + 0.10 * (1.0 - clamp01(spam_penalty))
    )

    relevance_score = clamp01(relevance_score)
    confidence_score = clamp01(confidence_score)

    if relevance_score >= 0.72 and confidence_score >= 0.65:
        action = "watch_now"
    elif relevance_score >= 0.45 and confidence_score >= 0.45:
        action = "likely_real"
    else:
        action = "ignore"

    item["signals"].update(
        {
            "liquidity_score": round(liquidity_score, 4),
            "activity_score": round(activity_score, 4),
            "wallet_score": round(wallet_score, 4),
            "social_score": round(social_score, 4),
            "factory_score": round(factory_score, 4),
            "volume_score": round(volume_score, 4),
            "momentum_score": round(momentum_score, 4),
        }
    )

    item["risk_scores"] = {
        "spam_penalty": round(spam_penalty, 4),
        "confidence_score": round(confidence_score, 4),
    }
    item["scores"] = {
        "relevance_score": round(relevance_score, 4),
        "confidence_score": round(confidence_score, 4),
    }
    item["action"] = action
    return item
