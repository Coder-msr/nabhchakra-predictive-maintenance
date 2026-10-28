"""Module B — Aircraft Health Monitoring.

Deep-dive health inspection for individual aircraft: Subsystem health indices,
interactive time-series telemetry trends, threshold breach alerts, and maintenance logs.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import SENSOR_THRESHOLDS, THEME_COLORS
from src.ui.components import (
    render_header,
    render_kpi_card,
    render_status_badge,
    render_telemetry_chart,
)
from src.ui.session_state import (
    initialize_session,
    load_base_tables,
    load_live_ml_predictions,
)
from src.ui.theme import apply_theme

st.set_page_config(page_title="Fleet Health Monitoring — NABHCHAKRA", page_icon="⚡", layout="wide")
apply_theme()
initialize_session()

render_header(
    title="Aircraft Health Monitoring",
    subtitle="Subsystem Telemetry, Vibration Harmonics, Thermal Trends, and Anomaly Tracking"
)

# Load data
tables = load_base_tables()
aircraft_df = tables["aircraft"]
components_df = tables["components"]
telemetry_df = tables["sensor_telemetry"]
faults_df = tables["fault_events"]
records_df = tables["maintenance_records"]
predictions_df = load_live_ml_predictions()

# Aircraft Selector
aircraft_options = [
    f"{row['aircraft_id']} — {row['model_type']} ({row['tail_number']}) [{row['operational_status']}]"
    for _, row in aircraft_df.iterrows()
]
selected_str = st.selectbox("Select Aircraft Airframe to Inspect", options=aircraft_options, index=0)
selected_ac_id = selected_str.split(" — ")[0]

ac_info = aircraft_df[aircraft_df["aircraft_id"] == selected_ac_id].iloc[0]

# Airframe Header Metrics
st.markdown('<div class="section-header">Airframe Master Metadata</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    render_kpi_card("Tail Number", ac_info["tail_number"], delta=ac_info["model_type"], delta_type="info")
with c2:
    st_type = "nominal" if ac_info["operational_status"] == "Available" else "warning" if ac_info["operational_status"] == "In Maintenance" else "critical"
    render_kpi_card("Operational Status", ac_info["operational_status"], delta=ac_info["role"], delta_type=st_type)
with c3:
    render_kpi_card("Flight Hours", f"{ac_info['total_flight_hours']} hrs", delta=f"{ac_info['total_flight_cycles']} Cycles", delta_type="info")
with c4:
    render_kpi_card("Squadron", ac_info["squadron_id"].split(" (")[0], delta=ac_info["commission_date"], delta_type="info")
with c5:
    render_kpi_card("Next Inspection", ac_info["next_inspection_due"], delta=f"Last: {ac_info['last_inspection_date']}", delta_type="warning")

# Subsystem Components Health
st.markdown('<div class="section-header">Subsystem Component Health Indices</div>', unsafe_allow_html=True)
ac_components = components_df[components_df["aircraft_id"] == selected_ac_id].copy()

# Merge predictions
comp_preds = predictions_df[predictions_df["aircraft_id"] == selected_ac_id][
    ["component_id", "predicted_risk_prob", "risk_tier", "risk_drivers"]
]
ac_components = ac_components.merge(comp_preds, on="component_id", how="left")

# Component display cards
comp_cols = st.columns(len(ac_components))
for idx, (_, comp) in enumerate(ac_components.iterrows()):
    with comp_cols[idx]:
        h_idx = comp["health_index"]
        c_status = "nominal" if h_idx >= 75.0 else "warning" if h_idx >= 50.0 else "critical"
        render_kpi_card(
            title=comp["component_type"],
            value=f"{h_idx}%",
            delta=f"Risk: {comp.get('risk_tier', 'Low')} ({comp.get('predicted_risk_prob', 0.0):.2f})",
            delta_type=c_status
        )

# Detailed Telemetry Trend Analysis
st.markdown('<div class="section-header">Time-Series Telemetry Trends & Threshold Limits</div>', unsafe_allow_html=True)

# Select Component for telemetry charts
subsystem_types = list(ac_components["component_type"])
sel_comp_type = st.radio("Select Subsystem to View Sensor Waveforms", options=subsystem_types, horizontal=True)

sel_comp_row = ac_components[ac_components["component_type"] == sel_comp_type].iloc[0]
sel_comp_id = sel_comp_row["component_id"]

comp_telemetry = telemetry_df[telemetry_df["component_id"] == sel_comp_id].copy()

if not comp_telemetry.empty:
    comp_telemetry["timestamp"] = pd.to_datetime(comp_telemetry["timestamp"])

    # 4 interactive telemetry charts in 2x2 grid
    ch1, ch2 = st.columns(2)
    with ch1:
        st.subheader("1. Exhaust Gas / Engine Temperature (°C)")
        fig_temp = render_telemetry_chart(
            comp_telemetry,
            sensor_col="engine_temp_c",
            sensor_label="Temperature",
            unit="°C",
            warning_thresh=SENSOR_THRESHOLDS["engine_temp_c"]["warning_max"],
            critical_thresh=SENSOR_THRESHOLDS["engine_temp_c"]["critical_max"]
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    with ch2:
        st.subheader("2. Vibration RMS (mm/s)")
        fig_vib = render_telemetry_chart(
            comp_telemetry,
            sensor_col="vibration_rms",
            sensor_label="Vibration RMS",
            unit="mm/s",
            warning_thresh=SENSOR_THRESHOLDS["vibration_rms"]["warning_max"],
            critical_thresh=SENSOR_THRESHOLDS["vibration_rms"]["critical_max"]
        )
        st.plotly_chart(fig_vib, use_container_width=True)

    ch3, ch4 = st.columns(2)
    with ch3:
        st.subheader("3. Lubrication & Hydraulic Pressures")
        fig_press = go.Figure()
        fig_press.add_trace(go.Scatter(
            x=comp_telemetry["timestamp"],
            y=comp_telemetry["oil_pressure_psi"],
            mode="lines",
            name="Oil Pressure (PSI)",
            line=dict(color="#F59E0B", width=2)
        ))
        fig_press.add_trace(go.Scatter(
            x=comp_telemetry["timestamp"],
            y=comp_telemetry["hydraulic_pressure_bar"],
            mode="lines",
            name="Hydraulic (bar)",
            line=dict(color="#3B82F6", width=2)
        ))
        fig_press.update_layout(
            paper_bgcolor="#1C2541",
            plot_bgcolor="#1C2541",
            height=260,
            margin={"l": 40, "r": 20, "t": 30, "b": 30},
            xaxis=dict(showgrid=True, gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8", size=10)),
            yaxis=dict(showgrid=True, gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8", size=10), title="Pressure Units"),
            legend=dict(font=dict(color="#FFFFFF"))
        )
        st.plotly_chart(fig_press, use_container_width=True)

    with ch4:
        st.subheader("4. Telemetry Anomaly Index")
        fig_anom = render_telemetry_chart(
            comp_telemetry,
            sensor_col="anomaly_score",
            sensor_label="Anomaly Score",
            unit="idx",
            warning_thresh=SENSOR_THRESHOLDS["anomaly_score"]["warning_max"],
            critical_thresh=SENSOR_THRESHOLDS["anomaly_score"]["critical_max"]
        )
        st.plotly_chart(fig_anom, use_container_width=True)
else:
    st.info("No telemetry logs recorded for this subsystem.")

# Fault Events & Maintenance History for this aircraft
c_flt, c_rec = st.columns(2)

with c_flt:
    st.markdown('<div class="section-header">Recorded Fault Events</div>', unsafe_allow_html=True)
    ac_faults = faults_df[faults_df["aircraft_id"] == selected_ac_id]
    if not ac_faults.empty:
        st.dataframe(
            ac_faults[["fault_code", "severity", "detected_timestamp", "description", "is_resolved"]].rename(columns={
                "fault_code": "Code", "severity": "Severity", "detected_timestamp": "Timestamp",
                "description": "Fault Description", "is_resolved": "Resolved"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("No active or historical fault event logs recorded for this airframe.")

with c_rec:
    st.markdown('<div class="section-header">Maintenance Work Order History</div>', unsafe_allow_html=True)
    ac_records = records_df[records_df["aircraft_id"] == selected_ac_id]
    if not ac_records.empty:
        st.dataframe(
            ac_records[["record_id", "maintenance_type", "start_time", "status", "action_taken"]].rename(columns={
                "record_id": "Order ID", "maintenance_type": "Type", "start_time": "Date",
                "status": "Status", "action_taken": "Action Performed"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No prior maintenance work orders recorded.")
