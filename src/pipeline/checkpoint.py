from src.utils import load_json, save_json


def get_checkpoint() -> dict:
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
        },
    )


def set_run_status(payload: dict) -> None:
    save_json("state/run_status.json", payload)
