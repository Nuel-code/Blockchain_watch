from typing import List

from src.utils import append_unique, load_json, save_json


def store_snapshot(snapshot_date: str, items: List[dict]) -> None:
    day_path = f"data/{snapshot_date}.json"
    save_json(day_path, items)

    save_json("data/latest.json", items)

    manifest = load_json("data/manifest.json", {})
    manifest[snapshot_date] = {
        "count": len(items),
        "top_ids": [x.get("id") for x in items[:20]],
    }
    save_json("data/manifest.json", manifest)

    all_rows = load_json("data/all.json", [])
    all_rows = append_unique(all_rows, items, key="id")
    save_json("data/all.json", all_rows)


def update_seen_ids(items: List[dict]) -> None:
    seen_ids = set(load_json("state/seen_ids.json", []))
    for item in items:
        seen_ids.add(item["id"])
    save_json("state/seen_ids.json", sorted(seen_ids))
