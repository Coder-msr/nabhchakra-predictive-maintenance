"""Synthetic Maintenance Records, Teams, and Schedules Generator.

Generates maintenance teams, historical work orders, and forward-looking maintenance
schedules linked to specific aircraft, components, and spare parts.
"""

from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple
import pandas as pd

from config.settings import RANDOM_SEED


def generate_maintenance_teams_data() -> pd.DataFrame:
    """Generate technical maintenance specialist teams."""
    teams = [
        {
            "team_id": "TEAM-PROPULSION-A",
            "team_name": "Propulsion Systems Bay Alpha",
            "specialty": "Turbofan Engine",
            "technician_count": 6,
            "max_concurrent_aircraft": 2,
            "current_active_tasks": 1,
        },
        {
            "team_id": "TEAM-PROPULSION-B",
            "team_name": "Propulsion Systems Bay Bravo",
            "specialty": "Turbofan Engine",
            "technician_count": 5,
            "max_concurrent_aircraft": 2,
            "current_active_tasks": 0,
        },
        {
            "team_id": "TEAM-AVIONICS",
            "team_name": "Avionics & Radar Specialist Cell",
            "specialty": "Avionics & Radar System",
            "technician_count": 4,
            "max_concurrent_aircraft": 2,
            "current_active_tasks": 1,
        },
        {
            "team_id": "TEAM-HYDRAULICS",
            "team_name": "Hydraulic & Flight Control Section",
            "specialty": "Hydraulic Actuator",
            "technician_count": 4,
            "max_concurrent_aircraft": 2,
            "current_active_tasks": 1,
        },
        {
            "team_id": "TEAM-AIRFRAME-GEAR",
            "team_name": "Airframe & Landing Gear Depot",
            "specialty": "Landing Gear Assembly",
            "technician_count": 5,
            "max_concurrent_aircraft": 3,
            "current_active_tasks": 0,
        },
    ]
    return pd.DataFrame(teams)


