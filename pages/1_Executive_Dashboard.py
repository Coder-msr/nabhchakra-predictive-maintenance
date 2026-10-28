"""Module A — Executive Fleet Dashboard.

High-level operational metrics, fleet readiness indicators, interactive status charts,
and a searchable, filterable aircraft registry.
"""

from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import THEME_COLORS
from src.business_logic.availability_engine import FleetAvailabilityEngine
from src.business_logic.scheduler_engine import MaintenanceSchedulerEngine
from src.ui.components import (
    render_availability_gauge,
    render_header,
    render_kpi_card,
    render_status_badge,
    render_status_donut,
)
from src.ui.session_state import (
    initialize_session,
    load_base_tables,
    load_fleet_readiness,
    load_prioritized_fleet,
)
from src.ui.theme import apply_theme

st.set_page_config(page_title="Executive Fleet Dashboard — NABHCHAKRA", page_icon="⚡", layout="wide")
apply_theme()
initialize_session()

render_header(
    title="Executive Fleet Dashboard",
    subtitle="Operational Availability, Fleet Readiness, and Maintenance Backlog"
)

# Load data
tables = load_base_tables()
readiness = load_fleet_readiness()
prioritized_df = load_prioritized_fleet()
aircraft_df = tables["aircraft"]
schedules_df = tables["maintenance_schedules"]

# Compute required metrics dynamically
total_aircraft = readiness["total_aircraft"]
available_count = readiness["available_status_count"]
maint_count = readiness["maintenance_status_count"]
grounded_count = readiness["grounded_status_count"]
inspect_count = readiness["inspection_status_count"]
unavailable_count = maint_count + grounded_count + inspect_count
avail_pct = readiness["availability_pct"]

# Overdue inspection count
today_str = datetime.now().strftime("%Y-%m-%d")
aircraft_df["is_insp_due"] = aircraft_df["next_inspection_due"] <= today_str
inspection_needed_count = int(aircraft_df["is_insp_due"].sum())

# Elevated risk count
elevated_risk_ac_ids = set(
    prioritized_df[prioritized_df["priority_category"].isin(["Critical", "High"])]["aircraft_id"]
)
elevated_risk_count = len(elevated_risk_ac_ids)

# Backlog metrics
backlog_info = MaintenanceSchedulerEngine.calculate_maintenance_backlog(schedules_df)
backlog_hours = backlog_info["total_backlog_hours"]

# 1. 8 Mandatory KPI Cards in 2 rows
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_kpi_card("Total Aircraft", f"{total_aircraft}", delta="All Squadrons", delta_type="info")
with col2:
    render_kpi_card("Available Aircraft", f"{available_count}", delta=f"{(available_count/total_aircraft)*100:.1f}% of Fleet", delta_type="nominal")
with col3:
    render_kpi_card("Under Maintenance", f"{maint_count}", delta="Active Depot/Line", delta_type="warning")
with col4:
    render_kpi_card("Unavailable Aircraft", f"{unavailable_count}", delta=f"{grounded_count} Grounded", delta_type="critical")

col5, col6, col7, col8 = st.columns(4)
with col5:
    render_kpi_card("Fleet Availability", f"{avail_pct}%", delta=f"{readiness['fmc_count']} FMC / {readiness['pmc_count']} PMC", delta_type="nominal")
with col6:
    render_kpi_card("Inspection Due", f"{inspection_needed_count}", delta="Flight Line Check", delta_type="warning")
with col7:
    render_kpi_card("Elevated Risk", f"{elevated_risk_count}", delta="Predicted Anomaly", delta_type="critical")
with col8:
    render_kpi_card("Maintenance Backlog", f"{backlog_hours} hrs", delta=f"{backlog_info['total_scheduled_events']} Work Orders", delta_type="info")

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# 2. Charts Row: Availability Gauge, Status Donut, Model Availability Bar Chart
c_gauge, c_donut, c_bar = st.columns([1.1, 1.1, 1.8])

with c_gauge:
    st.markdown('<div class="section-header">Availability Rate</div>', unsafe_allow_html=True)
    gauge_fig = render_availability_gauge(avail_pct)
    st.plotly_chart(gauge_fig, use_container_width=True)

