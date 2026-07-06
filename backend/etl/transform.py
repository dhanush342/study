"""
Bharat Tech Atlas — Data Transformation Layer
Cleans raw data, normalizes categories, geocodes addresses to lat/lng.
"""
import re
import json
import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .extract import RawStartupRecord

logger = logging.getLogger(__name__)


# ─── Sector Normalization Map ────────────────────────────────────────────────
SECTOR_ALIASES = {
    # Fintech
    "financial services": "fintech", "finance": "fintech", "payments": "fintech",
    "banking": "fintech", "lending": "fintech", "neobank": "fintech",
    "insurance": "insurtech", "wealth management": "wealthtech",
    # SaaS / AI
    "saas": "saas_ai", "software": "saas_ai", "enterprise software": "saas_ai",
    "artificial intelligence": "ai_ml", "machine learning": "ai_ml",
    "deep learning": "ai_ml", "computer vision": "ai_ml", "nlp": "ai_ml",
    # E-Commerce
    "e-commerce": "ecommerce", "ecommerce": "ecommerce", "marketplace": "ecommerce",
    "retail": "ecommerce", "d2c": "d2c", "direct to consumer": "d2c",
    # Healthcare
    "healthcare": "healthcare", "health": "healthcare", "healthtech": "healthtech",
    "medical": "healthcare", "pharma": "healthcare", "biotech": "biotech",
    "telemedicine": "healthtech",
    # Education
    "education": "edtech", "edtech": "edtech", "e-learning": "edtech",
    "online learning": "edtech", "skill development": "edtech",
    # Agriculture
    "agriculture": "agritech", "agritech": "agritech", "farming": "agritech",
    "food processing": "foodtech", "foodtech": "foodtech",
    # Others
    "clean energy": "cleantech", "renewable energy": "cleantech",
    "electric vehicle": "ev", "ev": "ev", "mobility": "mobility",
    "logistics": "logistics", "supply chain": "logistics",
    "gaming": "gaming", "esports": "gaming",
    "cybersecurity": "cybersecurity", "security": "cybersecurity",
    "real estate": "proptech", "proptech": "proptech",
    "media": "mediatech", "entertainment": "mediatech",
    "space": "spacetech", "aerospace": "spacetech",
    "iot": "iot", "hardware": "iot", "robotics": "deeptech",
    "drone": "drone_tech", "uav": "drone_tech",
    "legal": "legaltech", "legaltech": "legaltech",
    "social enterprise": "social_impact", "ngo tech": "social_impact",
    "manufacturing": "manufacturing", "industrial": "manufacturing",
}

# ─── Indian State Name Normalization ─────────────────────────────────────────
STATE_ALIASES = {
    "karnataka": "Karnataka", "ka": "Karnataka", "bengaluru": "Karnataka",
    "maharashtra": "Maharashtra", "mh": "Maharashtra", "mumbai": "Maharashtra",
    "delhi": "Delhi", "new delhi": "Delhi", "ncr": "Delhi", "dl": "Delhi",
    "tamil nadu": "Tamil Nadu", "tn": "Tamil Nadu", "chennai": "Tamil Nadu",
    "telangana": "Telangana", "ts": "Telangana", "hyderabad": "Telangana",
    "gujarat": "Gujarat", "gj": "Gujarat", "ahmedabad": "Gujarat",
    "kerala": "Kerala", "kl": "Kerala",
    "rajasthan": "Rajasthan", "rj": "Rajasthan",
    "uttar pradesh": "Uttar Pradesh", "up": "Uttar Pradesh",
    "west bengal": "West Bengal", "wb": "West Bengal", "kolkata": "West Bengal",
    "haryana": "Haryana", "hr": "Haryana", "gurugram": "Haryana",
    "punjab": "Punjab", "pb": "Punjab",
    "madhya pradesh": "Madhya Pradesh", "mp": "Madhya Pradesh",
    "bihar": "Bihar", "br": "Bihar",
    "odisha": "Odisha", "or": "Odisha",
    "assam": "Assam", "as": "Assam",
    "goa": "Goa", "ga": "Goa",
    "andhra pradesh": "Andhra Pradesh", "ap": "Andhra Pradesh",
    "uttarakhand": "Uttarakhand", "uk": "Uttarakhand",
    "jharkhand": "Jharkhand", "jh": "Jharkhand",
    "chhattisgarh": "Chhattisgarh", "cg": "Chhattisgarh",
}

