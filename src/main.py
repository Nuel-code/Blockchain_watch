from __future__ import annotations
import argparse
from src.config import Config
from src.pipeline.backfill import run_backfill
from src.pipeline.daily import run_daily


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["backfill", "daily"], nargs="?", default="backfill")
    args = parser.parse_args()

    config = Config()

    if args.mode == "backfill":
        run_backfill(config)
    elif args.mode == "daily":
        run_daily(config)


if __name__ == "__main__":
    main()
