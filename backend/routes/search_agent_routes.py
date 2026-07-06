"""
Bharat Tech Atlas — Web Search Agent API Routes
Analyzes startups using web search to fetch latest news, funding updates, and social media.
v3.3: Added URL validation, enhanced content filtering, audit logging, stricter PII redaction.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import logging
import asyncio
import os
import re
from urllib.parse import urlparse

from ..security import (
    validate_url,
    sanitize_url,
    escape_html,
    audit_log,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Sensitive data patterns to redact ────────────────────────────────────────
SENSITIVE_PATTERNS = [
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    re.compile(r'\b(?:\d{4}[\s-]?){3}\d{4}\b'),
    re.compile(r'\b\d{10,12}\b'),
    re.compile(r'\b(?:password|secret|token|key|api[_-]?key)\s*[:=]\s*\S+', re.I),
    re.compile(r'\b[A-Fa-f0-9]{32,}\b'),
    re.compile(r'\b\d{2}/\d{2}/\d{4}\b'),
    re.compile(r'\b[A-Z]{2}\d{6}\b'),
]


def _redact_sensitive(text: str) -> str:
    """Redact sensitive personal/secret information from text."""
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub('[REDACTED]', text)
    return text


def _sanitize_search_result(result: dict) -> dict:
    """Sanitize a single search result: redact PII, validate URL, escape HTML."""
    url = result.get("url", "")
    ok, _ = validate_url(url, allow_empty=True)
    if not ok:
        url = ""
    return {
        "title": escape_html(_redact_sensitive(result.get("title", "")))[:200],
        "url": sanitize_url(url),
        "snippet": escape_html(_redact_sensitive(result.get("snippet", "")))[:500],
        "source": escape_html(result.get("source", "unknown")),
    }


# ─── Web search helper (lazy import — degrades gracefully without package) ─────
async def _web_search(query: str, max_results: int = 5) -> List[Dict]:
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                raw = {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source": "duckduckgo",
                }
                results.append(_sanitize_search_result(raw))
    except ImportError:
        logger.warning("duckduckgo-search not installed — web search unavailable.")
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")

    if not results:
        brave_key = os.environ.get("BRAVE_API_KEY")
        if brave_key:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={"X-Subscription-Token": brave_key},
                        params={"q": query, "count": max_results}
                    )
                    data = resp.json()
                    for r in data.get("web", {}).get("results", []):
                        raw = {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("description", ""),
                            "source": "brave",
                        }
                        results.append(_sanitize_search_result(raw))
            except Exception as e:
                logger.warning(f"Brave search failed: {e}")
    return results


# ─── Social media profile finder ──────────────────────────────────────────────
SOCIAL_PLATFORMS = {
    "linkedin": lambda name: f"https://www.linkedin.com/search/results/companies/?keywords={name.replace(' ', '%20')}",
    "twitter_x": lambda name: f"https://x.com/search?q={name.replace(' ', '%20')}&src=typed_query",
    "instagram": lambda name: f"https://www.instagram.com/{name.lower().replace(' ', '').replace('.', '')}",
    "google": lambda name: f"https://www.google.com/search?q={name.replace(' ', '+')}+company",
    "crunchbase": lambda name: f"https://www.crunchbase.com/organization/{name.lower().replace(' ', '-').replace('.', '')}",
    "tracxn": lambda name: f"https://tracxn.com/d/companies/{name.lower().replace(' ', '-')}/",
}


def _build_social_links(name: str, website: Optional[str] = None) -> Dict[str, str]:
    """Build social media search links with URL validation."""
    links = {}
    for platform, url_builder in SOCIAL_PLATFORMS.items():
        url = url_builder(name)
        ok, _ = validate_url(url, allow_empty=False)
        if ok:
            links[platform] = url
    if website:
        ok, _ = validate_url(website, allow_empty=False)
        if ok:
            links["website"] = website
    return links


# ─── Pydantic schemas ───────────────────────────────────────────────────────────
class StartupAnalysisRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=100)
    sector: Optional[str] = None
    city: Optional[str] = None


class NewsItem(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    date: Optional[str] = None


class SocialProfiles(BaseModel):
    linkedin: str
    twitter_x: str
    instagram: str
    google: str
    crunchbase: str
    tracxn: str
    website: Optional[str] = None


class StartupAnalysisResponse(BaseModel):
    company_name: str
    summary: str
    latest_news: List[NewsItem]
    social_profiles: SocialProfiles
    sector_trend: str
    confidence: str
    last_updated: str


# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/analyze-startup", response_model=StartupAnalysisResponse)
async def analyze_startup(request: Request, body: StartupAnalysisRequest):
    """Analyze a startup by searching the web for latest news and trends."""
    req_id = getattr(request.state, "request_id", "unknown")

    try:
        import duckduckgo_search  # noqa: F401
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Web search unavailable: duckduckgo-search not installed. "
                   "The map and all other API endpoints work fine. "
                   "Install with: pip install duckduckgo-search"
        )

    company = body.company_name
    sector = body.sector or ""
    city = body.city or ""

    queries = [
        f'"{company}" startup India latest news funding 2024 2025',
        f'"{company}" {sector} India valuation investment',
    ]
    if city:
        queries.append(f'"{company}" {city} startup')

    all_results = []
    for q in queries:
        results = await _web_search(q, max_results=3)
        all_results.extend(results)
        await asyncio.sleep(0.5)

    # Deduplicate by URL
    seen = set()
    deduped = []
    for r in all_results:
        if r["url"] and r["url"] not in seen:
            seen.add(r["url"])
            deduped.append(r)

    news = [
        NewsItem(
            title=r["title"],
            url=r["url"],
            snippet=r["snippet"][:280] + "..." if len(r["snippet"]) > 280 else r["snippet"],
            source=r["source"],
        )
        for r in deduped[:8]
    ]

    if news:
        summary = (
            f"Found {len(news)} recent articles about {company}. "
            f"Top story: {news[0].title}. "
            f"Use the social links below to verify details on LinkedIn, Crunchbase, and X (Twitter)."
        )
        confidence = "high" if len(news) >= 3 else "medium"
    else:
        summary = (
            f"No recent web results for {company}. "
            f"This may be a very early-stage startup or operates under a different brand name. "
            f"Try searching on LinkedIn, Crunchbase, or Tracxn directly."
        )
        confidence = "low"

    sector_trend = f"{sector.title() if sector else 'Startup'} sector in India shows strong momentum in 2025."

    import datetime
    resp = StartupAnalysisResponse(
        company_name=company,
        summary=summary,
        latest_news=news,
        social_profiles=SocialProfiles(**_build_social_links(company)),
        sector_trend=sector_trend,
        confidence=confidence,
        last_updated=datetime.datetime.utcnow().isoformat(),
    )

    audit_log("agent_analyze", req_id,
              details={"company": company, "news_count": len(news), "confidence": confidence},
              severity="info")
    return resp


@router.get("/search-news")
async def search_news(
    request: Request,
    q: str = Query(..., min_length=2, max_length=200),
    max_results: int = Query(5, ge=1, le=10),
):
    """Generic web news search. Requires duckduckgo-search."""
    req_id = getattr(request.state, "request_id", "unknown")

    try:
        import duckduckgo_search  # noqa: F401
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Web search unavailable: duckduckgo-search not installed."
        )

    results = await _web_search(q, max_results=max_results)

    audit_log("agent_search_news", req_id,
              details={"query": q, "result_count": len(results)}, severity="info")

    return {
        "query": q,
        "results": results,
        "count": len(results),
    }


@router.get("/social-links/{slug}")
async def get_social_links(request: Request, slug: str):
    """Get social media links for a startup by its database slug."""
    req_id = getattr(request.state, "request_id", "unknown")

    from ..database import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT name, website, linkedin_url, twitter_url, instagram_url, facebook_url "
        "FROM entities WHERE slug = ? AND is_active = 1",
        (slug,),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity = dict(row)
    profiles = _build_social_links(entity["name"], entity.get("website"))

    # Override with stored verified URLs if present
    if entity.get("linkedin_url"):
        ok, _ = validate_url(entity["linkedin_url"], allow_empty=False)
        if ok:
            profiles["linkedin"] = entity["linkedin_url"]
    if entity.get("twitter_url"):
        ok, _ = validate_url(entity["twitter_url"], allow_empty=False)
        if ok:
            profiles["twitter_x"] = entity["twitter_url"]
    if entity.get("instagram_url"):
        ok, _ = validate_url(entity["instagram_url"], allow_empty=False)
        if ok:
            profiles["instagram"] = entity["instagram_url"]
    if entity.get("facebook_url"):
        ok, _ = validate_url(entity["facebook_url"], allow_empty=False)
        if ok:
            profiles["facebook"] = entity["facebook_url"]

    audit_log("agent_social_links", req_id,
              details={"slug": slug, "name": entity["name"]}, severity="info")

    return {
        "slug": slug,
        "name": entity["name"],
        "profiles": profiles,
        "stored": {
            "linkedin": bool(entity.get("linkedin_url")),
            "twitter": bool(entity.get("twitter_url")),
            "instagram": bool(entity.get("instagram_url")),
            "facebook": bool(entity.get("facebook_url")),
        },
    }
