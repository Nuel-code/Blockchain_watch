import json, os
from pathlib import Path


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def write_json(path, data):
    ensure_dir(Path(path).parent)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def atomic_replace(tmp, final):
    os.replace(tmp, final)


def candidate_id(chain, object_type, address):
    return f"{chain}:{object_type}:{address.lower()}"
