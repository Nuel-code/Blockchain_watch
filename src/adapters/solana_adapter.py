import requests


class SolanaAdapter:
    URL = "https://api.dexscreener.com/token-profiles/latest/v1"

    def fetch_candidates_for_day(self, day):
        data = requests.get(self.URL).json()

        return [
            {
                "chain": "solana",
                "object_type": "token",
                "first_seen": f"{day}T12:00:00Z",
                "address": x["tokenAddress"],
                "name": x.get("header"),
                "website": next((l["url"] for l in x.get("links", []) if l.get("type") == "website"), None),
                "raw_refs": {"links": x.get("links", [])},
            }
            for x in data if x["chainId"] == "solana"
        ][:100]
