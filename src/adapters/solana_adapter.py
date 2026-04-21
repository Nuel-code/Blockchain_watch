from __future__ import annotations


class SolanaAdapter:
    chain = "solana"

    def fetch_candidates_for_day(self, day: str) -> list[dict]:
        return [
            {
                "chain": "solana",
                "object_type": "token",
                "first_seen": f"{day}T10:00:00Z",
                "address": "So1FakeMint111111111111111111111111111111111",
                "deployer": "So1FakeDeployer11111111111111111111111111111",
                "name": "Solana Test Asset",
                "symbol": "SOLX",
                "decimals": 9,
                "website": None,
                "raw_refs": {},
            }
        ]