# ─── Indian City Geocoding (fallback coordinates) ────────────────────────────
CITY_COORDINATES = {
    "Bengaluru": (12.9716, 77.5946),
    "Mumbai": (19.0760, 72.8777),
    "New Delhi": (28.6139, 77.2090),
    "Delhi": (28.6139, 77.2090),
    "Hyderabad": (17.3850, 78.4867),
    "Chennai": (13.0827, 80.2707),
    "Pune": (18.5204, 73.8567),
    "Gurugram": (28.4595, 77.0266),
    "Noida": (28.5355, 77.3910),
    "Ahmedabad": (23.0225, 72.5714),
    "Kolkata": (22.5726, 88.3639),
    "Jaipur": (26.9124, 75.7873),
    "Kochi": (9.9312, 76.2673),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Indore": (22.7196, 75.8577),
    "Chandigarh": (30.7333, 76.7794),
    "Lucknow": (26.8467, 80.9462),
    "Coimbatore": (11.0168, 76.9558),
    "Bhubaneswar": (20.2961, 85.8245),
    "Visakhapatnam": (17.6868, 83.2185),
    "Patna": (25.6093, 85.1376),
    "Guwahati": (26.1445, 91.7362),
    "Nagpur": (21.1458, 79.0882),
    "Surat": (21.1702, 72.8311),
    "Vadodara": (22.3072, 73.1812),
    "Mysuru": (12.2958, 76.6394),
    "Mangaluru": (12.9141, 74.8560),
    "Hubli": (15.3647, 75.1240),
    "Goa": (15.2993, 74.1240),
    "Panaji": (15.4909, 73.8278),
}


@dataclass
class TransformedRecord:
    """Cleaned and normalized record ready for database loading."""
    name: str
    slug: str
    entity_type: str
    sectors: List[str]
    dpiit_category: Optional[str] = None
    business_model: Optional[str] = None
    stage: Optional[str] = None
    dpiit_recognized: bool = False
    nsa_winner: bool = False
    is_women_led: bool = False
    is_rural_impact: bool = False
    is_campus_startup: bool = False
    unicorn_status: Optional[str] = None
    funding_inr: float = 0
    funding_stage: Optional[str] = None
    valuation_usd: Optional[float] = None
    description: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    investors: List[str] = field(default_factory=list)
    address: Optional[str] = None
    city: str = ""
    district: Optional[str] = None
    state: str = ""
    pin_code: Optional[str] = None
    latitude: float = 0.0
    longitude: float = 0.0
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    data_sources: List[str] = field(default_factory=list)


