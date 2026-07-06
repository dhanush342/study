"""
Bharat Tech Atlas — Data Enrichment API
v3.2: Config-driven enrichment. If API keys are absent, endpoints return
structured empty data with configured=false instead of pretending to enrich.
"""
import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
GITHUB_API_BASE = "https://api.github.com"
GOOGLE_MAPS_BASE = "https://maps.googleapis.com/maps/api"


class LinkedInEnricher:
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.environ.get("LINKEDIN_TOKEN")
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = timedelta(hours=24)

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)

    async def enrich_company(self, company_name: str, linkedin_url: Optional[str] = None) -> Dict:
        cache_key = hashlib.md5((company_name + str(linkedin_url)).encode()).hexdigest()
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.utcnow() - cached.get("_cached_at", datetime.min) < self._cache_ttl:
                return cached

        enriched = {
            "source": "linkedin", "company_name": company_name, "linkedin_url": linkedin_url,
            "team_size": None, "industry": None, "specialties": [], "headquarters": None,
            "description": None, "founded_year": None, "key_people": [],
            "enriched_at": datetime.utcnow().isoformat(), "configured": self.is_configured,
        }
        if not self.is_configured:
            return enriched

        try:
            import aiohttp
            headers = {"Authorization": f"Bearer {self.access_token}"}
            vanity = self._extract_vanity(linkedin_url)
            if vanity:
                async with aiohttp.ClientSession() as session:
                    url = f"{LINKEDIN_API_BASE}/organizations?q=vanityName&vanityName={vanity}"
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            org = data.get("elements", [{}])[0]
                            enriched["team_size"] = org.get("staffCountRange", {}).get("start")
                            enriched["industry"] = org.get("localizedName")
                            enriched["specialties"] = org.get("specialties", [])
                            enriched["description"] = org.get("localizedDescription")
        except Exception as e:
            logger.warning("LinkedIn enrichment failed for %s: %s", company_name, e)

        self._cache[cache_key] = {**enriched, "_cached_at": datetime.utcnow()}
        return enriched

    async def get_key_people(self, company_linkedin_url: str) -> List[Dict]:
        return []

    def _extract_vanity(self, url: Optional[str]) -> str:
        if not url:
            return ""
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else ""


