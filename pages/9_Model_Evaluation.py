"""Module C Support — Model Evaluation and Performance Transparency.

Displays actual test metrics on unseen test aircraft: Precision, Recall, F1, ROC-AUC,
interactive Confusion Matrix, and Random Forest feature importance rankings.
"""

import json
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import METADATA_PATH, THEME_COLORS
from src.ui.components import (
    render_header,
    render_kpi_card,
)
from src.ui.session_state import initialize_session
from src.ui.theme import apply_theme

st.set_page_config(page_title="Model Evaluation — NABHCHAKRA", page_icon="⚡", layout="wide")
apply_theme()
initialize_session()

render_header(
    title="Predictive Model Evaluation & Validation",
    subtitle="Model Performance, Unseen Test Aircraft Validation, and Degradation Feature Importances"
)

# Load model metadata
with open(METADATA_PATH, "r", encoding="utf-8") as f:
    meta = json.load(f)

metrics = meta["evaluation_metrics"]
dataset = meta["dataset_summary"]
cm = metrics["confusion_matrix"]

st.markdown(
    """
    <div class="command-alert alert-info">
        <b>Data Integrity Note:</b> Validation was conducted using <b>Group-Aware Cross-Validation</b> split on <code>aircraft_id</code>. Telemetry from test aircraft was held out completely during training to ensure zero data leakage.
    </div>
    """,
    unsafe_allow_html=True
)

# 1. Metric KPI Cards
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    render_kpi_card("Test ROC-AUC", f"{metrics['roc_auc']:.3f}", delta="Area Under Curve", delta_type="nominal")
with m2:
    render_kpi_card("Test F1-Score", f"{metrics['f1_score']:.3f}", delta="Harmonic Mean", delta_type="nominal")
with m3:
    render_kpi_card("Test Precision", f"{metrics['precision']:.3f}", delta=f"{metrics['precision']*100:.1f}% True Hazard", delta_type="nominal")
with m4:
    render_kpi_card("Test Recall", f"{metrics['recall']:.3f}", delta=f"{metrics['recall']*100:.1f}% Failures Caught", delta_type="nominal")
with m5:
    render_kpi_card("Test Accuracy", f"{metrics['accuracy']:.3f}", delta=f"{dataset['test_samples']} Unseen Samples", delta_type="info")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# 2. Confusion Matrix & Dataset Split
c_cm, c_ds = st.columns([1.5, 1.5])

with c_cm:
    st.markdown('<div class="section-header">Evaluation Confusion Matrix (Holdout Aircraft)</div>', unsafe_allow_html=True)
    cm_matrix = [
        [cm["tn"], cm["fp"]],
        [cm["fn"], cm["tp"]]
    ]
    cm_labels_x = ["Pred: Nominal (0)", "Pred: Failure (1)"]
    cm_labels_y = ["True: Nominal (0)", "True: Failure (1)"]

    cm_fig = go.Figure(data=go.Heatmap(
        z=cm_matrix,
        x=cm_labels_x,
        y=cm_labels_y,
        text=[[f"TN: {cm['tn']}", f"FP: {cm['fp']}"], [f"FN: {cm['fn']}", f"TP: {cm['tp']}"]],
        texttemplate="%{text}",
        textfont={"size": 16, "color": "#FFFFFF"},
        colorscale=[[0, "#1C2541"], [0.5, "#3A506B"], [1.0, "#5BC0BE"]],
        showscale=False
    ))
    cm_fig.update_layout(
        paper_bgcolor="#1C2541",
        plot_bgcolor="#1C2541",
        height=260,
        margin={"l": 40, "r": 20, "t": 20, "b": 30},
        xaxis=dict(tickfont=dict(color="#FFFFFF")),
        yaxis=dict(tickfont=dict(color="#FFFFFF"))
    )
    st.plotly_chart(cm_fig, use_container_width=True)
    st.caption("Evaluated on 105 samples across 7 held-out aircraft (zero train/test overlap).")

with c_ds:
    st.markdown('<div class="section-header">Dataset Split & Class Distribution</div>', unsafe_allow_html=True)
    st.markdown(f"**Trained Model:** `{meta['model_name']}`")
    st.markdown(f"**Trained Timestamp:** `{meta['trained_timestamp']}`")
    st.markdown(f"**Random Seed:** `{meta['random_seed']}` (Deterministic reproducibility)")

    split_table = [
        {"Split": "Training Set", "Samples": dataset["train_samples"], "Aircraft Count": dataset["train_aircraft_count"], "Failure Class Ratio": f"{dataset['train_positive_rate']*100:.1f}%"},
        {"Split": "Testing Set (Holdout)", "Samples": dataset["test_samples"], "Aircraft Count": dataset["test_aircraft_count"], "Failure Class Ratio": f"{dataset['test_positive_rate']*100:.1f}%"},
    ]
    st.table(split_table)

    st.markdown("#### Hyperparameters:")
    st.json(meta["hyperparameters"])

# 3. Feature Importance Ranking
st.markdown('<div class="section-header">Top Sensor & Subsystem Degradation Feature Importances</div>', unsafe_allow_html=True)

top_feats = meta["all_feature_importances"][:10]
feats_df = pd.DataFrame(top_feats).sort_values(by="importance", ascending=True)

feat_fig = px.bar(
    feats_df,
    x="importance",
    y="feature",
    orientation="h",
    text="importance",
    color="importance",
    color_continuous_scale=[(0, "#3A506B"), (1.0, "#5BC0BE")],
    labels={"importance": "Gini Impurity Importance", "feature": "Engineered Indicator"}
)
feat_fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
feat_fig.update_layout(
    paper_bgcolor="#1C2541",
    plot_bgcolor="#1C2541",
    height=340,
    margin={"l": 40, "r": 30, "t": 20, "b": 30},
    xaxis=dict(showgrid=True, gridcolor="#2E3B5E", tickfont=dict(color="#94A3B8"), range=[0, max(feats_df["importance"]) * 1.25]),
    yaxis=dict(tickfont=dict(color="#FFFFFF", size=11)),
    coloraxis_showscale=False
)
st.plotly_chart(feat_fig, use_container_width=True)

st.markdown(
    """
    <div style="margin-top: 16px; padding: 12px; background: rgba(15, 23, 42, 0.6); border: 1px solid #1E293B; border-radius: 6px; font-size: 11px; color: #64748B;">
        <b>SCIENTIFIC DISCLAIMER:</b> Model performance metrics reflect evaluation against mathematically generated synthetic degradation signatures. They demonstrate ML architecture, pipeline hygiene, and decision explainability for hackathon evaluation, and do not constitute certified military avionics testing.
    </div>
    """,
    unsafe_allow_html=True
)
