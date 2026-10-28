"""Unit tests for Data Preprocessing, Feature Engineering, and Leakage Prevention."""

import numpy as np
import pandas as pd
import pytest
from src.ml.preprocessor import FEATURE_COLUMNS, TARGET_COLUMN, TelemetryFeatureEngineer


@pytest.fixture
def feature_engineer():
    """Instantiate TelemetryFeatureEngineer."""
    return TelemetryFeatureEngineer()


def test_load_data_returns_expected_dataframes(feature_engineer):
    """Verify loading from SQLite returns valid parsed tables."""
    data = feature_engineer.load_data()
    assert "aircraft" in data
    assert "components" in data
    assert "sensor_telemetry" in data
    assert pd.api.types.is_datetime64_any_dtype(data["sensor_telemetry"]["timestamp"])


def test_feature_columns_and_no_missing_values(feature_engineer):
    """Verify generated dataset contains all expected feature columns without NaNs or Infs."""
    full_df = feature_engineer.build_dataset()

    assert not full_df.empty
    assert TARGET_COLUMN in full_df.columns

    for col in FEATURE_COLUMNS:
        assert col in full_df.columns, f"Missing feature column: {col}"
        # No NaNs or Infs
        assert not full_df[col].isna().any(), f"NaN values detected in feature {col}"
        assert not np.isinf(full_df[col]).any(), f"Infinite values detected in feature {col}"


def test_target_is_binary(feature_engineer):
    """Verify target column contains only 0 and 1 values."""
    full_df = feature_engineer.build_dataset()
    unique_targets = set(full_df[TARGET_COLUMN].unique())
    assert unique_targets.issubset({0, 1}), f"Unexpected target classes: {unique_targets}"


def test_zero_leakage_group_split(feature_engineer):
    """Verify group-aware split guarantees zero aircraft overlap between train and test sets."""
    full_df = feature_engineer.build_dataset()
    train_df, test_df = feature_engineer.split_train_test_by_aircraft(full_df, test_size=0.25)

    train_aircraft = set(train_df["aircraft_id"])
    test_aircraft = set(test_df["aircraft_id"])

    # Overlap must be strictly empty
    overlap = train_aircraft.intersection(test_aircraft)
    assert len(overlap) == 0, f"Data leakage detected! Aircraft shared between train and test: {overlap}"
    assert len(train_df) + len(test_df) == len(full_df)


def test_latest_inference_features_scale(feature_engineer):
    """Ensure latest feature extraction returns exactly 140 components for live fleet monitoring."""
    latest_df = feature_engineer.extract_latest_fleet_features()

    assert len(latest_df) == 140
    assert "component_id" in latest_df.columns
    assert "aircraft_id" in latest_df.columns
    for col in FEATURE_COLUMNS:
        assert col in latest_df.columns
