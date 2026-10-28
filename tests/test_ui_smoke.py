"""Smoke tests for Streamlit UI modules, pages, components, and data caching."""

import ast
from pathlib import Path
import pandas as pd
import pytest

from config.settings import BASE_DIR
from src.ui.components import (
    render_availability_gauge,
    render_status_badge,
    render_status_donut,
    render_telemetry_chart,
)
from src.ui.session_state import (
    load_base_tables,
    load_fleet_readiness,
    load_live_ml_predictions,
    load_prioritized_fleet,
)


def test_all_pages_exist_and_syntax_is_valid():
    """Verify that all Streamlit page scripts exist and have valid Python syntax."""
    pages_dir = BASE_DIR / "pages"
    assert pages_dir.exists()

    expected_pages = [
        "1_Executive_Dashboard.py",
        "2_Fleet_Health_Monitoring.py",
        "3_Predictive_Maintenance.py",
        "4_Maintenance_Planning.py",
        "5_Spare_Parts_Inventory.py",
        "6_Fleet_Availability_Analytics.py",
        "8_Digital_Twin_View.py",
        "9_Model_Evaluation.py",
    ]

    # Check app.py
    app_path = BASE_DIR / "app.py"
    assert app_path.exists(), "app.py must exist"
    ast.parse(app_path.read_text(encoding="utf-8"))

    # Check each page in pages/
    for page_name in expected_pages:
        page_file = pages_dir / page_name
        assert page_file.exists(), f"Page {page_name} missing"
        source = page_file.read_text(encoding="utf-8")
        # ast.parse raises SyntaxError if invalid
        ast.parse(source)


def test_ui_components_render_valid_figures():
    """Verify that UI chart component generators produce valid Plotly figures."""
    # Gauge
    gauge = render_availability_gauge(78.5)
    assert gauge is not None
    assert gauge.data[0].type == "indicator"

    # Status donut
    donut = render_status_donut({"Available": 20, "In Maintenance": 4, "Grounded": 1})
    assert donut is not None
    assert donut.data[0].type == "pie"

    # Telemetry chart
    mock_telemetry = pd.DataFrame({
        "timestamp": pd.date_range("2026-10-01", periods=10, freq="D"),
        "engine_temp_c": [710.0 + i for i in range(10)]
    })
    chart = render_telemetry_chart(
        mock_telemetry,
        sensor_col="engine_temp_c",
        sensor_label="Temperature",
        unit="°C",
        warning_thresh=875.0,
        critical_thresh=930.0
    )
    assert chart is not None

    # Status badge
    badge = render_status_badge("Available")
    assert "badge" in badge
    assert "Available" in badge


def test_session_state_data_loaders():
    """Verify session state data loader functions return populated data."""
    tables = load_base_tables()
    assert len(tables["aircraft"]) == 28
    assert len(tables["components"]) == 140

    predictions = load_live_ml_predictions()
    assert len(predictions) == 140
    assert "predicted_risk_prob" in predictions.columns

    prioritized = load_prioritized_fleet()
    assert len(prioritized) == 140
    assert "priority_score" in prioritized.columns

    readiness = load_fleet_readiness()
    assert readiness["total_aircraft"] == 28
    assert readiness["availability_pct"] > 0
