from typing import Any, Dict, List, Set

from src.clients.dexscreener import collect_visible_candidates_for_chain
from src.clients.etherscan import (
    etherscan_get,
    get_block_by_timestamp,
    search_contract_creations_from_known_factory,
)
from src.config import KNOWN_EVM_FACTORY_ADDRESSES
from src.pipeline.normalize import normalize_evm_creation, normalize_visible_token_candidate
from src.utils import date_to_unix_end, date_to_unix_start


TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO_TOPIC = "0x0000000000000000000000000000000000000000000000000000000000000000"


def _get_mint_logs(chain: str, startblock: int, endblock: int, limit: int = 250) -> List[Dict[str, Any]]:
    """
    Discover token/NFT-like contracts by Transfer events from the zero address.

    On Ethereum this can be noisy, so we cap hard and let downstream filtering score aggressively.
    """
    data = etherscan_get(
        chain,
        {
            "module": "logs",
            "action": "getLogs",
            "fromBlock": startblock,
            "toBlock": endblock,
            "topic0": TRANSFER_TOPIC,
            "topic1": ZERO_TOPIC,
            "page": 1,
            "offset": limit,
        },
        retries=1,
    )

    result = data.get("result", [])
    return result if isinstance(result, list) else []


def _mint_log_to_discovery_row(chain: str, log: Dict[str, Any], target_date: str) -> Dict[str, Any]:
    return {
        "source": "etherscan_mint_event_scan",
        "chain": chain,
        "address": log.get("address"),
        "contract_address": log.get("address"),
        "creation_tx": log.get("transactionHash"),
        "block_number": int(log.get("blockNumber", "0x0"), 16)
        if isinstance(log.get("blockNumber"), str) and log.get("blockNumber", "").startswith("0x")
        else log.get("blockNumber"),
        "timestamp": None,
        "creator": None,
        "target_date": target_date,
        "raw": log,
    }


def discover_ethereum_candidates(target_date: str) -> List[Dict[str, Any]]:
    chain = "ethereum"
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    start_ts = date_to_unix_start(target_date)
    end_ts = date_to_unix_end(target_date)

    startblock = get_block_by_timestamp(chain, start_ts, closest="after")
    endblock = get_block_by_timestamp(chain, end_ts, closest="before")

    if startblock is not None and endblock is not None:
        # 1. Mint-event discovery.
        for log in _get_mint_logs(chain, startblock, endblock, limit=300):
            address = log.get("address")
            if not address:
                continue

            key = address.lower()
            if key in seen:
                continue
            seen.add(key)

            raw = _mint_log_to_discovery_row(chain, log, target_date)
            item = normalize_evm_creation(raw, chain, target_date)
            item["object_type"] = "token"
            item["id"] = f"{chain}:token:{address.lower()}"
            item["labels"].append("mint_event_discovered")
            out.append(item)

        # 2. Optional known factory scans.
        for factory in KNOWN_EVM_FACTORY_ADDRESSES.get(chain, []):
            for raw in search_contract_creations_from_known_factory(
                chain=chain,
                factory_address=factory,
                startblock=startblock,
                endblock=endblock,
                offset=100,
            ):
                address = raw.get("contract_address") or raw.get("to")
                if not address:
                    continue

                key = address.lower()
                if key in seen:
                    continue
                seen.add(key)

                item = normalize_evm_creation(raw, chain, target_date)
                item["labels"].append("factory_discovered")
                out.append(item)

    # 3. Backup visible candidates.
    for raw in collect_visible_candidates_for_chain(chain, target_date):
        address = raw.get("address")
        if not address:
            continue

        key = address.lower()
        if key in seen:
            continue
        seen.add(key)

        item = normalize_visible_token_candidate(raw, target_date)
        item["labels"].append("visible_candidate_backup")
        out.append(item)

    return out[:500]
