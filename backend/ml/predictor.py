"""
Bharat Tech Atlas — Startup Growth Predictor
Predicts startup growth potential using features like funding, team size,
sector momentum, and location factors.

Model: Gradient Boosted Trees (XGBoost/LightGBM) or a simple neural network.
Features are engineered from the entity database.
"""
import logging
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GrowthPrediction:
    """Growth prediction result for a startup."""
    entity_id: int
    entity_name: str
    growth_score: float  # 0.0 to 1.0
    growth_label: str  # "high", "medium", "low"
    factors: List[Dict[str, float]]  # Contributing factors with weights
    confidence: float
    predicted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Feature weights for rule-based predictor ────────────────────────────────
SECTOR_MOMENTUM = {
    "ai_ml": 0.95, "saas_ai": 0.90, "fintech": 0.85, "deeptech": 0.88,
    "healthtech": 0.82, "ev": 0.85, "cybersecurity": 0.80, "spacetech": 0.78,
    "cleantech": 0.80, "edtech": 0.65, "ecommerce": 0.60, "d2c": 0.55,
    "agritech": 0.72, "biotech": 0.75, "drone_tech": 0.77, "iot": 0.70,
    "logistics": 0.65, "foodtech": 0.55, "proptech": 0.50, "gaming": 0.60,
    "mediatech": 0.45, "legaltech": 0.55, "insurtech": 0.65, "wealthtech": 0.70,
    "mobility": 0.60, "social_impact": 0.50, "manufacturing": 0.55,
    "healthcare": 0.70, "saas": 0.80,
}

CITY_ECOSYSTEM_SCORE = {
    "Bengaluru": 0.95, "Mumbai": 0.88, "Delhi": 0.85, "Gurugram": 0.85,
    "Hyderabad": 0.80, "Pune": 0.78, "Chennai": 0.75, "Noida": 0.72,
    "Ahmedabad": 0.65, "Kolkata": 0.55, "Jaipur": 0.50, "Kochi": 0.55,
    "Indore": 0.45, "Coimbatore": 0.50, "Thiruvananthapuram": 0.48,
}


