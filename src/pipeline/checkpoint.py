from __future__ import annotations
from datetime import datetime, timedelta, timezone
from src.utils import read_json, write_json

CP_PATH = "state/backfill_checkpoint.json"


def load_or_init(start_date: str, end_date: str) -> dict:
    cp = read_json(CP_PATH, {})
    if cp and cp.get("next_day"):
        return cp

    cp = {
        "mode": "backfill",
        "start_date": start_date,
        "end_date": end_date,
        "last_completed_day": None,
        "next_day": start_date,
        "status": "running",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
    }
    write_json(CP_PATH, cp)
    return cp


def mark_day_complete(day: str) -> dict:
    cp = read_json(CP_PATH, {})
    next_day = (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()
    cp["last_completed_day"] = day
    cp["next_day"] = next_day
    cp["status"] = "running"
    cp["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(CP_PATH, cp)
    return cp
