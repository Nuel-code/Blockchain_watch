from __future__ import annotations
from src.models import Candidate


def apply_filters(c: Candidate) -> Candidate:
    why_kept = []
    why_flagged = []
    spam = 0.0
    scam = 0.0

    # --- HARD NEGATIVES ---
    if c.liquidity_usd <= 0:
        spam += 0.4
        why_flagged.append("no liquidity")

    if c.tx_count_1h == 0:
        spam += 0.3
        why_flagged.append("no activity")

    if c.unique_external_wallets_1h <= 1:
        spam += 0.2
        why_flagged.append("no external participation")

    # --- WEAK SIGNAL ---
    if c.liquidity_usd < 2000:
        spam += 0.1
        why_flagged.append("very low liquidity")

    # --- POSITIVES ---
    if c.liquidity_usd >= 5000:
        why_kept.append("liquidity present")

    if c.tx_count_1h >= 10:
        why_kept.append("active trading")

    if c.unique_external_wallets_1h >= 5:
        why_kept.append("multiple wallets interacting")

    if c.recognized_factory:
        why_kept.append("recognized dex")

    if c.website:
        why_kept.append("website found")

    if c.social_confidence >= 0.4:
        why_kept.append("social presence")

    # --- SCAM SIGNALS ---
    if c.social_confidence == 0 and c.website is None:
        scam += 0.3
        why_flagged.append("no socials or website")

    if c.liquidity_usd > 0 and c.tx_count_1h == 0:
        scam += 0.2
        why_flagged.append("liquidity but no activity")

    # Clamp
    c.spam_score = min(spam, 1.0)
    c.scam_score = min(scam, 1.0)
    c.why_kept = why_kept
    c.why_flagged = why_flagged

    return c
