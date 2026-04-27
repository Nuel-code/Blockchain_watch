from typing import Dict, List
from src.utils import request_json

DEFILLAMA_API = "https://api.llama.fi/protocols"


def get_protocols() -> List[Dict]:
    """
    Pull known protocols from DeFiLlama.
    Good for validating real projects.
    """
    try:
        data = request_json("GET", DEFILLAMA_API)
    except Exception:
        return []

    results = []

    for p in data:
        results.append(
            {
                "name": p.get("name"),
                "category": p.get("category"),
                "tvl": p.get("tvl"),
                "chains": p.get("chains"),
                "url": p.get("url"),
                "description": p.get("description"),
                "source": "defillama",
            }
        )

    return results