class GitHubEnricher:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    async def enrich_company(self, org_name: str, github_url: Optional[str] = None) -> Dict:
        enriched = {
            "source": "github", "org_name": org_name, "github_url": github_url,
            "public_repos": 0, "total_stars": 0, "top_languages": [],
            "recent_activity": False, "contributors": 0, "repositories": [],
            "enriched_at": datetime.utcnow().isoformat(), "configured": self.is_configured,
        }
        if not self.is_configured:
            return enriched
        try:
            import aiohttp
            org = self._extract_org(github_url) or org_name.lower().replace(" ", "")
            headers = {"Authorization": f"token {self.token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{GITHUB_API_BASE}/orgs/{org}", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        enriched["public_repos"] = data.get("public_repos", 0)
                async with session.get(f"{GITHUB_API_BASE}/orgs/{org}/repos?sort=stars&per_page=5", headers=headers) as resp:
                    if resp.status == 200:
                        repos = await resp.json()
                        enriched["total_stars"] = sum(r.get("stargazers_count", 0) for r in repos)
                        enriched["top_languages"] = list({r.get("language") for r in repos if r.get("language")})
                        enriched["repositories"] = [
                            {"name": r["name"], "stars": r["stargazers_count"], "language": r.get("language")}
                            for r in repos[:5]
                        ]
        except Exception as e:
            logger.warning("GitHub enrichment failed for %s: %s", org_name, e)
        return enriched

    def _extract_org(self, url: Optional[str]) -> str:
        if not url:
            return ""
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else ""


class GoogleMapsEnricher:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_MAPS_KEY")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def enrich_location(self, company_name: str, city: str, state: str) -> Dict:
        enriched = {
            "source": "google_maps", "company_name": company_name,
            "verified_lat": None, "verified_lng": None, "formatted_address": None,
            "place_rating": None, "total_reviews": 0, "business_status": None,
            "phone": None, "google_maps_url": None, "photos": [],
            "enriched_at": datetime.utcnow().isoformat(), "configured": self.is_configured,
        }
        if not self.is_configured:
            return enriched
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                params = {
                    "input": f"{company_name} {city} {state} India",
                    "inputtype": "textquery",
                    "fields": "place_id,formatted_address,geometry,name,rating,user_ratings_total",
                    "key": self.api_key,
                }
                async with session.get(f"{GOOGLE_MAPS_BASE}/place/findplacefromtext/json", params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            place = candidates[0]
                            enriched["verified_lat"] = place["geometry"]["location"]["lat"]
                            enriched["verified_lng"] = place["geometry"]["location"]["lng"]
                            enriched["formatted_address"] = place.get("formatted_address")
                            enriched["place_rating"] = place.get("rating")
                            enriched["total_reviews"] = place.get("user_ratings_total", 0)
        except Exception as e:
            logger.warning("Google Maps enrichment failed for %s: %s", company_name, e)
        return enriched

    async def batch_geocode(self, addresses: List[Dict]) -> List[Tuple[float, float]]:
        results = []
        for addr in addresses:
            enriched = await self.enrich_location(addr.get("name", ""), addr.get("city", ""), addr.get("state", ""))
            if enriched["verified_lat"] and enriched["verified_lng"]:
                results.append((enriched["verified_lat"], enriched["verified_lng"]))
            else:
                results.append(None)
        return results


class DataEnrichmentService:
    def __init__(self):
        self.linkedin = LinkedInEnricher()
        self.github = GitHubEnricher()
        self.google_maps = GoogleMapsEnricher()
        self._enrichment_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    @property
    def configured_sources(self) -> List[str]:
        sources = []
        if self.linkedin.is_configured:
            sources.append("linkedin")
        if self.github.is_configured:
            sources.append("github")
        if self.google_maps.is_configured:
            sources.append("google_maps")
        return sources

    async def enrich_entity(self, entity: Dict) -> Dict:
        tasks = [self.linkedin.enrich_company(entity.get("name", ""), entity.get("linkedin_url"))]
        sectors = entity.get("sectors", [])
        if isinstance(sectors, str):
            try:
                sectors = json.loads(sectors)
            except Exception:
                sectors = []
        if any(s in ["saas_ai", "ai_ml", "deeptech", "cybersecurity", "iot", "saas"] for s in sectors):
            tasks.append(self.github.enrich_company(entity.get("name", "")))
        tasks.append(self.google_maps.enrich_location(entity.get("name", ""), entity.get("city", ""), entity.get("state", "")))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged = {"enrichments": [], "enriched_at": datetime.utcnow().isoformat(), "configured_sources": self.configured_sources}
        for result in results:
            if isinstance(result, dict):
                merged["enrichments"].append(result)
                if result.get("source") == "linkedin":
                    if result.get("team_size"):
                        merged["linkedin_team_size"] = result["team_size"]
                    if result.get("industry"):
                        merged["linkedin_industry"] = result["industry"]
                    if result.get("specialties"):
                        merged["linkedin_specialties"] = json.dumps(result["specialties"])
                elif result.get("source") == "google_maps":
                    if result.get("verified_lat"):
                        merged["verified_latitude"] = result["verified_lat"]
                        merged["verified_longitude"] = result["verified_lng"]
                    if result.get("formatted_address"):
                        merged["verified_address"] = result["formatted_address"]
        return merged

    async def start_background_enrichment(self, db_path: str, batch_size: int = 10):
        self._running = True
        while self._running:
            await asyncio.sleep(300)

    def stop(self):
        self._running = False
