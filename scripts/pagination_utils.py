import math
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, List, Optional, Any

# Known default pagination schemas for popular job boards
KNOWN_SITE_PAGINATION = {
    "builtin": {"pagination_type": "page_param", "page_param": "page", "items_per_page": 20},
    "dice": {"pagination_type": "page_param", "page_param": "page", "items_per_page": 20},
    "indeed": {"pagination_type": "offset", "offset_param": "start", "items_per_page": 10},
    "linkedin": {"pagination_type": "offset", "offset_param": "start", "items_per_page": 25},
    "simplyhired": {"pagination_type": "page_param", "page_param": "pn", "items_per_page": 20},
    "careerbuilder": {"pagination_type": "page_param", "page_param": "page_number", "items_per_page": 25},
    "monster": {"pagination_type": "page_param", "page_param": "page", "items_per_page": 25},
}

def extract_page_count(
    text: str,
    pagination_elements: Optional[List[str]] = None,
    items_per_page: int = 25
) -> Dict[str, Any]:
    """
    Extract total page count and estimated total job count from page text or DOM elements.
    Returns: {"page_count": int, "total_jobs": Optional[int]}
    """
    if not text and not pagination_elements:
        return {"page_count": 1, "total_jobs": None}

    clean_text = text or ""

    # 1. Look for "Page X of Y"
    m_page_of = re.search(r'(?i)\bpage\s+\d+\s+of\s+([\d,]+)\b', clean_text)
    if m_page_of:
        try:
            total_pages = int(m_page_of.group(1).replace(",", ""))
            if total_pages > 0:
                return {"page_count": total_pages, "total_jobs": total_pages * items_per_page}
        except ValueError:
            pass

    # 2. Look for "Showing X-Y of Z jobs" or "X to Y of Z"
    m_showing = re.search(r'(?i)(?:showing\s+)?\d+\s*[-–to\s]+\s*\d+\s+of\s+([\d,]+)\s*(?:jobs?|openings?|results?|positions?|entries)?', clean_text)
    if m_showing:
        try:
            total_jobs = int(m_showing.group(1).replace(",", ""))
            if total_jobs > 0:
                calc_pages = max(1, math.ceil(total_jobs / items_per_page))
                return {"page_count": calc_pages, "total_jobs": total_jobs}
        except ValueError:
            pass

    # 3. Look for "Z jobs found" or "Z open positions"
    m_jobs_found = re.search(r'(?i)\b([\d,]+)\s+(?:jobs?|openings?|positions?|results?)\s+(?:found|available)\b', clean_text)
    if m_jobs_found:
        try:
            total_jobs = int(m_jobs_found.group(1).replace(",", ""))
            if total_jobs > 0:
                calc_pages = max(1, math.ceil(total_jobs / items_per_page))
                return {"page_count": calc_pages, "total_jobs": total_jobs}
        except ValueError:
            pass

    # 4. Check pagination numbers in links / buttons
    if pagination_elements:
        nums = []
        for el in pagination_elements:
            el_clean = (el or "").strip()
            if el_clean.isdigit():
                nums.append(int(el_clean))
        if nums:
            max_page = max(nums)
            return {"page_count": max(1, max_page), "total_jobs": max_page * items_per_page}

    return {"page_count": 1, "total_jobs": None}

def build_page_url(
    base_url: str,
    site_config: Optional[Dict[str, Any]] = None,
    page_num: int = 1,
    site_name: str = ""
) -> str:
    """
    Construct a URL for page N using explicit site config or heuristic detection.
    For page_num <= 1, returns the original base_url unaltered.
    """
    if page_num <= 1 or not base_url:
        return base_url

    cfg = site_config or {}
    site_key = site_name.lower().strip() if site_name else ""
    known_cfg = KNOWN_SITE_PAGINATION.get(site_key, {})

    pagination_type = cfg.get("pagination_type") or known_cfg.get("pagination_type")
    parsed = urlparse(base_url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    if pagination_type == "offset":
        offset_param = cfg.get("offset_param") or known_cfg.get("offset_param") or "start"
        items_per_page = cfg.get("items_per_page") or known_cfg.get("items_per_page") or 25
        offset_val = str((page_num - 1) * items_per_page)
        params[offset_param] = [offset_val]

    elif pagination_type == "page_param":
        page_param = cfg.get("page_param") or known_cfg.get("page_param") or "page"
        params[page_param] = [str(page_num)]

    else:
        # Heuristic fallback based on query parameters present in base_url
        if "start" in params:
            items_per_page = cfg.get("items_per_page") or 25
            params["start"] = [str((page_num - 1) * items_per_page)]
        elif "pn" in params:
            params["pn"] = [str(page_num)]
        elif "page_number" in params:
            params["page_number"] = [str(page_num)]
        elif "p" in params:
            params["p"] = [str(page_num)]
        else:
            # Default to appending page=N
            params["page"] = [str(page_num)]

    # Flatten single-item lists for query encoding
    flat_query = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
    new_query = urlencode(flat_query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
