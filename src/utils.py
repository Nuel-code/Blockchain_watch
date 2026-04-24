import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
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
        value = item.get(key)
        if value and value not in seen:
            out.append(item)
            seen.add(value)

    return out


def utc_today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def date_to_unix_start(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def date_to_unix_end(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    dt = dt + timedelta(days=1) - timedelta(seconds=1)
    return int(dt.timestamp())


def unix_to_iso(value: Any) -> Optional[str]:
    try:
        ts = int(value)
        return datetime.utcfromtimestamp(ts).isoformat() + "Z"
    except Exception:
        return None


def daterange(start_date: str, end_date: str) -> Iterable[str]:
    start = parse_date(start_date)
    end = parse_date(end_date)
    cursor = start

    while cursor <= end:
        yield cursor.strftime("%Y-%m-%d")
        cursor += timedelta(days=1)


def previous_n_dates(anchor_date: str, n: int) -> List[str]:
    anchor = parse_date(anchor_date)
    return [
        (anchor - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(1, n + 1)
    ]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in [None, ""]:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in [None, ""]:
            return default
        return int(float(value))
    except Exception:
        return default


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def count_non_empty(values: Iterable[Any]) -> int:
    return sum(1 for v in values if v)


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in [None, "", [], {}]:
            return value
    return None


def normalize_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None

    url = str(url).strip()
    if not url:
        return None

    if url.startswith("//"):
        return "https:" + url

    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url

    return url


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)

    return text or None


def request_json(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 25,
    retries: int = 2,
    sleep_seconds: float = 1.0,
) -> Any:
    last_error = None

    for attempt in range(retries + 1):
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                headers=headers or {
                    "User-Agent": "BlockchainWatch/1.0"
                },
                timeout=timeout,
            )

            if response.status_code >= 400:
                last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
            else:
                return response.json()

        except Exception as exc:
            last_error = exc

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
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; BlockchainWatch/1.0)"
                },
            )

            if response.status_code >= 400:
                last_error = RuntimeError(f"HTTP {response.status_code}")
            else:
                return response.text

        except Exception as exc:
            last_error = exc

        if attempt < retries:
            time.sleep(sleep_seconds)

    raise last_error
