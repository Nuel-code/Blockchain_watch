import json
from typing import Any, Dict, Optional

from src.config import GENERIC_BAD_NAME_TERMS
from src.utils import clean_text


ERC20_METHODS = {
    "name",
    "symbol",
    "decimals",
    "totalSupply",
    "balanceOf",
    "transfer",
    "transferFrom",
    "approve",
    "allowance",
}

ERC721_METHODS = {
    "ownerOf",
    "tokenURI",
    "safeTransferFrom",
    "setApprovalForAll",
    "isApprovedForAll",
}

ERC1155_METHODS = {
    "balanceOfBatch",
    "uri",
    "safeBatchTransferFrom",
}


def _abi_function_names(abi_text: Optional[str]) -> set:
    if not abi_text:
        return set()

    try:
        abi = json.loads(abi_text)
    except Exception:
        return set()

    names = set()
    for entry in abi:
        if isinstance(entry, dict) and entry.get("type") == "function" and entry.get("name"):
            names.add(entry["name"])

    return names


def _looks_generic_name(name: Optional[str], symbol: Optional[str]) -> bool:
    haystack = f"{name or ''} {symbol or ''}".lower()

    if not haystack.strip():
        return True

    for term in GENERIC_BAD_NAME_TERMS:
        if term in haystack:
            return True

    if len((name or "").strip()) <= 2 and len((symbol or "").strip()) <= 2:
        return True

    return False


def classify_evm_contract(item: Dict[str, Any], source_meta: Dict[str, Any], abi_text: Optional[str]) -> Dict[str, Any]:
    """
    Classify EVM objects using source metadata + ABI.
    """
    contract_signals = item["contract_signals"]

    contract_name = clean_text(source_meta.get("ContractName"))
    source_code = source_meta.get("SourceCode")
    abi_from_source = source_meta.get("ABI")
    proxy_value = str(source_meta.get("Proxy") or "").lower()
    implementation = source_meta.get("Implementation")

    abi_to_use = abi_text
    if not abi_to_use and abi_from_source and abi_from_source != "Contract source code not verified":
        abi_to_use = abi_from_source

    method_names = _abi_function_names(abi_to_use)

    is_verified = bool(source_code and str(source_code).strip())
    is_proxy = proxy_value in {"1", "true", "yes"} or bool(implementation)

    erc20 = len(ERC20_METHODS.intersection(method_names)) >= 6
    erc721 = len(ERC721_METHODS.intersection(method_names)) >= 3
    erc1155 = len(ERC1155_METHODS.intersection(method_names)) >= 2

    if erc20:
        object_type = "token"
    elif erc721:
        object_type = "nft_collection"
    elif erc1155:
        object_type = "nft_collection"
    elif is_proxy:
        object_type = "proxy_contract"
    else:
        object_type = "unknown_contract"

    item["object_type"] = object_type
    item["id"] = f"{item['chain']}:{object_type}:{item['address'].lower()}"

    contract_signals.update(
        {
            "verified_contract": is_verified,
            "contract_name": contract_name,
            "is_proxy": is_proxy,
            "implementation": implementation or None,
            "erc20": erc20,
            "erc721": erc721,
            "erc1155": erc1155,
            "has_metadata": bool(item.get("name") or item.get("symbol") or contract_name),
            "bytecode_known": bool(abi_to_use or source_code),
            "generic_name_risk": _looks_generic_name(item.get("name") or contract_name, item.get("symbol")),
        }
    )

    if not item.get("name"):
        item["name"] = contract_name

    return item


def classify_solana_object(item: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Solana MVP classification.

    Solana project objects may be token mints, NFT collections, programs, or visible DEX candidates.
    For this pipeline, candidate-first Solana objects start as token-like unless metadata says otherwise.
    """
    metadata = metadata or {}

    name = metadata.get("name") or item.get("name")
    symbol = metadata.get("symbol") or item.get("symbol")
    description = metadata.get("description") or item.get("description")

    item["object_type"] = "token"
    item["id"] = f"{item['chain']}:token:{item['address'].lower()}"

    item["name"] = name
    item["symbol"] = symbol
    item["description"] = description

    item["contract_signals"].update(
        {
            "verified_contract": False,
            "contract_name": name,
            "is_proxy": False,
            "implementation": None,
            "erc20": False,
            "erc721": False,
            "erc1155": False,
            "has_metadata": bool(name or symbol or description),
            "bytecode_known": True,
            "generic_name_risk": _looks_generic_name(name, symbol),
        }
    )

    return item
