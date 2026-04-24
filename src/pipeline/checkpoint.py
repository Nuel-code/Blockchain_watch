from datetime import datetime
from typing import Dict

from src.utils import load_json, save_json


def get_checkpoint() -> Dict:
    return load_json(
        "state/backfill_checkpoint.json",
        {
            "last_completed_date": None,
            "status": "idle",
        },
    )


def set_checkpoint(last_completed_date: str, status: str = "running") -> None:
    save_json(
        "state/backfill_checkpoint.json",
        {
            "last_completed_date": last_completed_date,
            "status": status,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        },
    )


def set_run_status(payload: Dict) -> None:
    payload = {
        **payload,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    save_json("state/run_status.json", payload)
