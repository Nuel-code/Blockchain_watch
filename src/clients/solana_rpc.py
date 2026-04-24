from typing import Any, Dict, List, Optional, Set

from src.config import SOLANA_RPC_URL
from src.utils import request_json


def solana_rpc(method: str, params: Optional[list] = None, retries: int = 1) -> Dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }

    try:
        data = request_json(
            "POST",
            SOLANA_RPC_URL,
            json_body=payload,
            timeout=25,
            retries=retries,
            sleep_seconds=1.0,
        )
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_account_info(address: str) -> Dict[str, Any]:
    data = solana_rpc(
        "getAccountInfo",
        [
            address,
            {
                "encoding": "jsonParsed",
                "commitment": "confirmed",
            },
        ],
    )
    return data.get("result", {}) if isinstance(data, dict) else {}


def get_signatures_for_address(address: str, limit: int = 25) -> List[Dict[str, Any]]:
    data = solana_rpc(
        "getSignaturesForAddress",
        [
            address,
            {
                "limit": limit,
            },
        ],
    )
    result = data.get("result", [])
    return result if isinstance(result, list) else []


def get_transaction(signature: str) -> Dict[str, Any]:
    data = solana_rpc(
        "getTransaction",
        [
            signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0,
                "commitment": "confirmed",
            },
        ],
        retries=0,
    )
    return data.get("result", {}) if isinstance(data, dict) else {}


def verify_account_exists(address: str) -> bool:
    info = get_account_info(address)
    return bool(info.get("value"))


def estimate_recent_activity(address: str, limit: int = 20) -> Dict[str, Any]:
    """
    Lightweight activity proxy for a known Solana account/mint.

    This is not a full historical indexer.
    It verifies recent activity around a candidate.
    """
    signatures = get_signatures_for_address(address, limit=limit)

    unique_wallets: Set[str] = set()
    tx_count = 0
    first_signature = None
    latest_signature = None
    first_block_time = None
    latest_block_time = None

    for idx, row in enumerate(signatures):
        sig = row.get("signature")
        if not sig:
            continue

        if idx == 0:
            latest_signature = sig
            latest_block_time = row.get("blockTime")

        first_signature = sig
        first_block_time = row.get("blockTime")

        tx = get_transaction(sig)
        if not tx:
            continue

        tx_count += 1

        message = tx.get("transaction", {}).get("message", {})
        account_keys = message.get("accountKeys", [])

        for k in account_keys[:20]:
            if isinstance(k, dict):
                pubkey = k.get("pubkey")
            else:
                pubkey = k

            if pubkey and pubkey != address:
                unique_wallets.add(pubkey)

    return {
        "tx_count_sample": tx_count,
        "unique_wallets_sample": len(unique_wallets),
        "latest_signature": latest_signature,
        "first_signature_sample": first_signature,
        "latest_block_time": latest_block_time,
        "first_block_time_sample": first_block_time,
      }
