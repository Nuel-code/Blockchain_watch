from typing import Any, Dict, List, Optional, Set

from src.config import HELIUS_API_KEY
from src.utils import request_json


def has_helius_key() -> bool:
    return bool(HELIUS_API_KEY)


def _helius_rpc_url() -> Optional[str]:
    if not HELIUS_API_KEY:
        return None
    return f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"


def helius_rpc(method: str, params: Optional[list] = None, retries: int = 1) -> Dict[str, Any]:
    url = _helius_rpc_url()
    if not url:
        return {}

    payload = {
        "jsonrpc": "2.0",
        "id": "blockchain-watch",
        "method": method,
        "params": params or [],
    }

    try:
        data = request_json(
            "POST",
            url,
            json_body=payload,
            timeout=30,
            retries=retries,
            sleep_seconds=1.0,
        )
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_asset(asset_id: str) -> Dict[str, Any]:
    """
    DAS getAsset-style lookup.

    Useful for token/NFT metadata when available.
    """
    if not HELIUS_API_KEY:
        return {}

    data = helius_rpc(
        "getAsset",
        {
            "id": asset_id,
        },
    )

    result = data.get("result", {})
    return result if isinstance(result, dict) else {}


def get_signatures_for_address(address: str, limit: int = 25) -> List[Dict[str, Any]]:
    data = helius_rpc(
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


def get_parsed_transactions(signatures: List[str]) -> List[Dict[str, Any]]:
    """
    Enhanced transaction API endpoint.

    If unavailable or rate-limited, caller should fall back to Solana RPC.
    """
    if not HELIUS_API_KEY or not signatures:
        return []

    url = f"https://api.helius.xyz/v0/transactions/?api-key={HELIUS_API_KEY}"

    try:
        data = request_json(
            "POST",
            url,
            json_body={"transactions": signatures[:100]},
            timeout=30,
            retries=1,
            sleep_seconds=1.0,
        )
        return data if isinstance(data, list) else []
    except Exception:
        return []


def estimate_activity_with_helius(address: str, limit: int = 25) -> Dict[str, Any]:
    signatures = get_signatures_for_address(address, limit=limit)
    sig_values = [x.get("signature") for x in signatures if x.get("signature")]

    parsed = get_parsed_transactions(sig_values[:20])

    unique_wallets: Set[str] = set()
    tx_types: Set[str] = set()

    for tx in parsed:
        tx_type = tx.get("type")
        if tx_type:
            tx_types.add(tx_type)

        fee_payer = tx.get("feePayer")
        if fee_payer:
            unique_wallets.add(fee_payer)

        for transfer in tx.get("tokenTransfers", []) or []:
            src = transfer.get("fromUserAccount")
            dst = transfer.get("toUserAccount")
            if src:
                unique_wallets.add(src)
            if dst:
                unique_wallets.add(dst)

        for transfer in tx.get("nativeTransfers", []) or []:
            src = transfer.get("fromUserAccount")
            dst = transfer.get("toUserAccount")
            if src:
                unique_wallets.add(src)
            if dst:
                unique_wallets.add(dst)

    return {
        "tx_count_sample": len(parsed) if parsed else len(sig_values),
        "unique_wallets_sample": len(unique_wallets),
        "tx_types_sample": sorted(tx_types),
        "latest_signature": sig_values[0] if sig_values else None,
        "first_signature_sample": sig_values[-1] if sig_values else None,
        "used_helius": True,
    }


def extract_asset_metadata(asset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Helius DAS asset response into basic metadata/social-ish fields.
    """
    content = asset.get("content", {}) if isinstance(asset, dict) else {}
    metadata = content.get("metadata", {}) if isinstance(content, dict) else {}
    links = content.get("links", {}) if isinstance(content, dict) else {}

    return {
        "name": metadata.get("name"),
        "symbol": metadata.get("symbol"),
        "description": metadata.get("description"),
        "image": links.get("image"),
        "external_url": links.get("external_url"),
        "raw": asset,
    }
