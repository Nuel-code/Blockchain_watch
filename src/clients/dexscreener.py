import requests


class DexClient:
    URL = "https://api.dexscreener.com/latest/dex/tokens/{token}"

    def fetch_pairs(self, token):
        try:
            r = requests.get(self.URL.format(token=token), timeout=20)
            r.raise_for_status()
            return r.json().get("pairs", [])
        except:
            return []
