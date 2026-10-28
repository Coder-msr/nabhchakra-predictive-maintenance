"""Unit tests for the Machine Learning Pipeline: Training, Inference & Explainability."""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest

from config.settings import METADATA_PATH, MODEL_PATH
from src.ml.predictor import MaintenancePredictor
from src.ml.preprocessor import FEATURE_COLUMNS
from src.ml.trainer import train_and_evaluate_models


@pytest.fixture(scope="module")
def trained_artifacts():
    """Ensure models and metadata exist."""
    metadata = train_and_evaluate_models()
    return metadata


def test_model_and_metadata_files_exist(trained_artifacts):
    """Verify model joblib and metadata json exist and are non-empty."""
    assert MODEL_PATH.exists(), f"Model file missing: {MODEL_PATH}"
    assert METADATA_PATH.exists(), f"Metadata file missing: {METADATA_PATH}"

    # Verify model is loadable
    model = joblib.load(MODEL_PATH)
    assert hasattr(model, "predict_proba"), "Loaded model must have predict_proba method"

    # Verify metadata contents
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    metrics = meta["evaluation_metrics"]
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "roc_auc" in metrics
    assert "confusion_matrix" in metrics
    assert len(meta["top_features"]) > 0


def test_predictor_probability_bounds_and_tiers(trained_artifacts):
    """Ensure predicted probabilities are within [0.0, 1.0] and risk tiers map accurately."""
    predictor = MaintenancePredictor()

    # Synthetic test input: Row 0 is Nominal, Row 1 is Severe Degradation
    nominal_row = {col: 0.0 for col in FEATURE_COLUMNS}
    nominal_row.update({
        "temp_mean_30d": 710.0, "temp_max_30d": 740.0,
        "vib_mean_30d": 1.2, "vib_max_30d": 1.6,
        "oil_mean_30d": 65.0, "oil_min_30d": 60.0,
        "hyd_mean_30d": 205.0, "hyd_min_30d": 200.0,
        "anomaly_score_mean_14d": 0.05, "anomaly_score_max_14d": 0.10, "latest_anomaly_score": 0.05,
        "comp_health_index": 98.0, "comp_operating_hours": 400.0,
        "aircraft_flight_hours": 800.0, "aircraft_flight_cycles": 500,
        "comp_type_Turbofan Engine": 1,
    })

    degraded_row = {col: 0.0 for col in FEATURE_COLUMNS}
    degraded_row.update({
        "temp_mean_30d": 880.0, "temp_max_30d": 940.0, "temp_trend_slope": 1.2,
        "vib_mean_30d": 3.8, "vib_max_30d": 5.4, "vib_trend_slope": 0.08,
        "oil_mean_30d": 38.0, "oil_min_30d": 28.0,
        "hyd_mean_30d": 175.0, "hyd_min_30d": 160.0,
        "anomaly_score_mean_14d": 0.85, "anomaly_score_max_14d": 0.96, "latest_anomaly_score": 0.94,
        "comp_health_index": 35.0, "comp_operating_hours": 2800.0,
        "aircraft_flight_hours": 2900.0, "aircraft_flight_cycles": 1900,
        "comp_type_Turbofan Engine": 1,
    })

    synthetic_input = pd.DataFrame([nominal_row, degraded_row])

    scored = predictor.predict_features(synthetic_input)

    probs = scored["predicted_risk_prob"].values
    assert (probs >= 0.0).all() and (probs <= 1.0).all(), f"Probabilities out of bounds: {probs}"
    assert scored.loc[1, "predicted_risk_prob"] >= scored.loc[0, "predicted_risk_prob"]

    # Verify tier mapping
    assert MaintenancePredictor.assign_risk_tier(0.15) == "Low"
    assert MaintenancePredictor.assign_risk_tier(0.45) == "Moderate"
    assert MaintenancePredictor.assign_risk_tier(0.75) == "Elevated"
    assert MaintenancePredictor.assign_risk_tier(0.92) == "Critical"


def test_explainability_identifies_risk_drivers(trained_artifacts):
    """Ensure explain_component_risk highlights exceeding engineering thresholds."""
    predictor = MaintenancePredictor()

    degraded_row = pd.Series({
        "temp_max_30d": 915.0,
        "vib_max_30d": 4.2,
        "oil_min_30d": 32.0,
        "hyd_min_30d": 172.0,
        "latest_anomaly_score": 0.88,
        "comp_health_index": 45.0,
    })

    drivers = predictor.explain_component_risk(degraded_row)
    assert len(drivers) > 0
    # Check that temperature or vibration or pressure is highlighted
    combined = " ".join(drivers)
    assert any(term in combined for term in ["temperature", "Vibration", "pressure", "anomaly", "health"])


def test_predict_fleet_live_scale_and_sorting(trained_artifacts):
    """Verify live fleet inference returns all 140 components sorted descending by risk."""
    predictor = MaintenancePredictor()
    fleet_scored = predictor.predict_fleet_live()

    assert len(fleet_scored) == 140
    assert "aircraft_id" in fleet_scored.columns
    assert "component_id" in fleet_scored.columns
    assert "predicted_risk_prob" in fleet_scored.columns
    assert "risk_tier" in fleet_scored.columns
    assert "risk_drivers" in fleet_scored.columns

    # Check sorting descending
    probs = fleet_scored["predicted_risk_prob"].tolist()
    assert probs == sorted(probs, reverse=True), "Fleet predictions must be sorted descending by risk"
