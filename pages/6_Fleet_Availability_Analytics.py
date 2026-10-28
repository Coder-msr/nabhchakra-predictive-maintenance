"""Module G — Fleet Availability Analytics.

Deep-dive availability metrics (FMC, PMC, NMC), planned vs. unplanned downtime decomposition,
and readiness breakdowns across aircraft models and squadrons.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import THEME_COLORS
from src.business_logic.availability_engine import FleetAvailabilityEngine
from src.ui.components import (
    render_availability_gauge,
    render_header,
    render_kpi_card,
)
from src.ui.session_state import (
    initialize_session,
    load_base_tables,
    load_fleet_readiness,
    load_prioritized_fleet,
)
from src.ui.theme import apply_theme

st.set_page_config(page_title="Fleet Availability Analytics — NABHCHAKRA", page_icon="⚡", layout="wide")
apply_theme()
initialize_session()

render_header(
    title="Fleet Availability & Mission Readiness Analytics",
    subtitle="Mission Capability Ratios, Planned vs. Unplanned Downtime, and Squadron Deployability"
)

# Load data
tables = load_base_tables()
readiness = load_fleet_readiness()
prioritized_df = load_prioritized_fleet()
aircraft_df = tables["aircraft"]
records_df = tables["maintenance_records"]

total_ac = readiness["total_aircraft"]
fmc = readiness["fmc_count"]
pmc = readiness["pmc_count"]
nmc = readiness["nmc_count"]
avail_pct = readiness["availability_pct"]

# Downtime decomposition
downtime_info = FleetAvailabilityEngine.calculate_downtime_decomposition(records_df, aircraft_df)

# 1. Mission Capability KPIs
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    render_kpi_card("Readiness Index", f"{avail_pct}%", delta="Overall Fleet Availability", delta_type="nominal")
with c2:
    render_kpi_card("Fully Mission Capable (FMC)", f"{fmc}", delta=f"{readiness['fmc_pct']}% of Fleet", delta_type="nominal")
with c3:
    render_kpi_card("Partially Capable (PMC)", f"{pmc}", delta=f"{readiness['pmc_pct']}% Limited Sortie", delta_type="warning")
with c4:
    render_kpi_card("Non-Mission Capable (NMC)", f"{nmc}", delta=f"{readiness['nmc_pct']}% Grounded/Maint", delta_type="critical")
with c5:
    render_kpi_card("Total Logged Downtime", f"{downtime_info['total_downtime_hours']} hrs", delta=f"{downtime_info['unplanned_pct']}% Unplanned", delta_type="warning")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# 2. Downtime Decomposition + Squadron Readiness
col_dt, col_sq = st.columns([1.5, 2.0])

with col_dt:
    st.markdown('<div class="section-header">Downtime Decomposition (Planned vs Unplanned)</div>', unsafe_allow_html=True)
    dt_fig = go.Figure(data=[go.Pie(
        labels=["Planned Preventative Maintenance", "Unplanned Component Failures"],
        values=[downtime_info["planned_hours"], downtime_info["unplanned_hours"]],
        hole=0.5,
        marker=dict(colors=[THEME_COLORS["status_info"], THEME_COLORS["status_critical"]], line=dict(color="#0B132B", width=2)),
        textinfo="label+percent",
        textfont=dict(color="#FFFFFF", size=11)
    )])
    dt_fig.update_layout(
        paper_bgcolor="#1C2541",
        plot_bgcolor="#1C2541",
        height=260,
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        showlegend=False
    )
    st.plotly_chart(dt_fig, use_container_width=True)
    st.caption(f"Planned Maintenance: {downtime_info['planned_hours']} hrs | Unplanned Rectification: {downtime_info['unplanned_hours']} hrs")

with col_sq:
    st.markdown('<div class="section-header">Availability Rate Across Operational Squadrons</div>', unsafe_allow_html=True)
    sq_avail_df = FleetAvailabilityEngine.get_availability_by_squadron(aircraft_df, prioritized_df)
    sq_fig = px.bar(
        sq_avail_df,
        x="squadron_id",
        y="availability_pct",
        color="availability_pct",
        color_continuous_scale=[(0, "#EF4444"), (0.6, "#F59E0B"), (1.0, "#10B981")],
        range_color=[50, 100],
        text="availability_pct",
        labels={"squadron_id": "Squadron", "availability_pct": "Availability (%)"}
    )
    sq_fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    sq_fig.update_layout(
        paper_bgcolor="#1C2541",
        plot_bgcolor="#1C2541",
        height=260,
        margin={"l": 20, "r": 20, "t": 20, "b": 40},
        xaxis=dict(showgrid=False, tickfont=dict(color="#FFFFFF", size=10)),
        yaxis=dict(range=[0, 115], showgrid=True, gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8")),
        coloraxis_showscale=False
    )
    st.plotly_chart(sq_fig, use_container_width=True)

# 3. Model Breakdown & Projected 30-Day Availability Trajectory
col_mod, col_proj = st.columns([1.5, 2.0])

with col_mod:
    st.markdown('<div class="section-header">Capability Matrix by Airframe Model</div>', unsafe_allow_html=True)
    model_df = FleetAvailabilityEngine.get_availability_by_model(aircraft_df, prioritized_df)
    st.dataframe(
        model_df.rename(columns={
            "model_type": "Model", "role": "Role", "total_aircraft": "Total",
            "fmc": "FMC", "pmc": "PMC", "nmc": "NMC", "availability_pct": "Avail. (%)"
        }),
        use_container_width=True,
        hide_index=True
    )

with col_proj:
    st.markdown('<div class="section-header">Projected 30-Day Fleet Availability Trajectory</div>', unsafe_allow_html=True)
    # Synthetic forecast simulation curve
    days = list(range(0, 31, 3))
    # Simulated recovery as scheduled maintenance finishes vs new wear
    projected_avail = [
        round(avail_pct + (i * 0.45) - ((i**1.4) * 0.04), 1) for i in days
    ]
    proj_df = pd.DataFrame({"Days Forward": days, "Projected Availability (%)": projected_avail})

    proj_fig = px.line(
        proj_df,
        x="Days Forward",
        y="Projected Availability (%)",
        markers=True,
        line_shape="spline"
    )
    proj_fig.update_traces(line=dict(color="#5BC0BE", width=3), marker=dict(size=6, color="#6FFFE9"))
    proj_fig.add_hline(y=75.0, line_dash="dash", line_color="#10B981", annotation_text="Benchmark Threshold (75%)")
    proj_fig.update_layout(
        paper_bgcolor="#1C2541",
        plot_bgcolor="#1C2541",
        height=260,
        margin={"l": 30, "r": 20, "t": 20, "b": 30},
        xaxis=dict(showgrid=True, gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8")),
        yaxis=dict(range=[50, 95], showgrid=True, gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8")),
    )
    st.plotly_chart(proj_fig, use_container_width=True)
    st.caption("Forecast assumption: Scheduled depot turnarounds completed on time without emergency parts stockouts.")
