from typing import Any, Dict, List

from src.config import DUNE_API_KEY
from src.utils import request_json


DUNE_API_BASE = "https://api.dune.com/api/v1"


def has_dune_key() -> bool:
    return bool(DUNE_API_KEY)


def dune_headers() -> Dict[str, str]:
    return {
        "X-Dune-API-Key": DUNE_API_KEY,
        "Content-Type": "application/json",
    }


def get_latest_query_results(query_id: str | int, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Fetch the latest saved result rows for a Dune query.

    This does not execute a fresh query.
    It pulls the latest completed result from Dune.
    Good for GitHub Actions because it is fast.
    """
    if not DUNE_API_KEY:
        return []

    try:
        data = request_json(
            "GET",
            f"{DUNE_API_BASE}/query/{query_id}/results",
            params={"limit": limit},
            headers=dune_headers(),
            timeout=30,
            retries=1,
            sleep_seconds=1.0,
        )
    except Exception:
        return []

    result = data.get("result", {}) if isinstance(data, dict) else {}
    rows = result.get("rows", []) if isinstance(result, dict) else []

    return rows if isinstance(rows, list) else []
