from typing import Any, Dict, List

from src.config import DUNE_API_KEY
from src.utils import request_json


DUNE_API_BASE = "https://api.dune.com/api/v1"


def has_dune_key() -> bool:
    present = bool(DUNE_API_KEY)
    print({"dune_key_present": present})
    return present


def dune_headers() -> Dict[str, str]:
    return {
        "X-Dune-API-Key": DUNE_API_KEY,
        "Content-Type": "application/json",
    }


def get_latest_query_results(query_id: str | int, limit: int = 500) -> List[Dict[str, Any]]:
    if not DUNE_API_KEY:
        print({"dune_error": "missing_dune_api_key"})
        return []

    url = f"{DUNE_API_BASE}/query/{query_id}/results"

    print(
        {
            "dune_fetch_url": url,
            "dune_query_id": str(query_id),
            "dune_key_present": bool(DUNE_API_KEY),
            "limit": limit,
        }
    )

    try:
        data = request_json(
            "GET",
            url,
            params={"limit": limit},
            headers=dune_headers(),
            timeout=30,
            retries=1,
            sleep_seconds=1.0,
        )
    except Exception as exc:
        print(
            {
                "dune_fetch_exception": type(exc).__name__,
                "message": str(exc)[:500],
            }
        )
        return []

    print(
        {
            "dune_response_type": type(data).__name__,
            "dune_response_top_keys": list(data.keys()) if isinstance(data, dict) else None,
        }
    )

    if isinstance(data, dict):
        if "error" in data:
            print({"dune_api_error": data.get("error")})

        if "message" in data:
            print({"dune_api_message": data.get("message")})

    result = data.get("result", {}) if isinstance(data, dict) else {}
    rows = result.get("rows", []) if isinstance(result, dict) else []

    print(
        {
            "dune_result_keys": list(result.keys()) if isinstance(result, dict) else None,
            "dune_rows_returned": len(rows) if isinstance(rows, list) else "not_list",
        }
    )

    if isinstance(rows, list) and rows:
        print({"dune_first_row_keys": list(rows[0].keys())})

    return rows if isinstance(rows, list) else []
