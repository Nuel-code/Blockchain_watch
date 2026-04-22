from typing import List


def rank_and_limit(items: List[dict], limit: int = 500) -> List[dict]:
    def sort_key(x: dict):
        scores = x.get("scores", {})
        return (
            scores.get("relevance_score", 0),
            scores.get("confidence_score", 0),
            x.get("liquidity_usd", 0),
            x.get("tx_count_1h", 0),
            x.get("unique_external_wallets_1h", 0),
        )

    ranked = sorted(items, key=sort_key, reverse=True)
    return ranked[:limit]
