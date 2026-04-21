from __future__ import annotations
from datetime import datetime, timezone

from src.adapters.base_adapter import BaseAdapter
from src.adapters.ethereum_adapter import EthereumAdapter
from src.adapters.solana_adapter import SolanaAdapter

from src.pipeline.normalize import normalize
from src.pipeline.enrich import enrich
from src.pipeline.filtering import apply_filters
from src.pipeline.scoring import score
from src.pipeline.storage import write_day, update_latest, update_manifest
from src.pipeline.aggregate import dedupe_new_candidates, rebuild_all_json


def rank_key(c):
    return (
        c.relevance_score,
        c.confidence_score,
        c.liquidity_usd,
        c.unique_external_wallets_1h,
    )


def run_daily(config) -> None:
    day = datetime.now(timezone.utc).date().isoformat()

    adapters = [
        SolanaAdapter(),
        BaseAdapter(),
        EthereumAdapter(),
    ]

    raw = []
    for adapter in adapters:
        try:
            raw.extend(adapter.fetch_candidates_for_day(day))
        except Exception as e:
            print(f"[{adapter.chain}] adapter error: {e}")

    normalized = [normalize(item, day) for item in raw]
    enriched = [enrich(x) for x in normalized]
    filtered = [apply_filters(x) for x in enriched]
    scored = [score(x) for x in filtered]

    survivors = [
        x for x in scored
        if x.action != "ignore" or x.relevance_score >= 0.45
    ]
    survivors.sort(key=rank_key, reverse=True)

    deduped = dedupe_new_candidates(survivors)
    kept = deduped[: config.daily_cap]

    meta = {
        "date": day,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "mode": "daily",
        "daily_cap": config.daily_cap,
        "total_raw_candidates": len(raw),
        "total_filtered_candidates": len(filtered),
        "total_scored_survivors": len(survivors),
        "post_dedupe_count": len(deduped),
        "stored_count": len(kept),
        "excluded_due_to_cap": max(0, len(deduped) - len(kept)),
        "chains": ["solana", "base", "ethereum"],
    }

    write_day(day, kept, meta)
    update_latest(day, kept, meta)
    update_manifest(day, meta)
    rebuild_all_json()

    print(
        f"[daily {day}] raw={len(raw)} "
        f"filtered={len(filtered)} "
        f"scored={len(survivors)} "
        f"deduped={len(deduped)} "
        f"stored={len(kept)}"
    )
