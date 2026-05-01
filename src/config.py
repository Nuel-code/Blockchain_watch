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

# Important:
# OFF for historical backfill speed.
# ON for daily mode/project-first discovery.
ENABLE_PROJECT_SEEDS = os.getenv("ENABLE_PROJECT_SEEDS", "0") == "1"

BACKFILL_START_OVERRIDE = os.getenv("BACKFILL_START_OVERRIDE", "").strip()
BACKFILL_END_OVERRIDE = os.getenv("BACKFILL_END_OVERRIDE", "").strip()

TODAY_UTC = datetime.utcnow().strftime("%Y-%m-%d")


CHAIN_TO_ETHERSCAN_ID = {
    "ethereum": "1",
    "base": "8453",
}


KNOWN_EVM_FACTORY_ADDRESSES = {
    "base": [],
    "ethereum": [],
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
    "contract",
    "erc20",
    "erc721",
    "shitcoin",
}


SUSPICIOUS_TOKEN_NAME_TERMS = {
    "usdt",
    "usdc",
    "busd",
    "usdd",
    "dai",
    "wrapped",
    "staked",
    "savings",
    "yield",
    "claim",
    "airdrop",
    "free",
    "elon",
    "pepe",
    "doge",
}


MIN_EXTERNAL_WALLETS_SOFT = 2
MIN_TRANSFER_COUNT_SOFT = 2
MIN_SIGNAL_COUNT_FOR_PROJECT_LIKE = 3

MIN_WATCH_VOLUME_USD_24H = 200.0
MIN_WATCH_RECENT_DEX_TX_1H = 2
MIN_WATCH_UNIQUE_WALLETS = 10

STALE_VOLUME_LIQUIDITY_RATIO = 0.005
EXTREME_STALE_VOLUME_LIQUIDITY_RATIO = 0.001
STALE_LIQUIDITY_CHECK_MIN_USD = 10_000.0
