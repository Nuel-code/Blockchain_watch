from __future__ import annotations
import json
import os
from pathlib import Path


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def write_json(path: str, data) -> None:
    ensure_dir(str(Path(path).parent))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_replace(tmp_path: str, final_path: str) -> None:
    os.replace(tmp_path, final_path)


def candidate_id(chain: str, object_type: str, address: str) -> str:
    return f"{chain}:{object_type}:{address.lower()}"
