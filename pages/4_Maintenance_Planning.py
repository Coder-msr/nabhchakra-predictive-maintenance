"""Module F — Maintenance Planning and Resource Scheduling.

Rule-based maintenance window planning, technician team workload tracking,
supply chain bottleneck identification, and schedule impact simulation.
"""

from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

from src.business_logic.inventory_engine import InventoryEngine
from src.business_logic.scheduler_engine import MaintenanceSchedulerEngine
from src.ui.components import (
    render_header,
    render_kpi_card,
    render_status_badge,
)
from src.ui.session_state import (
    initialize_session,
    load_base_tables,
    load_prioritized_fleet,
)
from src.ui.theme import apply_theme

st.set_page_config(page_title="Maintenance Planning — NABHCHAKRA", page_icon="⚡", layout="wide")
apply_theme()
initialize_session()

render_header(
    title="Maintenance Planning & Resource Allocation",
    subtitle="Technician Bay Capacity, Rule-Based Slotting, and Spare-Parts Bottleneck Detection"
)

# Load data
tables = load_base_tables()
prioritized_df = load_prioritized_fleet()
teams_df = tables["maintenance_teams"]
parts_df = tables["spare_parts"]
schedules_df = tables["maintenance_schedules"]

# Cross-reference schedules with spare parts
enriched_schedules = InventoryEngine.check_schedule_bottlenecks(schedules_df, parts_df)
backlog_info = MaintenanceSchedulerEngine.calculate_maintenance_backlog(enriched_schedules)
teams_status = MaintenanceSchedulerEngine.get_team_workload_status(teams_df, enriched_schedules)

# 1. Backlog Summary Cards
b1, b2, b3, b4 = st.columns(4)
with b1:
    render_kpi_card("Scheduled Work Orders", f"{backlog_info['total_scheduled_events']}", delta="Active Fleet Schedules", delta_type="info")
with b2:
    render_kpi_card("Total Backlog Duration", f"{backlog_info['total_backlog_hours']} hrs", delta="Required Engineering Time", delta_type="warning")
with b3:
    render_kpi_card("Critical Event Backlog", f"{backlog_info['critical_backlog_count']}", delta="Immediate Focus", delta_type="critical")
with b4:
    render_kpi_card("Supply Bottlenecks", f"{backlog_info['bottlenecked_events']}", delta="Delayed by Out-of-Stock Parts", delta_type="critical")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# 2. Maintenance Bay & Technician Capacity Cards
st.markdown('<div class="section-header">Technician Team & Maintenance Bay Utilization</div>', unsafe_allow_html=True)

team_cols = st.columns(len(teams_status))
for idx, (_, team) in enumerate(teams_status.iterrows()):
    with team_cols[idx]:
        st_color = "nominal" if team["capacity_status"] == "Available" else "warning" if team["capacity_status"] == "Moderate Load" else "critical"
        render_kpi_card(
            title=team["team_name"].replace(" Section", "").replace(" Specialist Cell", "").replace(" Depot", ""),
            value=f"{team['utilization_pct']}%",
            delta=f"{team['active_tasks']}/{team['max_concurrent_aircraft']} Bays Busy ({team['available_slots']} Open)",
            delta_type=st_color
        )

# 3. Active & Scheduled Maintenance Work Orders
st.markdown('<div class="section-header">Scheduled Maintenance Work Orders & Parts Readiness</div>', unsafe_allow_html=True)

display_sched = enriched_schedules[[
    "schedule_id", "aircraft_id", "priority_level", "planned_start", "planned_duration_hours",
    "assigned_team_id", "required_part_id", "part_status", "is_bottlenecked", "schedule_status"
]].rename(columns={
    "schedule_id": "Schedule ID",
    "aircraft_id": "Airframe",
    "priority_level": "Priority",
    "planned_start": "Planned Window Start",
    "planned_duration_hours": "Duration (hrs)",
    "assigned_team_id": "Assigned Bay/Team",
    "required_part_id": "Required Part",
    "part_status": "Parts Stock Status",
    "is_bottlenecked": "Supply Hold",
    "schedule_status": "Status"
})

st.dataframe(display_sched, use_container_width=True, hide_index=True)

# 4. Interactive Schedule Proposal Engine
st.markdown('<div class="section-header">Rule-Based Schedule Proposal Engine</div>', unsafe_allow_html=True)

st.write(
    "Generate transparent, automated schedule proposals for unassigned aircraft with **Critical** or **High** "
    "failure risk, matching certified technician bays and evaluating spare parts lead times."
)

if st.button("Generate Optimized Schedule Proposals for At-Risk Airframes", type="primary"):
    proposed_df = MaintenanceSchedulerEngine.propose_maintenance_schedule(
        prioritized_components_df=prioritized_df,
        teams_df=teams_df,
        spare_parts_df=parts_df
    )

    if not proposed_df.empty:
        st.success(f"Generated {len(proposed_df)} rule-based maintenance proposals based on failure risk and team capacity.")
        st.dataframe(
            proposed_df[[
                "schedule_id", "aircraft_id", "component_type", "priority_level",
                "planned_start", "planned_duration_hours", "assigned_team_id",
                "required_part_id", "is_bottlenecked", "estimated_delay_days"
            ]].rename(columns={
                "schedule_id": "Proposal ID",
                "aircraft_id": "Aircraft",
                "component_type": "Subsystem",
                "priority_level": "Priority",
                "planned_start": "Proposed Window Start",
                "planned_duration_hours": "Est. Duration (hrs)",
                "assigned_team_id": "Allocated Team",
                "required_part_id": "Part ID",
                "is_bottlenecked": "Supply Delayed",
                "estimated_delay_days": "Lead Delay (Days)"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No unassigned airframes currently require urgent maintenance.")

st.markdown(
    """
    <div style="margin-top: 24px; padding: 10px; background: rgba(30, 41, 59, 0.4); border-radius: 4px; font-size: 11px; color: #94A3B8;">
        <b>Operational Boundary Note:</b> This module does not perform autonomous military dispatch or flight tasking. All proposals require human maintenance controller sign-off.
    </div>
    """,
    unsafe_allow_html=True
)