with c_donut:
    st.markdown('<div class="section-header">Operational Status</div>', unsafe_allow_html=True)
    donut_fig = render_status_donut({
        "Available": available_count,
        "In Maintenance": maint_count,
        "Under Inspection": inspect_count,
        "Grounded": grounded_count,
    })
    st.plotly_chart(donut_fig, use_container_width=True)

with c_bar:
    st.markdown('<div class="section-header">Availability by Model Type</div>', unsafe_allow_html=True)
    model_avail_df = FleetAvailabilityEngine.get_availability_by_model(aircraft_df, prioritized_df)
    bar_fig = px.bar(
        model_avail_df,
        x="model_type",
        y="availability_pct",
        color="availability_pct",
        color_continuous_scale=[(0, "#EF4444"), (0.6, "#F59E0B"), (1.0, "#10B981")],
        range_color=[40, 100],
        text="availability_pct",
        labels={"model_type": "Aircraft Model", "availability_pct": "Availability (%)"}
    )
    bar_fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    bar_fig.update_layout(
        paper_bgcolor="#1C2541",
        plot_bgcolor="#1C2541",
        height=220,
        margin={"l": 30, "r": 20, "t": 20, "b": 30},
        xaxis=dict(showgrid=False, tickfont=dict(color="#FFFFFF", size=11)),
        yaxis=dict(range=[0, 115], showgrid=True, gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8")),
        coloraxis_showscale=False
    )
    st.plotly_chart(bar_fig, use_container_width=True)

# 3. Searchable, Filterable Aircraft Table
st.markdown('<div class="section-header">Fleet Airframe Registry & Health Status</div>', unsafe_allow_html=True)

# Filters
f1, f2, f3, f4 = st.columns([1.5, 1.5, 1.5, 2.5])
with f1:
    model_filter = st.multiselect("Filter by Model", options=sorted(aircraft_df["model_type"].unique()), default=[])
with f2:
    status_filter = st.multiselect("Filter by Status", options=sorted(aircraft_df["operational_status"].unique()), default=[])
with f3:
    squadron_filter = st.multiselect("Filter by Squadron", options=sorted(aircraft_df["squadron_id"].unique()), default=[])
with f4:
    search_query = st.text_input("Search Aircraft ID or Tail Number", placeholder="e.g. AF-001 or IAF-SU-101")

# Apply filters
filtered_df = aircraft_df.copy()
if model_filter:
    filtered_df = filtered_df[filtered_df["model_type"].isin(model_filter)]
if status_filter:
    filtered_df = filtered_df[filtered_df["operational_status"].isin(status_filter)]
if squadron_filter:
    filtered_df = filtered_df[filtered_df["squadron_id"].isin(squadron_filter)]
if search_query:
    q = search_query.strip().lower()
    filtered_df = filtered_df[
        filtered_df["aircraft_id"].str.lower().str.contains(q) |
        filtered_df["tail_number"].str.lower().str.contains(q)
    ]

# Merge with highest component risk for this aircraft
max_risk_per_ac = prioritized_df.groupby("aircraft_id")["predicted_risk_prob"].max().reset_index()
max_risk_per_ac.columns = ["aircraft_id", "highest_subsystem_risk"]
filtered_df = filtered_df.merge(max_risk_per_ac, on="aircraft_id", how="left")

# Display table
st.dataframe(
    filtered_df[[
        "aircraft_id", "tail_number", "model_type", "role", "squadron_id",
        "total_flight_hours", "total_flight_cycles", "operational_status",
        "last_inspection_date", "next_inspection_due", "highest_subsystem_risk"
    ]].rename(columns={
        "aircraft_id": "Airframe ID",
        "tail_number": "Tail Number",
        "model_type": "Model",
        "role": "Mission Role",
        "squadron_id": "Squadron",
        "total_flight_hours": "Flight Hours",
        "total_flight_cycles": "Cycles",
        "operational_status": "Status",
        "last_inspection_date": "Last Insp.",
        "next_inspection_due": "Next Due",
        "highest_subsystem_risk": "Max Failure Risk"
    }),
    use_container_width=True,
    hide_index=True
)

st.caption(f"Displaying {len(filtered_df)} of {len(aircraft_df)} aircraft records. Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
