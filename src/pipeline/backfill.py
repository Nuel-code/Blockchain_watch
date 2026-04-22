from datetime import datetime, timedelta

from src.config import BACKFILL_END_OVERRIDE, BACKFILL_START_OVERRIDE, DEFAULT_BACKFILL_START, TODAY_UTC
from src.pipeline.checkpoint import get_checkpoint, set_checkpoint, set_run_status
from src.pipeline.daily import run_daily_for_date


def _resolve_start_end():
    start = BACKFILL_START_OVERRIDE or DEFAULT_BACKFILL_START
    end = BACKFILL_END_OVERRIDE or TODAY_UTC
    return start, end


def backfill():
    start_str, end_str = _resolve_start_end()
    checkpoint = get_checkpoint()

    if checkpoint.get("last_completed_date"):
        last_done = datetime.strptime(checkpoint["last_completed_date"], "%Y-%m-%d")
        start_dt = last_done + timedelta(days=1)
    else:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d")

    end_dt = datetime.strptime(end_str, "%Y-%m-%d")

    set_run_status(
        {
            "mode": "backfill",
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
            "status": "running",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
    )

    cursor = start_dt
    while cursor <= end_dt:
        target_date = cursor.strftime("%Y-%m-%d")
        run_daily_for_date(target_date)
        set_checkpoint(target_date, status="running")
        cursor += timedelta(days=1)

    set_checkpoint(end_dt.strftime("%Y-%m-%d"), status="complete")
    set_run_status(
        {
            "mode": "backfill",
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
            "status": "complete",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
    )


if __name__ == "__main__":
    backfill()
