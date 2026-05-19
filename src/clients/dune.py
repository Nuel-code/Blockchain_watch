import time
from typing import Any, Dict, List, Optional

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


def execute_query(query_id: str | int) -> Optional[str]:
    if not DUNE_API_KEY:
        print({"dune_error": "missing_dune_api_key"})
        return None

    url = f"{DUNE_API_BASE}/query/{query_id}/execute"

    print(
        {
            "dune_execute_url": url,
            "dune_query_id": str(query_id),
            "dune_key_present": bool(DUNE_API_KEY),
        }
    )

    try:
        data = request_json(
            "POST",
            url,
            headers=dune_headers(),
            json_body={},
            timeout=30,
            retries=1,
            sleep_seconds=1.0,
        )
    except Exception as exc:
        print(
            {
                "dune_execute_exception": type(exc).__name__,
                "message": str(exc)[:500],
            }
        )
        return None

    execution_id = data.get("execution_id") if isinstance(data, dict) else None

    print(
        {
            "dune_execute_response_keys": list(data.keys()) if isinstance(data, dict) else None,
            "dune_execution_id": execution_id,
        }
    )

    return execution_id


def get_execution_status(execution_id: str) -> Dict[str, Any]:
    url = f"{DUNE_API_BASE}/execution/{execution_id}/status"

    try:
        data = request_json(
            "GET",
            url,
            headers=dune_headers(),
            timeout=30,
            retries=1,
            sleep_seconds=1.0,
        )
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(
            {
                "dune_status_exception": type(exc).__name__,
                "message": str(exc)[:500],
            }
        )
        return {}


def get_execution_results(execution_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    url = f"{DUNE_API_BASE}/execution/{execution_id}/results"

    print(
        {
            "dune_results_url": url,
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
                "dune_results_exception": type(exc).__name__,
                "message": str(exc)[:500],
            }
        )
        return []

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


def execute_and_wait_for_results(
    query_id: str | int,
    limit: int = 500,
    max_wait_seconds: int = 90,
    poll_seconds: int = 5,
) -> List[Dict[str, Any]]:
    execution_id = execute_query(query_id)

    if not execution_id:
        return []

    started = time.time()

    while time.time() - started < max_wait_seconds:
        status = get_execution_status(execution_id)

        state = status.get("state")
        print(
            {
                "dune_execution_id": execution_id,
                "dune_state": state,
            }
        )

        if state == "QUERY_STATE_COMPLETED":
            return get_execution_results(execution_id, limit=limit)

        if state in {"QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED", "QUERY_STATE_CANCELED"}:
            print({"dune_terminal_status": status})
            return []

        time.sleep(poll_seconds)

    print(
        {
            "dune_timeout": True,
            "execution_id": execution_id,
            "waited_seconds": max_wait_seconds,
        }
    )

    return []


def get_latest_query_results(query_id: str | int, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Main entrypoint used by the adapter.

    It executes the saved query and fetches the result rows.
    This is slower than latest-result fetch, but avoids:
      'No execution found for the latest version of the given query'
    """
    return execute_and_wait_for_results(
        query_id=query_id,
        limit=limit,
        max_wait_seconds=90,
        poll_seconds=5,
    )
