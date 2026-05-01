from typing import Dict

from src.config import ENABLE_PROJECT_SEEDS
from src.clients.github_search import search_recent_crypto_repos
from src.clients.defillama import get_protocols


PROJECT_KEYWORDS = {
    "defi", "dex", "yield", "staking", "protocol", "finance",
    "liquidity", "market", "trading", "vault", "swap",
    "ai", "inference", "model", "data",
    "game", "gaming", "metaverse",
    "nft", "collection",
    "dao", "governance",
    "payments", "wallet",
    "bridge", "oracle", "lending", "borrow", "perps",
    "derivatives", "index", "launchpad", "restaking",
}


SPAM_WORDS = {
    "moon", "airdrop", "claim", "free", "bonus",
    "best", "profit", "100x", "pump", "elon",
    "pepe", "doge", "inu", "safe",
}


def _clean(text: str) -> str:
    return (text or "").lower()


def _contains_keywords(text: str, keywords: set) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def assess_project_identity(item: Dict) -> Dict:
    name = _clean(item.get("name"))
    desc = _clean(item.get("description"))

    labels = item.get("labels", [])
    why_kept = item.get("why_kept", [])
    why_flagged = item.get("why_flagged", [])

    score = 0.0

    if desc:
        score += 0.20
    else:
        why_flagged.append("no_description")

    keyword_hits = _contains_keywords(desc, PROJECT_KEYWORDS)

    if keyword_hits >= 2:
        score += 0.30
        labels.append("strong_project_keywords")
        why_kept.append("description_has_project_keywords")
    elif keyword_hits == 1:
        score += 0.15
        labels.append("some_project_keywords")

    spam_hits = _contains_keywords(desc + " " + name, SPAM_WORDS)

    if spam_hits:
        score -= 0.30
        labels.append("spammy_description")
        why_flagged.append("spammy_description")

    # Heavy external project matching only runs in daily mode.
    # Backfill keeps this off so historical scans do not time out.
    if ENABLE_PROJECT_SEEDS:
        try:
            github_projects = search_recent_crypto_repos()
        except Exception:
            github_projects = []

        for repo in github_projects:
            repo_name = (repo.get("name") or "").lower()
            repo_full_name = (repo.get("full_name") or "").lower()

            if repo_name and (repo_name in name or name in repo_name):
                score += 0.25
                labels.append("github_match")
                why_kept.append("github_project_match")
                break

            if repo_full_name and name and name in repo_full_name:
                score += 0.20
                labels.append("github_match")
                why_kept.append("github_project_match")
                break

        try:
            protocols = get_protocols()
        except Exception:
            protocols = []

        for protocol in protocols:
            protocol_name = (protocol.get("name") or "").lower()

            if protocol_name and (protocol_name in name or name in protocol_name):
                score += 0.35
                labels.append("defillama_match")
                why_kept
