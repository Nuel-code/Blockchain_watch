from typing import Dict, List

from src.pipeline.aggregate import summarize_actions
from src.utils import append_unique, load_json, save_json


def _ensure_dict(value):
    return value if isinstance(value, dict) else {}


def _ensure_list(value):
    return value if isinstance(value, list) else []


def store_snapshot(snapshot_date: str, items: List[Dict]) -> None:
    """
    Storage rules:
      - data/YYYY-MM-DD.json is the daily partition
      - latest.json always points to the most recent run output
      - manifest.json tracks counts/actions per date
      - all.json keeps unique candidates globally by id
    """
    day_path = f"data/{snapshot_date}.json"
    save_json(day_path, items)

    save_json("data/latest.json", items)

    manifest = _ensure_dict(load_json("data/manifest.json", {}))

    manifest[snapshot_date] = {
        "count": len(items),
        "actions": summarize_actions(items),
        "top_ids": [item.get("id") for item in items[:25]],
    }

    save_json("data/manifest.json", manifest)

    all_rows = _ensure_list(load_json("data/all.json", []))
    all_rows = append_unique(all_rows, items, key="id")
    save_json("data/all.json", all_rows)


def update_seen_ids(items: List[Dict]) -> None:
    seen_ids_raw = load_json("state/seen_ids.json", [])
    seen_ids = set(seen_ids_raw if isinstance(seen_ids_raw, list) else [])

    for item in items:
        if item.get("id"):
            seen_ids.add(item["id"])

    save_json("state/seen_ids.json", sorted(seen_ids))
