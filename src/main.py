from __future__ import annotations
import argparse
from src.config import Config
from src.pipeline.backfill import run_backfill


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["backfill", "daily"], nargs="?", default="backfill")
    args = parser.parse_args()

    config = Config()

    if args.mode in ("backfill", "daily"):
        run_backfill(config)


if __name__ == "__main__":
    main()
