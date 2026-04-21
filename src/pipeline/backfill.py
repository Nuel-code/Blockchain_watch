from __future__ import annotations
from datetime import datetime, timedelta

from src.adapters.base_adapter import BaseAdapter
from src.adapters.ethereum_adapter import EthereumAdapter
from src.adapters.solana_adapter import SolanaAdapter

from src.pipeline.checkpoint import load_or_init, mark_day_complete
from src.pipeline.normalize import normalize
from src.pipeline.enrich import enrich
from src.pipeline.filtering import apply_filters
from src.pipeline.scoring import score
from src.pipeline.storage import write_day, update_latest, update_manifest

from src.pipeline.aggregate import dedupe_new_candidates, rebuild_all_json


def daterange(start_date: str, end_date: str):
    cur = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    while cur <= end:
        yield cur.isoformat()
        cur += timedelta(days=1)


def rank_key(c):
    return (
        c.relevance_score,
        c.confidence_score,
        c.liquidity_usd,
        c.unique_external_wallets_1h,
    )


def run_backfill(config) -> None:
    adapters = [
        SolanaAdapter(),
        BaseAdapter(),
        EthereumAdapter(),
    ]

    cp = load_or_init(config.start_date, config.end_date)
    current = cp["next_day"]
    processed = 0

    for day in daterange(current, config.end_date):

        if processed >= config.max_days_per_run:
            break

        # 1. Fetch raw candidates
        raw = []
        for adapter in adapters:
            try:
                raw.extend(adapter.fetch_candidates_for_day(day))
            except Exception as e:
                print(f"[{adapter.chain}] adapter error: {e}")

        # 2. Normalize
        normalized = [normalize(item, day) for item in raw]

        # 3. Enrich
        enriched = [enrich(x) for x in normalized]

        # 4. Filter
        filtered = [apply_filters(x) for x in enriched]

        # 5. Score
        scored = [score(x) for x in filtered]

        # 6. Select survivors
        survivors = [
            x for x in scored
            if x.action != "ignore" or x.relevance_score >= 0.45
        ]

        # 7. Rank
        survivors.sort(key=rank_key, reverse=True)

        # 8. DEDUPE (global)
        deduped = dedupe_new_candidates(survivors)

        # 9. Apply daily cap AFTER dedupe
        kept = deduped[: config.daily_cap]

        # 10. Build metadata
        meta = {
            "date": day,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "mode": "backfill",
            "daily_cap": config.daily_cap,
            "total_raw_candidates": len(raw),
            "total_filtered_candidates": len(filtered),
            "total_scored_survivors": len(survivors),
            "post_dedupe_count": len(deduped),
            "stored_count": len(kept),
            "excluded_due_to_cap": max(0, len(deduped) - len(kept)),
            "chains": ["solana", "base", "ethereum"],
        }

        # 11. Write outputs
        write_day(day, kept, meta)
        update_latest(day, kept, meta)
        update_manifest(day, meta)

        # 12. Rebuild aggregate dataset
        rebuild_all_json()

        # 13. Update checkpoint
        mark_day_complete(day)

        print(
            f"[{day}] raw={len(raw)} "
            f"filtered={len(filtered)} "
            f"scored={len(survivors)} "
            f"deduped={len(deduped)} "
            f"stored={len(kept)}"
        )

        processed += 1
