from typing import Any, Dict, List

from src.utils import request_json

BASE = "https://api.dexscreener.com"


def latest_token_profiles() -> List[Dict[str, Any]]:
    data = request_json("GET", f"{BASE}/token-profiles/latest/v1")
    return data if isinstance(data, list) else []


def latest_token_boosts() -> List[Dict[str, Any]]:
    data = request_json("GET", f"{BASE}/token-boosts/latest/v1")
    return data if isinstance(data, list) else []


def top_token_boosts() -> List[Dict[str, Any]]:
    data = request_json("GET", f"{BASE}/token-boosts/top/v1")
    return data if isinstance(data, list) else []


def orders_for_token(chain_id: str, token_address: str) -> List[Dict[str, Any]]:
    data = request_json("GET", f"{BASE}/orders/v1/{chain_id}/{token_address}")
    return data if isinstance(data, list) else []


def token_pairs(chain_id: str, token_address: str) -> List[Dict[str, Any]]:
    data = request_json("GET", f"{BASE}/token-pairs/v1/{chain_id}/{token_address}")
    return data if isinstance(data, list) else []


def pair_by_pair_address(chain_id: str, pair_address: str) -> List[Dict[str, Any]]:
    data = request_json("GET", f"{BASE}/latest/dex/pairs/{chain_id}/{pair_address}")
    return data.get("pairs", []) if isinstance(data, dict) else []


def search_pairs(query: str) -> List[Dict[str, Any]]:
    data = request_json("GET", f"{BASE}/latest/dex/search", params={"q": query})
    return data.get("pairs", []) if isinstance(data, dict) else []
