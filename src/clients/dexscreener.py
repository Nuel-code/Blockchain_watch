from __future__ import annotations
import requests


class DexScreenerClient:
    BASE_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens/{token_address}"

    def fetch_token_pairs(self, token_address: str) -> list[dict]:
        url = self.BASE_TOKEN_URL.format(token_address=token_address)
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            data = r.json()
            return data.get("pairs", []) or []
        except Exception as e:
            print(f"[dexscreener] pair fetch failed for {token_address}: {e}")
            return []