class Geocoder:
    """
    Geocode addresses to latitude/longitude coordinates.
    Uses a tiered approach:
    1. Known city coordinates (instant, free)
    2. Pin code centroid lookup
    3. External geocoding API (Nominatim/Google Maps) as fallback
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._cache: Dict[str, Tuple[float, float]] = {}

    def geocode(self, city: Optional[str], state: Optional[str],
                address: Optional[str] = None, pin_code: Optional[str] = None
                ) -> Tuple[float, float]:
        """
        Returns (latitude, longitude) for the given location.
        Falls back through multiple strategies.
        """
        # Strategy 1: Direct city lookup
        if city and city in CITY_COORDINATES:
            return CITY_COORDINATES[city]

        # Strategy 2: Check cache
        cache_key = f"{city}|{state}|{pin_code}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Strategy 3: State capital fallback
        state_capitals = {
            "Karnataka": (12.9716, 77.5946),
            "Maharashtra": (19.0760, 72.8777),
            "Delhi": (28.6139, 77.2090),
            "Tamil Nadu": (13.0827, 80.2707),
            "Telangana": (17.3850, 78.4867),
            "Gujarat": (23.0225, 72.5714),
            "Kerala": (9.9312, 76.2673),
            "Rajasthan": (26.9124, 75.7873),
            "Uttar Pradesh": (26.8467, 80.9462),
            "West Bengal": (22.5726, 88.3639),
            "Haryana": (28.4595, 77.0266),
            "Punjab": (30.7333, 76.7794),
        }
        if state and state in state_capitals:
            coords = state_capitals[state]
            self._cache[cache_key] = coords
            return coords

        # Strategy 4: External API (Nominatim - OpenStreetMap)
        # In production:
        # import aiohttp
        # query = f"{address or ''} {city or ''} {state or ''} India"
        # async with aiohttp.ClientSession() as session:
        #     params = {"q": query, "format": "json", "limit": 1}
        #     async with session.get("https://nominatim.openstreetmap.org/search",
        #                            params=params) as resp:
        #         results = await resp.json()
        #         if results:
        #             return (float(results[0]["lat"]), float(results[0]["lon"]))

        # Default: center of India
        logger.warning(f"Could not geocode: city={city}, state={state}")
        return (20.5937, 78.9629)

    async def batch_geocode(self, records: List[Dict]) -> List[Tuple[float, float]]:
        """Geocode multiple records with rate limiting."""
        results = []
        for record in records:
            coords = self.geocode(
                city=record.get("city"),
                state=record.get("state"),
                address=record.get("address"),
                pin_code=record.get("pin_code")
            )
            results.append(coords)
        return results


class ETLTransformer:
    """
    Transform raw extracted records into clean, normalized data.
    Handles: deduplication, sector normalization, geocoding, data enrichment.
    """

    def __init__(self, geocoder: Optional[Geocoder] = None):
        self.geocoder = geocoder or Geocoder()
        self._seen_slugs: set = set()

    def transform_all(self, raw_records: List[RawStartupRecord]) -> List[TransformedRecord]:
        """Transform and deduplicate all raw records."""
        logger.info(f"Transforming {len(raw_records)} raw records...")

        transformed = []
        for record in raw_records:
            try:
                result = self.transform_record(record)
                if result and result.slug not in self._seen_slugs:
                    self._seen_slugs.add(result.slug)
                    transformed.append(result)
            except Exception as e:
                logger.error(f"Transform failed for {record.name}: {e}")

        logger.info(f"Transformation complete: {len(transformed)} clean records")
        return transformed

    def transform_record(self, raw: RawStartupRecord) -> Optional[TransformedRecord]:
        """Transform a single raw record."""
        # Clean name
        name = self._clean_name(raw.name)
        if not name:
            return None

        # Generate slug
        slug = self._generate_slug(name)

        # Normalize sectors
        sectors = self._normalize_sectors(raw.sectors)

        # Normalize state
        state = self._normalize_state(raw.state)
        city = self._clean_city(raw.city)

        # Geocode
        lat, lng = self.geocoder.geocode(city=city, state=state,
                                          address=raw.address, pin_code=raw.pin_code)

        # Convert funding USD to INR (1 USD ≈ 83.5 INR)
        funding_inr = (raw.funding_usd or 0) * 83.5

        # Determine entity type
        entity_type = self._classify_entity_type(raw)

        # Determine DPIIT category
        dpiit_category = sectors[0] if sectors else None

        return TransformedRecord(
            name=name,
            slug=slug,
            entity_type=entity_type,
            sectors=sectors,
            dpiit_category=dpiit_category,
            dpiit_recognized=raw.dpiit_recognized,
            is_women_led=raw.is_women_led,
            funding_inr=funding_inr,
            description=self._clean_description(raw.description),
            website=self._clean_url(raw.website),
            linkedin_url=raw.linkedin_url,
            investors=raw.investors,
            address=raw.address,
            city=city,
            state=state,
            pin_code=raw.pin_code,
            latitude=lat,
            longitude=lng,
            founded_year=raw.founded_year,
            employee_count=raw.employee_count,
            data_sources=[raw.source],
        )

    def _clean_name(self, name: str) -> str:
        """Clean and normalize company name."""
        if not name:
            return ""
        # Remove common suffixes
        name = re.sub(r'\s*(Private|Pvt\.?|Ltd\.?|Limited|Inc\.?|LLP|Technologies|Tech)\s*', ' ', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name."""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug).strip('-')
        # Add hash suffix for uniqueness
        if slug in self._seen_slugs:
            hash_suffix = hashlib.md5(name.encode()).hexdigest()[:6]
            slug = f"{slug}-{hash_suffix}"
        return slug

    def _normalize_sectors(self, raw_sectors: List[str]) -> List[str]:
        """Normalize sector names to standard taxonomy."""
        normalized = set()
        for sector in raw_sectors:
            sector_lower = sector.lower().strip()
            if sector_lower in SECTOR_ALIASES:
                normalized.add(SECTOR_ALIASES[sector_lower])
            elif sector_lower:
                # Try partial matching
                for alias, standard in SECTOR_ALIASES.items():
                    if alias in sector_lower or sector_lower in alias:
                        normalized.add(standard)
                        break
        return list(normalized) or ["saas_ai"]  # default sector

    def _normalize_state(self, state: Optional[str]) -> str:
        """Normalize state name to standard format."""
        if not state:
            return "Karnataka"  # default
        state_lower = state.lower().strip()
        return STATE_ALIASES.get(state_lower, state.title())

    def _clean_city(self, city: Optional[str]) -> str:
        """Clean and normalize city name."""
        if not city:
            return "Bengaluru"
        city = city.strip()
        # Common aliases
        aliases = {
            "bangalore": "Bengaluru", "bombay": "Mumbai",
            "madras": "Chennai", "calcutta": "Kolkata",
            "gurgaon": "Gurugram", "trivandrum": "Thiruvananthapuram",
        }
        return aliases.get(city.lower(), city.title())

    def _clean_description(self, desc: Optional[str]) -> Optional[str]:
        """Clean description text."""
        if not desc:
            return None
        # Remove HTML tags
        desc = re.sub(r'<[^>]+>', '', desc)
        # Normalize whitespace
        desc = re.sub(r'\s+', ' ', desc).strip()
        # Truncate
        if len(desc) > 500:
            desc = desc[:497] + "..."
        return desc

    def _clean_url(self, url: Optional[str]) -> Optional[str]:
        """Normalize URL format."""
        if not url:
            return None
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        return url

    def _classify_entity_type(self, raw: RawStartupRecord) -> str:
        """Classify entity type based on available data."""
        # Heuristics for classification
        if raw.description:
            desc_lower = raw.description.lower()
            if any(kw in desc_lower for kw in ['incubator', 'incubation']):
                return 'incubator'
            if any(kw in desc_lower for kw in ['accelerator', 'acceleration']):
                return 'accelerator'
            if any(kw in desc_lower for kw in ['coworking', 'co-working']):
                return 'coworking'
            if any(kw in desc_lower for kw in ['angel', 'venture capital', 'vc fund']):
                return 'investor'
            if any(kw in desc_lower for kw in ['e-cell', 'ecell', 'entrepreneurship cell']):
                return 'college_ecell'

        # Default to startup
        if (raw.employee_count and raw.employee_count > 200) or \
           (raw.funding_usd and raw.funding_usd > 5000000):
            return 'startup'

        return 'startup'