def generate_maintenance_records_and_schedules(
    aircraft_df: pd.DataFrame,
    components_df: pd.DataFrame,
    parts_df: pd.DataFrame,
    teams_df: pd.DataFrame,
    seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate historical maintenance records and forward maintenance schedules.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (maintenance_records_df, maintenance_schedules_df)
    """
    random.seed(seed)
    base_date = datetime(2026, 10, 28, 12, 0, 0)

    records: List[Dict] = []
    schedules: List[Dict] = []

    record_counter = 1
    schedule_counter = 1

    # Team mapping by specialty
    teams_by_spec = {}
    for _, t in teams_df.iterrows():
        teams_by_spec.setdefault(t["specialty"], []).append(t["team_id"])

    # Part mapping by component type
    parts_by_comp = {}
    for _, p in parts_df.iterrows():
        parts_by_comp.setdefault(p["compatible_component_type"], []).append(p["part_id"])

    # 1. HISTORICAL MAINTENANCE RECORDS (Past 90 days)
    for _, ac in aircraft_df.iterrows():
        ac_id = ac["aircraft_id"]
        ac_components = components_df[components_df["aircraft_id"] == ac_id]

        # 2 to 5 historical maintenance events per aircraft
        num_past_events = random.randint(2, 5)
        for _ in range(num_past_events):
            days_ago = random.randint(3, 88)
            event_date = base_date - timedelta(days=days_ago)
            start_str = event_date.strftime("%Y-%m-%d %H:%M:%S")

            # Duration: 4 to 36 hours
            duration_hrs = random.choice([4.0, 8.0, 16.0, 24.0, 48.0])
            end_date = event_date + timedelta(hours=duration_hrs)
            end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

            # Pick a component
            comp = ac_components.sample(1).iloc[0]
            comp_id = comp["component_id"]
            comp_type = comp["component_type"]

            eligible_teams = teams_by_spec.get(comp_type, list(teams_df["team_id"]))
            team_id = random.choice(eligible_teams)

            m_type = random.choice(["Scheduled", "Scheduled", "Pre-Flight Inspection", "Unscheduled"])
            action = f"Servicing and diagnostic calibration performed on {comp_type}."

            records.append({
                "record_id": f"MTR-{record_counter:04d}",
                "aircraft_id": ac_id,
                "component_id": comp_id,
                "maintenance_type": m_type,
                "start_time": start_str,
                "end_time": end_str,
                "technician_team_id": team_id,
                "action_taken": action,
                "status": "Completed",
                "notes": "Standard procedural sign-off; telemetry within limits post-service.",
            })
            record_counter += 1

        # In-Progress Maintenance for currently In Maintenance / Grounded aircraft
        if ac["operational_status"] in ("In Maintenance", "Grounded"):
            # Ongoing maintenance record
            comp = ac_components.sample(1).iloc[0]
            comp_id = comp["component_id"]
            comp_type = comp["component_type"]
            team_id = random.choice(teams_by_spec.get(comp_type, list(teams_df["team_id"])))

            start_str = (base_date - timedelta(hours=random.randint(6, 48))).strftime("%Y-%m-%d %H:%M:%S")

            records.append({
                "record_id": f"MTR-{record_counter:04d}",
                "aircraft_id": ac_id,
                "component_id": comp_id,
                "maintenance_type": "Unscheduled" if ac["operational_status"] == "Grounded" else "Scheduled",
                "start_time": start_str,
                "end_time": None,  # Ongoing
                "technician_team_id": team_id,
                "action_taken": f"Undergoing active depot rectification for {comp_type}.",
                "status": "In Progress",
                "notes": "Awaiting final sensor calibration and engine run-up checks.",
            })
            record_counter += 1

    # 2. UPCOMING MAINTENANCE SCHEDULES
    # Schedule maintenance for aircraft that are Grounded, In Maintenance, Under Inspection, or have low health
    candidate_aircraft = aircraft_df[
        (aircraft_df["operational_status"].isin(["Grounded", "In Maintenance", "Under Inspection"])) |
        (aircraft_df["total_flight_hours"] > 2400)
    ]

    for _, ac in candidate_aircraft.iterrows():
        ac_id = ac["aircraft_id"]
        ac_components = components_df[components_df["aircraft_id"] == ac_id]

        # Target degraded component or sample
        degraded = ac_components[ac_components["health_index"] < 75.0]
        comp = degraded.iloc[0] if not degraded.empty else ac_components.sample(1).iloc[0]
        comp_id = comp["component_id"]
        comp_type = comp["component_type"]

        # Planned date (within next 1 to 14 days)
        plan_days = random.randint(1, 14)
        planned_start = (base_date + timedelta(days=plan_days, hours=random.randint(8, 14))).strftime("%Y-%m-%d %H:%M:%S")

        # Priority level
        if ac["operational_status"] == "Grounded" or comp["health_index"] < 50.0:
            priority = "Critical"
        elif ac["operational_status"] == "In Maintenance" or comp["health_index"] < 70.0:
            priority = "High"
        else:
            priority = random.choice(["Medium", "Low"])

        # Match team and required part
        team_id = random.choice(teams_by_spec.get(comp_type, list(teams_df["team_id"])))
        parts = parts_by_comp.get(comp_type, [])
        part_id = random.choice(parts) if parts else None

        schedules.append({
            "schedule_id": f"SCH-{schedule_counter:04d}",
            "aircraft_id": ac_id,
            "component_id": comp_id,
            "planned_start": planned_start,
            "planned_duration_hours": float(random.choice([8.0, 12.0, 24.0, 48.0])),
            "priority_level": priority,
            "required_part_id": part_id,
            "assigned_team_id": team_id,
            "schedule_status": "Confirmed" if priority in ("Critical", "High") else "Proposed",
        })
        schedule_counter += 1

    records_df = pd.DataFrame(records)
    schedules_df = pd.DataFrame(schedules)

    return records_df, schedules_df
