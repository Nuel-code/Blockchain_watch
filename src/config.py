from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Config:
    start_date: str = os.getenv("START_DATE", f"{utc_now().year}-01-01")
    end_date: str = os.getenv("END_DATE", utc_now().strftime("%Y-%m-%d"))
    daily_cap: int = int(os.getenv("DAILY_CAP", "500"))
    max_days_per_run: int = int(os.getenv("MAX_DAYS_PER_RUN", "1"))
