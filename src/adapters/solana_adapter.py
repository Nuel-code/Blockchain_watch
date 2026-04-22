from __future__ import annotations

from typing import Dict, List

from src.clients.dexscreener import DexScreenerClient
from src.config import ChainConfig
from src.models import DiscoveryCandidate, SocialLinks
from src.utils import normalize_url, request_json, safe_float, safe_int, utc_now_iso


class SolanaAdapter:
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
        rpc_url = self.chain_config.solana_rpc_url
        if not rpc_url:
            return candidate

        signatures_payload = request_json(
            self.session,
            "POST",
            rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [candidate.address, {"limit": 50}],
            },
        )
        signatures = ((signatures_payload or {}).get("result") or [])[:50]
        wallets = set()
        tx_count = len(signatures)
        for item in signatures[:25]:
            sig = item.get("signature")
            if not sig:
                continue
            tx_payload = request_json(
                self.session,
                "POST",
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
                },
            )
            tx = (tx_payload or {}).get("result") or {}
            account_keys = (((tx.get("transaction") or {}).get("message") or {}).get("accountKeys") or [])
            for key in account_keys:
                if isinstance(key, dict):
                    pubkey = key.get("pubkey")
                else:
                    pubkey = key
                if pubkey and pubkey != candidate.address:
                    wallets.add(pubkey)
        candidate.tx_count_1h = max(candidate.tx_count_1h or 0, tx_count)
        candidate.unique_external_wallets_1h = max(candidate.unique_external_wallets_1h or 0, len(wallets))
        candidate.discovery_meta["activity_source"] = "solana_rpc_signature_proxy"
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
            txns = pair.get("txns", {}).get("h1", {})
            candidate = DiscoveryCandidate(
                object_type=self.object_type,
                chain="solana",
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
                socials=SocialLinks(
                    website=normalize_url(websites[0].get("url")) if websites else None,
                    twitter_x=normalize_url(next((x.get("url") for x in links if x.get("type") in ["twitter", "x"]), None)),
                    telegram=normalize_url(next((x.get("url") for x in links if x.get("type") == "telegram"), None)),
                    discord=normalize_url(next((x.get("url") for x in links if x.get("type") == "discord"), None)),
                    github=normalize_url(next((x.get("url") for x in links if x.get("type") == "github"), None)),
                    docs=normalize_url(next((x.get("url") for x in links if x.get("type") in ["docs", "whitepaper"]), None)),
                ),
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
