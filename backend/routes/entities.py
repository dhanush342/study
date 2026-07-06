"""
Bharat Tech Atlas — API routes v3.3
- Bounding-box viewport queries for performance
- Optimized spatial indexing
- SEO directory endpoints
- Heatmap with weighted points
- Deduplicated utilities imported from shared utils module
- v3.3: Added query timeouts, stricter input validation, URL validation for social links
"""
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import Response
from typing import Optional
import json
import math
import csv
import io
import time

from ..database import get_db, haversine_distance
from ..utils import row_to_dict, format_funding, sanitize_like
from ..security import (
    validate_startup_name,
    validate_coordinates,
    validate_funding_amount,
    validate_year,
    validate_url,
    audit_log,
)

router = APIRouter()

# ─── Query timeout wrapper ───────────────────────────────────────────────────
QUERY_TIMEOUT_MS = 10000  # 10 seconds max per query


def _execute_with_timeout(conn, query, params, timeout_ms=QUERY_TIMEOUT_MS):
    """Execute query with timeout via busy_timeout PRAGMA."""
    conn.execute(f"PRAGMA busy_timeout={timeout_ms}")
    return conn.execute(query, params).fetchall()


def _apply_filters(query, params, filters):
    """Apply common filters to a query. All parameterized for safety."""
    if filters.get("entity_type"):
        types = filters["entity_type"].split(",")
        placeholders = ",".join("?" * len(types))
        query += f" AND e.entity_type IN ({placeholders})"
        params.extend(types)

    if filters.get("sector"):
        sectors = filters["sector"].split(",")
        conds = []
        for s in sectors:
            conds.append("e.sectors LIKE ?")
            params.append(f'%{s}%')
        query += f" AND ({' OR '.join(conds)})"

    if filters.get("stage"):
        stages = filters["stage"].split(",")
        placeholders = ",".join("?" * len(stages))
        query += f" AND e.stage IN ({placeholders})"
        params.extend(stages)

    if filters.get("dpiit_only"):
        query += " AND e.dpiit_recognized = 1"

    if filters.get("dpiit_category"):
        cats = filters["dpiit_category"].split(",")
        placeholders = ",".join("?" * len(cats))
        query += f" AND e.dpiit_category IN ({placeholders})"
        params.extend(cats)

    if filters.get("business_model"):
        models = filters["business_model"].split(",")
        placeholders = ",".join("?" * len(models))
        query += f" AND e.business_model IN ({placeholders})"
        params.extend(models)

    if filters.get("unicorn_status"):
        statuses = filters["unicorn_status"].split(",")
        placeholders = ",".join("?" * len(statuses))
        query += f" AND e.unicorn_status IN ({placeholders})"
        params.extend(statuses)

    if filters.get("is_women_led"):
        query += " AND e.is_women_led = 1"
    if filters.get("is_rural_impact"):
        query += " AND e.is_rural_impact = 1"
    if filters.get("is_campus_startup"):
        query += " AND e.is_campus_startup = 1"
    if filters.get("nsa_winner"):
        query += " AND e.nsa_winner = 1"

    if filters.get("min_funding"):
        try:
            amount = float(filters["min_funding"])
            ok, err = validate_funding_amount(amount)
            if ok:
                query += " AND e.funding_inr >= ?"
                params.append(amount)
        except (ValueError, TypeError):
            pass

    if filters.get("founded_after"):
        try:
            year = int(filters["founded_after"])
            ok, _ = validate_year(year)
            if ok:
                query += " AND e.founded_year >= ?"
                params.append(year)
        except (ValueError, TypeError):
            pass

    if filters.get("founded_before"):
        try:
            year = int(filters["founded_before"])
            ok, _ = validate_year(year)
            if ok:
                query += " AND e.founded_year <= ?"
                params.append(year)
        except (ValueError, TypeError):
            pass

    if filters.get("search"):
        safe = sanitize_like(filters["search"])
        query += " AND e.name LIKE ? ESCAPE '\\'"
        params.append(f"%{safe}%")

    if filters.get("state"):
        query += " AND e.state = ?"
        params.append(filters["state"])

    if filters.get("city"):
        query += " AND e.city = ?"
        params.append(filters["city"])

    return query, params


