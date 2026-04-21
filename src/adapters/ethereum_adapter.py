from __future__ import annotations


class EthereumAdapter:
    chain = "ethereum"

    def fetch_candidates_for_day(self, day: str) -> list[dict]:
        return [
            {
                "chain": "ethereum",
                "object_type": "token",
                "first_seen": f"{day}T08:00:00Z",
                "address": "0xethfake00000000000000000000000000000001",
                "deployer": "0xdeployereth0000000000000000000000000001",
                "name": "Ethereum Test Asset",
                "symbol": "ETHX",
                "decimals": 18,
            }
        ]
