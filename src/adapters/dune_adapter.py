from typing import Any, Dict, List, Set

from src.clients.dune import get_latest_query_results, has_dune_key
from src.config import DUNE_BASE_QUERY_ID
from src.models import base_candidate
from src.utils import clean_text, first_non_empty


def _normalize_dune_row(row: Dict[str, Any], snapshot_date: str) -> Dict[str, Any]:
    """
    Normalize a Dune result row into the same candidate shape used by the pipeline.

    Expected row fields from your Dune query:
      - chain
      - address
      - name
      - symbol
      - decimals
      - first_seen_at
      - first_seen_date
      - transfer_count_1d
      - wallet_touch_count_1d
      - transfer_volume_usd_1d
      - discovery_source
    """
    chain = row.get("chain")
    address = row.get("address")

    item = base_candidate(
        chain=chain,
        address=address,
        object_type="token",
        snapshot_date=snapshot_date,
        source="dune",
    )

    item["id"] = f"{chain}:token:{str(address).lower()}"
    item["name"] = clean_text(row.get("name"))
    item["symbol"] = clean_text(row.get("symbol"))
    item["description"] = clean_text(
        first_non_empty(
            row.get("description"),
            row.get("category"),
            row.get("name"),
        )
    )

    item["first_seen"] = str(first_non_empty(row.get("first_seen_date"), snapshot_date))
    item["created_at"] = str(row.get("first_seen_at")) if row.get("first_seen_at") else None

    transfer_count = int(row.get("transfer_count_1d") or row.get("transfer_count_3d") or 0)
    wallet_count = int(row.get("wallet_touch_count_1d") or row.get("wallet_touch_count_3d") or 0)
    transfer_volume = float(row.get("transfer_volume_usd_1d") or row.get("transfer_volume_usd_3d") or 0)

    item["activity_signals"].update(
        {
            "transfer_count": transfer_count,
            "unique_wallets": wallet_count,
            "tx_count_sample": transfer_count,
            "unique_wallets_sample": wallet_count,
            "deployer_only": wallet_count <= 1 if transfer_count > 0 else None,
            "activity_continues": transfer_count >= 5 and wallet_count >= 3,
        }
    )

    item["market_signals"]["volume_usd_24h"] = transfer_volume

    item["labels"].append("dune_discovered")
    item["labels"].append("fresh_first_seen_candidate")

    item["why_kept"].append("dune_first_seen_transfer_candidate")
    item["why_kept"].append(f"transfer_count={transfer_count}")
    item["why_kept"].append(f"wallet_touch_count={wallet_count}")

    item["raw"]["dune"] = row
    item["raw"]["discovery_source"] = row.get("discovery_source")

    return item


def discover_dune_candidates(snapshot_date: str) -> List[Dict[str, Any]]:
    """
    Dune-powered discovery.

    This should become the main discovery layer once query quality is proven.
    """
    if not has_dune_key() or not DUNE_BASE_QUERY_ID:
        return []

    rows = get_latest_query_results(DUNE_BASE_QUERY_ID, limit=500)

    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for row in rows:
        chain = row.get("chain")
        address = row.get("address")

        if not chain or not address:
            continue

        key = f"{chain}:{str(address).lower()}"
        if key in seen:
            continue

        seen.add(key)
        out.append(_normalize_dune_row(row, snapshot_date))

    return out