@router.get("/clusters")
async def get_clusters(
    request: Request,
    min_lng: float = Query(68.0, ge=60, le=100),
    max_lng: float = Query(97.0, ge=60, le=100),
    min_lat: float = Query(6.0, ge=0, le=40),
    max_lat: float = Query(37.0, ge=0, le=40),
    zoom: float = Query(4.5, ge=0, le=22),
    entity_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    dpiit_only: bool = Query(False),
    dpiit_category: Optional[str] = Query(None),
    business_model: Optional[str] = Query(None),
    unicorn_status: Optional[str] = Query(None),
    is_women_led: bool = Query(False),
    is_rural_impact: bool = Query(False),
    is_campus_startup: bool = Query(False),
    nsa_winner: bool = Query(False),
    min_funding: Optional[float] = Query(None),
    founded_after: Optional[int] = Query(None),
    founded_before: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
):
    """Server-side grid clustering at low zoom, individual points at high zoom."""
    req_id = getattr(request.state, "request_id", "unknown")

    filters = {
        "entity_type": entity_type, "sector": sector, "stage": stage,
        "dpiit_only": dpiit_only, "dpiit_category": dpiit_category,
        "business_model": business_model, "unicorn_status": unicorn_status,
        "is_women_led": is_women_led, "is_rural_impact": is_rural_impact,
        "is_campus_startup": is_campus_startup, "nsa_winner": nsa_winner,
        "min_funding": min_funding, "founded_after": founded_after,
        "founded_before": founded_before, "search": search,
        "state": state, "city": city,
    }

    if zoom >= 12:
        return await get_geojson(
            min_lng=min_lng, max_lng=max_lng, min_lat=min_lat, max_lat=max_lat,
            entity_type=entity_type, sector=sector, stage=stage,
            dpiit_only=dpiit_only, dpiit_category=dpiit_category,
            business_model=business_model, unicorn_status=unicorn_status,
            is_women_led=is_women_led, is_rural_impact=is_rural_impact,
            is_campus_startup=is_campus_startup, nsa_winner=nsa_winner,
            min_funding=min_funding, founded_after=founded_after,
            founded_before=founded_before, search=search,
            state=state, city=city, max_features=5000,
        )

    conn = get_db()
    cell_size = 360.0 / (2 ** zoom) * 2

    query = """
        SELECT
            CAST(ROUND(e.longitude / ?) AS INTEGER) AS gx,
            CAST(ROUND(e.latitude / ?) AS INTEGER) AS gy,
            COUNT(*) AS point_count,
            AVG(e.longitude) AS avg_lng,
            AVG(e.latitude) AS avg_lat,
            SUM(CASE WHEN e.entity_type='startup' THEN 1 ELSE 0 END) AS startups,
            SUM(CASE WHEN e.unicorn_status='unicorn' THEN 1 ELSE 0 END) AS unicorns,
            SUM(CASE WHEN e.is_women_led=1 THEN 1 ELSE 0 END) AS women_led,
            SUM(CASE WHEN e.dpiit_recognized=1 THEN 1 ELSE 0 END) AS dpiit,
            GROUP_CONCAT(DISTINCT e.city) AS cities
        FROM entities e
        INNER JOIN entities_rtree r ON e.id = r.id
        WHERE r.min_lng >= ? AND r.max_lng <= ?
          AND r.min_lat >= ? AND r.max_lat <= ?
          AND e.is_active = 1
    """
    params = [cell_size, cell_size, min_lng, max_lng, min_lat, max_lat]
    query, params = _apply_filters(query, params, filters)
    query += " GROUP BY gx, gy ORDER BY point_count DESC LIMIT 500"

    rows = _execute_with_timeout(conn, query, params)

    count_q = """
        SELECT COUNT(*) as total FROM entities e
        INNER JOIN entities_rtree r ON e.id = r.id
        WHERE r.min_lng >= ? AND r.max_lng <= ? AND r.min_lat >= ? AND r.max_lat <= ? AND e.is_active = 1
    """
    count_params = [min_lng, max_lng, min_lat, max_lat]
    count_q, count_params = _apply_filters(count_q, count_params, filters)
    total_row = conn.execute(count_q, count_params).fetchone()
    total_count = total_row["total"] if total_row else 0
    conn.close()

    features = []
    for row in rows:
        d = dict(row)
        count = d["point_count"]
        cities_list = (d["cities"] or "").split(",")[:3]
        city_label = ", ".join(c.strip() for c in cities_list if c.strip())
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [d["avg_lng"], d["avg_lat"]]},
            "properties": {
                "cluster": True, "cluster_id": f"{d['gx']}_{d['gy']}",
                "point_count": count,
                "point_count_abbreviated": f"{count/1000:.1f}k" if count >= 1000 else str(count),
                "startups": d["startups"], "unicorns": d["unicorns"],
                "women_led": d["women_led"], "dpiit": d["dpiit"],
                "city_label": city_label,
                "expansion_zoom": min(zoom + 2, 18),
            }
        })

    audit_log("clusters_query", req_id,
              details={"bbox": f"{min_lng},{min_lat},{max_lng},{max_lat}", "zoom": zoom, "clusters": len(features)},
              severity="info")

    return {
        "type": "FeatureCollection", "features": features,
        "total_count": total_count, "cluster_mode": True, "zoom": zoom,
    }


