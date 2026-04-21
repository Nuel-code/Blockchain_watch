
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
            confidence += 0.1

    return socials, min(confidence, 0.8)


def scrape_website(url: str) -> tuple[Socials, float] | None:
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(r.text, "lxml")
    hrefs = [a.get("href") for a in soup.find_all("a", href=True)]
    text = "\n".join(hrefs)

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


def resolve_socials(candidate: Candidate) -> Candidate:
    sources = []

    # 1. DexScreener links
    links = candidate.raw_refs.get("links", [])
    if links:
        s, conf = extract_from_links(links)
        if any(vars(s).values()):
            sources.append(("dexscreener_links", s, conf))

    # 2. Website scraping
    if candidate.website:
        result = scrape_website(candidate.website)
        if result:
            s, conf = result
            sources.append(("website_scrape", s, conf))

    # Merge sources
    if not sources:
        return candidate

    final = Socials()
    best_conf = 0.0
    source_name = "combined"

    for name, s, conf in sources:
        for field in vars(s):
            val = getattr(s, field)
            if val and not getattr(final, field):
                setattr(final, field, val)

        best_conf = max(best_conf, conf)

    candidate.socials = final
    candidate.social_source = source_name
    candidate.social_confidence = min(best_conf, 1.0)

    return candidate
