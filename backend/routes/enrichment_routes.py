"""
Bharat Tech Atlas — Enrichment API Routes
Real-time data enrichment from LinkedIn, GitHub, Google Maps.
v3.2: Returns honest status about whether enrichment is configured.
"""
from fastapi import APIRouter, HTTPException
import json

router = APIRouter()


@router.get("/profile/{slug}")
async def get_enriched_profile(slug: str):
    """Get fully enriched entity profile. Returns stored data + enrichment status."""
    from ..database import get_db
    from ..enrichment import DataEnrichmentService

    conn = get_db()
    row = conn.execute("SELECT * FROM entities WHERE slug = ? AND is_active = 1", (slug,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity = dict(row)
    for field in ["sectors", "investors", "funding_rounds", "data_sources"]:
        if field in entity and isinstance(entity[field], str):
            try:
                entity[field] = json.loads(entity[field])
            except Exception:
                entity[field] = []

    service = DataEnrichmentService()
    enriched = await service.enrich_entity(entity)

    return {
        "entity": entity,
        "enrichment": enriched,
        "sources": {
            "linkedin": {"configured": service.linkedin.is_configured, "has_url": bool(entity.get("linkedin_url"))},
            "github": {"configured": service.github.is_configured},
            "google_maps": {"configured": service.google_maps.is_configured},
        },
    }


@router.get("/linkedin/{slug}")
async def get_linkedin_data(slug: str):
    """Get LinkedIn enrichment for an entity."""
    from ..database import get_db
    from ..enrichment import LinkedInEnricher

    conn = get_db()
    row = conn.execute(
        "SELECT name, linkedin_url, linkedin_team_size, linkedin_industry, linkedin_specialties FROM entities WHERE slug = ? AND is_active = 1",
        (slug,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity = dict(row)
    enricher = LinkedInEnricher()
    live_data = await enricher.enrich_company(entity["name"], entity.get("linkedin_url"))

    return {
        "configured": enricher.is_configured,
        "stored": {
            "team_size": entity.get("linkedin_team_size"),
            "industry": entity.get("linkedin_industry"),
            "specialties": entity.get("linkedin_specialties"),
        },
        "live": live_data,
    }


@router.get("/github/{slug}")
async def get_github_data(slug: str):
    """Get GitHub activity data for a tech startup."""
    from ..database import get_db
    from ..enrichment import GitHubEnricher

    conn = get_db()
    row = conn.execute(
        "SELECT name, website, sectors FROM entities WHERE slug = ? AND is_active = 1",
        (slug,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity = dict(row)
    enricher = GitHubEnricher()
    data = await enricher.enrich_company(entity["name"])

    return {"entity_name": entity["name"], "configured": enricher.is_configured, "github": data}


@router.get("/location/{slug}")
async def get_verified_location(slug: str):
    """Get Google Maps verified location for an entity."""
    from ..database import get_db
    from ..enrichment import GoogleMapsEnricher

    conn = get_db()
    row = conn.execute(
        "SELECT name, city, state, latitude, longitude, address FROM entities WHERE slug = ? AND is_active = 1",
        (slug,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity = dict(row)
    enricher = GoogleMapsEnricher()
    maps_data = await enricher.enrich_location(entity["name"], entity["city"], entity["state"])

    return {
        "entity_name": entity["name"],
        "configured": enricher.is_configured,
        "stored_location": {
            "lat": entity["latitude"],
            "lng": entity["longitude"],
            "city": entity["city"],
            "state": entity["state"],
            "address": entity.get("address"),
        },
        "google_maps": maps_data,
    }
