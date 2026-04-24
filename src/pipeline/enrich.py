from typing import Any, Dict, List, Set

from src.clients.dexscreener import get_best_pair_for_token, orders_for_token
from src.clients.etherscan import (
    get_contract_abi,
    get_contract_creation,
    get_contract_source,
    get_token_info,
    get_token_transfers,
)
from src.config import RECOGNIZED_DEX_IDS
from src.pipeline.classify import classify_evm_contract
from src.utils import first_non_empty, safe_float, safe_int, unix_to_iso


def _extract_wallets_from_token_transfers(transfers: List[Dict[str, Any]]) -> Set[str]:
    wallets = set()

    for tx in transfers:
        frm = tx.get("from")
        to = tx.get("to")

        if frm:
            wallets.add(frm.lower())

        if to:
            wallets.add(to.lower())

    return wallets


def _is_deployer_only(transfers: List[Dict[str, Any]], creator: str | None) -> bool | None:
    if not transfers:
        return None

    if not creator:
        return None

    creator = creator.lower()
    wallets = _extract_wallets_from_token_transfers(transfers)

    # zero address should not count as a real participant
    wallets.discard("0x0000000000000000000000000000000000000000")

    if not wallets:
        return None

    return wallets == {creator}


def enrich_evm_contract(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    EVM enrichment for Ethereum/Base:
      - source metadata / verification
      - ABI-based classification
      - token info if available
      - transfer/wallet activity proxy
      - contract creation info if available
    """
    chain = item["chain"]
    address = item["address"]

    source_meta = get_contract_source(chain, address)
    abi_text = get_contract_abi(chain, address)

    token_info = get_token_info(chain, address)

    # Fill token/name metadata from explorer if available.
    item["name"] = first_non_empty(
        item.get("name"),
        token_info.get("tokenName"),
        token_info.get("name"),
        source_meta.get("ContractName"),
    )

    item["symbol"] = first_non_empty(
        item.get("symbol"),
        token_info.get("symbol"),
        token_info.get("tokenSymbol"),
    )

    item["description"] = first_non_empty(
        item.get("description"),
        token_info.get("description"),
    )

    # Classify after basic metadata fill.
    item = classify_evm_contract(item, source_meta=source_meta, abi_text=abi_text)

    # Creation info enrichment, if Etherscan gives it.
    creation_rows = get_contract_creation(chain, [address])
    if creation_rows:
        row = creation_rows[0]
        item["creator"] = first_non_empty(item.get("creator"), row.get("contractCreator"))
        item["creation_tx"] = first_non_empty(item.get("creation_tx"), row.get("txHash"))
        item["raw"]["contract_creation"] = row

    # Activity proxy: token transfers.
    transfers = get_token_transfers(chain, address, offset=100, sort="desc")

    wallets = _extract_wallets_from_token_transfers(transfers)
    wallets.discard("0x0000000000000000000000000000000000000000")

    item["activity_signals"].update(
        {
            "transfer_count": len(transfers),
            "unique_wallets": len(wallets),
            "tx_count_sample": len(transfers),
            "unique_wallets_sample": len(wallets),
            "deployer_only": _is_deployer_only(transfers, item.get("creator")),
            "activity_continues": len(transfers) >= 5 and len(wallets) >= 3,
        }
    )

    item["raw"]["etherscan_source"] = source_meta
    item["raw"]["etherscan_token_info"] = token_info
    item["raw"]["token_transfer_sample"] = transfers[:20]

    return item


def enrich_market_data(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    DexScreener market enrichment.

    Market data is no longer discovery truth. It is just a signal.
    """
    chain = item["chain"]
    address = item["address"]

    pair = get_best_pair_for_token(chain, address)

    if not pair:
        item["market_signals"].update(
            {
                "dex_listed": False,
                "dex_id": None,
                "pair_address": None,
                "liquidity_usd": 0.0,
                "volume_usd_24h": 0.0,
                "price_usd": 0.0,
                "recognized_dex": False,
            }
        )
        return item

    dex_id = (pair.get("dexId") or "").lower()
    recognized = dex_id in RECOGNIZED_DEX_IDS.get(chain, set())

    liquidity_usd = safe_float((pair.get("liquidity") or {}).get("usd"), 0.0)
    volume_usd_24h = safe_float((pair.get("volume") or {}).get("h24"), 0.0)
    price_usd = safe_float(pair.get("priceUsd"), 0.0)

    txns_h1 = pair.get("txns", {}).get("h1", {}) or {}
    dex_tx_count_1h = safe_int(txns_h1.get("buys")) + safe_int(txns_h1.get("sells"))

    item["market_signals"].update(
        {
            "dex_listed": True,
            "dex_id": dex_id,
            "pair_address": pair.get("pairAddress"),
            "liquidity_usd": liquidity_usd,
            "volume_usd_24h": volume_usd_24h,
            "price_usd": price_usd,
            "recognized_dex": recognized,
            "dex_tx_count_1h": dex_tx_count_1h,
        }
    )

    # Use DEX tx count as extra activity signal, but do not overwrite stronger explorer/RPC activity.
    item["activity_signals"]["tx_count_sample"] = max(
        safe_int(item["activity_signals"].get("tx_count_sample")),
        dex_tx_count_1h,
    )

    base_token = pair.get("baseToken") or {}
    item["name"] = first_non_empty(item.get("name"), base_token.get("name"))
    item["symbol"] = first_non_empty(item.get("symbol"), base_token.get("symbol"))

    item["raw"]["dexscreener_pair"] = pair

    try:
        item["raw"]["dexscreener_orders"] = orders_for_token(chain, address)
    except Exception:
        item["raw"]["dexscreener_orders"] = []

    return item


def enrich_candidate(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main enrichment entrypoint.

    Solana candidates are partially enriched in the adapter because Helius/RPC verification
    happens there. Here we still add market data.

    EVM candidates get source/activity enrichment here.
    """
    if item["chain"] in {"base", "ethereum"}:
        item = enrich_evm_contract(item)

    item = enrich_market_data(item)

    return item
