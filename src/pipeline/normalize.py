from __future__ import annotations
from src.models import Candidate
from src.utils import candidate_id


def normalize(raw: dict, snapshot_date: str) -> Candidate:
    chain = raw["chain"]
    object_type = raw.get("object_type", "token")
    address = raw["address"]

    return Candidate(
        id=candidate_id(chain, object_type, address),
        chain=chain,
        first_seen=raw.get("first_seen", f"{snapshot_date}T00:00:00Z"),
        snapshot_date=snapshot_date,
        object_type=object_type,
        address=address,
        deployer=raw.get("deployer"),
        name=raw.get("name"),
        symbol=raw.get("symbol"),
        decimals=raw.get("decimals"),
        website=raw.get("website"),
        raw_refs=raw.get("raw_refs", {}),
    )
