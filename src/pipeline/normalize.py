from typing import Any, Dict

from src.models import base_candidate
from src.utils import clean_text, first_non_empty, unix_to_iso


def normalize_evm_creation(raw: Dict[str, Any], chain: str, snapshot_date: str) -> Dict[str, Any]:
    """
    Normalize an EVM creation-like row into the shared candidate schema.

    Works with:
    - factory scan rows
    - direct contract creation rows
    - future explorer/indexer rows
    """
    address = first_non_empty(
        raw.get("contract_address"),
        raw.get("contractAddress"),
        raw.get("address"),
        raw.get("to"),
    )

    item = base_candidate(
        chain=chain,
        address=address,
        object_type="unknown_contract",
        snapshot_date=snapshot_date,
        source=raw.get("source") or "evm_creation",
    )

    item["creator"] = first_non_empty(raw.get("creator"), raw.get("from"))
    item["creation_tx"] = first_non_empty(raw.get("creation_tx"), raw.get("hash"))
    item["created_block"] = first_non_empty(raw.get("block_number"), raw.get("blockNumber"))
    item["created_at"] = unix_to_iso(first_non_empty(raw.get("timestamp"), raw.get("timeStamp")))
    item["raw"]["discovery"] = raw

    return item


def normalize_visible_token_candidate(raw: Dict[str, Any], snapshot_date: str) -> Dict[str, Any]:
    """
    Normalize DexScreener visible candidates.

    Used especially for Solana, and as backup candidates for EVM.
    """
    chain = raw["chain"]
    address = raw["address"]

    item = base_candidate(
        chain=chain,
        address=address,
        object_type=raw.get("object_type_hint") or "token",
        snapshot_date=snapshot_date,
        source=raw.get("source") or "visible_candidate",
    )

    profile = raw.get("raw", {}) or {}

    item["name"] = clean_text(first_non_empty(profile.get("description"), profile.get("name")))
    item["symbol"] = clean_text(profile.get("symbol"))
    item["description"] = clean_text(profile.get("description"))
    item["raw"]["profile"] = profile
    item["raw"]["discovery_bucket"] = raw.get("discovery_bucket")

    return item
