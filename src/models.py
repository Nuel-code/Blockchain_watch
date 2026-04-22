from typing import Dict, Any


def make_id(chain: str, object_type: str, address: str) -> str:
    return f"{chain}:{object_type}:{(address or '').lower()}"


def empty_socials() -> Dict[str, Any]:
    return {
        "website": None,
        "twitter_x": None,
        "telegram": None,
        "discord": None,
        "github": None,
        "docs": None,
    }
