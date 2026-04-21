from __future__ import annotations
from src.models import Candidate


def apply_filters(c: Candidate) -> Candidate:
    why_kept = []
    why_flagged = []
    spam = 0.0
    scam = 0.0

    if c.tx_count_1h == 0:
        spam += 0.35
        why_flagged.append("no post-deploy activity")

    if c.unique_external_wallets_1h <= 1:
        spam += 0.20
        why_flagged.append("deployer-only or near-single-party activity")

    if c.liquidity_usd <= 0:
        spam += 0.20
        why_flagged.append("no liquidity detected")
    else:
        why_kept.append("liquidity detected")

    if c.recognized_factory:
        why_kept.append("recognized factory/ecosystem")

    if c.source_verified:
        why_kept.append("verified source or explorer metadata")

    if c.website:
        why_kept.append("website resolved")

    if c.social_confidence >= 0.4:
        why_kept.append("project socials resolved")

    c.spam_score = min(spam, 1.0)
    c.scam_score = min(scam, 1.0)
    c.why_kept = why_kept
    c.why_flagged = why_flagged
    return c
