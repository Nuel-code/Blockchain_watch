from collections import Counter
from typing import Any, Dict, List

from src.clients.dexscreener import orders_for_token, token_pairs
from src.config import CHAIN_TO_ETHERSCAN_ID, ETHERSCAN_API_KEY, SOLANA_RPC_URL
from src.utils import request_json, safe_float


def select_best_pair(chain: str, token_address: str) -> dict:
    pairs = token_pairs(chain, token_address)
    if not pairs:
        return {}

    def pair_score(p: dict) -> float:
        liquidity = safe_float((p.get("liquidity") or {}).get("usd"), 0.0)
        volume = safe_float((p.get("volume") or {}).get("h24"), 0.0)
        txns_h1 = p.get("txns", {}).get("h1", {})
        tx_count_1h = safe_float(txns_h1.get("buys"), 0) + safe_float(txns_h1.get("sells"), 0)
        return liquidity * 1.0 + volume * 0.2 + tx_count_1h * 10

    pairs = sorted(pairs, key=pair_score, reverse=True)
    return pairs[0]


def _solana_activity_proxy(token_address: str) -> Dict[str, int]:
    # MVP proxy: fetch recent signatures for the token address, then inspect up to 15 txs.
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            token_address,
            {"limit": 15}
        ],
    }

    try:
        data = request_json("POST", SOLANA_RPC_URL, json_body=payload, timeout=20, retries=1)
        signatures = data.get("result", []) if isinstance(data, dict) else []
    except Exception:
        return {"tx_count_1h": 0, "unique_external_wallets_1h": 0}

    tx_count = 0
    wallets = set()

    for row in signatures[:15]:
        sig = row.get("signature")
        block_time = row.get("blockTime")
        if not sig:
            continue

        tx_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                sig,
                {"encoding": "json", "maxSupportedTransactionVersion": 0}
            ],
        }

        try:
            tx = request_json("POST", SOLANA_RPC_URL, json_body=tx_payload, timeout=20, retries=0)
            result = tx.get("result")
            if not result:
                continue
            tx_count += 1

            account_keys = result.get("transaction", {}).get("message", {}).get("accountKeys", [])
            for k in account_keys[:10]:
                if isinstance(k, dict):
                    pubkey = k.get("pubkey")
                else:
                    pubkey = k
                if pubkey and pubkey != token_address:
                    wallets.add(pubkey)
        except Exception:
            continue

    return {
        "tx_count_1h": tx_count,
        "unique_external_wallets_1h": len(wallets),
    }


def _etherscan_activity_proxy(chain: str, token_address: str) -> Dict[str, int]:
    if not ETHERSCAN_API_KEY:
        return {"tx_count_1h": 0, "unique_external_wallets_1h": 0, "metadata": {}}

    chainid = CHAIN_TO_ETHERSCAN_ID[chain]
    metadata = {}

    # tokeninfo may be throttled / paid-plan gated; fail soft.
    try:
        meta_resp = request_json(
            "GET",
            "https://api.etherscan.io/v2/api",
            params={
                "chainid": chainid,
                "module": "token",
                "action": "tokeninfo",
                "contractaddress": token_address,
                "apikey": ETHERSCAN_API_KEY,
            },
            timeout=20,
            retries=0,
        )
        metadata = meta_resp
    except Exception:
        metadata = {}

    try:
        tx_resp = request_json(
            "GET",
            "https://api.etherscan.io/v2/api",
            params={
                "chainid": chainid,
                "module": "account",
                "action": "tokentx",
                "contractaddress": token_address,
                "page": 1,
                "offset": 25,
                "sort": "desc",
                "apikey": ETHERSCAN_API_KEY,
            },
            timeout=20,
            retries=1,
        )
        rows = tx_resp.get("result", []) if isinstance(tx_resp, dict) else []
    except Exception:
        rows = []

    wallets = set()
    tx_count = 0

    for row in rows[:25]:
        frm = row.get("from")
        to = row.get("to")
        if frm:
            wallets.add(frm.lower())
        if to:
            wallets.add(to.lower())
        tx_count += 1

    return {
        "tx_count_1h": tx_count,
        "unique_external_wallets_1h": len(wallets),
        "metadata": metadata,
    }


def enrich_market_data(item: dict) -> dict:
    pair = item.get("raw", {}).get("pair", {})
    txns_h1 = pair.get("txns", {}).get("h1", {}) if pair else {}

    item["liquidity_usd"] = safe_float((pair.get("liquidity") or {}).get("usd"), 0.0)
    item["volume_usd_24h"] = safe_float((pair.get("volume") or {}).get("h24"), 0.0)
    item["price_usd"] = safe_float(pair.get("priceUsd"), 0.0)

    # DexScreener txns are first proxy.
    dex_tx_count_1h = safe_float(txns_h1.get("buys"), 0) + safe_float(txns_h1.get("sells"), 0)

    chain = item["chain"]
    address = item["address"]

    if chain == "solana":
        proxy = _solana_activity_proxy(address)
        item["tx_count_1h"] = max(int(dex_tx_count_1h), int(proxy["tx_count_1h"]))
        item["unique_external_wallets_1h"] = int(proxy["unique_external_wallets_1h"])
    else:
        proxy = _etherscan_activity_proxy(chain, address)
        item["tx_count_1h"] = max(int(dex_tx_count_1h), int(proxy["tx_count_1h"]))
        item["unique_external_wallets_1h"] = int(proxy["unique_external_wallets_1h"])
        item["raw"]["etherscan_metadata"] = proxy.get("metadata", {})

    # paid order / promoted metadata
    try:
        orders = orders_for_token(chain, address)
    except Exception:
        orders = []

    item["raw"]["orders"] = orders
    return item
