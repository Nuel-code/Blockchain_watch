from __future__ import annotations


class BaseAdapter:
    chain = "base"

    def fetch_candidates_for_day(self, day: str) -> list[dict]:
        return [
            {
                "chain": "base",
                "object_type": "token",
                "first_seen": f"{day}T09:00:00Z",
                "address": "0xbasefake00000000000000000000000000000001",
                "deployer": "0xdeployerbase000000000000000000000000001",
                "name": "Base Test Asset",
                "symbol": "BASX",
                "decimals": 18,
            }
        ]