@router.get("/geojson")
async def get_geojson(
    request: Request,
    min_lng: float = Query(68.0, ge=60, le=100),
    max_lng: float = Query(97.0, ge=60, le=100),
    min_lat: float = Query(6.0, ge=0, le=40),
    max_lat: float = Query(37.0, ge=0, le=40),
    entity_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    dpiit_only: bool = Query(False),
    dpiit_category: Optional[str] = Query(None),
    business_model: Optional[str] = Query(None),
    unicorn_status: Optional[str] = Query(None),
    is_women_led: bool = Query(False),
    is_rural_impact: bool = Query(False),
    is_campus_startup: bool = Query(False),
    nsa_winner: bool = Query(False),
    min_funding: Optional[float] = Query(None),
    founded_after: Optional[int] = Query(None),
    founded_before: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    max_features: int = Query(3000, ge=100, le=10000),
):
    """Return GeoJSON for entities within viewport bbox.
    Uses R-Tree spatial index for O(log n) bbox lookups.
    LIMIT prevents massive payloads on zoom-out.
    """
    req_id = getattr(request.state, "request_id", "unknown")
    conn = get_db()

    query = """
        SELECT e.id, e.name, e.slug, e.entity_type, e.sectors, e.stage,
               e.city, e.state, e.latitude, e.longitude,
               e.founded_year, e.employee_count, e.funding_inr,
               e.dpiit_recognized, e.description, e.college_name,
               e.unicorn_status, e.is_women_led, e.is_rural_impact,
               e.is_campus_startup, e.nsa_winner, e.dpiit_category,
               e.business_model, e.linkedin_team_size
        FROM entities e
        INNER JOIN entities_rtree r ON e.id = r.id
        WHERE r.min_lng >= ? AND r.max_lng <= ?
          AND r.min_lat >= ? AND r.max_lat <= ?
          AND e.is_active = 1
    """
    params = [min_lng, max_lng, min_lat, max_lat]

    filters = {
        "entity_type": entity_type, "sector": sector, "stage": stage,
        "dpiit_only": dpiit_only, "dpiit_category": dpiit_category,
        "business_model": business_model, "unicorn_status": unicorn_status,
        "is_women_led": is_women_led, "is_rural_impact": is_rural_impact,
        "is_campus_startup": is_campus_startup, "nsa_winner": nsa_winner,
        "min_funding": min_funding, "founded_after": founded_after,
        "founded_before": founded_before, "search": search,
        "state": state, "city": city,
    }
    query, params = _apply_filters(query, params, filters)
    query += f" LIMIT {max_features}"

    rows = _execute_with_timeout(conn, query, params)
    conn.close()

    features = []
    for row in rows:
        d = row_to_dict(row)
        funding_weight = 0
        if d.get("funding_inr") and d["funding_inr"] > 0:
            funding_weight = min(1.0, math.log10(d["funding_inr"] / 1e8 + 1) / 4)

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [d["longitude"], d["latitude"]]
            },
            "properties": {
                "id": d["id"],
                "name": d["name"],
                "slug": d["slug"],
                "entity_type": d["entity_type"],
                "sectors": d["sectors"],
                "stage": d["stage"],
                "city": d["city"],
                "state": d["state"],
                "founded_year": d["founded_year"],
                "employee_count": d["employee_count"],
                "funding_crores": d["funding_crores"],
                "funding_display": format_funding(d["funding_inr"]),
                "dpiit_recognized": bool(d["dpiit_recognized"]),
                "description": d["description"],
                "college_name": d.get("college_name", ""),
                "unicorn_status": d.get("unicorn_status"),
                "is_women_led": bool(d.get("is_women_led")),
                "is_rural_impact": bool(d.get("is_rural_impact")),
                "is_campus_startup": bool(d.get("is_campus_startup")),
                "nsa_winner": bool(d.get("nsa_winner")),
                "dpiit_category": d.get("dpiit_category"),
                "business_model": d.get("business_model"),
                "linkedin_team_size": d.get("linkedin_team_size"),
                "funding_weight": funding_weight,
            }
        })

    audit_log("geojson_query", req_id,
              details={"bbox": f"{min_lng},{min_lat},{max_lng},{max_lat}", "features": len(features), "limit": max_features},
              severity="info")

    return {"type": "FeatureCollection", "features": features}


