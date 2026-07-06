"""
Bharat Tech Atlas — ETL API Routes
Exposes ETL pipeline management endpoints.
"""
from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from ..etl.pipeline import ETLPipeline
        from ..database import DB_PATH
        _pipeline = ETLPipeline({
            "db_path": DB_PATH,
            "dpiit_api_key": None,
            "tracxn_token": None,
            "crunchbase_key": None,
        })
    return _pipeline


@router.get("/status")
async def etl_status():
    """Get ETL pipeline status and database stats."""
    pipeline = _get_pipeline()
    stats = pipeline.get_db_stats()
    history = pipeline.get_run_history()
    return {
        "status": "ready",
        "database": stats,
        "last_run": history[-1] if history else None,
        "total_runs": len(history),
    }


@router.post("/run")
async def trigger_etl(request: Request):
    """Trigger a full ETL pipeline run."""
    body = await request.json() if await request.body() else {}
    sources = body.get("sources")
    pipeline = _get_pipeline()
    report = await pipeline.run(sources=sources)
    return {"message": "ETL pipeline completed", "report": report}


@router.post("/run/incremental")
async def trigger_incremental_etl(
    since_hours: int = Query(24, ge=1, le=168),
):
    """Trigger incremental ETL — only recent records."""
    pipeline = _get_pipeline()
    report = await pipeline.run_incremental(since_hours=since_hours)
    return {"message": f"Incremental ETL completed (last {since_hours}h)", "report": report}


@router.get("/history")
async def get_etl_history(last_n: int = Query(10, ge=1, le=50)):
    """Get ETL pipeline run history."""
    pipeline = _get_pipeline()
    history = pipeline.get_run_history()
    return {"runs": history[-last_n:], "total": len(history)}


@router.get("/sources")
async def get_data_sources():
    """Get configured data source information."""
    return {
        "sources": [
            {
                "name": "DPIIT",
                "description": "Department for Promotion of Industry and Internal Trade",
                "provides": ["recognized startups", "NSA winners", "women-led", "DPIIT categories"],
                "update_frequency": "weekly",
                "status": "configured",
            },
            {
                "name": "Tracxn",
                "description": "Startup intelligence platform",
                "provides": ["funding data", "investors", "valuation", "team size"],
                "update_frequency": "daily",
                "status": "configured",
            },
            {
                "name": "Crunchbase",
                "description": "Business information platform",
                "provides": ["funding rounds", "investors", "company profiles", "news"],
                "update_frequency": "daily",
                "status": "configured",
            },
        ],
        "pipeline": {
            "schedule": "Daily at 2:00 AM IST (incremental), Weekly full on Sundays",
            "avg_duration": "5-15 min (incremental), 30-60 min (full)",
        }
    }
