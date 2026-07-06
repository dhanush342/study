"""
Bharat Tech Atlas — ML API Routes
Exposes ML model predictions via FastAPI endpoints.
Includes sector classification, growth prediction, and batch inference.

v3.2: All model imports are lazy and degrade gracefully if
transformers/torch are not installed (keyword fallback works without them).
"""
from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional, List
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Lazy-loaded model instances ──────────────────────────────────────────────
_classifier = None
_classifier_failed = False  # sentinel: tried and gave up
_predictor = None


def _get_classifier():
    global _classifier, _classifier_failed
    if _classifier_failed:
        return None
    if _classifier is not None:
        return _classifier

    try:
        from ..ml.classifier import StartupSectorClassifier
        _classifier = StartupSectorClassifier(model_name="facebook/bart-large-mnli", use_onnx=False)
        _classifier.load_model()
        logger.info("✅ StartupSectorClassifier loaded (transformers available)")
        return _classifier
    except ImportError as e:
        logger.warning(f"⚠️ transformers/torch not installed — using keyword fallback: {e}")
        _classifier_failed = True
        return None
    except Exception as e:
        logger.warning(f"⚠️ Classifier load failed, using keyword fallback: {e}")
        _classifier_failed = True
        return None


def _get_predictor():
    global _predictor
    if _predictor is None:
        from ..ml.predictor import GrowthPredictor
        _predictor = GrowthPredictor()
        _predictor.load_model()
    return _predictor


# ─── Sector Classification Endpoint ──────────────────────────────────────────

@router.get("/classify/sector")
async def classify_sector(
    description: str = Query(..., min_length=10, max_length=2000,
                             description="Startup description text to classify"),
    top_k: int = Query(3, ge=1, le=10, description="Number of top sectors to return"),
):
    """
    Classify a startup's sector using NLP.
    Returns top-K sector predictions with confidence scores.
    Uses keyword-based fallback if transformers/torch unavailable.
    """
    classifier = _get_classifier()
    if classifier is None:
        # Use keyword classifier directly
        try:
            from ..ml.classifier import StartupSectorClassifier, SECTOR_LABELS, SECTOR_DESCRIPTIONS
        except ImportError:
            raise HTTPException(status_code=503, detail="ML module unavailable. Install: pip install transformers torch")

        kw = StartupSectorClassifier(use_onnx=False)
        kw._loaded = True  # Skip model loading, go straight to keywords
        result = kw._classify_keywords(description, top_k)
        return {
            "sector": result.sector,
            "confidence": round(result.confidence, 3),
            "top_sectors": [{"sector": s, "confidence": round(c, 3)} for s, c in result.top_sectors],
            "model_version": "keyword_fallback_v1",
            "note": "transformers not installed — using keyword classification",
        }

    try:
        result = classifier.classify(description, top_k=top_k)
        return {
            "sector": result.sector,
            "confidence": round(result.confidence, 3),
            "top_sectors": [{"sector": s, "confidence": round(c, 3)} for s, c in result.top_sectors],
            "model_version": result.model_version,
        }
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post("/classify/sector/batch")
async def classify_sector_batch(request: Request):
    """Batch sector classification for multiple descriptions (max 50)."""
    body = await request.json()
    descriptions = body.get("descriptions", [])
    top_k = body.get("top_k", 3)

    if not descriptions:
        raise HTTPException(status_code=400, detail="No descriptions provided")
    if len(descriptions) > 50:
        raise HTTPException(status_code=400, detail="Max 50 descriptions per batch")

    classifier = _get_classifier()
    if classifier is None:
        try:
            from ..ml.classifier import StartupSectorClassifier
        except ImportError:
            raise HTTPException(status_code=503, detail="ML module unavailable")

        kw = StartupSectorClassifier(use_onnx=False)
        kw._loaded = True
        results = [kw._classify_keywords(d, top_k) for d in descriptions]
        return {
            "results": [{"sector": r.sector, "confidence": round(r.confidence, 3),
                         "top_sectors": [{"sector": s, "confidence": round(c, 3)} for s, c in r.top_sectors]}
                        for r in results],
            "count": len(results),
            "note": "keyword_fallback",
        }

    try:
        results = classifier.classify_batch(descriptions, top_k=top_k)
        return {
            "results": [{"sector": r.sector, "confidence": round(r.confidence, 3),
                         "top_sectors": [{"sector": s, "confidence": round(c, 3)} for s, c in r.top_sectors]}
                        for r in results],
            "count": len(results),
        }
    except Exception as e:
        logger.error(f"Batch classification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Growth Prediction Endpoint ──────────────────────────────────────────────

@router.get("/predict/growth/{slug}")
async def predict_growth(slug: str):
    """Predict growth potential for a specific entity by slug."""
    from ..database import get_db

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM entities WHERE slug = ? AND is_active = 1", (slug,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity = dict(row)
    for field in ["sectors", "investors", "funding_rounds", "data_sources"]:
        if field in entity and isinstance(entity[field], str):
            try:
                entity[field] = json.loads(entity[field])
            except (json.JSONDecodeError, TypeError):
                entity[field] = []

    predictor = _get_predictor()
    result = predictor.predict(entity)

    return {
        "entity_id": result.entity_id,
        "entity_name": result.entity_name,
        "growth_score": result.growth_score,
        "growth_label": result.growth_label,
        "factors": result.factors,
        "confidence": result.confidence,
        "predicted_at": result.predicted_at,
    }


@router.get("/predict/growth")
async def predict_growth_batch(
    entity_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("growth_score", pattern="^(growth_score|funding_inr|name)$"),
):
    """Get growth predictions for multiple entities with filtering."""
    from ..database import get_db

    conn = get_db()
    query = "SELECT * FROM entities WHERE is_active = 1"
    params = []

    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)
    if sector:
        query += " AND sectors LIKE ?"
        params.append(f'%{sector}%')
    if state:
        query += " AND state = ?"
        params.append(state)

    query += " ORDER BY funding_inr DESC LIMIT ?"
    params.append(min(limit * 3, 300))

    rows = conn.execute(query, params).fetchall()
    conn.close()

    predictor = _get_predictor()
    predictions = []

    for row in rows:
        entity = dict(row)
        for field in ["sectors", "investors", "funding_rounds", "data_sources"]:
            if field in entity and isinstance(entity[field], str):
                try:
                    entity[field] = json.loads(entity[field])
                except (json.JSONDecodeError, TypeError):
                    entity[field] = []

        result = predictor.predict(entity)
        if result.growth_score >= min_score:
            predictions.append({
                "entity_id": result.entity_id,
                "entity_name": result.entity_name,
                "slug": entity.get("slug"),
                "city": entity.get("city"),
                "state": entity.get("state"),
                "sectors": entity.get("sectors", []),
                "growth_score": result.growth_score,
                "growth_label": result.growth_label,
                "confidence": result.confidence,
                "top_factor": result.factors[0] if result.factors else None,
            })

    if sort == "growth_score":
        predictions.sort(key=lambda x: x["growth_score"], reverse=True)
    elif sort == "name":
        predictions.sort(key=lambda x: x["entity_name"])

    return {
        "predictions": predictions[:limit],
        "total": len(predictions),
        "filters": {"entity_type": entity_type, "sector": sector, "state": state},
    }


