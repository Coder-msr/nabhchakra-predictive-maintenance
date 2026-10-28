"""Module C — Predictive Maintenance Engine.

Live Scikit-Learn Random Forest inference over fleet telemetry, risk probability rankings,
calibrated risk tier distributions, and explainable engineering root drivers.
"""

import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import METADATA_PATH, RISK_TIERS, THEME_COLORS
from src.ui.components import (
    render_header,
    render_kpi_card,
    render_status_badge,
)
from src.ui.session_state import (
    initialize_session,
    load_live_ml_predictions,
    load_prioritized_fleet,
)
from src.ui.theme import apply_theme

st.set_page_config(page_title="Predictive Maintenance — NABHCHAKRA", page_icon="⚡", layout="wide")
apply_theme()
initialize_session()

render_header(
    title="Predictive Maintenance Engine",
    subtitle="Machine Learning Failure Risk Inference, Subsystem Degradation Drivers & Explainability"
)

# Load real ML predictions
predictions_df = load_live_ml_predictions()

# Load model metadata
with open(METADATA_PATH, "r", encoding="utf-8") as f:
    model_meta = json.load(f)

# Risk Distribution Summary
tier_counts = predictions_df["risk_tier"].value_counts().to_dict()
low_cnt = tier_counts.get("Low", 0)
mod_cnt = tier_counts.get("Moderate", 0)
elev_cnt = tier_counts.get("Elevated", 0)
crit_cnt = tier_counts.get("Critical", 0)

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    render_kpi_card("Total Components", f"{len(predictions_df)}", delta="28 Aircraft x 5 Subsystems", delta_type="info")
with k2:
    render_kpi_card("Critical Risk (>85%)", f"{crit_cnt}", delta="Immediate Stand-down", delta_type="critical")
with k3:
    render_kpi_card("Elevated Risk (65-85%)", f"{elev_cnt}", delta="Priority Rectification", delta_type="warning")
with k4:
    render_kpi_card("Moderate Risk (35-65%)", f"{mod_cnt}", delta="Pre-Flight Watch", delta_type="warning")
with k5:
    render_kpi_card("Nominal Low Risk", f"{low_cnt}", delta="Standard Operation", delta_type="nominal")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# Visual Distribution of Risk
col_hist, col_top = st.columns([1.3, 1.7])

with col_hist:
    st.markdown('<div class="section-header">Fleet Failure Risk Probability Distribution</div>', unsafe_allow_html=True)
    hist_fig = px.histogram(
        predictions_df,
        x="predicted_risk_prob",
        nbins=20,
        color="risk_tier",
        color_discrete_map={
            "Low": THEME_COLORS["status_nominal"],
            "Moderate": THEME_COLORS["status_warning"],
            "Elevated": "#F97316",
            "Critical": THEME_COLORS["status_critical"],
        },
        labels={"predicted_risk_prob": "Predicted Risk Probability", "count": "Component Count"}
    )
    hist_fig.update_layout(
        paper_bgcolor="#1C2541",
        plot_bgcolor="#1C2541",
        height=240,
        margin={"l": 30, "r": 20, "t": 20, "b": 30},
        xaxis=dict(showgrid=True, gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8")),
        yaxis=dict(showgrid=True, gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8")),
        legend=dict(font=dict(color="#FFFFFF"), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(hist_fig, use_container_width=True)

with col_top:
    st.markdown('<div class="section-header">Top High-Risk Subsystems (Prioritized)</div>', unsafe_allow_html=True)
    high_risk_table = predictions_df[predictions_df["predicted_risk_prob"] >= 0.35][
        ["aircraft_id", "model_type", "component_type", "predicted_risk_prob", "risk_tier", "risk_drivers"]
    ].head(6)

    st.dataframe(
        high_risk_table.rename(columns={
            "aircraft_id": "Aircraft",
            "model_type": "Model",
            "component_type": "Subsystem",
            "predicted_risk_prob": "Risk Prob",
            "risk_tier": "Risk Tier",
            "risk_drivers": "Engineering Root Drivers"
        }),
        use_container_width=True,
        hide_index=True
    )

# Subsystem Deep-Dive and Explainability
st.markdown('<div class="section-header">Component Explainability & Telemetry Signature Inspection</div>', unsafe_allow_html=True)

comp_options = [
    f"{r['component_id']} — {r['aircraft_id']} ({r['model_type']}): {r['component_type']} [Risk: {r['predicted_risk_prob']:.2f} — {r['risk_tier']}]"
    for _, r in predictions_df.iterrows()
]
selected_comp_str = st.selectbox("Select Component to Explain Prediction", options=comp_options, index=0)
sel_comp_id = selected_comp_str.split(" — ")[0]
comp_data = predictions_df[predictions_df["component_id"] == sel_comp_id].iloc[0]

c_exp_left, c_exp_right = st.columns([1.5, 1.5])

with c_exp_left:
    st.markdown(f"### Component: `{comp_data['component_type']}` ({comp_data['component_id']})")
    st.write(f"**Installed On:** {comp_data['aircraft_id']} ({comp_data['model_type']} — {comp_data['tail_number']})")
    st.write(f"**Operational Airframe Status:** `{comp_data['operational_status']}`")
    st.write(f"**Operating Hours:** {comp_data['comp_operating_hours']:.1f} hrs | **Health Index:** {comp_data['comp_health_index']:.1f}%")

    st.markdown("#### Primary Identified Risk Drivers:")
    drivers = comp_data["risk_drivers"].split(", ")
    for d in drivers:
        st.markdown(f"- 🔴 **{d}**")

with c_exp_right:
    st.markdown("#### Physical Telemetry Observation Summary:")
    obs_df = pd.DataFrame([
        {"Metric": "Max 30d Temperature", "Value": f"{comp_data['temp_max_30d']} °C", "Limit": "875 °C Warning / 930 °C Critical"},
        {"Metric": "Max 30d Vibration RMS", "Value": f"{comp_data['vib_max_30d']} mm/s", "Limit": "3.6 mm/s Warning / 4.8 mm/s Critical"},
        {"Metric": "Min 30d Lubrication Oil", "Value": f"{comp_data['oil_min_30d']} PSI", "Limit": "40 PSI Warning / 32 PSI Critical"},
        {"Metric": "Min 30d Hydraulic Pressure", "Value": f"{comp_data['hyd_min_30d']} bar", "Limit": "185 bar Warning / 170 bar Critical"},
        {"Metric": "Peak Telemetry Anomaly Index", "Value": f"{comp_data['anomaly_score_max_14d']:.3f}", "Limit": "0.70 Warning / 1.00 Critical"},
    ])
    st.table(obs_df)

# Model Governance, Limitations & Disclaimer
st.markdown("---")
st.markdown('<div class="section-header">Experimental Model Governance & Limitations</div>', unsafe_allow_html=True)
st.markdown(
    """
    * **Algorithm:** Scikit-Learn `RandomForestClassifier` trained on non-leaking historical window aggregates.
    * **Prediction Target:** Probability of an unscheduled maintenance event, severe fault, or catastrophic threshold breach within the forward 30-day window.
    * **Synthetic Data Limitation:** All probabilities are experimental statistical estimates derived from synthetic Gaussian and physical wear degradation equations.
    * **Non-Operational Boundary:** Predictions must NOT be used for real-world flight clearances or certified maintenance actions.
    """
)
