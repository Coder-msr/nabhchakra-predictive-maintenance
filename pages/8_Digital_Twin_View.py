"""Module I — Digital-Twin-Inspired Aircraft View.

Simplified digital representation of individual aircraft subsystems, health indices,
stress gauges, and real-time degradation radar profiles.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import THEME_COLORS
from src.ui.components import (
    render_header,
    render_kpi_card,
    render_status_badge,
)
from src.ui.session_state import (
    initialize_session,
    load_base_tables,
    load_live_ml_predictions,
)
from src.ui.theme import apply_theme

st.set_page_config(page_title="Digital Twin View — NABHCHAKRA", page_icon="⚡", layout="wide")
apply_theme()
initialize_session()

render_header(
    title="Digital-Twin-Inspired Aircraft Subsystem View",
    subtitle="Simplified Structural Telemetry Mirror, Subsystem Health Panels, and Wear Fingerprints"
)

st.markdown(
    """
    <div class="command-alert alert-info">
        ℹ️ <b>Demonstration Architecture Note:</b> This simplified digital-twin-inspired panel illustrates telemetry mapping, subsystem health status, and failure risk correlation. It is a synthetic representation and not a certified flight dynamics or physics-validated finite element model.
    </div>
    """,
    unsafe_allow_html=True
)

# Load data
tables = load_base_tables()
aircraft_df = tables["aircraft"]
components_df = tables["components"]
telemetry_df = tables["sensor_telemetry"]
predictions_df = load_live_ml_predictions()

# Aircraft Selector
aircraft_options = [
    f"{row['aircraft_id']} — {row['model_type']} ({row['tail_number']}) [{row['operational_status']}]"
    for _, row in aircraft_df.iterrows()
]
selected_str = st.selectbox("Select Target Airframe for Digital Inspection", options=aircraft_options, index=0)
selected_ac_id = selected_str.split(" — ")[0]

ac_info = aircraft_df[aircraft_df["aircraft_id"] == selected_ac_id].iloc[0]
ac_components = components_df[components_df["aircraft_id"] == selected_ac_id].copy()
comp_preds = predictions_df[predictions_df["aircraft_id"] == selected_ac_id]
ac_components = ac_components.merge(comp_preds[["component_id", "predicted_risk_prob", "risk_tier", "risk_drivers"]], on="component_id", how="left")

# Airframe Header Summary
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi_card("Airframe Identifier", ac_info["aircraft_id"], delta=ac_info["tail_number"], delta_type="info")
with c2:
    render_kpi_card("Model & Mission Role", ac_info["model_type"], delta=ac_info["role"], delta_type="info")
with c3:
    st_type = "nominal" if ac_info["operational_status"] == "Available" else "warning" if ac_info["operational_status"] == "In Maintenance" else "critical"
    render_kpi_card("Operational Status", ac_info["operational_status"], delta=f"{ac_info['total_flight_hours']} Flight Hours", delta_type=st_type)
with c4:
    max_risk = ac_components["predicted_risk_prob"].max()
    r_type = "critical" if max_risk >= 0.70 else "warning" if max_risk >= 0.35 else "nominal"
    render_kpi_card("Max Subsystem Risk", f"{max_risk:.2f}", delta="Peak Component Hazard", delta_type=r_type)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# 2. Schematic Subsystem Health Grid
st.markdown('<div class="section-header">Subsystem Digital Representation & Health Metrics</div>', unsafe_allow_html=True)

for _, comp in ac_components.iterrows():
    c_type = comp["component_type"]
    c_id = comp["component_id"]
    h_idx = comp["health_index"]
    r_prob = comp.get("predicted_risk_prob", 0.0)
    r_tier = comp.get("risk_tier", "Low")
    drivers = comp.get("risk_drivers", "Nominal")

    # Icon mapping
    icon_map = {
        "Turbofan Engine": "🔥",
        "Hydraulic Actuator": "⚙️",
        "Avionics & Radar System": "📡",
        "Auxiliary Power Unit (APU)": "⚡",
        "Landing Gear Assembly": "🛞",
    }
    icon = icon_map.get(c_type, "🔧")

    border_color = (
        THEME_COLORS["status_critical"] if r_tier in ("Critical", "Elevated")
        else THEME_COLORS["status_warning"] if r_tier == "Moderate"
        else THEME_COLORS["card_border"]
    )

    with st.container():
        st.markdown(
            f"""
            <div style="background: #1C2541; border: 1px solid {border_color}; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 20px; margin-right: 8px;">{icon}</span>
                        <b style="font-size: 16px; color: #FFFFFF;">{c_type}</b>
                        <span style="color: #94A3B8; font-size: 12px; margin-left: 10px;">ID: {c_id} | Serial: {comp['serial_number']}</span>
                    </div>
                    <div>
                        {render_status_badge(r_tier + ' Risk (' + f'{r_prob:.2f}' + ')')}
                    </div>
                </div>
                <div style="margin-top: 10px; display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; color: #94A3B8;">HEALTH INDEX: <b>{h_idx:.1f}%</b></div>
                        <div style="background: #0B132B; border-radius: 4px; height: 8px; width: 100%; margin-top: 4px; overflow: hidden;">
                            <div style="background: {'#10B981' if h_idx >= 75 else '#F59E0B' if h_idx >= 50 else '#EF4444'}; width: {h_idx}%; height: 100%;"></div>
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #94A3B8;">OPERATING HOURS</div>
                        <div style="color: #FFFFFF; font-weight: 600; font-size: 14px;">{comp['operating_hours']:.1f} hrs</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #94A3B8;">ACTIVE DRIVERS</div>
                        <div style="color: {'#FCA5A5' if r_tier in ('Critical', 'Elevated') else '#94A3B8'}; font-size: 12px;">{drivers}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# 3. Subsystem Stress Radar Fingerprint
