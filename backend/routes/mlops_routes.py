"""
Bharat Tech Atlas — MLOps API Routes
Exposes monitoring, drift detection, and model management endpoints.
"""
from fastapi import APIRouter, Query, Request
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Lazy-loaded singleton instances ──────────────────────────────────────────
_drift_detector = None
_model_monitor = None
_model_registry = None
_cicd = None


def _get_drift_detector():
    global _drift_detector
    if _drift_detector is None:
        from ..mlops import DataDriftDetector
        _drift_detector = DataDriftDetector()
    return _drift_detector


def _get_monitor():
    global _model_monitor
    if _model_monitor is None:
        from ..mlops import ModelMonitor
        _model_monitor = ModelMonitor()
    return _model_monitor


def _get_registry():
    global _model_registry
    if _model_registry is None:
        from ..mlops import ModelRegistry
        _model_registry = ModelRegistry()
        _model_registry.register(
            "sector_classifier", "v1.0",
            data_hash="seed_data_2024", metrics={"accuracy": 0.78, "f1": 0.75},
            description="Keyword-based fallback classifier"
        )
        _model_registry.register(
            "growth_predictor", "v1.0",
            data_hash="seed_data_2024", metrics={"accuracy": 0.72, "auc": 0.80},
            description="Rule-based growth scoring"
        )
        _model_registry.promote("sector_classifier", "v1.0")
        _model_registry.promote("growth_predictor", "v1.0")
    return _model_registry


def _get_cicd():
    global _cicd
    if _cicd is None:
        from ..mlops import CICDPipeline
        _cicd = CICDPipeline()
    return _cicd


# ─── Data Drift Endpoints ────────────────────────────────────────────────────

@router.get("/drift/check")
async def check_data_drift(
    sample_size: int = Query(100, ge=10, le=1000),
    features: Optional[str] = Query(None, description="Comma-separated features to check"),
):
    """Check for data drift in current database vs reference distribution."""
    from ..database import get_db

    detector = _get_drift_detector()
    conn = get_db()

    rows = conn.execute("""
        SELECT entity_type, state, funding_inr, employee_count, founded_year
        FROM entities WHERE is_active = 1
        ORDER BY updated_at DESC LIMIT ?
    """, (sample_size,)).fetchall()
    conn.close()

    current_data = [dict(r) for r in rows]
    feature_list = features.split(",") if features else None
    reports = detector.check_drift(current_data, features=feature_list)

    return {
        "drift_reports": [
            {
                "feature": r.feature_name,
                "drift_detected": r.drift_detected,
                "drift_score": r.drift_score,
                "method": r.test_method,
                "threshold": r.threshold,
                "reference": r.reference_stats,
                "current": r.current_stats,
            }
            for r in reports
        ],
        "summary": {
            "features_checked": len(reports),
            "drifted_features": sum(1 for r in reports if r.drift_detected),
            "max_drift_score": max((r.drift_score for r in reports), default=0),
            "recommendation": "RETRAIN" if any(r.drift_detected for r in reports) else "OK",
        },
        "checked_at": datetime.utcnow().isoformat(),
    }


@router.get("/drift/history")
async def get_drift_history(last_n: int = Query(50, ge=1, le=200)):
    """Get historical drift detection results."""
    detector = _get_drift_detector()
    return {"history": detector.get_drift_history(last_n)}


# ─── Model Monitoring ─────────────────────────────────────────────────────────

@router.get("/monitor/metrics")
async def get_model_metrics(model_name: Optional[str] = Query(None)):
    """Get real-time model performance metrics."""
    monitor = _get_monitor()
    return {"metrics": monitor.get_metrics(model_name)}


@router.get("/monitor/alerts")
async def get_monitoring_alerts(last_n: int = Query(20, ge=1, le=100)):
    """Get recent MLOps alerts."""
    monitor = _get_monitor()
    return {"alerts": monitor.get_alerts(last_n)}


# ─── Model Registry ──────────────────────────────────────────────────────────

@router.get("/registry/models")
async def list_models():
    """List all registered models with their versions."""
    registry = _get_registry()
    return {
        "models": {
            "sector_classifier": {
                "active_version": registry.get_active_version("sector_classifier"),
                "versions": registry.get_versions("sector_classifier"),
            },
            "growth_predictor": {
                "active_version": registry.get_active_version("growth_predictor"),
                "versions": registry.get_versions("growth_predictor"),
            },
        }
    }


@router.get("/registry/compare")
async def compare_model_versions(
    model: str = Query(..., description="Model name"),
    v1: str = Query(..., description="First version"),
    v2: str = Query(..., description="Second version"),
):
    """Compare two model versions."""
    registry = _get_registry()
    return registry.compare_versions(model, v1, v2)


# ─── CI/CD ────────────────────────────────────────────────────────────────────

@router.get("/cicd/workflow")
async def get_cicd_workflow():
    """Get the GitHub Actions workflow YAML."""
    cicd = _get_cicd()
    return {
        "workflow_yaml": cicd.get_workflow_yaml(),
        "description": "Automated ML pipeline: test → validate data → train → deploy",
    }


@router.post("/cicd/trigger-retrain")
async def trigger_retraining(request: Request):
    """Manually trigger model retraining."""
    body = await request.json() if await request.body() else {}
    reason = body.get("reason", "Manual trigger")
    cicd = _get_cicd()
    event = cicd.trigger_retraining(reason)
    return {"status": "triggered", "event": event}


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def mlops_health():
    """Overall MLOps system health."""
    registry = _get_registry()
    return {
        "status": "healthy",
        "components": {
            "model_monitor": "active",
            "drift_detector": "active",
            "model_registry": "active",
            "cicd_pipeline": "configured",
        },
        "models": {
            "sector_classifier": registry.get_active_version("sector_classifier"),
            "growth_predictor": registry.get_active_version("growth_predictor"),
        },
        "last_check": datetime.utcnow().isoformat(),
    }