class GrowthPredictor:
    """
    Predict startup growth potential using engineered features.

    In production, this would use a trained ML model (XGBoost/LightGBM).
    Current implementation uses a weighted scoring system based on
    empirical startup success factors from Indian ecosystem data.

    Features used:
    - Funding trajectory (amount, rounds, velocity)
    - Team size and growth rate
    - Sector momentum (market trends)
    - Location ecosystem strength
    - Age / stage appropriateness
    - Investor quality signal
    - DPIIT recognition / awards
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize predictor.

        Args:
            model_path: Path to trained model file (pickle/joblib).
                       If None, uses rule-based scoring.
        """
        self.model_path = model_path
        self._model = None
        self._loaded = False

    def load_model(self):
        """Load trained ML model for predictions."""
        if self.model_path:
            try:
                import joblib
                self._model = joblib.load(self.model_path)
                logger.info(f"Growth model loaded from {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not load model: {e}. Using rule-based scoring.")
        self._loaded = True

    def predict(self, entity: Dict) -> GrowthPrediction:
        """
        Predict growth potential for a single entity.

        Args:
            entity: Dict with entity fields from database

        Returns:
            GrowthPrediction with score, label, and contributing factors
        """
        if not self._loaded:
            self.load_model()

        features = self._extract_features(entity)

        if self._model:
            score = self._predict_ml(features)
        else:
            score = self._predict_rules(features)

        # Determine label
        if score >= 0.7:
            label = "high"
        elif score >= 0.4:
            label = "medium"
        else:
            label = "low"

        # Top contributing factors
        factors = sorted(features.items(), key=lambda x: x[1], reverse=True)[:5]
        factor_list = [{"factor": k, "score": round(v, 3)} for k, v in factors]

        return GrowthPrediction(
            entity_id=entity.get("id", 0),
            entity_name=entity.get("name", ""),
            growth_score=round(score, 3),
            growth_label=label,
            factors=factor_list,
            confidence=self._calculate_confidence(features),
        )

    def predict_batch(self, entities: List[Dict]) -> List[GrowthPrediction]:
        """Batch prediction for multiple entities."""
        return [self.predict(e) for e in entities]

    def _extract_features(self, entity: Dict) -> Dict[str, float]:
        """Extract normalized features from entity data."""
        features = {}

        # ─── Funding Signal ─────────────────────────────────────────
        funding_inr = entity.get("funding_inr", 0) or 0
        if funding_inr > 0:
            # Log-scale normalization (₹1L to ₹10000Cr range)
            features["funding_signal"] = min(1.0, math.log10(funding_inr / 1e5 + 1) / 5)
        else:
            features["funding_signal"] = 0.1  # Bootstrapped gets small score

        # ─── Team Size Signal ────────────────────────────────────────
        employees = entity.get("employee_count", 0) or entity.get("linkedin_team_size", 0) or 0
        if employees > 0:
            features["team_signal"] = min(1.0, math.log10(employees + 1) / 3)
        else:
            features["team_signal"] = 0.2

        # ─── Sector Momentum ────────────────────────────────────────
        sectors = entity.get("sectors", [])
        if isinstance(sectors, str):
            import json
            try:
                sectors = json.loads(sectors)
            except:
                sectors = []

        sector_scores = [SECTOR_MOMENTUM.get(s, 0.5) for s in sectors]
        features["sector_momentum"] = max(sector_scores) if sector_scores else 0.5

        # ─── Location Ecosystem ──────────────────────────────────────
        city = entity.get("city", "")
        features["ecosystem_score"] = CITY_ECOSYSTEM_SCORE.get(city, 0.3)

        # ─── Age Appropriateness ─────────────────────────────────────
        founded_year = entity.get("founded_year")
        if founded_year:
            age = datetime.now().year - founded_year
            # Sweet spot: 2-7 years old
            if 2 <= age <= 7:
                features["age_signal"] = 0.8
            elif age < 2:
                features["age_signal"] = 0.6  # Too early to tell
            elif age <= 12:
                features["age_signal"] = 0.5
            else:
                features["age_signal"] = 0.3  # Older = less "growth startup"
        else:
            features["age_signal"] = 0.4

        # ─── Recognition Signals ─────────────────────────────────────
        recognition_score = 0.0
        if entity.get("dpiit_recognized"):
            recognition_score += 0.3
        if entity.get("nsa_winner"):
            recognition_score += 0.4
        if entity.get("unicorn_status") == "unicorn":
            recognition_score += 0.5
        elif entity.get("unicorn_status") == "soonicorn":
            recognition_score += 0.4
        features["recognition_signal"] = min(1.0, recognition_score)

        # ─── Investor Quality ────────────────────────────────────────
        investors = entity.get("investors", [])
        if isinstance(investors, str):
            import json
            try:
                investors = json.loads(investors)
            except:
                investors = []

        top_investors = [
            "sequoia", "accel", "tiger global", "softbank", "a16z",
            "peak xv", "matrix", "lightspeed", "blume", "elevation",
            "nexus", "kalaari", "chiratae", "stellaris", "3one4"
        ]
        investor_matches = sum(
            1 for inv in investors
            if any(top in inv.lower() for top in top_investors)
        )
        features["investor_signal"] = min(1.0, investor_matches * 0.3)

        return features

    def _predict_rules(self, features: Dict[str, float]) -> float:
        """Rule-based weighted scoring."""
        weights = {
            "funding_signal": 0.25,
            "team_signal": 0.15,
            "sector_momentum": 0.20,
            "ecosystem_score": 0.10,
            "age_signal": 0.10,
            "recognition_signal": 0.10,
            "investor_signal": 0.10,
        }

        score = sum(
            features.get(k, 0) * w
            for k, w in weights.items()
        )
        return min(1.0, max(0.0, score))

    def _predict_ml(self, features: Dict[str, float]) -> float:
        """ML model-based prediction."""
        import numpy as np
        feature_vector = np.array([[
            features.get("funding_signal", 0),
            features.get("team_signal", 0),
            features.get("sector_momentum", 0),
            features.get("ecosystem_score", 0),
            features.get("age_signal", 0),
            features.get("recognition_signal", 0),
            features.get("investor_signal", 0),
        ]])
        prediction = self._model.predict_proba(feature_vector)[0][1]
        return float(prediction)

    def _calculate_confidence(self, features: Dict[str, float]) -> float:
        """Calculate prediction confidence based on feature completeness."""
        total_features = 7
        non_default_features = sum(
            1 for v in features.values()
            if v not in [0.2, 0.3, 0.4, 0.5]  # Default values
        )
        return round(non_default_features / total_features, 2)

    def train(self, training_data: List[Dict], labels: List[int],
              output_path: str = "models/growth_model.joblib"):
        """
        Train the growth prediction model on labeled data.

        Args:
            training_data: List of entity dicts
            labels: Binary labels (1=high growth, 0=low growth)
            output_path: Where to save trained model
        """
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            from sklearn.model_selection import cross_val_score
            import numpy as np
            import joblib

            # Extract features for all training examples
            X = []
            for entity in training_data:
                features = self._extract_features(entity)
                X.append([
                    features["funding_signal"],
                    features["team_signal"],
                    features["sector_momentum"],
                    features["ecosystem_score"],
                    features["age_signal"],
                    features["recognition_signal"],
                    features["investor_signal"],
                ])

            X = np.array(X)
            y = np.array(labels)

            # Train model
            model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
            )

            # Cross-validation
            scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
            logger.info(f"CV accuracy: {scores.mean():.3f} (+/- {scores.std():.3f})")

            # Full training
            model.fit(X, y)

            # Save
            joblib.dump(model, output_path)
            logger.info(f"Model saved to {output_path}")

            self._model = model

        except ImportError as e:
            logger.error(f"Training dependencies not installed: {e}")
            raise
