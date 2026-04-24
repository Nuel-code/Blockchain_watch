from typing import Dict, List


def _rank_key(item: Dict):
    scores = item.get("scores", {})
    market = item.get("market_signals", {})
    activity = item.get("activity_signals", {})

    return (
        scores.get("project_likelihood_score", 0),
        scores.get("confidence_score", 0),
        scores.get("economic_activity_score", 0),
        scores.get("social_presence_score", 0),
        -scores.get("spam_risk_score", 1),
        market.get("liquidity_usd", 0),
        activity.get("unique_wallets", 0),
        activity.get("transfer_count", 0),
    )


def rank_and_limit(items: List[Dict], limit: int = 500) -> List[Dict]:
    ranked = sorted(items, key=_rank_key, reverse=True)
    return ranked[:limit]


def summarize_actions(items: List[Dict]) -> Dict[str, int]:
    summary = {
        "watch_now": 0,
        "research": 0,
        "ignore": 0,
    }

    for item in items:
        action = item.get("action", "ignore")
        summary[action] = summary.get(action, 0) + 1

    return summary