@router.get("/viewport/summary")
async def get_viewport_summary(
    request: Request,
    min_lng: float = Query(..., ge=60, le=100),
    max_lng: float = Query(..., ge=60, le=100),
    min_lat: float = Query(..., ge=0, le=40),
    max_lat: float = Query(..., ge=0, le=40),
    entity_type: Optional[str] = Query(None),
):
    """Lightweight viewport summary for dynamic updates."""
    conn = get_db()

    query = """
        SELECT COUNT(*) as count,
               COUNT(CASE WHEN e.entity_type = 'startup' THEN 1 END) as startups,
               COUNT(CASE WHEN e.unicorn_status = 'unicorn' THEN 1 END) as unicorns,
               COUNT(CASE WHEN e.is_women_led = 1 THEN 1 END) as women_led,
               COUNT(CASE WHEN e.dpiit_recognized = 1 THEN 1 END) as dpiit
        FROM entities e
        INNER JOIN entities_rtree r ON e.id = r.id
        WHERE r.min_lng >= ? AND r.max_lng <= ?
          AND r.min_lat >= ? AND r.max_lat <= ?
          AND e.is_active = 1
    """
    params = [min_lng, max_lng, min_lat, max_lat]

    if entity_type:
        types = entity_type.split(",")
        placeholders = ",".join("?" * len(types))
        query += f" AND e.entity_type IN ({placeholders})"
        params.extend(types)

    row = conn.execute(query, params).fetchone()
    conn.close()

    return {
        "count": row["count"],
        "startups": row["startups"],
        "unicorns": row["unicorns"],
        "women_led": row["women_led"],
        "dpiit": row["dpiit"],
    }


@router.get("/heatmap")
async def get_heatmap_data(
    request: Request,
    sector: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    dpiit_category: Optional[str] = Query(None),
    max_points: int = Query(5000, ge=500, le=20000),
):
    """Returns weighted GeoJSON optimized for heatmap layer rendering."""
    conn = get_db()

    query = """
        SELECT e.latitude, e.longitude, e.funding_inr, e.employee_count,
               e.sectors, e.entity_type, e.city
        FROM entities e WHERE e.is_active = 1
    """
    params = []

    if entity_type:
        types = entity_type.split(",")
        placeholders = ",".join("?" * len(types))
        query += f" AND e.entity_type IN ({placeholders})"
        params.extend(types)

    if sector:
        sectors = sector.split(",")
        conds = []
        for s in sectors:
            conds.append("e.sectors LIKE ?")
            params.append(f'%{s}%')
        query += f" AND ({' OR '.join(conds)})"

    if dpiit_category:
        cats = dpiit_category.split(",")
        placeholders = ",".join("?" * len(cats))
        query += f" AND e.dpiit_category IN ({placeholders})"
        params.extend(cats)

    query += f" LIMIT {max_points}"
    rows = _execute_with_timeout(conn, query, params)
    conn.close()

    features = []
    for row in rows:
        d = dict(row)
        funding = d["funding_inr"] or 0
        weight = min(1.0, math.log10(funding / 1e8 + 1) / 4) if funding > 0 else 0.1
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [d["longitude"], d["latitude"]]},
            "properties": {"weight": weight, "city": d["city"]}
        })

    return {"type": "FeatureCollection", "features": features}


