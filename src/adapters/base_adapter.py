from typing import Any, Dict, List, Optional, Set

from src.clients.defillama import get_protocols
from src.clients.dexscreener import collect_visible_candidates_for_chain, search_pairs
from src.clients.etherscan import (
    etherscan_get,
    get_block_by_timestamp,
    search_contract_creations_from_known_factory,
)
from src.clients.github_search import search_recent_crypto_repos
from src.config import KNOWN_EVM_FACTORY_ADDRESSES
from src.pipeline.normalize import normalize_evm_creation, normalize_visible_token_candidate
from src.utils import date_to_unix_end, date_to_unix_start, first_non_empty


TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO_TOPIC = "0x0000000000000000000000000000000000000000000000000000000000000000"


def _get_mint_logs(chain: str, startblock: int, endblock: int, limit: int = 250) -> List[Dict[str, Any]]:
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


def _hex_or_raw_block(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("0x"):
        try:
            return int(value, 16)
        except Exception:
            return value
    return value


def _mint_log_to_discovery_row(chain: str, log: Dict[str, Any], target_date: str) -> Dict[str, Any]:
    return {
        "source": "etherscan_mint_event_scan",
        "chain": chain,
        "address": log.get("address"),
        "contract_address": log.get("address"),
        "creation_tx": log.get("transactionHash"),
        "block_number": _hex_or_raw_block(log.get("blockNumber")),
        "timestamp": None,
        "creator": None,
        "target_date": target_date,
        "raw": log,
    }


def _pair_to_visible_candidate(
    *,
    chain: str,
    pair: Dict[str, Any],
    target_date: str,
    source: str,
    discovery_bucket: str,
    description: Optional[str] = None,
    project_url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    base = pair.get("baseToken") or {}
    address = base.get("address")

    if not address:
        return None

    profile = {
        "name": base.get("name"),
        "symbol": base.get("symbol"),
        "description": description or base.get("name"),
        "url": project_url or pair.get("url"),
        "links": [],
        "pair": pair,
    }

    return {
        "source": source,
        "discovery_bucket": discovery_bucket,
        "target_date": target_date,
        "chain": chain,
        "address": address,
        "object_type_hint": "token",
        "raw": profile,
    }


def _project_seed_candidates(chain: str, target_date: str, seen: Set[str]) -> List[Dict[str, Any]]:
    """
    Project-first discovery:
      - GitHub web3 repos
      - DeFiLlama protocol names
      - resolve names to onchain token/pair candidates through DexScreener search

    This does not replace onchain discovery.
    It adds project-shaped seeds before token-noise fallback.
    """
    out: List[Dict[str, Any]] = []

    # GitHub seeds: small cap to avoid slow runs and noisy API abuse.
    for repo in search_recent_crypto_repos()[:20]:
        query = first_non_empty(repo.get("name"), repo.get("full_name"))
        if not query:
            continue

        for pair in search_pairs(query)[:10]:
            if (pair.get("chainId") or "").lower() != chain:
                continue

            candidate = _pair_to_visible_candidate(
                chain=chain,
                pair=pair,
                target_date=target_date,
                source="github_project_seed",
                discovery_bucket="github_search_resolved_to_dex_pair",
                description=repo.get("description"),
                project_url=repo.get("url"),
            )

            if not candidate:
                continue

            key = candidate["address"].lower()
            if key in seen:
                continue

            seen.add(key)
            item = normalize_visible_token_candidate(candidate, target_date)
            item["labels"].append("project_seed_github")
            item["raw"]["github_seed"] = repo
            item["raw"]["dexscreener_pair_seed"] = pair
            out.append(item)

    # DeFiLlama seeds: only protocols explicitly on Base.
    for protocol in get_protocols()[:2500]:
        chains = [str(c).lower() for c in protocol.get("chains") or []]
        if "base" not in chains:
            continue

        query = protocol.get("name")
        if not query:
            continue

        for pair in search_pairs(query)[:10]:
            if (pair.get("chainId") or "").lower() != chain:
                continue

            candidate = _pair_to_visible_candidate(
                chain=chain,
                pair=pair,
                target_date=target_date,
                source="defillama_project_seed",
                discovery_bucket="defillama_resolved_to_dex_pair",
                description=protocol.get("description") or protocol.get("category"),
                project_url=protocol.get("url"),
            )

            if not candidate:
                continue

            key = candidate["address"].lower()
            if key in seen:
                continue

            seen.add(key)
            item = normalize_visible_token_candidate(candidate, target_date)
            item["labels"].append("project_seed_defillama")
            item["raw"]["defillama_seed"] = protocol
            item["raw"]["dexscreener_pair_seed"] = pair
            out.append(item)

    return out


def discover_base_candidates(target_date: str) -> List[Dict[str, Any]]:
    chain = "base"
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    # 1. Project-first discovery.
    out.extend(_project_seed_candidates(chain, target_date, seen))

    start_ts = date_to_unix_start(target_date)
    end_ts = date_to_unix_end(target_date)

    startblock = get_block_by_timestamp(chain, start_ts, closest="after")
    endblock = get_block_by_timestamp(chain, end_ts, closest="before")

    if startblock is not None and endblock is not None:
        # 2. Onchain creation-style discovery via mint events.
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

        # 3. Optional known factory scans.
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

    # 4. DEX visible fallback, but now explicitly marked as weaker.
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
        item["labels"].append("token_surface_only")
        out.append(item)

    return out[:500]
