from __future__ import annotations
from src.models import Candidate


def enrich(candidate: Candidate) -> Candidate:
    if candidate.chain == "ethereum":
        candidate.liquidity_usd = 12000
        candidate.unique_external_wallets_1h = 8
        candidate.tx_count_1h = 25
        candidate.time_to_first_liquidity = 420
        candidate.source_verified = True
    elif candidate.chain == "base":
        candidate.liquidity_usd = 24000
        candidate.unique_external_wallets_1h = 15
        candidate.tx_count_1h = 44
        candidate.time_to_first_liquidity = 180
        candidate.recognized_factory = True
        candidate.recognized_factory_name = "UniswapV2"
    elif candidate.chain == "solana":
        candidate.liquidity_usd = 9000
        candidate.unique_external_wallets_1h = 11
        candidate.tx_count_1h = 37
        candidate.time_to_first_liquidity = 300

    return candidate
