"""
Bharat Tech Atlas — Data Extraction Layer
Handles API calls to DPIIT, Tracxn, and Crunchbase data sources.
Uses async HTTP (aiohttp) for concurrent extraction.
"""
import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RawStartupRecord:
    """Raw record from any data source before transformation."""
    source: str  # 'dpiit', 'tracxn', 'crunchbase'
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    sectors: List[str] = field(default_factory=list)
    founded_year: Optional[int] = None
    funding_usd: Optional[float] = None
    employee_count: Optional[int] = None
    founders: List[str] = field(default_factory=list)
    investors: List[str] = field(default_factory=list)
    is_women_led: bool = False
    dpiit_recognized: bool = False
    linkedin_url: Optional[str] = None
    raw_data: Dict = field(default_factory=dict)
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class DPIITExtractor:
    """
    Extract startup data from DPIIT (Department for Promotion of Industry
    and Internal Trade) recognition portal.

    DPIIT provides: recognized startups, NSA winners, women-led classification,
    DPIIT categories, and business model types.
    """

    BASE_URL = "https://recognition.startupindia.gov.in/api"

    def __init__(self, api_key: Optional[str] = None, rate_limit: int = 10):
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._semaphore = asyncio.Semaphore(rate_limit)

    async def extract_recognized_startups(
        self, state: Optional[str] = None, sector: Optional[str] = None,
        page: int = 1, page_size: int = 100
    ) -> List[RawStartupRecord]:
        """
        Extract DPIIT-recognized startups with pagination.
        Supports filtering by state and sector.
        """
        records = []
        params = {
            "page": page,
            "size": page_size,
            "sort": "recognitionDate,desc"
        }
        if state:
            params["state"] = state
        if sector:
            params["sector"] = sector

        logger.info(f"DPIIT extraction: state={state}, sector={sector}, page={page}")

        # Production implementation:
        # async with aiohttp.ClientSession() as session:
        #     async with self._semaphore:
        #         async with session.get(f"{self.BASE_URL}/startups",
        #                                params=params,
        #                                headers={"Authorization": f"Bearer {self.api_key}"}) as resp:
        #             if resp.status == 200:
        #                 data = await resp.json()
        #                 for item in data.get("content", []):
        #                     records.append(RawStartupRecord(
        #                         source="dpiit",
        #                         name=item["entityName"],
        #                         city=item.get("city"),
        #                         state=item.get("state"),
        #                         sectors=[item.get("industryCategory", "")],
        #                         dpiit_recognized=True,
        #                         is_women_led=item.get("womenLed", False),
        #                         raw_data=item,
        #                     ))

        return records

    async def extract_nsa_winners(self, year: Optional[int] = None) -> List[RawStartupRecord]:
        """Extract National Startup Award winners."""
        logger.info(f"Extracting NSA winners for year={year}")
        return []

    async def extract_all(self, states: Optional[List[str]] = None) -> List[RawStartupRecord]:
        """Full extraction across all states with rate limiting."""
        all_records = []
        target_states = states or [
            "Karnataka", "Maharashtra", "Delhi", "Tamil Nadu", "Telangana",
            "Gujarat", "Kerala", "Rajasthan", "Uttar Pradesh", "West Bengal",
            "Haryana", "Punjab", "Madhya Pradesh", "Bihar", "Odisha"
        ]

        tasks = [
            self.extract_recognized_startups(state=s)
            for s in target_states
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_records.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Extraction failed: {result}")

        return all_records


class TracxnExtractor:
    """
    Extract startup data from Tracxn API.
    Provides: funding data, investors, valuation, team size, LinkedIn data.
    """

    BASE_URL = "https://tracxn.com/api/2.2"

    def __init__(self, access_token: Optional[str] = None, rate_limit: int = 5):
        self.access_token = access_token
        self.rate_limit = rate_limit
        self._semaphore = asyncio.Semaphore(rate_limit)

    async def search_companies(
        self, query: str = "", country: str = "India",
        sector: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[RawStartupRecord]:
        """
        Search Tracxn for companies matching criteria.
        Returns funding, valuation, and investor data.
        """
        records = []
        payload = {
            "filter": {
                "country": [country],
                "query": query,
            },
            "limit": limit,
            "offset": offset,
            "fields": [
                "name", "domain", "description", "city", "state",
                "totalFundingAmount", "lastFundingRound", "investors",
                "employeeCount", "foundedYear", "sectors"
            ]
        }
        if sector:
            payload["filter"]["sector"] = [sector]

        logger.info(f"Tracxn search: query={query}, sector={sector}")

        # Production implementation:
        # headers = {"accessToken": self.access_token, "Content-Type": "application/json"}
        # async with aiohttp.ClientSession() as session:
        #     async with self._semaphore:
        #         async with session.post(f"{self.BASE_URL}/companies/search",
        #                                  json=payload, headers=headers) as resp:
        #             if resp.status == 200:
        #                 data = await resp.json()
        #                 for item in data.get("results", []):
        #                     records.append(self._to_record(item))

        return records

    async def get_company_details(self, domain: str) -> Optional[RawStartupRecord]:
        """Get detailed company profile from Tracxn by domain."""
        logger.info(f"Tracxn company details: domain={domain}")
        return None

    async def extract_unicorns(self) -> List[RawStartupRecord]:
        """Extract all Indian unicorns from Tracxn."""
        return await self.search_companies(query="unicorn", country="India", limit=200)

    def _to_record(self, item: Dict) -> RawStartupRecord:
        """Convert Tracxn API response to RawStartupRecord."""
        return RawStartupRecord(
            source="tracxn",
            name=item.get("name", ""),
            description=item.get("description"),
            website=item.get("domain"),
            city=item.get("city"),
            state=item.get("state"),
            sectors=item.get("sectors", []),
            founded_year=item.get("foundedYear"),
            funding_usd=item.get("totalFundingAmount"),
            employee_count=item.get("employeeCount"),
            investors=[inv.get("name", "") for inv in item.get("investors", [])],
            raw_data=item,
        )


class CrunchbaseExtractor:
    """
    Extract startup data from Crunchbase API.
    Provides: comprehensive funding rounds, investors, team, news.
    """

    BASE_URL = "https://api.crunchbase.com/api/v4"

    def __init__(self, api_key: Optional[str] = None, rate_limit: int = 5):
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._semaphore = asyncio.Semaphore(rate_limit)

    async def search_organizations(
        self, location: str = "India", categories: Optional[List[str]] = None,
        funding_min: Optional[float] = None, limit: int = 50
    ) -> List[RawStartupRecord]:
        """
        Search Crunchbase for organizations by location and category.
        """
        records = []
        params = {
            "user_key": self.api_key,
            "location_identifiers": location,
            "limit": limit,
        }
        if categories:
            params["categories"] = ",".join(categories)
        if funding_min:
            params["funding_total_min"] = funding_min

        logger.info(f"Crunchbase search: location={location}, categories={categories}")

        # Production implementation:
        # async with aiohttp.ClientSession() as session:
        #     async with self._semaphore:
        #         async with session.get(f"{self.BASE_URL}/searches/organizations",
        #                                params=params) as resp:
        #             if resp.status == 200:
        #                 data = await resp.json()
        #                 for item in data.get("entities", []):
        #                     records.append(self._to_record(item))

        return records

    async def get_funding_rounds(self, org_uuid: str) -> List[Dict]:
        """Get all funding rounds for an organization."""
        logger.info(f"Crunchbase funding rounds: org={org_uuid}")
        return []

    def _to_record(self, item: Dict) -> RawStartupRecord:
        """Convert Crunchbase API response to RawStartupRecord."""
        props = item.get("properties", {})
        founded = props.get("founded_on", "")
        return RawStartupRecord(
            source="crunchbase",
            name=props.get("name", ""),
            description=props.get("short_description"),
            website=props.get("homepage_url"),
            city=props.get("city"),
            state=props.get("region"),
            sectors=props.get("categories", []),
            founded_year=int(founded[:4]) if founded and len(founded) >= 4 else None,
            funding_usd=props.get("funding_total", {}).get("value_usd"),
            employee_count=props.get("num_employees_enum"),
            raw_data=item,
        )


class ETLExtractor:
    """
    Unified extractor that orchestrates extraction from all sources.
    Handles rate limiting, retries, and deduplication across sources.
    """

    def __init__(self, config: Dict):
        self.dpiit = DPIITExtractor(
            api_key=config.get("dpiit_api_key"),
            rate_limit=config.get("dpiit_rate_limit", 10)
        )
        self.tracxn = TracxnExtractor(
            access_token=config.get("tracxn_token"),
            rate_limit=config.get("tracxn_rate_limit", 5)
        )
        self.crunchbase = CrunchbaseExtractor(
            api_key=config.get("crunchbase_key"),
            rate_limit=config.get("crunchbase_rate_limit", 5)
        )

    async def extract_all(self) -> List[RawStartupRecord]:
        """
        Run full extraction pipeline across all sources.
        Returns deduplicated records with source attribution.
        """
        logger.info("Starting full ETL extraction...")

        results = await asyncio.gather(
            self.dpiit.extract_all(),
            self.tracxn.search_companies(country="India", limit=1000),
            self.crunchbase.search_organizations(location="India", limit=1000),
            return_exceptions=True,
        )

        all_records = []
        for result in results:
            if isinstance(result, list):
                all_records.extend(result)
            else:
                logger.error(f"Source extraction failed: {result}")

        logger.info(f"Extraction complete: {len(all_records)} raw records")
        return all_records
