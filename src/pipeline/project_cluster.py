from typing import Any, Dict, List, Set

from src.clients.etherscan import get_normal_txs_by_address
from src.utils import safe_int, unix_to_iso


UTILITY_HINTS = {
    "stake",
    "staking",
    "vest",
    "vesting",
    "claim",
    "airdrop",
    "vault",
    "treasury",
    "factory",
    "router",
    "pool",
    "pair",
    "market",
    "launch",
    "reward",
    "governance",
    "dao",
    "escrow",
    "lock",
    "locker",
}


def empty_cluster_signals() -> Dict[str, Any]:
    return {
        "cluster_size": 1,
        "same_creator_nearby_contracts": 0,
        "creator_tx_sample_size": 0,
        "creator_spammy": False,
        "has_project_cluster": False,
        "has_utility_contract_hint": False,
        "has_proxy_or_implementation_pattern": False,
        "cluster_score": 0.0,
        "related_contracts": [],
    }


def _looks_like_utility_contract(row: Dict[str, Any]) -> bool:
    text = " ".join(
        str(row.get(k) or "").lower()
        for k in [
            "functionName",
            "methodId",
            "input",
            "contractAddress",
            "to",
        ]
    )

    return any(hint in text for hint in UTILITY_HINTS)


def _extract_created_contract(row: Dict[str, Any]) -> str | None:
    """
    Etherscan txlist rows expose contractAddress when a tx creates a contract.
    """
    address = row.get("contractAddress")
    if address:
        return address

    return None


def analyze_evm_deployment_cluster(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deployment cluster heuristic for Base/Ethereum.

    The question:
      did the creator deploy other nearby contracts that make this look like a project system,
      not one lonely contract?

    This is a lightweight sample, not a full graph indexer.
    """
    if item.get("chain") not in {"base", "ethereum"}:
        item["cluster_signals"] = empty_cluster_signals()
        return item

    creator = item.get("creator")
    created_block = safe_int(item.get("created_block"), 0)

    cluster = empty_cluster_signals()

    if not creator:
        item["cluster_signals"] = cluster
        item["why_flagged"].append("cluster_unavailable_missing_creator")
        return item

    startblock = max(created_block - 50_000, 0) if created_block else 0
    endblock = created_block + 50_000 if created_block else 99999999

    txs = get_normal_txs_by_address(
        chain=item["chain"],
        address=creator,
        startblock=startblock,
        endblock=endblock,
        page=1,
        offset=100,
        sort="asc",
    )

    created_contracts = []
    utility_hint_count = 0

    for tx in txs:
        contract_address = _extract_created_contract(tx)
        if not contract_address:
            continue

        if contract_address.lower() == item["address"].lower():
            continue

        if _looks_like_utility_contract(tx):
            utility_hint_count += 1

        created_contracts.append(
            {
                "address": contract_address,
                "tx_hash": tx.get("hash"),
                "block_number": tx.get("blockNumber"),
                "created_at": unix_to_iso(tx.get("timeStamp")),
                "function_name": tx.get("functionName"),
                "utility_hint": _looks_like_utility_contract(tx),
            }
        )

    same_creator_nearby = len(created_contracts)
    creator_spammy = same_creator_nearby >= 30 or len(txs) >= 100

    cluster_size = 1 + same_creator_nearby
    has_project_cluster = 2 <= cluster_size <= 15
    has_utility_contract_hint = utility_hint_count > 0

    score = 0.0

    if has_project_cluster:
        score += 0.45

    if same_creator_nearby >= 2:
        score += 0.20

    if has_utility_contract_hint:
        score += 0.20

    if item.get("contract_signals", {}).get("is_proxy"):
        score += 0.10

    if creator_spammy:
        score -= 0.35

    score = max(0.0, min(1.0, score))

    cluster.update(
        {
            "cluster_size": cluster_size,
            "same_creator_nearby_contracts": same_creator_nearby,
            "creator_tx_sample_size": len(txs),
            "creator_spammy": creator_spammy,
            "has_project_cluster": has_project_cluster,
            "has_utility_contract_hint": has_utility_contract_hint,
            "has_proxy_or_implementation_pattern": bool(
                item.get("contract_signals", {}).get("is_proxy")
                or item.get("contract_signals", {}).get("implementation")
            ),
            "cluster_score": round(score, 4),
            "related_contracts": created_contracts[:15],
        }
    )

    item["cluster_signals"] = cluster

    if has_project_cluster:
        item["labels"].append("deployment_cluster")
        item["why_kept"].append(f"deployment_cluster_size={cluster_size}")
    else:
        item["why_flagged"].append("no_deployment_cluster_detected")

    if has_utility_contract_hint:
        item["labels"].append("utility_contract_cluster_hint")
        item["why_kept"].append("utility_contract_hint_detected")

    if creator_spammy:
        item["labels"].append("creator_spammy")
        item["why_flagged"].append("creator_deployed_many_contracts_nearby")

    return item


def analyze_solana_cluster(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Solana placeholder cluster heuristic.

    For now, Solana gets weak clustering because proper clustering needs:
      - update authority
      - mint authority
      - related pool creation
      - creator wallet history
      - Helius parsed links

    We don't fake confidence here.
    """
    cluster = empty_cluster_signals()

    raw = item.get("raw", {})
    activity = item.get("activity_signals", {})

    if raw.get("helius_asset"):
        cluster["cluster_score"] += 0.15

    if activity.get("unique_wallets_sample", 0) >= 10:
        cluster["cluster_score"] += 0.10

    cluster["cluster_score"] = round(min(1.0, cluster["cluster_score"]), 4)
    item["cluster_signals"] = cluster

    return item


def apply_project_cluster(item: Dict[str, Any]) -> Dict[str, Any]:
    if item.get("chain") in {"base", "ethereum"}:
        return analyze_evm_deployment_cluster(item)

    if item.get("chain") == "solana":
        return analyze_solana_cluster(item)

    item["cluster_signals"] = empty_cluster_signals()
    return item