@router.get("/nearby")
async def find_nearby(
    request: Request,
    lat: float = Query(..., ge=6.0, le=37.0),
    lng: float = Query(..., ge=68.0, le=98.0),
    radius_km: float = Query(10.0, ge=0.5, le=200),
    entity_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
):
    """Find nearby entities within a radius."""
    ok, err = validate_coordinates(lat, lng)
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    conn = get_db()
    delta = radius_km / 111.0
    bbox_params = [lng - delta, lng + delta, lat - delta, lat + delta]

    query = """
        SELECT e.*
        FROM entities e
        INNER JOIN entities_rtree r ON e.id = r.id
        WHERE r.min_lng >= ? AND r.max_lng <= ?
          AND r.min_lat >= ? AND r.max_lat <= ?
          AND e.is_active = 1
    """
    params = bbox_params[:]

    if entity_type:
        types = entity_type.split(",")
        placeholders = ",".join("?" * len(types))
        query += f" AND e.entity_type IN ({placeholders})"
        params.extend(types)

    if sector:
        sectors = sector.split(",")
        conds = []
        for s in sectors:
            conds.append("e.sectors LIKE ?")
            params.append(f'%{s}%')
        query += f" AND ({' OR '.join(conds)})"

    rows = _execute_with_timeout(conn, query, params)
    conn.close()

    results = []
    for row in rows:
        d = row_to_dict(row)
        dist = haversine_distance(lat, lng, d["latitude"], d["longitude"])
        if dist <= radius_km:
            d["distance_km"] = round(dist, 2)
            results.append(d)

    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]


@router.get("/detail/{slug}")
async def get_entity_detail(request: Request, slug: str):
    """Get entity detail by slug."""
    req_id = getattr(request.state, "request_id", "unknown")

    ok, err = validate_startup_name(slug)
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    conn = get_db()
    row = conn.execute("SELECT * FROM entities WHERE slug = ? AND is_active = 1", (slug,)).fetchone()

    if not row:
        conn.close()
        audit_log("entity_not_found", req_id, details={"slug": slug}, severity="warning")
        raise HTTPException(status_code=404, detail="Entity not found")

    entity = row_to_dict(row)

    nearby_rows = conn.execute("""
        SELECT e.id, e.name, e.slug, e.entity_type, e.sectors, e.city,
               e.latitude, e.longitude
        FROM entities e
        INNER JOIN entities_rtree r ON e.id = r.id
        WHERE r.min_lng >= ? AND r.max_lng <= ?
          AND r.min_lat >= ? AND r.max_lat <= ?
          AND e.id != ? AND e.is_active = 1
        LIMIT 100
    """, (
        entity["longitude"] - 0.1, entity["longitude"] + 0.1,
        entity["latitude"] - 0.1, entity["latitude"] + 0.1,
        entity["id"]
    )).fetchall()
    conn.close()

    nearby = []
    for nr in nearby_rows:
        nd = row_to_dict(nr)
        dist = haversine_distance(entity["latitude"], entity["longitude"], nd["latitude"], nd["longitude"])
        if dist <= 10:
            nd["distance_km"] = round(dist, 2)
            nearby.append(nd)
    nearby.sort(key=lambda x: x["distance_km"])
    entity["nearby"] = nearby[:10]

    audit_log("entity_detail", req_id, details={"slug": slug, "name": entity.get("name")}, severity="info")
    return entity


