from __future__ import annotations
import re
import requests
from bs4 import BeautifulSoup
from src.models import Candidate, Socials


SOCIAL_PATTERNS = {
    "twitter": r"https?://(?:www\.)?(?:x|twitter)\.com/[^\s\"'<>]+",
    "telegram": r"https?://(?:t\.me|telegram\.me)/[^\s\"'<>]+",
    "discord": r"https?://(?:discord\.gg|discord\.com/invite)/[^\s\"'<>]+",
    "github": r"https?://(?:www\.)?github\.com/[^\s\"'<>]+",
}


def extract_from_links(links: list[dict]) -> tuple[Socials, float]:
    socials = Socials()
    confidence = 0.0

    for link in links:
        url = link.get("url")
        if not url:
            continue

        for key, pattern in SOCIAL_PATTERNS.items():
            if re.search(pattern, url, re.IGNORECASE):
                setattr(socials, key, url)
                confidence += 0.15

        if "docs" in url.lower() or "gitbook" in url.lower():
            socials.docs = url
            confidence += 0.10

    return socials, min(confidence, 0.8)


def scrape_website(url: str) -> tuple[Socials, float] | None:
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(r.text, "lxml")
    hrefs = [a.get("href") for a in soup.find_all("a", href=True)]
    text = "\n".join(h for h in hrefs if h)

    socials = Socials()
    confidence = 0.0

    for key, pattern in SOCIAL_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            setattr(socials, key, match.group(0))
            confidence += 0.2

    for h in hrefs:
        if not h:
            continue
        if "docs" in h.lower() or "gitbook" in h.lower():
            socials.docs = h
            confidence += 0.1
            break

    return socials, min(confidence, 0.9)


def merge_socials(base: Socials, new: Socials) -> Socials:
    merged = base.model_copy(deep=True)
    for field in merged.model_fields:
        if getattr(merged, field) is None and getattr(new, field) is not None:
            setattr(merged, field, getattr(new, field))
    return merged


def has_any_socials(s: Socials) -> bool:
    return any(getattr(s, field) for field in s.model_fields)


def resolve_socials(candidate: Candidate) -> Candidate:
    sources: list[tuple[str, Socials, float]] = []

    links = candidate.raw_refs.get("links", [])
    if links:
        s, conf = extract_from_links(links)
        if has_any_socials(s):
            sources.append(("dexscreener_links", s, conf))

    if candidate.website:
        result = scrape_website(candidate.website)
        if result:
            s, conf = result
            if has_any_socials(s):
                sources.append(("website_scrape", s, conf))

    if not sources:
        return candidate

    final = Socials()
    best_conf = 0.0

    for _, s, conf in sources:
        final = merge_socials(final, s)
        best_conf = max(best_conf, conf)

    candidate.socials = final
    candidate.social_source = "combined" if len(sources) > 1 else sources[0][0]
    candidate.social_confidence = min(best_conf, 1.0)

    return candidate
