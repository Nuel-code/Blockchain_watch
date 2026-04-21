from __future__ import annotations
from datetime import datetime, timezone
from src.models import Candidate
from src.utils import write_json, atomic_replace, read_json


def write_day(day: str, items: list[Candidate], meta: dict) -> None:
    path = f"data/{day}.json"
    tmp = f"{path}.tmp"
    payload = {
        "meta": meta,
        "items": [item.model_dump() for item in items],
    }
    write_json(tmp, payload)
    atomic_replace(tmp, path)


def update_latest(day: str, items: list[Candidate], meta: dict) -> None:
    payload = {
        "meta": meta | {"latest_day": day},
        "items": [item.model_dump() for item in items],
    }
    write_json("data/latest.json", payload)


def update_manifest(day: str, meta: dict) -> None:
    manifest = read_json("data/manifest.json", {"days": [], "updated_at": None})
    manifest["days"] = [d for d in manifest["days"] if d["date"] != day]
    manifest["days"].append(
        {
            "date": day,
            "stored_count": meta.get("stored_count", 0),
            "chains": meta.get("chains", []),
        }
    )
    manifest["days"] = sorted(manifest["days"], key=lambda x: x["date"])
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json("data/manifest.json", manifest)