st.markdown('<div class="section-header">Multivariate Subsystem Stress Radar</div>', unsafe_allow_html=True)

radar_col1, radar_col2 = st.columns([1.5, 1.5])

with radar_col1:
    # Build radar chart across 5 components
    categories = list(ac_components["component_type"])
    health_values = list(ac_components["health_index"])
    risk_values = [round((1.0 - p) * 100, 1) for p in ac_components["predicted_risk_prob"]]

    radar_fig = go.Figure()
    radar_fig.add_trace(go.Scatterpolar(
        r=health_values,
        theta=categories,
        fill="toself",
        name="Component Health Index (%)",
        line=dict(color="#10B981", width=2)
    ))
    radar_fig.add_trace(go.Scatterpolar(
        r=risk_values,
        theta=categories,
        fill="toself",
        name="Safety Margin (1 - Risk %)",
        line=dict(color="#5BC0BE", width=2)
    ))
    radar_fig.update_layout(
        polar=dict(
            bgcolor="#1C2541",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8")),
            angularaxis=dict(gridcolor="#2E3B5E", tickfont=dict(color="#FFFFFF", size=10))
        ),
        paper_bgcolor="#1C2541",
        height=320,
        margin={"l": 30, "r": 30, "t": 20, "b": 20},
        legend=dict(font=dict(color="#FFFFFF"), orientation="h", y=-0.1)
    )
    st.plotly_chart(radar_fig, use_container_width=True)

with radar_col2:
    st.markdown("#### Digital Mirror Diagnostic Analysis")
    st.write(
        f"The digital mirror for **{ac_info['aircraft_id']}** synthesizes 90 days of sensor measurements across "
        f"thermal, acoustic, and fluid dynamics subsystems."
    )
    st.write(
        f"Current operational assignment: **{ac_info['squadron_id']}**. Cumulative airframe flight cycles: "
        f"**{ac_info['total_flight_cycles']}**."
    )
    if max_risk >= 0.70:
        st.error(
            f"⚠️ **Engineering Intervention Required:** {ac_components[ac_components['predicted_risk_prob'] == max_risk].iloc[0]['component_type']} "
            f"exhibits elevated degradation signatures requiring scheduled flight line borescope check."
        )
    else:
        st.success("✅ **Airframe Subsystems Balanced:** Telemetry signatures indicate stable operational margins.")
