import re
from typing import List, Tuple, Optional, Any
from urllib.parse import urljoin, urlparse

FALLBACK_CARD_SELECTORS = [
    "article",
    "li[data-testid*='job']",
    "li[class*='job']",
    "div[data-testid*='job-card']",
    "div[data-testid*='job-item']",
    "div[data-testid*='job_card']",
    "div[data-job-id]",
    "div[data-jk]",
    "div[class*='job-card']",
    "div[class*='jobCard']",
    "div[class*='JobCard']",
    "div[class*='job-item']",
    "div[class*='posting']",
    "div[class*='result-item']",
    "div[class*='search-result']",
    "div[class*='vacancy']",
]

FALLBACK_TITLE_SELECTORS = [
    "h2",
    "h3",
    "h1",
    "h4",
    "a[class*='title']",
    "a[data-testid*='title']",
    "span[class*='title']",
    "div[class*='title']",
    "strong",
]

FALLBACK_COMPANY_SELECTORS = [
    "[data-testid*='company']",
    "a[href*='/company/']",
    "a[href*='/companies/']",
    "span[class*='company']",
    "div[class*='company']",
    "p[class*='company']",
    "span[class*='employer']",
]

FALLBACK_LOCATION_SELECTORS = [
    "[data-testid*='location']",
    "[data-testid*='text-location']",
    ".job-search-card__location",
    ".base-search-card__metadata span",
    ".companyLocation",
    ".job-location",
    ".location",
    "span[class*='location']",
    "div[class*='location']",
    "span[class*='remote']",
]

JOB_LINK_KEYWORDS = [
    "/job/",
    "/jobs/",
    "/job-detail/",
    "/job-detail",
    "/job-listing/",
    "/job-listing",
    "/joblisting",
    "/viewjob",
    "/rc/clk",
    "/posting/",
    "/postings/",
    "/position/",
    "/positions/",
    "/career/",
    "/careers/",
    "/opening/",
    "/opportunity/",
    "/opportunities/",
    "jobid=",
    "job_id=",
    "gh_jid=",
]

NON_JOB_SUBSTRINGS = [
    "login",
    "signin",
    "signup",
    "register",
    "/privacy",
    "/terms",
    "cookie",
    "bookmark",
    "favorite",
    "share",
    "mailto:",
    "tel:",
    "javascript:",
    "#",
]

KNOWN_ATS_DOMAINS = [
    "greenhouse.io",
    "myworkdayjobs.com",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "smartrecruiters.com",
    "bamboohr.com",
    "recruitee.com",
    "teamtailor.com",
    "jobvite.com",
    "join.com",
    "personio.de",
    "personio.com",
]

def is_likely_job_url(href: str, base_url: str = "", allow_career_portals: bool = False) -> bool:
    """Validate whether an anchor href represents an individual job posting."""
    if not href:
        return False

    href_clean = href.strip()
    if not href_clean or href_clean == "#" or href_clean.startswith("javascript:"):
        return False

    h_lower = href_clean.lower()

    # Reject non-job substrings
    for sub in NON_JOB_SUBSTRINGS:
        if sub in h_lower:
            return False

    parsed = urlparse(href_clean)
    path = parsed.path.lower()

    # Reject search landing endpoints if no individual slug/id
    if path.rstrip("/") in ["/search", "/jobs/search", "/search-results", "/jobs/results"]:
        segments = [s for s in path.split("/") if s]
        if len(segments) <= 2:
            return False

    # Check if identical to search base_url (ignoring query/fragments)
    if base_url:
        try:
            base_norm = urlparse(base_url)._replace(query="", fragment="").geturl().rstrip("/")
            cand_full = urljoin(base_url, href_clean) if not href_clean.startswith("http") else href_clean
            cand_norm = urlparse(cand_full)._replace(query="", fragment="").geturl().rstrip("/")
            if cand_norm == base_norm:
                return False
        except Exception:
            pass

    path_slash = "/" + path.lstrip("/")

    # Check for strong job keywords
    if any(k in path_slash for k in JOB_LINK_KEYWORDS):
        return True

    # If the URL ends with an ID or alphanumeric slug
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 2 and any(seg.isdigit() for seg in segments):
        return True

    # Recognize career portals or known ATS domains (e.g. from company directories or Layoffs & Hires)
    netloc_lower = parsed.netloc.lower()
    if any(ats in netloc_lower for ats in KNOWN_ATS_DOMAINS) or allow_career_portals:
        if parsed.path.strip("/") or parsed.query:
            return True

    return False


