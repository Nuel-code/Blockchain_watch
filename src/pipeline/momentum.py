from __future__ import annotations
from glob import glob
from src.utils import read_json


def compute_momentum(current_items: list) -> dict:
    """
    Returns {id: appearance_count_last_3_days}
    """

    files = sorted(
        f for f in glob("data/*.json")
        if f.endswith(".json") and "latest" not in f and "manifest" not in f and "all" not in f
    )[-3:]  # last 3 days

    counts = {}

    for path in files:
        payload = read_json(path, {})
        for item in payload.get("items", []):
            _id = item.get("id")
            if not _id:
                continue
            counts[_id] = counts.get(_id, 0) + 1

    return counts
