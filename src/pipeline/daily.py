import math
from typing import Dict

from src.config import (
    EXTREME_STALE_VOLUME_LIQUIDITY_RATIO,
    MIN_WATCH_RECENT_DEX_TX_1H,
    MIN_WATCH_UNIQUE_WALLETS,
    MIN_WATCH_VOLUME_USD_24H,
    STALE_LIQUIDITY_CHECK_MIN_USD,
    STALE_VOLUME_LIQUIDITY_RATIO,
)
from src.pipeline.fodder_filter import count_project_signals
from src.utils import clamp01, safe_float


def _log_scaled(value: float, cap: float) -> float:
    if value <= 0:
        return 0.0
    if value >= cap:
        return 1.0
    return clamp01(math.log1p(value) / math.log1p(cap))


def _social_score(socials: Dict) -> float:
    weights = {
        "website": 0.30,
        "twitter_x": 0.22,
        "telegram": 0.12,
        "discord": 0.10,
        "github": 0.13,
        "docs": 0.13,
    }
    return clamp01(sum(weight for key, weight in weights.items() if socials.get(key)))


def _volume_liquidity_ratio(market: Dict) -> float:
    volume = safe_float(market.get("volume_usd_24h"), 0.0)
    liquidity = safe_float(market.get("liquidity_usd"), 0.0)
    return volume / liquidity if liquidity > 0 else 0.0


def _watch_support_count(
    *,
    socials_score: float,
    volume_usd_24h: float,
    dex_tx_count_1h: int,
    volume_liquidity_ratio: float,
    unique_wallets: int,
    verified_or_metadata: bool,
    cluster_score: float,
    name_quality_score: float,
    identity_score: float,
) -> int:
    support = 0

    if socials_score > 0:
        support += 1
    if volume_usd_24h >= MIN_WATCH_VOLUME_USD_24H:
        support += 1
    if dex_tx_count_1h >= MIN_WATCH_RECENT_DEX_TX_1H:
        support += 1
    if volume_liquidity_ratio >= STALE_VOLUME_LIQUIDITY_RATIO:
        support += 1
    if unique_wallets >= MIN_WATCH_UNIQUE_WALLETS:
        support += 1
    if verified_or_metadata:
        support += 1
    if cluster_score >= 0.35:
        support += 1
    if name_quality_score >= 0.45:
        support += 1
    if identity_score >= 0.40:
        support += 1

    return support


