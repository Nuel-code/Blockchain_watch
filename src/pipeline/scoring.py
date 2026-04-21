from __future__ import annotations
from src.models import Candidate


def bucketize_liquidity(liquidity_usd: float) -> float:
    if liquidity_usd >= 100_000:
        return 1.0
    if liquidity_usd >= 25_000:
        return 0.8
    if liquidity_usd >= 10_000:
        return 0.6
    if liquidity_usd >= 2_500:
        return 0.4
    if liquidity_usd > 0:
        return 0.2
    return 0.0


def derive_labels(c: Candidate) -> list[str]:
    labels = []
    if c.relevance_score >= 0.70:
        labels.append("emerging")
    if c.relevance_score < 0.45:
        labels.append("low_signal")
    if c.spam_score >= 0.60:
        labels.append("spam_candidate")
    if c.scam_score >= 0.65:
        labels.append("scam_candidate")
    if c.confidence_score >= 0.60 and c.spam_score < 0.40:
        labels.append("likely_real")
    return labels


def derive_action(c: Candidate) -> str:
    if c.relevance_score >= 0.75 and c.confidence_score >= 0.60:
        return "watch_now"
    if c.relevance_score >= 0.55 and c.spam_score < 0.50:
        return "likely_real"
    return "ignore"


def score(c: Candidate) -> Candidate:
    liquidity_score = bucketize_liquidity(c.liquidity_usd)
    wallet_score = min(c.unique_external_wallets_1h / 20, 1.0)
    tx_score = min(c.tx_count_1h / 100, 1.0)
    setup_score = 1.0 if c.time_to_first_liquidity and c.time_to_first_liquidity < 3600 else 0.3
    factory_score = 1.0 if c.recognized_factory else 0.0
    verification_score = 1.0 if c.source_verified else 0.0
    website_score = 1.0 if c.website else 0.0
    social_score = c.social_confidence

    relevance = (
        0.22 * liquidity_score +
        0.18 * wallet_score +
        0.14 * tx_score +
        0.10 * setup_score +
        0.08 * factory_score +
        0.06 * verification_score +
        0.07 * website_score +
        0.10 * social_score +
        0.05 * c.deployer_quality_score -
        0.15 * c.spam_score -
        0.10 * c.scam_score
    )
    c.relevance_score = max(0.0, min(relevance, 1.0))

    confidence = 0.25
    if c.website:
        confidence += 0.15
    if c.source_verified:
        confidence += 0.15
    if c.recognized_factory:
        confidence += 0.10
    if c.tx_count_1h >= 10:
        confidence += 0.10
    if c.unique_external_wallets_1h >= 5:
        confidence += 0.10
    confidence += min(c.social_confidence, 0.15)

    c.confidence_score = max(0.0, min(confidence, 1.0))
    c.labels = derive_labels(c)
    c.action = derive_action(c)
    return c
