from __future__ import annotations
import requests


class SolanaAdapter:
    chain = "solana"
    URL = "https://api.dexscreener.com/token-profiles/latest/v1"

    def fetch_candidates_for_day(self, day: str) -> list[dict]:
        try:
            r = requests.get(self.URL, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[solana] fetch failed: {e}")
            return []

        results = []
        for item in data:
            if item.get("chainId") != "solana":
                continue

            token_address = item.get("tokenAddress")
            if not token_address:
                continue

            results.append(
                {
                    "chain": "solana",
                    "object_type": "token",
                    "first_seen": f"{day}T12:00:00Z",
                    "address": token_address,
                    "deployer": None,
                    "name": item.get("header") or item.get("description") or "Unknown",
                    "symbol": None,
                    "decimals": None,
                    "website": self._extract_website(item),
                    "raw_refs": {
                        "icon": item.get("icon"),
                        "header": item.get("header"),
                        "description": item.get("description"),
                        "links": item.get("links", []),
                    },
                }
            )

        return results[:100]

    def _extract_website(self, item: dict) -> str | None:
        for link in item.get("links", []):
            if link.get("type") == "website" and link.get("url"):
                return link["url"]
        return None
