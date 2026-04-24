import re
from typing import Dict, Optional

from src.models import empty_socials
from src.utils import first_non_empty, normalize_url, request_text


URL_RE = re.compile(r'https?://[^\s"\'<>]+', re.IGNORECASE)

TWITTER_RE = re.compile(
    r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[A-Za-z0-9_]+',
    re.IGNORECASE,
)

TELEGRAM_RE = re.compile(
    r'https?://(?:www\.)?t\.me/[A-Za-z0-9_/\-]+',
    re.IGNORECASE,
)

DISCORD_RE = re.compile(
    r'https?://(?:www\.)?(?:discord\.gg|discord\.com/invite)/[A-Za-z0-9]+',
    re.IGNORECASE,
)

GITHUB_RE = re.compile(
    r'https?://(?:www\.)?github\.com/[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)?',
    re.IGNORECASE,
)

DOCS_RE = re.compile(
    r'https?://[^\s"\'<>]*(?:docs|documentation|gitbook|notion\.site)[^\s"\'<>]*',
    re.IGNORECASE,
)


def _merge_socials(*social_sets: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    merged = empty_socials()

    for key in merged:
        merged[key] = first_non_empty(*[s.get(key) for s in social_sets if isinstance(s, dict)])

    return merged


def _extract_from_profile(profile: dict) -> Dict[str, Optional[str]]:
    socials = empty_socials()

    if not isinstance(profile, dict):
        return socials

    # DexScreener token profiles often expose links as a list.
    links = profile.get("links") or []
    url = normalize_url(profile.get("url"))

    # Be careful: DexScreener profile URL is not the project website.
    # Use it only as weak fallback? No. Keep it in raw, not website.
    for link in links:
        if not isinstance(link, dict):
            continue

        link_type = (link.get("type") or link.get("label") or "").lower()
        link_url = normalize_url(link.get("url"))

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
        elif link_type in {"docs", "documentation", "gitbook"}:
            socials["docs"] = first_non_empty(socials["docs"], link_url)

    return socials


def _extract_from_pair(pair: dict) -> Dict[str, Optional[str]]:
    socials = empty_socials()

    if not isinstance(pair, dict):
        return socials

    info = pair.get("info") or {}
    websites = info.get("websites") or []
    socials_list = info.get("socials") or []

    for site in websites:
        if not isinstance(site, dict):
            continue

        url = normalize_url(site.get("url"))
        label = (site.get("label") or "").lower()

        if not url:
            continue

        if label in {"website", "site", "web", "official"} or not socials["website"]:
            socials["website"] = first_non_empty(socials["website"], url)

    for s in socials_list:
        if not isinstance(s, dict):
            continue

        stype = (s.get("type") or "").lower()
        surl = normalize_url(s.get("url"))

        if not surl:
            continue

        if stype in {"twitter", "x"}:
            socials["twitter_x"] = first_non_empty(socials["twitter_x"], surl)
        elif stype == "telegram":
            socials["telegram"] = first_non_empty(socials["telegram"], surl)
        elif stype == "discord":
            socials["discord"] = first_non_empty(socials["discord"], surl)
        elif stype == "github":
            socials["github"] = first_non_empty(socials["github"], surl)

    return socials


def _extract_from_token_info(token_info: dict) -> Dict[str, Optional[str]]:
    socials = empty_socials()

    if not isinstance(token_info, dict):
        return socials

    socials["website"] = normalize_url(
        first_non_empty(
            token_info.get("website"),
            token_info.get("Website"),
            token_info.get("officialSite"),
        )
    )

    socials["twitter_x"] = normalize_url(
        first_non_empty(
            token_info.get("twitter"),
            token_info.get("Twitter"),
            token_info.get("twitterUrl"),
        )
    )

    socials["telegram"] = normalize_url(
        first_non_empty(
            token_info.get("telegram"),
            token_info.get("Telegram"),
            token_info.get("telegramUrl"),
        )
    )

    socials["discord"] = normalize_url(
        first_non_empty(
            token_info.get("discord"),
            token_info.get("Discord"),
            token_info.get("discordUrl"),
        )
    )

    socials["github"] = normalize_url(
        first_non_empty(
            token_info.get("github"),
            token_info.get("Github"),
            token_info.get("githubUrl"),
        )
    )

    socials["docs"] = normalize_url(
        first_non_empty(
            token_info.get("docs"),
            token_info.get("documentation"),
            token_info.get("whitepaper"),
        )
    )

    return socials


def _extract_from_helius_asset(asset: dict) -> Dict[str, Optional[str]]:
    socials = empty_socials()

    if not isinstance(asset, dict):
        return socials

    content = asset.get("content") or {}
    links = content.get("links") or {}
    metadata = content.get("metadata") or {}

    socials["website"] = normalize_url(
        first_non_empty(
            links.get("external_url"),
            metadata.get("external_url"),
            metadata.get("website"),
        )
    )

    # Helius metadata usually won’t cleanly expose socials, but catch common fields.
    socials["twitter_x"] = normalize_url(first_non_empty(metadata.get("twitter"), metadata.get("x")))
    socials["telegram"] = normalize_url(metadata.get("telegram"))
    socials["discord"] = normalize_url(metadata.get("discord"))
    socials["github"] = normalize_url(metadata.get("github"))
    socials["docs"] = normalize_url(first_non_empty(metadata.get("docs"), metadata.get("documentation")))

    return socials


def _extract_from_website(website: Optional[str]) -> Dict[str, Optional[str]]:
    socials = empty_socials()

    website = normalize_url(website)
    if not website:
        return socials

    socials["website"] = website

    try:
        html = request_text(website, timeout=15, retries=1)
    except Exception:
        return socials

    urls = set(URL_RE.findall(html))

    for url in urls:
        cleaned = normalize_url(url)
        if not cleaned:
            continue

        if not socials["twitter_x"] and TWITTER_RE.search(cleaned):
            socials["twitter_x"] = cleaned
        elif not socials["telegram"] and TELEGRAM_RE.search(cleaned):
            socials["telegram"] = cleaned
        elif not socials["discord"] and DISCORD_RE.search(cleaned):
            socials["discord"] = cleaned
        elif not socials["github"] and GITHUB_RE.search(cleaned):
            socials["github"] = cleaned
        elif not socials["docs"] and DOCS_RE.search(cleaned):
            socials["docs"] = cleaned

    return socials


def enrich_socials(item: dict) -> dict:
    """
    Social extraction order:
      1. metadata
      2. aggregator APIs
      3. website scraping
    """
    raw = item.get("raw", {})

    metadata_socials = _merge_socials(
        _extract_from_token_info(raw.get("etherscan_token_info", {})),
        _extract_from_helius_asset(raw.get("helius_asset", {})),
        _extract_from_profile(raw.get("profile", {})),
    )

    aggregator_socials = _extract_from_pair(raw.get("dexscreener_pair", {}))

    website = first_non_empty(
        metadata_socials.get("website"),
        aggregator_socials.get("website"),
        item.get("socials", {}).get("website"),
    )

    website_socials = _extract_from_website(website)

    merged = _merge_socials(
        item.get("socials", {}),
        metadata_socials,
        aggregator_socials,
        website_socials,
    )

    item["socials"] = merged

    social_count = sum(1 for value in merged.values() if value)
    item["raw"]["social_count"] = social_count

    if social_count > 0:
        item["labels"].append("social_identity_found")
        item["why_kept"].append(f"social_count={social_count}")
    else:
        item["why_flagged"].append("no_socials_found")

    return item