def score_item(item: Dict) -> Dict:
    contract = item.get("contract_signals", {}) or {}
    activity = item.get("activity_signals", {}) or {}
    market = item.get("market_signals", {}) or {}
    cluster = item.get("cluster_signals", {}) or {}
    socials = item.get("socials", {}) or {}
    identity = item.get("identity_signals", {}) or {}

    signal_count = count_project_signals(item)

    verified_score = 1.0 if contract.get("verified_contract") else 0.0
    metadata_score = 1.0 if contract.get("has_metadata") else 0.0
    name_quality_score = safe_float(item.get("name_quality", {}).get("score"), 0.0)
    identity_score = safe_float(identity.get("score"), 0.0)

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

    volume_usd_24h = safe_float(market.get("volume_usd_24h"), 0.0)
    liquidity_usd = safe_float(market.get("liquidity_usd"), 0.0)
    dex_tx_count_1h = int(market.get("dex_tx_count_1h") or 0)
    vl_ratio = _volume_liquidity_ratio(market)

    wallet_score = _log_scaled(unique_wallets, 150)
    tx_score = _log_scaled(tx_count, 300)
    liquidity_score = _log_scaled(liquidity_usd, 100_000)
    volume_score = _log_scaled(volume_usd_24h, 100_000)

    dex_score = 1.0 if market.get("dex_listed") else 0.0
    recognized_dex_score = 1.0 if market.get("recognized_dex") else 0.0
    socials_score = _social_score(socials)
    momentum_score = clamp01(item.get("scores", {}).get("momentum_score", 0.0))
    project_signal_score = clamp01(signal_count / 10.0)
    cluster_score = clamp01(safe_float(cluster.get("cluster_score"), 0.0))

    verified_or_metadata = bool(
        contract.get("verified_contract")
        or contract.get("has_metadata")
        or (item.get("chain") == "solana" and contract.get("bytecode_known"))
    )

    economic_activity_score = clamp01(
        0.25 * wallet_score
        + 0.20 * tx_score
        + 0.16 * liquidity_score
        + 0.16 * volume_score
        + 0.10 * dex_score
        + 0.05 * recognized_dex_score
        + 0.08 * cluster_score
    )

    spam_risk_score = 0.0

    if contract.get("generic_name_risk"):
        spam_risk_score += 0.14
    if not contract.get("verified_contract") and item.get("chain") in {"base", "ethereum"}:
        spam_risk_score += 0.10
    if not contract.get("has_metadata"):
        spam_risk_score += 0.12
    if unique_wallets <= 1:
        spam_risk_score += 0.18
    if tx_count <= 1:
        spam_risk_score += 0.14
    if not market.get("dex_listed"):
        spam_risk_score += 0.08
    if socials_score == 0:
        spam_risk_score += 0.18
    if activity.get("deployer_only") is True:
        spam_risk_score += 0.22
    if dex_tx_count_1h == 0:
        spam_risk_score += 0.08
    if volume_usd_24h < MIN_WATCH_VOLUME_USD_24H:
        spam_risk_score += 0.07

    if liquidity_usd >= STALE_LIQUIDITY_CHECK_MIN_USD and vl_ratio < EXTREME_STALE_VOLUME_LIQUIDITY_RATIO:
        spam_risk_score += 0.22
    elif liquidity_usd >= STALE_LIQUIDITY_CHECK_MIN_USD and vl_ratio < STALE_VOLUME_LIQUIDITY_RATIO:
        spam_risk_score += 0.12

    if cluster.get("creator_spammy"):
        spam_risk_score += 0.22
    if cluster_score == 0 and item.get("chain") in {"base", "ethereum"}:
        spam_risk_score += 0.04
    if "suspicious_name_pattern" in item.get("labels", []):
        spam_risk_score += 0.08

    if name_quality_score < 0.25:
        spam_risk_score += 0.18
    elif name_quality_score < 0.45:
        spam_risk_score += 0.10

    if identity_score < 0.20:
        spam_risk_score += 0.16
    elif identity_score < 0.40:
        spam_risk_score += 0.08

    if identity.get("spam_hits", 0) > 0:
        spam_risk_score += 0.18

    if "bad_phrase_name" in item.get("labels", []):
        spam_risk_score += 0.20
    if "long_phrase_name" in item.get("labels", []):
        spam_risk_score += 0.12
    if item.get("raw", {}).get("hard_ignore"):
        spam_risk_score += 0.40

    spam_risk_score = clamp01(spam_risk_score)

    project_likelihood_score = clamp01(
        0.11 * verified_score
        + 0.10 * metadata_score
        + 0.09 * standard_score
        + 0.12 * wallet_score
        + 0.08 * tx_score
        + 0.13 * socials_score
        + 0.10 * cluster_score
        + 0.06 * identity_score
        + 0.04 * name_quality_score
        + 0.05 * dex_score
        + 0.03 * recognized_dex_score
        + 0.05 * project_signal_score
        + 0.04 * momentum_score
        - 0.34 * spam_risk_score
    )

    confidence_score = clamp01(
        0.16 * project_signal_score
        + 0.14 * wallet_score
        + 0.15 * socials_score
        + 0.10 * metadata_score
        + 0.09 * verified_score
        + 0.11 * economic_activity_score
        + 0.08 * cluster_score
        + 0.08 * identity_score
        + 0.04 * name_quality_score
        + 0.05 * (1.0 - spam_risk_score)
    )

    watch_support_count = _watch_support_count(
        socials_score=socials_score,
        volume_usd_24h=volume_usd_24h,
        dex_tx_count_1h=dex_tx_count_1h,
        volume_liquidity_ratio=vl_ratio,
        unique_wallets=unique_wallets,
        verified_or_metadata=verified_or_metadata,
        cluster_score=cluster_score,
        name_quality_score=name_quality_score,
        identity_score=identity_score,
    )

    watch_block_reasons = []

    if item.get("raw", {}).get("hard_ignore"):
        watch_block_reasons.append("hard_ignore")
    if spam_risk_score > 0.35:
        watch_block_reasons.append("spam_risk_above_0_35")
    if socials_score == 0 and dex_tx_count_1h == 0 and cluster_score < 0.35 and identity_score < 0.40:
        watch_block_reasons.append("no_socials_zero_recent_dex_no_cluster_no_identity")
    if liquidity_usd >= STALE_LIQUIDITY_CHECK_MIN_USD and vl_ratio < EXTREME_STALE_VOLUME_LIQUIDITY_RATIO:
        watch_block_reasons.append("extremely_stale_liquidity")
    if activity.get("deployer_only") is True:
        watch_block_reasons.append("deployer_only_activity")
    if cluster.get("creator_spammy"):
        watch_block_reasons.append("creator_spammy")
    if name_quality_score < 0.45:
        watch_block_reasons.append("poor_name_quality")
    if identity_score < 0.40:
        watch_block_reasons.append("weak_project_identity")
    if watch_support_count < 4:
        watch_block_reasons.append(f"watch_support_count_below_4={watch_support_count}")

    if (
        project_likelihood_score >= 0.72
        and confidence_score >= 0.62
        and not watch_block_reasons
    ):
        action = "watch_now"
    elif (
        project_likelihood_score >= 0.38
        and confidence_score >= 0.34
        and not item.get("raw", {}).get("hard_ignore")
    ):
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
            "identity_score": round(identity_score, 4),
            "name_quality_score": round(name_quality_score, 4),
            "cluster_score": round(cluster_score, 4),
        }
    )

    item.setdefault("raw", {})
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
        "cluster_score": round(cluster_score, 4),
        "identity_score": round(identity_score, 4),
        "name_quality_score": round(name_quality_score, 4),
        "volume_liquidity_ratio": round(vl_ratio, 6),
        "watch_support_count": watch_support_count,
        "watch_block_reasons": watch_block_reasons,
    }

    item["action"] = action

    for reason in watch_block_reasons:
        item["why_flagged"].append(f"watch_block={reason}")

    if action == "watch_now":
        item["labels"].append("watch_now")
    elif action == "research":
        item["labels"].append("research_candidate")
    else:
        item["labels"].append("ignored_by_score")

    item["labels"] = sorted(set(item.get("labels", [])))
    item["why_flagged"] = list(dict.fromkeys(item.get("why_flagged", [])))
    item["why_kept"] = list(dict.fromkeys(item.get("why_kept", [])))

    return item
