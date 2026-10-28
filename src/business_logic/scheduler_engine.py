"""Rule-Based Maintenance Planning and Scheduling Engine.

Proposes optimal maintenance windows by balancing priority rankings, technician team
specialization and capacity, and spare parts supply constraints.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

from src.business_logic.inventory_engine import InventoryEngine


class MaintenanceSchedulerEngine:
    """Assigns maintenance slots and teams using deterministic, explainable operational rules."""

    @staticmethod
    def calculate_maintenance_backlog(schedules_df: pd.DataFrame) -> Dict:
        """Compute fleet maintenance backlog metrics."""
        if schedules_df.empty:
            return {
                "total_scheduled_events": 0,
                "total_backlog_hours": 0.0,
                "critical_backlog_count": 0,
                "high_backlog_count": 0,
                "bottlenecked_events": 0,
            }

        total_events = len(schedules_df)
        total_hours = float(schedules_df["planned_duration_hours"].sum())
        critical_count = int((schedules_df["priority_level"] == "Critical").sum())
        high_count = int((schedules_df["priority_level"] == "High").sum())
        bottlenecked = int(schedules_df.get("is_bottlenecked", pd.Series([False] * len(schedules_df))).sum())

        return {
            "total_scheduled_events": total_events,
            "total_backlog_hours": round(total_hours, 1),
            "critical_backlog_count": critical_count,
            "high_backlog_count": high_count,
            "bottlenecked_events": bottlenecked,
        }

    @staticmethod
    def get_team_workload_status(
        teams_df: pd.DataFrame,
        schedules_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Compute current workload and available slots for each maintenance team."""
        teams_status = teams_df.copy()

        # Count active / confirmed tasks per team
        active_counts = {}
        if not schedules_df.empty:
            active_sched = schedules_df[schedules_df["schedule_status"].isin(["Confirmed", "In Progress"])]
            active_counts = active_sched["assigned_team_id"].value_counts().to_dict()

        utilization_pcts = []
        available_slots = []
        statuses = []

        for _, team in teams_status.iterrows():
            t_id = team["team_id"]
            max_slots = team["max_concurrent_aircraft"]
            active = active_counts.get(t_id, team.get("current_active_tasks", 0))

            util_pct = round((active / max_slots) * 100, 1) if max_slots > 0 else 100.0
            slots_left = max(0, max_slots - active)

            if slots_left == 0:
                st = "At Capacity"
            elif util_pct >= 50.0:
                st = "Moderate Load"
            else:
                st = "Available"

            utilization_pcts.append(util_pct)
            available_slots.append(slots_left)
            statuses.append(st)

        teams_status["active_tasks"] = [active_counts.get(t_id, 0) for t_id in teams_status["team_id"]]
        teams_status["available_slots"] = available_slots
        teams_status["utilization_pct"] = utilization_pcts
        teams_status["capacity_status"] = statuses

        return teams_status

    @staticmethod
    def propose_maintenance_schedule(
        prioritized_components_df: pd.DataFrame,
        teams_df: pd.DataFrame,
        spare_parts_df: pd.DataFrame,
        start_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Generate optimized proposed maintenance schedules for high/critical priority items."""
        base_time = pd.to_datetime(start_date) if start_date else pd.to_datetime(datetime.now())

        # Filter candidates: Critical or High priority items
        candidates = prioritized_components_df[
            prioritized_components_df["priority_category"].isin(["Critical", "High"])
        ].sort_values(by="priority_score", ascending=False)

        # Match parts
        parts_by_comp = {}
        for _, p in spare_parts_df.iterrows():
            parts_by_comp.setdefault(p["compatible_component_type"], []).append(p)

        # Match teams by specialty
        teams_by_spec = {}
        for _, t in teams_df.iterrows():
            teams_by_spec.setdefault(t["specialty"], []).append(t)

        proposed_records = []
        sched_counter = 100

        for _, item in candidates.iterrows():
            c_type = item["component_type"]
            ac_id = item["aircraft_id"]
            c_id = item["component_id"]
            p_cat = item["priority_category"]

            # Select qualified team
            eligible_teams = teams_by_spec.get(c_type, teams_df.to_dict(orient="records"))
            assigned_team = eligible_teams[0]["team_id"] if eligible_teams else "TEAM-GENERAL"

            # Select required part
            parts_list = parts_by_comp.get(c_type, [])
            req_part = parts_list[0] if len(parts_list) > 0 else None
            part_id = req_part["part_id"] if req_part is not None else None
            is_bottleneck = (req_part["stock_quantity"] == 0) if req_part is not None else False
            delay_days = req_part["lead_time_days"] if (req_part is not None and is_bottleneck) else 0

            # Estimate duration based on component complexity
            dur_map = {
                "Turbofan Engine": 24.0,
                "Hydraulic Actuator": 12.0,
                "Avionics & Radar System": 8.0,
                "Auxiliary Power Unit (APU)": 16.0,
                "Landing Gear Assembly": 16.0,
            }
            duration_hrs = dur_map.get(c_type, 8.0)

            # Planned start: stagger by priority and part delay
            lead_offset = delay_days if is_bottleneck else 0
            priority_offset = 1 if p_cat == "Critical" else 3
            plan_time = base_time + timedelta(days=lead_offset + priority_offset, hours=9)

            proposed_records.append({
                "schedule_id": f"PRP-{sched_counter:04d}",
                "aircraft_id": ac_id,
                "component_id": c_id,
                "component_type": c_type,
                "priority_level": p_cat,
                "planned_start": plan_time.strftime("%Y-%m-%d %H:%M:%S"),
                "planned_duration_hours": duration_hrs,
                "assigned_team_id": assigned_team,
                "required_part_id": part_id,
                "is_bottlenecked": is_bottleneck,
                "estimated_delay_days": delay_days,
                "schedule_status": "Proposed",
            })
            sched_counter += 1

        return pd.DataFrame(proposed_records)
