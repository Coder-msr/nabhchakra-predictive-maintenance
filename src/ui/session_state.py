"""Centralized Session State and Cached Data Access for Streamlit."""

from typing import Dict, Tuple
import pandas as pd
import streamlit as st

from config.settings import DB_PATH
from src.business_logic.availability_engine import FleetAvailabilityEngine
from src.business_logic.inventory_engine import InventoryEngine
from src.business_logic.priority_engine import PriorityEngine
from src.business_logic.scheduler_engine import MaintenanceSchedulerEngine
from src.database.db_manager import DatabaseManager
from src.ml.predictor import MaintenancePredictor


@st.cache_data(ttl=300)
def load_base_tables() -> Dict[str, pd.DataFrame]:
    """Load core relational tables from SQLite with 5-minute caching."""
    db = DatabaseManager(DB_PATH)
    return {
        "aircraft": db.query_to_df("SELECT * FROM aircraft;"),
        "components": db.query_to_df("SELECT * FROM components;"),
        "sensor_telemetry": db.query_to_df("SELECT * FROM sensor_telemetry ORDER BY timestamp ASC;"),
        "fault_events": db.query_to_df("SELECT * FROM fault_events ORDER BY detected_timestamp DESC;"),
        "spare_parts": db.query_to_df("SELECT * FROM spare_parts;"),
        "maintenance_teams": db.query_to_df("SELECT * FROM maintenance_teams;"),
        "maintenance_records": db.query_to_df("SELECT * FROM maintenance_records ORDER BY start_time DESC;"),
        "maintenance_schedules": db.query_to_df("SELECT * FROM maintenance_schedules ORDER BY planned_start ASC;"),
    }


@st.cache_data(ttl=300)
def load_live_ml_predictions() -> pd.DataFrame:
    """Run live batch ML inference across all fleet components."""
    predictor = MaintenancePredictor()
    return predictor.predict_fleet_live()


@st.cache_data(ttl=300)
def load_prioritized_fleet() -> pd.DataFrame:
    """Evaluate multi-criteria maintenance priority for all components."""
    tables = load_base_tables()
    predictions = load_live_ml_predictions()
    engine = PriorityEngine()
    return engine.evaluate_fleet_priorities(
        scored_fleet_df=predictions,
        spare_parts_df=tables["spare_parts"],
        aircraft_df=tables["aircraft"],
    )


@st.cache_data(ttl=300)
def load_fleet_readiness() -> Dict:
    """Calculate authoritative FMC/PMC/NMC fleet availability KPIs."""
    tables = load_base_tables()
    prioritized = load_prioritized_fleet()
    engine = FleetAvailabilityEngine()
    return engine.calculate_current_availability(
        aircraft_df=tables["aircraft"],
        prioritized_components_df=prioritized,
    )


def initialize_session():
    """Ensure baseline data is loaded into Streamlit session state."""
    if "is_simulation_active" not in st.session_state:
        st.session_state["is_simulation_active"] = False
        st.session_state["active_scenario_name"] = "Baseline Operational Fleet"

    if "simulated_tables" not in st.session_state:
        st.session_state["simulated_tables"] = None


def clear_ui_cache():
    """Clear cached data functions."""
    load_base_tables.clear()
    load_live_ml_predictions.clear()
    load_prioritized_fleet.clear()
    load_fleet_readiness.clear()
