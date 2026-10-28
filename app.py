"""NABHCHAKRA — Air Power Decision Platform Main Entrypoint.

Synthetic Non-Operational Research & Demonstration Hackathon Prototype.
"""

import streamlit as st

from config.settings import APP_SUBTITLE, APP_TITLE, DISCLAIMER_TEXT
from src.ui.components import (
    render_availability_gauge,
    render_header,
    render_kpi_card,
    render_status_donut,
)
from src.ui.session_state import (
    initialize_session,
    load_base_tables,
    load_fleet_readiness,
    load_prioritized_fleet,
)
from src.ui.theme import apply_theme

# Page configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom dark navy aerospace theme
apply_theme()
initialize_session()

# Render top header
render_header(
    title="NABHCHAKRA Command Center",
    subtitle=APP_SUBTITLE
)

# Load real backend data
tables = load_base_tables()
readiness = load_fleet_readiness()
prioritized_df = load_prioritized_fleet()

# Quick alert if any aircraft are grounded or have critical component failures
elevated_risk_count = len(prioritized_df[prioritized_df["priority_category"].isin(["Critical", "High"])]["aircraft_id"].unique())
grounded_count = readiness["grounded_status_count"]

if grounded_count > 0 or elevated_risk_count > 0:
    st.markdown(
        f"""
        <div class="command-alert alert-warning">
            ⚠️ <b>Operational Advisory:</b> {grounded_count} aircraft currently grounded; {elevated_risk_count} aircraft flagged with elevated subsystem failure risk requiring engineering review.
        </div>
        """,
        unsafe_allow_html=True
    )

# Top KPI Summary Cards
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    render_kpi_card("Fleet Strength", f"{readiness['total_aircraft']}", delta="28 Active Airframes", delta_type="info")
with col2:
    render_kpi_card("Fleet Availability", f"{readiness['availability_pct']}%", delta=f"{readiness['fmc_count']} FMC / {readiness['pmc_count']} PMC", delta_type="nominal")
with col3:
    render_kpi_card("Active In-Service", f"{readiness['available_status_count']}", delta="Mission-Ready Line", delta_type="nominal")
with col4:
    render_kpi_card("Under Maintenance", f"{readiness['maintenance_status_count']}", delta="Active Depot/Bay", delta_type="warning")
with col5:
    render_kpi_card("Elevated Risk", f"{elevated_risk_count}", delta="Priority Action", delta_type="critical")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# Main Grid: Availability Gauge + Status Donut + Quick Fleet Table
col_left, col_mid, col_right = st.columns([1.2, 1.2, 2.0])

with col_left:
    st.markdown('<div class="section-header">Fleet Readiness Rate</div>', unsafe_allow_html=True)
    gauge_fig = render_availability_gauge(readiness["availability_pct"])
    st.plotly_chart(gauge_fig, use_container_width=True)
    st.caption("Standard Readiness: $\\frac{FMC + 0.5 \\times PMC}{Total} \\times 100\\%$")

with col_mid:
    st.markdown('<div class="section-header">Operational Posture</div>', unsafe_allow_html=True)
    status_counts = {
        "Available": readiness["available_status_count"],
        "In Maintenance": readiness["maintenance_status_count"],
        "Under Inspection": readiness["inspection_status_count"],
        "Grounded": readiness["grounded_status_count"],
    }
    donut_fig = render_status_donut(status_counts)
    st.plotly_chart(donut_fig, use_container_width=True)
    st.caption("Distribution across flight line, depot maintenance, and ground holds.")

with col_right:
    st.markdown('<div class="section-header">Top Maintenance Action Items</div>', unsafe_allow_html=True)
    top_actions = prioritized_df[prioritized_df["priority_category"].isin(["Critical", "High"])][
        ["aircraft_id", "component_type", "priority_category", "predicted_risk_prob", "action_recommendation"]
    ].head(5)

    if not top_actions.empty:
        st.dataframe(
            top_actions.rename(columns={
                "aircraft_id": "Aircraft",
                "component_type": "Subsystem",
                "priority_category": "Priority",
                "predicted_risk_prob": "Risk Prob",
                "action_recommendation": "Recommended Action"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("All aircraft subsystems are currently operating within nominal baseline parameters.")

st.markdown("---")

# Module Navigation Directory
st.markdown('<div class="section-header">Operational Platform Navigation</div>', unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.info("**1. Executive Dashboard**\n\nHigh-level availability rates, fleet KPIs, and searchable airframe master tables.")
with m2:
    st.info("**2. Fleet Health**\n\nDetailed time-series telemetry, vibration harmonics, thermal creep, and anomaly charts.")
with m3:
    st.info("**3. Predictive Maintenance**\n\nScikit-learn risk probability scoring, risk tiers, and physical root-cause explainers.")
with m4:
    st.info("**4. Maintenance Planning**\n\nRule-based slotting, team capacity utilization, and supply bottleneck mitigation.")

m5, m6, m7, m8 = st.columns(4)
with m5:
    st.info("**5. Spare Parts Inventory**\n\nSubsystem parts catalog, stockout warnings, and simulated stock updates.")
with m6:
    st.info("**6. Fleet Availability**\n\nFMC/PMC/NMC breakdown, planned vs unplanned downtime, and squadron readiness.")
with m7:
    st.info("**7. Scenario Simulator**\n\nInteractive what-if simulations: engine degradation, sudden grounding, and supply chain delays.")
with m8:
    st.info("**8. Digital Twin & Eval**\n\nInteractive subsystem digital representation and transparent ML evaluation metrics.")

st.markdown(
    f"""
    <div style="margin-top: 32px; padding: 12px; background: rgba(15, 23, 42, 0.6); border: 1px solid #1E293B; border-radius: 6px; font-size: 11px; color: #64748B;">
        <b>DISCLAIMER:</b> {DISCLAIMER_TEXT}
    </div>
    """,
    unsafe_allow_html=True
)
