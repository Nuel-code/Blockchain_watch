import re
from typing import Dict, List, Optional, Tuple

from src.models import empty_socials
from src.utils import first_non_empty, request_text


URL_RE = re.compile(r'https?://[^\s"\'<>]+', re.IGNORECASE)

TWITTER_RE = re.compile(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[A-Za-z0-9_]+', re.IGNORECASE)
TELEGRAM_RE = re.compile(r'https?://(?:www\.)?t\.me/[A-Za-z0-9_/\-]+', re.IGNORECASE)
DISCORD_RE = re.compile(r'https?://(?:www\.)?(?:discord\.gg|discord\.com/invite)/[A-Za-z0-9]+', re.IGNORECASE)
GITHUB_RE = re.compile(r'https?://(?:www\.)?github\.com/[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)?', re.IGNORECASE)
DOCS_RE = re.compile(r'https?://[^\s"\'<>]*(?:docs|documentation|gitbook)[^\s"\'<>]*', re.IGNORECASE)


def _extract_links_from_profile(profile: dict) -> Dict[str, Optional[str]]:
    socials = empty_socials()

    links = profile.get("links") or []
    url = profile.get("url")

    if isinstance(url, str) and url.startswith("http"):
        socials["website"] = url

    for item in links:
        link_type = (item.get("type") or "").lower()
        link_url = item.get("url")
        if not link_url:
            continue

        if link_type in {"website", "site", "web"}:
            socials["website"] = first_non_empty(socials["website"], link_url)
        elif link_type in {"twitter", "x"}:
            socials["twitter_x"] = first_non_empty(socials["twitter_x"], link_url)
        elif link_type == "telegram":
            socials["telegram"] = first_non_empty(socials["telegram"], link_url)
        elif link_type == "discord":
            socials["discord"] = first_non_empty(socials["discord"], link_url)
        elif link_type == "github":
            socials["github"] = first_non_empty(socials["github"], link_url)
        elif link_type in {"docs", "documentation"}:
            socials["docs"] = first_non_empty(socials["docs"], link_url)

    return socials


def _extract_links_from_website(website_url: str) -> Dict[str, Optional[str]]:
    socials = empty_socials()
    try:
        html = request_text(website_url, timeout=15, retries=1)
    except Exception:
        return socials

    urls = set(URL_RE.findall(html))
    socials["twitter_x"] = next(iter([u for u in urls if TWITTER_RE.search(u)]), None)
    socials["telegram"] = next(iter([u for u in urls if TELEGRAM_RE.search(u)]), None)
    socials["discord"] = next(iter([u for u in urls if DISCORD_RE.search(u)]), None)
    socials["github"] = next(iter([u for u in urls if GITHUB_RE.search(u)]), None)
    socials["docs"] = next(iter([u for u in urls if DOCS_RE.search(u)]), None)
    socials["website"] = website_url
    return socials


def enrich_socials(item: dict) -> dict:
    profile = item.get("raw", {}).get("profile", {})
    pair = item.get("raw", {}).get("pair", {})

    profile_socials = _extract_links_from_profile(profile)

    # aggregator-derived fallback
    pair_info = pair.get("info", {}) if isinstance(pair, dict) else {}
    aggregator_socials = empty_socials()
    if pair_info:
        websites = pair_info.get("websites") or []
        socials_list = pair_info.get("socials") or []

        if websites and isinstance(websites, list):
            aggregator_socials["website"] = websites[0].get("url") if isinstance(websites[0], dict) else None

        for s in socials_list:
            stype = (s.get("type") or "").lower()
            surl = s.get("url")
            if stype in {"twitter", "x"}:
                aggregator_socials["twitter_x"] = surl
            elif stype == "telegram":
                aggregator_socials["telegram"] = surl
            elif stype == "discord":
                aggregator_socials["discord"] = surl

    website = first_non_empty(profile_socials["website"], aggregator_socials["website"])
    website_scraped = _extract_links_from_website(website) if website else empty_socials()

    merged = empty_socials()
    for key in merged.keys():
        merged[key] = first_non_empty(
            profile_socials.get(key),
            aggregator_socials.get(key),
            website_scraped.get(key),
        )

    item["socials"] = merged
    return item
