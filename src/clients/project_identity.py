import re
from typing import Dict, List

from src.clients.github_search import search_recent_crypto_repos
from src.clients.defillama import get_protocols
from src.utils import first_non_empty


PROJECT_KEYWORDS = {
    "defi", "dex", "yield", "staking", "protocol", "finance",
    "liquidity", "market", "trading", "vault", "swap",
    "ai", "inference", "model", "data",
    "game", "gaming", "metaverse",
    "nft", "collection",
    "dao", "governance",
    "payments", "wallet"
}

SPAM_WORDS = {
    "moon", "airdrop", "claim", "free", "bonus",
    "best", "profit", "100x", "pump", "elon"
}


def _clean(text: str) -> str:
    return (text or "").lower()


def _contains_keywords(text: str, keywords: set) -> int:
    return sum(1 for k in keywords if k in text)


def assess_project_identity(item: Dict) -> Dict:
    name = _clean(item.get("name"))
    desc = _clean(item.get("description"))

    labels = item.get("labels", [])
    why_kept = item.get("why_kept", [])
    why_flagged = item.get("why_flagged", [])

    score = 0.0
    categories: List[str] = []

    # description presence
    if desc:
        score += 0.2
    else:
        why_flagged.append("no_description")

    # keyword matching
    keyword_hits = _contains_keywords(desc, PROJECT_KEYWORDS)

    if keyword_hits >= 2:
        score += 0.3
        labels.append("strong_project_keywords")
        why_kept.append("description_has_project_keywords")
    elif keyword_hits == 1:
        score += 0.15

    # spam detection
    spam_hits = _contains_keywords(desc + " " + name, SPAM_WORDS)
    if spam_hits:
        score -= 0.3
        labels.append("spammy_description")
        why_flagged.append("spammy_description")

    # github match
    github_projects = search_recent_crypto_repos()
    for repo in github_projects:
        if repo["name"].lower() in name:
            score += 0.25
            labels.append("github_match")
            why_kept.append("github_project_match")
            break

    # defillama match
    protocols = get_protocols()
    for p in protocols:
        if p["name"].lower() in name:
            score += 0.35
            labels.append("defillama_match")
            why_kept.append("known_protocol_match")
            break

    score = max(0.0, min(1.0, score))

    item["identity_signals"] = {
        "description_present": bool(desc),
        "keyword_hits": keyword_hits,
        "spam_hits": spam_hits,
        "score": round(score, 4),
    }

    if score >= 0.4:
        labels.append("project_identity_strong")
    else:
        labels.append("weak_identity")

    item["labels"] = sorted(set(labels))
    item["why_kept"] = list(dict.fromkeys(why_kept))
    item["why_flagged"] = list(dict.fromkeys(why_flagged))

    return item
