from src.utils import load_json, previous_n_dates


def apply_momentum(item: dict, snapshot_date: str) -> dict:
    """
    3-day momentum:
      appearances / 3

    Includes today as one appearance because the item is currently present.
    """
    appearances = 1

    for date_str in previous_n_dates(snapshot_date, 2):
        rows = load_json(f"data/{date_str}.json", [])
        ids = {row.get("id") for row in rows if isinstance(row, dict)}

        if item.get("id") in ids:
            appearances += 1

    momentum_score = appearances / 3.0
    item["scores"]["momentum_score"] = round(momentum_score, 4)

    if appearances == 2:
        item["labels"].append("appeared_2_of_3_days")
        item["why_kept"].append("appeared_2_of_3_days")

    if appearances == 3:
        item["labels"].append("appeared_3_of_3_days")
        item["why_kept"].append("appeared_3_of_3_days")

    return item
