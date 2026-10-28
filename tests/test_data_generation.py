"""Unit tests for the Synthetic Data Generation Engine."""

import pytest
import pandas as pd
from config.settings import COMPONENT_TYPES, RANDOM_SEED
from src.database.db_manager import DatabaseManager
from src.data_generation.fleet_generator import generate_fleet_data
from src.data_generation.generator_runner import run_full_data_generation
from src.data_generation.inventory_data import generate_spare_parts_data
from src.data_generation.sensor_generator import generate_sensor_telemetry_and_faults


def test_generation_reproducibility():
    """Verify that using the same seed produces identical fleet and component records."""
    ac1, comp1 = generate_fleet_data(seed=42)
    ac2, comp2 = generate_fleet_data(seed=42)

    pd.testing.assert_frame_equal(ac1, ac2)
    pd.testing.assert_frame_equal(comp1, comp2)


def test_fleet_scale_and_component_distribution():
    """Ensure exactly 28 aircraft and 5 components per aircraft (total 140) are generated."""
    aircraft_df, components_df = generate_fleet_data(seed=RANDOM_SEED)

    assert len(aircraft_df) == 28
    assert len(components_df) == 140

    # Ensure each aircraft has all 5 required component types
    for ac_id, group in components_df.groupby("aircraft_id"):
        types = set(group["component_type"])
        assert types == set(COMPONENT_TYPES), f"Aircraft {ac_id} missing some component types"


def test_telemetry_ranges_and_anomalies():
    """Verify telemetry features lie within plausible limits and contain both normal and anomaly instances."""
    aircraft_df, components_df = generate_fleet_data(seed=RANDOM_SEED)
    telemetry_df, faults_df = generate_sensor_telemetry_and_faults(
        aircraft_df, components_df, days=30, interval_days=2, seed=RANDOM_SEED
    )

    assert not telemetry_df.empty
    assert (telemetry_df["engine_temp_c"] >= 500.0).all()
    assert (telemetry_df["engine_temp_c"] <= 1050.0).all()
    assert (telemetry_df["vibration_rms"] > 0.0).all()
    assert (telemetry_df["oil_pressure_psi"] > 0.0).all()
    assert (telemetry_df["hydraulic_pressure_bar"] > 0.0).all()

    # Ensure non-trivial anomaly distribution
    anomaly_counts = telemetry_df["is_anomaly"].value_counts().to_dict()
    assert anomaly_counts.get(0, 0) > 0, "Must have normal telemetry points"
    assert anomaly_counts.get(1, 0) > 0, "Must have anomalous telemetry points"

    # Ensure fault events reference valid components
    if not faults_df.empty:
        valid_comp_ids = set(components_df["component_id"])
        assert faults_df["component_id"].isin(valid_comp_ids).all()


def test_spare_parts_coverage_and_shortages():
    """Verify all component types are represented and that stockout scenarios exist."""
    parts_df = generate_spare_parts_data(seed=RANDOM_SEED)

    assert not parts_df.empty
    covered_components = set(parts_df["compatible_component_type"])
    assert covered_components == set(COMPONENT_TYPES)

    # Check for Out of Stock and Low Stock parts for realistic supply chain simulation
    statuses = set(parts_df["status"])
    assert "In Stock" in statuses
    assert "Low Stock" in statuses
    assert "Out of Stock" in statuses


def test_full_pipeline_seeds_database(tmp_path):
    """Verify that run_full_data_generation populates an isolated SQLite database cleanly."""
    test_db_path = tmp_path / "test_pipeline.db"
    tables, counts = run_full_data_generation(
        seed=RANDOM_SEED,
        export_csv=False,
        seed_db=True,
        db_path=test_db_path
    )

    db = DatabaseManager(test_db_path)
    db_counts = db.get_table_counts()

    assert db_counts["aircraft"] == 28
    assert db_counts["components"] == 140
    assert db_counts["sensor_telemetry"] > 5000
    assert db_counts["spare_parts"] >= 15
    assert db_counts["maintenance_teams"] == 5
    assert db_counts["maintenance_records"] > 50
    assert db_counts["maintenance_schedules"] > 5
