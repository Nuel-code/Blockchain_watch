from __future__ import annotations
from src.models import Candidate
from src.pipeline.socials import resolve_socials


def enrich(candidate: Candidate) -> Candidate:
    candidate = resolve_socials(candidate)

    if candidate.chain == "ethereum":
        candidate.liquidity_usd = 5000
        candidate.unique_external_wallets_1h = 6
        candidate.tx_count_1h = 12
        candidate.time_to_first_liquidity = 600

    elif candidate.chain == "base":
        candidate.liquidity_usd = 7000
        candidate.unique_external_wallets_1h = 7
        candidate.tx_count_1h = 14
        candidate.time_to_first_liquidity = 420

    elif candidate.chain == "solana":
        candidate.liquidity_usd = 9000
        candidate.unique_external_wallets_1h = 11
        candidate.tx_count_1h = 37
        candidate.time_to_first_liquidity = 300

    if candidate.website:
        candidate.deployer_quality_score = 0.35
    if candidate.social_confidence >= 0.4:
        candidate.deployer_quality_score = max(candidate.deployer_quality_score, 0.5)

    return candidate
