import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import requests


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: str, data: Any) -> None:
    parent = os.path.dirname(path)
    if parent:
        ensure_dir(parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_unique(existing: List[dict], new_items: List[dict], key: str = "id") -> List[dict]:
    seen = {item.get(key) for item in existing}
    out = list(existing)
    for item in new_items:
        if item.get(key) not in seen:
            out.append(item)
            seen.add(item.get(key))
    return out


def utc_today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def daterange(start_date: str, end_date: str) -> Iterable[str]:
    start = parse_date(start_date)
    end = parse_date(end_date)
    cursor = start
    while cursor <= end:
        yield cursor.strftime("%Y-%m-%d")
        cursor += timedelta(days=1)


def previous_n_dates(anchor_date: str, n: int) -> List[str]:
    anchor = parse_date(anchor_date)
    out = []
    for i in range(1, n + 1):
        out.append((anchor - timedelta(days=i)).strftime("%Y-%m-%d"))
    return out


def iso_from_unix(ts: Optional[int]) -> Optional[str]:
    if ts is None:
        return None
    try:
        return datetime.utcfromtimestamp(int(ts)).isoformat() + "Z"
    except Exception:
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def clamp01(x: float) -> float:
    if x < 0:
        return 0.0
    if x > 1:
        return 1.0
    return x


def count_non_empty(values: Iterable[Any]) -> int:
    return sum(1 for v in values if v)


def first_non_empty(*values: Any) -> Any:
    for v in values:
        if v:
            return v
    return None


def request_json(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 20,
    retries: int = 2,
    sleep_seconds: float = 1.0,
) -> Any:
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=timeout,
            )
            if resp.status_code >= 400:
                last_error = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            else:
                return resp.json()
        except Exception as e:
            last_error = e
        if attempt < retries:
            time.sleep(sleep_seconds)
    raise last_error


def request_text(
    url: str,
    *,
    timeout: int = 20,
    retries: int = 1,
    sleep_seconds: float = 1.0,
) -> str:
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; BlockchainWatch/1.0)"
                },
            )
            if resp.status_code >= 400:
                last_error = RuntimeError(f"HTTP {resp.status_code}")
            else:
                return resp.text
        except Exception as e:
            last_error = e
        if attempt < retries:
            time.sleep(sleep_seconds)
    raise last_error