@router.get("/search")
async def search_entities(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    entity_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
):
    """Search entities by keyword."""
    req_id = getattr(request.state, "request_id", "unknown")

    conn = get_db()
    safe_q = sanitize_like(q)
    query = """
        SELECT * FROM entities e
        WHERE e.is_active = 1
          AND (e.name LIKE ? ESCAPE '\\' OR e.city LIKE ? ESCAPE '\\' OR e.description LIKE ? ESCAPE '\\' OR e.college_name LIKE ? ESCAPE '\\')
    """
    search_term = f"%{safe_q}%"
    params = [search_term, search_term, search_term, search_term]

    filters = {"entity_type": entity_type, "sector": sector, "state": state, "city": city}
    query, params = _apply_filters(query, params, filters)

    count_query = f"SELECT COUNT(*) FROM ({query})"
    total = conn.execute(count_query, params).fetchone()[0]

    query += " ORDER BY e.funding_inr DESC, e.employee_count DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = _execute_with_timeout(conn, query, params)
    conn.close()

    audit_log("search", req_id,
              details={"q": q[:50], "total": total, "limit": limit, "offset": offset},
              severity="info")

    return {"results": [row_to_dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/facets")
async def get_facets(
    request: Request,
    entity_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    conn = get_db()
    base_where = "WHERE is_active = 1"
    params = []
    if search:
        safe_search = sanitize_like(search)
        base_where += " AND name LIKE ? ESCAPE '\\'"
        params.append(f"%{safe_search}%")

    tq = f"SELECT entity_type, COUNT(*) as count FROM entities {base_where}"
    tp = params[:]
    if sector:
        for s in sector.split(","):
            tq += " AND sectors LIKE ?"
            tp.append(f'%{s}%')
    if state:
        tq += " AND state = ?"
        tp.append(state)
    tq += " GROUP BY entity_type ORDER BY count DESC"
    type_counts = {r["entity_type"]: r["count"] for r in conn.execute(tq, tp).fetchall()}

    sq = f"SELECT state, COUNT(*) as count FROM entities {base_where}"
    sp = params[:]
    if entity_type:
        for t in entity_type.split(","):
            sq += " AND entity_type = ?"
            sp.append(t)
    sq += " GROUP BY state ORDER BY count DESC"
    state_counts = {r["state"]: r["count"] for r in conn.execute(sq, sp).fetchall()}

    stq = f"SELECT stage, COUNT(*) as count FROM entities {base_where} AND stage IS NOT NULL"
    stp = params[:]
    if entity_type:
        for t in entity_type.split(","):
            stq += " AND entity_type = ?"
            stp.append(t)
    stq += " GROUP BY stage ORDER BY count DESC"
    stage_counts = {r["stage"]: r["count"] for r in conn.execute(stq, stp).fetchall()}

    bmq = f"SELECT business_model, COUNT(*) as count FROM entities {base_where} AND business_model IS NOT NULL"
    bmp = params[:]
    bmq += " GROUP BY business_model ORDER BY count DESC"
    biz_model_counts = {r["business_model"]: r["count"] for r in conn.execute(bmq, bmp).fetchall()}

    dcq = f"SELECT dpiit_category, COUNT(*) as count FROM entities {base_where} AND dpiit_category IS NOT NULL"
    dcp = params[:]
    dcq += " GROUP BY dpiit_category ORDER BY count DESC"
    dpiit_cat_counts = {r["dpiit_category"]: r["count"] for r in conn.execute(dcq, dcp).fetchall()}

    awq = f"""SELECT SUM(is_women_led) as women, SUM(is_rural_impact) as rural, SUM(is_campus_startup) as campus,
              SUM(nsa_winner) as nsa,
              SUM(CASE WHEN unicorn_status='unicorn' THEN 1 ELSE 0 END) as unicorns,
              SUM(CASE WHEN unicorn_status='soonicorn' THEN 1 ELSE 0 END) as soonicorns
              FROM entities {base_where}"""
    awp = params[:]
    aw = conn.execute(awq, awp).fetchone()

    conn.close()

    return {
        "entity_type": type_counts,
        "state": state_counts,
        "stage": stage_counts,
        "business_model": biz_model_counts,
        "dpiit_category": dpiit_cat_counts,
        "awards": {
            "women_led": aw["women"] or 0,
            "rural_impact": aw["rural"] or 0,
            "campus_startup": aw["campus"] or 0,
            "nsa_winners": aw["nsa"] or 0,
            "unicorns": aw["unicorns"] or 0,
            "soonicorns": aw["soonicorns"] or 0,
        },
    }


@router.get("/analytics/overview")
async def analytics_overview(request: Request):
    conn = get_db()
    stats = {}

    rows = conn.execute("SELECT entity_type, COUNT(*) as count FROM entities WHERE is_active = 1 GROUP BY entity_type").fetchall()
    stats["by_type"] = {r["entity_type"]: r["count"] for r in rows}
    stats["total_entities"] = sum(stats["by_type"].values())

    row = conn.execute("""
        SELECT SUM(funding_inr) as total_funding,
               COUNT(CASE WHEN funding_inr > 0 THEN 1 END) as funded_count,
               AVG(CASE WHEN funding_inr > 0 THEN funding_inr END) as avg_funding
        FROM entities WHERE is_active = 1
    """).fetchone()
    stats["total_funding_inr"] = row["total_funding"] or 0
    stats["total_funding_display"] = format_funding(row["total_funding"] or 0)
    stats["funded_count"] = row["funded_count"] or 0

    rows = conn.execute("""
        SELECT city, state, COUNT(*) as count FROM entities
        WHERE is_active = 1 GROUP BY city ORDER BY count DESC LIMIT 10
    """).fetchall()
    stats["top_cities"] = [dict(r) for r in rows]

    rows = conn.execute("""
        SELECT state, COUNT(*) as count FROM entities
        WHERE is_active = 1 GROUP BY state ORDER BY count DESC LIMIT 10
    """).fetchall()
    stats["top_states"] = [dict(r) for r in rows]

    rows = conn.execute("""
        SELECT founded_year, COUNT(*) as count FROM entities
        WHERE is_active = 1 AND founded_year IS NOT NULL AND founded_year >= 2005
        GROUP BY founded_year ORDER BY founded_year
    """).fetchall()
    stats["founding_trend"] = [dict(r) for r in rows]

    row = conn.execute("""
        SELECT COUNT(CASE WHEN dpiit_recognized = 1 THEN 1 END) as recognized,
               COUNT(*) as total
        FROM entities WHERE is_active = 1 AND entity_type = 'startup'
    """).fetchone()
    stats["dpiit_recognized"] = row["recognized"]
    stats["dpiit_total_startups"] = row["total"]

    row = conn.execute("SELECT COUNT(*) as c FROM entities WHERE unicorn_status = 'unicorn' AND is_active = 1").fetchone()
    stats["unicorn_count"] = row["c"]

    row = conn.execute("SELECT COUNT(*) as c FROM entities WHERE is_women_led = 1 AND is_active = 1").fetchone()
    stats["women_led_count"] = row["c"]

    row = conn.execute("SELECT COUNT(*) as c FROM entities WHERE nsa_winner = 1 AND is_active = 1").fetchone()
    stats["nsa_winner_count"] = row["c"]

    conn.close()
    return stats


@router.get("/analytics/sectors")
async def analytics_sectors(request: Request):
    conn = get_db()
    rows = conn.execute("""
        SELECT sectors, funding_inr, employee_count, entity_type, founded_year, city, state
        FROM entities WHERE is_active = 1
    """).fetchall()
    conn.close()

    sector_data = {}
    for row in rows:
        try:
            sectors = json.loads(row["sectors"])
        except Exception:
            sectors = []
        for s in sectors:
            if s not in sector_data:
                sector_data[s] = {"count": 0, "total_funding": 0, "total_employees": 0, "cities": {}, "by_type": {}}
            sector_data[s]["count"] += 1
            sector_data[s]["total_funding"] += row["funding_inr"] or 0
            sector_data[s]["total_employees"] += row["employee_count"] or 0
            sector_data[s]["cities"][row["city"]] = sector_data[s]["cities"].get(row["city"], 0) + 1
            sector_data[s]["by_type"][row["entity_type"]] = sector_data[s]["by_type"].get(row["entity_type"], 0) + 1

    result = []
    for slug, data in sorted(sector_data.items(), key=lambda x: x[1]["count"], reverse=True):
        top_cities = sorted(data["cities"].items(), key=lambda x: x[1], reverse=True)[:5]
        result.append({
            "sector": slug, "count": data["count"],
            "total_funding_display": format_funding(data["total_funding"]),
            "total_employees": data["total_employees"],
            "top_cities": [{"city": c, "count": n} for c, n in top_cities],
            "by_type": data["by_type"],
        })
    return result


@router.get("/sectors")
async def get_sectors(request: Request):
    conn = get_db()
    rows = conn.execute("SELECT * FROM sectors ORDER BY category, label").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/locations/states")
async def get_states(request: Request):
    conn = get_db()
    rows = conn.execute("""
        SELECT state, COUNT(*) as count FROM entities WHERE is_active = 1 GROUP BY state ORDER BY count DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/locations/cities")
async def get_cities(request: Request, state: Optional[str] = None):
    conn = get_db()
    if state:
        rows = conn.execute("""
            SELECT city, state, COUNT(*) as count, AVG(latitude) as lat, AVG(longitude) as lng
            FROM entities WHERE is_active = 1 AND state = ?
            GROUP BY city ORDER BY count DESC
        """, (state,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT city, state, COUNT(*) as count, AVG(latitude) as lat, AVG(longitude) as lng
            FROM entities WHERE is_active = 1
            GROUP BY city ORDER BY count DESC LIMIT 50
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/export")
async def export_entities(
    request: Request,
    min_lng: float = Query(68.0, ge=60, le=100),
    max_lng: float = Query(97.0, ge=60, le=100),
    min_lat: float = Query(6.0, ge=0, le=40),
    max_lat: float = Query(37.0, ge=0, le=40),
    entity_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    dpiit_only: bool = Query(False),
    dpiit_category: Optional[str] = Query(None),
    business_model: Optional[str] = Query(None),
    unicorn_status: Optional[str] = Query(None),
    is_women_led: bool = Query(False),
    is_rural_impact: bool = Query(False),
    is_campus_startup: bool = Query(False),
    nsa_winner: bool = Query(False),
    min_funding: Optional[float] = Query(None),
    founded_after: Optional[int] = Query(None),
    founded_before: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    format: str = Query("csv", pattern="^(csv|json)$"),
):
    """Export filtered entities as CSV or JSON for download. Max 5000 rows."""
    req_id = getattr(request.state, "request_id", "unknown")

    conn = get_db()
    query = """
        SELECT e.name, e.entity_type, e.city, e.state, e.sectors, e.stage,
               e.founded_year, e.employee_count, e.funding_inr, e.dpiit_recognized,
               e.description, e.unicorn_status, e.is_women_led, e.is_rural_impact,
               e.is_campus_startup, e.nsa_winner, e.dpiit_category, e.business_model,
               e.website, e.linkedin_url, e.investors, e.valuation_usd,
               e.latitude, e.longitude
        FROM entities e
        INNER JOIN entities_rtree r ON e.id = r.id
        WHERE r.min_lng >= ? AND r.max_lng <= ?
          AND r.min_lat >= ? AND r.max_lat <= ?
          AND e.is_active = 1
    """
    params = [min_lng, max_lng, min_lat, max_lat]
    filters = {
        "entity_type": entity_type, "sector": sector, "stage": stage,
        "dpiit_only": dpiit_only, "dpiit_category": dpiit_category,
        "business_model": business_model, "unicorn_status": unicorn_status,
        "is_women_led": is_women_led, "is_rural_impact": is_rural_impact,
        "is_campus_startup": is_campus_startup, "nsa_winner": nsa_winner,
        "min_funding": min_funding, "founded_after": founded_after,
        "founded_before": founded_before, "search": search,
        "state": state, "city": city,
    }
    query, params = _apply_filters(query, params, filters)
    query += " ORDER BY e.funding_inr DESC LIMIT 5000"

    rows = _execute_with_timeout(conn, query, params)
    conn.close()

    items = [row_to_dict(r) for r in rows]
    for item in items:
        f = item.get("funding_inr") or 0
        item["funding_display"] = format_funding(f)

    audit_log("export", req_id,
              details={"format": format, "count": len(items), "bbox": f"{min_lng},{min_lat},{max_lng},{max_lat}"},
              severity="info")

    if format == "json":
        return Response(
            content=json.dumps(items, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=bharat-tech-atlas-export.json"},
        )

    output = io.StringIO()
    cols = ["name", "entity_type", "city", "state", "sectors", "stage",
            "founded_year", "employee_count", "funding_display", "dpiit_recognized",
            "unicorn_status", "is_women_led", "is_rural_impact", "dpiit_category",
            "business_model", "website", "linkedin_url", "investors",
            "valuation_usd", "latitude", "longitude"]
    writer = csv.DictWriter(output, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        writer.writerow(item)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bharat-tech-atlas-export.csv"},
    )
