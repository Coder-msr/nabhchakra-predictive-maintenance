"""Predictive Maintenance Inference & Explainability Service.

Loads the serialized Random Forest model, runs risk inference over live or simulated
telemetry features, categorizes risk tiers, and generates human-readable risk drivers.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from config.settings import MODEL_PATH, METADATA_PATH, RISK_TIERS
from src.ml.preprocessor import FEATURE_COLUMNS, TelemetryFeatureEngineer


class MaintenancePredictor:
    """Inference engine for predicting component failure risk and explaining key drivers."""

    def __init__(self, model_path: Optional[Union[str, Path]] = None, metadata_path: Optional[Union[str, Path]] = None):
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.metadata_path = Path(metadata_path) if metadata_path else METADATA_PATH

        self.model = self._load_model()
        self.metadata = self._load_metadata()

    def _load_model(self):
        """Load serialized scikit-learn model."""
        if not self.model_path.exists():
            from src.ml.trainer import train_and_evaluate_models
            train_and_evaluate_models()
        return joblib.load(self.model_path)

    def _load_metadata(self) -> Dict:
        """Load model evaluation and training metadata."""
        if not self.metadata_path.exists():
            from src.ml.trainer import train_and_evaluate_models
            train_and_evaluate_models()
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def assign_risk_tier(prob: float) -> str:
        """Map risk probability to standardized risk tier."""
        for tier, (low, high) in RISK_TIERS.items():
            if low <= prob < high:
                return tier
        return "Critical" if prob >= 0.85 else "Low"

    def predict_features(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Generate predicted risk probabilities, risk tiers, and explanation drivers."""
        df_out = features_df.copy()

        # Ensure all expected feature columns are present
        X = df_out[FEATURE_COLUMNS].fillna(0.0)

        # Generate probabilities
        probs = self.model.predict_proba(X)[:, 1]
        df_out["predicted_risk_prob"] = np.round(probs, 4)
        df_out["risk_tier"] = df_out["predicted_risk_prob"].apply(self.assign_risk_tier)

        # Generate risk explanation drivers
        explanations = []
        for _, row in df_out.iterrows():
            drivers = self.explain_component_risk(row)
            explanations.append(", ".join(drivers) if drivers else "Nominal operating envelope")

        df_out["risk_drivers"] = explanations
        return df_out

    def explain_component_risk(self, row: pd.Series) -> List[str]:
        """Explain the top engineering reasons for elevated risk based on physical indicators."""
        drivers = []

        # Temperature checks
        if row.get("temp_max_30d", 0.0) >= 880.0:
            drivers.append(f"Peak temperature reached {row['temp_max_30d']}°C (Exceeds Warning Threshold)")
        elif row.get("temp_trend_slope", 0.0) > 0.4:
            drivers.append("Positive thermal creep trend detected")

        # Vibration checks
        if row.get("vib_max_30d", 0.0) >= 3.6:
            drivers.append(f"Vibration RMS reached {row['vib_max_30d']} mm/s (Bearing/Harmonic Stress)")
        elif row.get("vib_trend_slope", 0.0) > 0.015:
            drivers.append("Accelerating vibration trend")

        # Pressure checks
        if row.get("oil_min_30d", 60.0) <= 38.0:
            drivers.append(f"Oil pressure dropped to {row['oil_min_30d']} PSI (Lubrication deficit)")
        if row.get("hyd_min_30d", 200.0) <= 180.0:
            drivers.append(f"Hydraulic pressure dropped to {row['hyd_min_30d']} bar (Actuation pressure loss)")

        # Anomaly score checks
        if row.get("latest_anomaly_score", 0.0) >= 0.65:
            drivers.append(f"Elevated telemetry anomaly index ({row['latest_anomaly_score']:.2f})")

        # Component health index
        if row.get("comp_health_index", 100.0) < 65.0:
            drivers.append(f"Subsystem health index degraded to {row['comp_health_index']:.1f}%")

        return drivers[:3]

    def predict_fleet_live(self, db_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
        """Run batch inference on the live fleet components using the latest telemetry snapshot."""
        engineer = TelemetryFeatureEngineer(db_path=db_path)
        latest_features = engineer.extract_latest_fleet_features()

        scored_df = self.predict_features(latest_features)

        # Merge with master aircraft details for rich presentation
        aircraft_df = engineer.db_manager.query_to_df(
            "SELECT aircraft_id, tail_number, model_type, role, squadron_id, operational_status FROM aircraft;"
        )
        comp_df = engineer.db_manager.query_to_df(
            "SELECT component_id, serial_number, status as comp_status FROM components;"
        )

        merged = scored_df.merge(aircraft_df, on="aircraft_id", how="left")
        merged = merged.merge(comp_df, on="component_id", how="left")

        # Sort by predicted risk probability descending
        merged = merged.sort_values(by="predicted_risk_prob", ascending=False).reset_index(drop=True)
        return merged
