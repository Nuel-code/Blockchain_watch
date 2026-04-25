import re
from typing import Dict


PROJECT_SUFFIXES = {
    "fi", "defi", "dao", "swap", "labs", "protocol", "finance", "network",
    "markets", "market", "exchange", "dex", "pay", "chain", "base", "sol",
    "ai", "vault", "capital", "fund", "yield", "stake", "staking", "launch",
    "terminal", "index", "oracle", "bridge", "layer", "zone", "hub", "app"
}


BAD_GENERIC_WORDS = {
    "test", "demo", "sample", "mock", "fake", "token", "coin", "contract",
    "mytoken", "newtoken", "erc20", "erc721", "airdrop", "claim", "free",
    "reward", "bonus", "giveaway", "official", "the", "will", "fly",
    "moon", "safe", "baby", "inu", "elon"
}


BAD_PHRASE_PATTERNS = [
    r"\bthe\s+\w+\s+\w+\s+will\s+\w+\b",
    r"\bwill\s+fly\b",
    r"\bto\s+the\s+moon\b",
    r"\bbest\s+token\b",
    r"\bfree\s+airdrop\b",
    r"\bclaim\s+now\b",
    r"\bofficial\s+token\b",
]


def _tokens(text: str):
    return re.findall(r"[a-z0-9]+", text.lower())


def assess_name_quality(item: Dict) -> Dict:
    name = (item.get("name") or "").strip()
    symbol = (item.get("symbol") or "").strip()
    text = f"{name} {symbol}".lower()

    labels = item.get("labels", [])
    why_kept = item.get("why_kept", [])
    why_flagged = item.get("why_flagged", [])

    score = 0.0

    words = _tokens(text)

    if not name and not symbol:
        score = 0.0
        why_flagged.append("missing_name_and_symbol")

    else:
        if 3 <= len(name) <= 32:
            score += 0.2

        if 2 <= len(symbol) <= 12:
            score += 0.15

        if len(words) <= 4:
            score += 0.15
        else:
            score -= 0.25
            labels.append("long_phrase_name")
            why_flagged.append("name_looks_like_sentence")

        if any(text.endswith(suffix) for suffix in PROJECT_SUFFIXES):
            score += 0.25
            labels.append("project_like_name_suffix")
            why_kept.append("project_like_name_suffix")

        if any(word in PROJECT_SUFFIXES for word in words):
            score += 0.2
            labels.append("project_like_name_word")
            why_kept.append("project_like_name_word")

        bad_word_count = sum(1 for word in words if word in BAD_GENERIC_WORDS)
        if bad_word_count:
            score -= min(0.35, bad_word_count * 0.12)
            labels.append("generic_or_hype_name")
            why_flagged.append("generic_or_hype_name")

        for pattern in BAD_PHRASE_PATTERNS:
            if re.search(pattern, text):
                score -= 0.4
                labels.append("bad_phrase_name")
                why_flagged.append("bad_phrase_name")
                break

        if len(name) > 40:
            score -= 0.35
            labels.append("excessively_long_name")
            why_flagged.append("excessively_long_name")

    score = max(0.0, min(1.0, score))

    item["name_quality"] = {
        "score": round(score, 4),
        "name": name or None,
        "symbol": symbol or None,
        "word_count": len(words),
    }

    if score >= 0.45:
        labels.append("acceptable_name_quality")
        why_kept.append(f"name_quality_score={round(score, 4)}")
    else:
        labels.append("poor_name_quality")
        why_flagged.append(f"poor_name_quality_score={round(score, 4)}")

    item["labels"] = sorted(set(labels))
    item["why_kept"] = list(dict.fromkeys(why_kept))
    item["why_flagged"] = list(dict.fromkeys(why_flagged))

    return item
