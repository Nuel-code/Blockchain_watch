import os
from datetime import datetime

CHAINS = ["solana", "base", "ethereum"]

DATA_DIR = "data"
STATE_DIR = "state"

DEFAULT_BACKFILL_START = "2026-01-01"
MAX_PER_DAY = 500

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "").strip() or "https://api.mainnet-beta.solana.com"

BACKFILL_START_OVERRIDE = os.getenv("BACKFILL_START_OVERRIDE", "").strip()
BACKFILL_END_OVERRIDE = os.getenv("BACKFILL_END_OVERRIDE", "").strip()

TODAY_UTC = datetime.utcnow().strftime("%Y-%m-%d")

CHAIN_TO_ETHERSCAN_ID = {
    "ethereum": "1",
    "base": "8453",
}

RECOGNIZED_FACTORIES = {
    "solana": {
        "raydium", "meteora", "orca", "pumpfun", "jupiter", "moonshot"
    },
    "base": {
        "uniswap", "aerodrome", "baseswap", "alienbase", "sushiswap"
    },
    "ethereum": {
        "uniswap", "sushiswap", "pancakeswap", "balancer", "curve"
    },
}

MIN_LIQUIDITY_USD = 500.0
MIN_TX_COUNT_1H = 3
MIN_UNIQUE_WALLETS_1H = 3
