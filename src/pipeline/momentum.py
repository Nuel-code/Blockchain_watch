from src.utils import load_json, previous_n_dates


def apply_momentum(item: dict, snapshot_date: str) -> dict:
    prev_dates = previous_n_dates(snapshot_date, 2)
    appearances = 1  # include today

    for d in prev_dates:
        rows = load_json(f"data/{d}.json", [])
        ids = {row.get("id") for row in rows}
        if item["id"] in ids:
            appearances += 1

    momentum_score = appearances / 3.0
    item["signals"]["momentum_score"] = round(momentum_score, 4)

    if appearances >= 2:
        item["labels"].append("sticky_3d")

    return item
