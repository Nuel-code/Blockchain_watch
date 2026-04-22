from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from src.clients.dexscreener import DexScreenerClient
from src.config import ChainConfig
from src.models import DiscoveryCandidate, SocialLinks
from src.utils import normalize_url, request_json, safe_float, safe_int, utc_now_iso


class BaseAdapter:
    object_type = "token"

    def __init__(self, chain_config: ChainConfig, session):
        self.chain_config = chain_config
        self.session = session
        self.dex = DexScreenerClient(session)

    def discover(self, snapshot_date: str) -> List[DiscoveryCandidate]:
        token_addresses = []
        for item in self.dex.get_latest_token_profiles() + self.dex.get_latest_boosts() + self.dex.get_top_boosts():
            if item.get("chainId") == self.chain_config.dexscreener_chain_id and item.get("tokenAddress"):
                token_addresses.append(item["tokenAddress"])

        pairs = self.dex.get_token_pairs(self.chain_config.dexscreener_chain_id, sorted(set(token_addresses))[:250])
        return self._pairs_to_candidates(pairs, snapshot_date)

    def enrich_activity(self, candidate: DiscoveryCandidate) -> DiscoveryCandidate:
        if not self.chain_config.etherscan_api_key:
            return candidate

        address = candidate.address
        url = "https://api.etherscan.io/v2/api"
        params = {
            "chainid": self.chain_config.etherscan_chain_id,
            "module": "account",
            "action": "tokentx",
            "contractaddress": address,
            "page": 1,
            "offset": 100,
            "sort": "desc",
            "apikey": self.chain_config.etherscan_api_key,
        }
        payload = request_json(self.session, "GET", url, params=params)
        result = payload.get("result", []) if isinstance(payload, dict) else []
        wallets = set()
        tx_count = 0
        deployer_like = defaultdict(int)
        for item in result[:100]:
            frm = (item.get("from") or "").lower()
            to = (item.get("to") or "").lower()
            if frm:
                wallets.add(frm)
                deployer_like[frm] += 1
            if to:
                wallets.add(to)
            tx_count += 1
        candidate.tx_count_1h = max(candidate.tx_count_1h or 0, min(tx_count, 100))
        candidate.unique_external_wallets_1h = max(candidate.unique_external_wallets_1h or 0, len(wallets))
        candidate.discovery_meta["dominant_wallet_share_proxy"] = (
            max(deployer_like.values()) / tx_count if tx_count else 1.0
        )

        info_params = {
            "chainid": self.chain_config.etherscan_chain_id,
            "module": "token",
            "action": "tokeninfo",
            "contractaddress": address,
            "apikey": self.chain_config.etherscan_api_key,
        }
        info_payload = request_json(self.session, "GET", url, params=info_params)
        info_items = info_payload.get("result", []) if isinstance(info_payload, dict) else []
        if info_items:
            info = info_items[0]
            candidate.socials.website = candidate.socials.website or normalize_url(info.get("website"))
            candidate.socials.twitter_x = candidate.socials.twitter_x or normalize_url(info.get("twitter"))
            candidate.socials.telegram = candidate.socials.telegram or normalize_url(info.get("telegram"))
            candidate.socials.discord = candidate.socials.discord or normalize_url(info.get("discord"))
            candidate.socials.github = candidate.socials.github or normalize_url(info.get("github"))
            candidate.socials.docs = candidate.socials.docs or normalize_url(info.get("whitepaper"))
        return candidate

    def _pairs_to_candidates(self, pairs: List[Dict], snapshot_date: str) -> List[DiscoveryCandidate]:
        out: List[DiscoveryCandidate] = []
        seen = set()
        now = utc_now_iso()
        for pair in pairs:
            base = pair.get("baseToken", {})
            address = base.get("address")
            if not address or address.lower() in seen:
                continue
            seen.add(address.lower())
            info = pair.get("info", {})
            links = info.get("socials", []) or []
            websites = info.get("websites", []) or []
            socials = SocialLinks(
                website=normalize_url(websites[0].get("url")) if websites else None,
                twitter_x=normalize_url(next((x.get("url") for x in links if x.get("type") in ["twitter", "x"]), None)),
                telegram=normalize_url(next((x.get("url") for x in links if x.get("type") == "telegram"), None)),
                discord=normalize_url(next((x.get("url") for x in links if x.get("type") == "discord"), None)),
                github=normalize_url(next((x.get("url") for x in links if x.get("type") == "github"), None)),
                docs=normalize_url(next((x.get("url") for x in links if x.get("type") in ["docs", "whitepaper"]), None)),
            )
            txns = pair.get("txns", {}).get("h1", {})
            candidate = DiscoveryCandidate(
                object_type=self.object_type,
                chain="base",
                address=address,
                name=base.get("name") or "Unknown",
                symbol=base.get("symbol") or "UNKNOWN",
                first_seen=(pair.get("pairCreatedAt") and now) or snapshot_date,
                snapshot_date=snapshot_date,
                pair_address=pair.get("pairAddress"),
                dex_id=pair.get("dexId"),
                price_usd=safe_float(pair.get("priceUsd"), 0.0),
                liquidity_usd=safe_float((pair.get("liquidity") or {}).get("usd"), 0.0),
                volume_usd_24h=safe_float((pair.get("volume") or {}).get("h24"), 0.0),
                tx_count_1h=safe_int(txns.get("buys"), 0) + safe_int(txns.get("sells"), 0),
                unique_external_wallets_1h=None,
                recognized_factory=pair.get("dexId"),
                socials=socials,
                source="dexscreener",
                discovery_meta={
                    "labels": pair.get("labels", []),
                    "pairCreatedAt": pair.get("pairCreatedAt"),
                    "quoteToken": pair.get("quoteToken", {}),
                    "url": pair.get("url"),
                },
            )
            out.append(candidate)
        return out