# ─── Model Health & Info ──────────────────────────────────────────────────────

@router.get("/health")
async def ml_health():
    """Get ML model server health status."""
    classifier = _get_classifier()
    predictor = _get_predictor()
    return {
        "status": "healthy" if classifier else "fallback",
        "mode": "transformers" if classifier else "keyword_fallback",
        "models": {
            "sector_classifier": {
                "loaded": classifier is not None,
                "mode": "keyword_fallback" if not classifier else "transformers",
            },
            "growth_predictor": {
                "loaded": True,
                "type": "rule_based",
            },
        },
    }


@router.get("/sectors/taxonomy")
async def get_sector_taxonomy():
    """Get the full sector taxonomy used by the classifier."""
    try:
        from ..ml.classifier import SECTOR_LABELS, SECTOR_DESCRIPTIONS
    except ImportError:
        SECTOR_LABELS = ["fintech", "saas_ai", "ecommerce", "healthcare", "manufacturing",
                         "edtech", "agritech", "cleantech", "deeptech", "logistics",
                         "gaming", "ai_ml", "cybersecurity", "foodtech", "proptech",
                         "legaltech", "mediatech", "mobility", "social_impact", "biotech",
                         "spacetech", "d2c", "saas", "healthtech", "iot", "drone_tech",
                         "ev", "insurtech", "wealthtech"]
        SECTOR_DESCRIPTIONS = {}
    return {
        "sectors": [{"slug": s, "description": SECTOR_DESCRIPTIONS.get(s, "")} for s in SECTOR_LABELS],
        "total": len(SECTOR_LABELS),
    }