async def find_fallback_cards(page) -> Tuple[Optional[str], List[Any]]:
    """
    Attempt to locate job card elements using common layout heuristics.
    Returns (matched_selector, card_locators) or (None, []).
    """
    for sel in FALLBACK_CARD_SELECTORS:
        try:
            locator = page.locator(sel)
            count = await locator.count()
            # A valid job list typically contains between 1 and 60 cards per page
            if 1 <= count <= 100:
                elements = await locator.all()
                return sel, elements
        except Exception:
            continue
    return None, []


async def extract_fallback_title(card) -> str:
    """Attempt to extract job title from a card using heading and class heuristics."""
    for sel in FALLBACK_TITLE_SELECTORS:
        try:
            el = card.locator(sel).first
            if await el.count():
                txt = (await el.text_content() or "").strip()
                if txt and len(txt) > 2 and len(txt) < 120:
                    t_lower = txt.lower()
                    if "apply" not in t_lower and "save" not in t_lower and "ago" not in t_lower:
                        return txt
        except Exception:
            continue
    return ""


async def extract_fallback_link(card, base_url: str = "") -> Optional[str]:
    """
    Attempt to extract a distinct job posting URL from a card, ensuring it
    does not point back to the search page itself.
    """
    # 1. Check if the card itself is an anchor
    try:
        tag_name = await card.evaluate("el => el.tagName.toLowerCase()")
        if tag_name == "a":
            href = await card.get_attribute("href")
            if href:
                if not href.startswith("http"):
                    try:
                        resolved = await card.evaluate("el => el.href")
                        if resolved and resolved.startswith("http"):
                            href = resolved
                        else:
                            href = urljoin(base_url, href)
                    except Exception:
                        href = urljoin(base_url, href)
                if is_likely_job_url(href, base_url):
                    return href
    except Exception:
        pass

    # 2. Check inner links in card
    try:
        links = await card.locator("a").all()
        for link in links:
            href = await link.get_attribute("href")
            if href:
                if not href.startswith("http"):
                    try:
                        resolved = await link.evaluate("el => el.href")
                        if resolved and resolved.startswith("http"):
                            href = resolved
                        else:
                            href = urljoin(base_url, href)
                    except Exception:
                        href = urljoin(base_url, href)
                if is_likely_job_url(href, base_url):
                    return href
    except Exception:
        pass

    return None


async def extract_fallback_company(card, candidate_title: str = "") -> str:
    """Attempt to extract company name from a card using common company selectors."""
    for sel in FALLBACK_COMPANY_SELECTORS:
        try:
            el = card.locator(sel).first
            if await el.count():
                txt = (await el.text_content() or "").strip()
                if txt and len(txt) > 1 and len(txt) < 80:
                    if txt != candidate_title and "apply" not in txt.lower():
                        return txt
        except Exception:
            continue
    return ""


async def extract_fallback_location(card) -> str:
    """Attempt to extract job location from a card using common location selectors."""
    for sel in FALLBACK_LOCATION_SELECTORS:
        try:
            el = card.locator(sel).first
            if await el.count():
                txt = (await el.text_content() or "").strip()
                if txt and len(txt) > 2 and len(txt) < 80:
                    t_lower = txt.lower()
                    if "ago" not in t_lower and "apply" not in t_lower:
                        return txt
        except Exception:
            continue
    return ""
