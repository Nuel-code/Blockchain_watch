from datetime import datetime, timedelta

from src.config import (
    BACKFILL_END_OVERRIDE,
    BACKFILL_START_OVERRIDE,
    DEFAULT_BACKFILL_START,
    TODAY_UTC,
)
from src.pipeline.aggregate import summarize_actions
from src.pipeline.checkpoint import get_checkpoint, set_checkpoint, set_run_status
from src.pipeline.daily import run_daily_for_date


def _resolve_start_end():
    start = BACKFILL_START_OVERRIDE or DEFAULT_BACKFILL_START
    end = BACKFILL_END_OVERRIDE or TODAY_UTC
    return start, end


def backfill() -> None:
    requested_start, requested_end = _resolve_start_end()

    checkpoint = get_checkpoint()
    checkpoint_date = checkpoint.get("last_completed_date")

    if checkpoint_date:
        start_dt = datetime.strptime(checkpoint_date, "%Y-%m-%d") + timedelta(days=1)
    else:
        start_dt = datetime.strptime(requested_start, "%Y-%m-%d")

    end_dt = datetime.strptime(requested_end, "%Y-%m-%d")

    if start_dt > end_dt:
        set_run_status(
            {
                "mode": "backfill",
                "status": "nothing_to_do",
                "requested_start": requested_start,
                "requested_end": requested_end,
                "effective_start": start_dt.strftime("%Y-%m-%d"),
                "effective_end": end_dt.strftime("%Y-%m-%d"),
            }
        )
        print("Nothing to backfill.")
        return

    set_run_status(
        {
            "mode": "backfill",
            "status": "running",
            "requested_start": requested_start,
            "requested_end": requested_end,
            "effective_start": start_dt.strftime("%Y-%m-%d"),
            "effective_end": end_dt.strftime("%Y-%m-%d"),
        }
    )

    cursor = start_dt
    total_days = 0
    total_items = 0
    latest_summary = {}

    while cursor <= end_dt:
        target_date = cursor.strftime("%Y-%m-%d")

        print(f"Running backfill date: {target_date}")

        items = run_daily_for_date(target_date, store=True)

        total_days += 1
        total_items += len(items)
        latest_summary = summarize_actions(items)

        set_checkpoint(target_date, status="running")

        set_run_status(
            {
                "mode": "backfill",
                "status": "running",
                "current_date": target_date,
                "days_completed": total_days,
                "items_written_total": total_items,
                "latest_actions": latest_summary,
                "effective_start": start_dt.strftime("%Y-%m-%d"),
                "effective_end": end_dt.strftime("%Y-%m-%d"),
            }
        )

        cursor += timedelta(days=1)

    set_checkpoint(end_dt.strftime("%Y-%m-%d"), status="complete")

    set_run_status(
        {
            "mode": "backfill",
            "status": "complete",
            "days_completed": total_days,
            "items_written_total": total_items,
            "latest_actions": latest_summary,
            "effective_start": start_dt.strftime("%Y-%m-%d"),
            "effective_end": end_dt.strftime("%Y-%m-%d"),
        }
    )


if __name__ == "__main__":
    backfill()
