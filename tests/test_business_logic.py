"""Unit tests for Core Business Logic Engines: Priority, Inventory, Scheduler, and Availability."""

import pandas as pd
import pytest

from src.business_logic.availability_engine import FleetAvailabilityEngine
from src.business_logic.inventory_engine import InventoryEngine
from src.business_logic.priority_engine import PriorityEngine
from src.business_logic.scheduler_engine import MaintenanceSchedulerEngine
from src.database.db_manager import DatabaseManager


@pytest.fixture
def db_tables():
    """Load tables from SQLite database."""
    db = DatabaseManager()
    return {
        "aircraft": db.query_to_df("SELECT * FROM aircraft;"),
        "components": db.query_to_df("SELECT * FROM components;"),
        "spare_parts": db.query_to_df("SELECT * FROM spare_parts;"),
        "maintenance_teams": db.query_to_df("SELECT * FROM maintenance_teams;"),
        "maintenance_records": db.query_to_df("SELECT * FROM maintenance_records;"),
        "maintenance_schedules": db.query_to_df("SELECT * FROM maintenance_schedules;"),
    }


def test_priority_engine_scoring_and_bounds():
    """Verify PriorityEngine calculates accurate composite scores and categories."""
    engine = PriorityEngine()

    # Overdue critical failure risk
    res_high = engine.assess_component_priority(
        predicted_risk_prob=0.88,
        next_inspection_due="2020-01-01",  # Overdue
        spare_part_status="Out of Stock",
        component_type="Turbofan Engine"
    )
    assert res_high["priority_score"] >= 0.70
    assert res_high["priority_category"] == "Critical"
    assert "diagnostics" in res_high["action_recommendation"]
    assert "risk_contribution" in res_high["score_breakdown"]

    # Low risk nominal component
    res_low = engine.assess_component_priority(
        predicted_risk_prob=0.05,
        next_inspection_due="2030-01-01",  # Far in future
        spare_part_status="In Stock",
        component_type="Auxiliary Power Unit (APU)"
    )
    assert res_low["priority_score"] < 0.40
    assert res_low["priority_category"] in ("Low", "Medium")


def test_inventory_engine_summary_and_bottlenecks(db_tables):
    """Verify inventory analytics and bottleneck detection in maintenance schedules."""
    engine = InventoryEngine()
    parts_df = db_tables["spare_parts"]
    schedules_df = db_tables["maintenance_schedules"]

    summary = engine.get_inventory_summary(parts_df)
    assert summary["total_part_types"] == len(parts_df)
    assert summary["out_of_stock_count"] >= 1
    assert summary["total_valuation_inr"] > 0
    assert 0.0 <= summary["stock_health_pct"] <= 100.0

    # Bottleneck check
    enriched_schedules = engine.check_schedule_bottlenecks(schedules_df, parts_df)
    assert "is_bottlenecked" in enriched_schedules.columns
    assert "estimated_delay_days" in enriched_schedules.columns

    # In-memory stock simulation
    part_id = parts_df.iloc[0]["part_id"]
    simulated_df = engine.simulate_stock_change(parts_df, part_id, delta_quantity=+10)
    orig_qty = parts_df.loc[parts_df["part_id"] == part_id, "stock_quantity"].values[0]
    new_qty = simulated_df.loc[simulated_df["part_id"] == part_id, "stock_quantity"].values[0]
    assert new_qty == orig_qty + 10


def test_scheduler_engine_backlog_and_proposals(db_tables):
    """Verify maintenance backlog metrics and proposed schedule generation."""
    scheduler = MaintenanceSchedulerEngine()
    schedules_df = db_tables["maintenance_schedules"]
    teams_df = db_tables["maintenance_teams"]
    parts_df = db_tables["spare_parts"]

    # Backlog calculation
    backlog = scheduler.calculate_maintenance_backlog(schedules_df)
    assert backlog["total_scheduled_events"] == len(schedules_df)
    assert backlog["total_backlog_hours"] >= 0.0

    # Team workload
    team_status = scheduler.get_team_workload_status(teams_df, schedules_df)
    assert "utilization_pct" in team_status.columns
    assert "capacity_status" in team_status.columns

    # Propose schedules from mock candidate items
    mock_candidates = pd.DataFrame([
        {
            "aircraft_id": "AF-001",
            "component_id": "CMP-0001",
            "component_type": "Turbofan Engine",
            "priority_category": "Critical",
            "priority_score": 0.82,
        },
        {
            "aircraft_id": "AF-002",
            "component_id": "CMP-0006",
            "component_type": "Hydraulic Actuator",
            "priority_category": "High",
            "priority_score": 0.65,
        }
    ])
    proposed = scheduler.propose_maintenance_schedule(mock_candidates, teams_df, parts_df)
    assert len(proposed) == 2
    assert "schedule_id" in proposed.columns
    assert "assigned_team_id" in proposed.columns
    assert proposed.iloc[0]["planned_duration_hours"] > 0


def test_fleet_availability_math(db_tables):
    """Verify FMC, PMC, NMC sum to total fleet and availability % is mathematically sound."""
    aircraft_df = db_tables["aircraft"]
    avail_engine = FleetAvailabilityEngine()

    result = avail_engine.calculate_current_availability(aircraft_df)

    total = result["total_aircraft"]
    fmc = result["fmc_count"]
    pmc = result["pmc_count"]
    nmc = result["nmc_count"]

    assert total == len(aircraft_df)
    assert fmc + pmc + nmc == total, f"FMC ({fmc}) + PMC ({pmc}) + NMC ({nmc}) != Total ({total})"

    expected_avail = round(((fmc + 0.5 * pmc) / total) * 100, 1)
    assert result["availability_pct"] == expected_avail
    assert 0.0 <= result["availability_pct"] <= 100.0

    # Model and squadron groupings
    model_df = avail_engine.get_availability_by_model(aircraft_df)
    assert len(model_df) == aircraft_df["model_type"].nunique()
    assert (model_df["availability_pct"] >= 0.0).all()
    assert (model_df["availability_pct"] <= 100.0).all()

    # Downtime decomposition
    decomp = avail_engine.calculate_downtime_decomposition(db_tables["maintenance_records"], aircraft_df)
    assert decomp["total_downtime_hours"] > 0
    assert abs((decomp["planned_pct"] + decomp["unplanned_pct"]) - 100.0) < 0.5
