import os
from datetime import datetime


CHAINS = ["base", "ethereum", "solana"]

DATA_DIR = "data"
STATE_DIR = "state"

DEFAULT_BACKFILL_START = "2026-01-01"
MAX_PER_DAY = 500

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "").strip() or "https://api.mainnet-beta.solana.com"
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "").strip()

BACKFILL_START_OVERRIDE = os.getenv("BACKFILL_START_OVERRIDE", "").strip()
BACKFILL_END_OVERRIDE = os.getenv("BACKFILL_END_OVERRIDE", "").strip()

TODAY_UTC = datetime.utcnow().strftime("%Y-%m-%d")


CHAIN_TO_ETHERSCAN_ID = {
    "ethereum": "1",
    "base": "8453",
}


# Known factory / launch-surface addresses.
# Keep this list conservative. Expanding it increases recall but also noise.
#
# For this MVP, DexScreener visible candidates fill the discovery gap.
# These factory lists can be expanded once the output quality is proven.
KNOWN_EVM_FACTORY_ADDRESSES = {
    "base": [
        # Add known Base launch/factory addresses here later.
        # Example format:
        # "0x0000000000000000000000000000000000000000",
    ],
    "ethereum": [
        # Add known Ethereum launch/factory addresses here later.
    ],
}


RECOGNIZED_DEX_IDS = {
    "solana": {
        "raydium",
        "meteora",
        "orca",
        "pumpfun",
        "pumpswap",
        "jupiter",
        "moonshot",
    },
    "base": {
        "uniswap",
        "aerodrome",
        "baseswap",
        "alienbase",
        "sushiswap",
        "pancakeswap",
    },
    "ethereum": {
        "uniswap",
        "sushiswap",
        "pancakeswap",
        "balancer",
        "curve",
    },
}


GENERIC_BAD_NAME_TERMS = {
    "test",
    "demo",
    "sample",
    "mock",
    "fake",
    "mytoken",
    "token",
    "contract",
    "erc20",
    "erc721",
    "shitcoin",
}


# These are not hard gates for final scoring.
# They are used for obvious-fodder filtering.
MIN_EXTERNAL_WALLETS_SOFT = 2
MIN_TRANSFER_COUNT_SOFT = 2
MIN_SIGNAL_COUNT_FOR_PROJECT_LIKE = 3
