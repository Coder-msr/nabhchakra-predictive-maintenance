"""Reusable UI Components and Plotly Visualizations for NABHCHAKRA."""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import APP_TITLE, DISCLAIMER_TEXT, THEME_COLORS


def render_header(title: str, subtitle: Optional[str] = None):
    """Render the standard aerospace command header with timestamp and research disclaimer."""
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    st.markdown(
        f"""
        <div class="command-header">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                <div>
                    <h1 class="command-title">
                        <span style="color: #5BC0BE;">⚡</span> {title}
                    </h1>
                    <div class="command-subtitle">{subtitle or 'Predictive Maintenance & Fleet Availability Decision Platform'}</div>
                    <div class="disclaimer-badge">NON-OPERATIONAL RESEARCH PROTOTYPE</div>
                </div>
                <div style="text-align: right; margin-top: 4px;">
                    <div style="font-size: 11px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px;">SYSTEM TELEMETRY CLOCK</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #5BC0BE; font-weight: 600;">{current_time_str}</div>
                    <div style="font-size: 11px; color: #10B981; font-weight: 500;">● STREAM LIVE</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_kpi_card(title: str, value: str, delta: Optional[str] = None, delta_type: str = "nominal"):
    """Render a styled metric KPI card."""
    delta_class = f"kpi-delta-{delta_type}"
    delta_html = f'<div class="kpi-delta {delta_class}">{delta}</div>' if delta else ""

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_status_badge(status_text: str) -> str:
    """Return an HTML snippet for a colored status pill badge."""
    clean = str(status_text).lower().replace(" ", "-")
    badge_type = "nominal"
    if any(k in clean for k in ["grounded", "critical", "out-of-stock", "elevated"]):
        badge_type = "critical"
    elif any(k in clean for k in ["maintenance", "warning", "low-stock", "moderate", "medium"]):
        badge_type = "warning"
    elif any(k in clean for k in ["inspection", "info", "proposed"]):
        badge_type = "info"
    elif any(k in clean for k in ["available", "in-stock", "nominal", "low", "completed"]):
        badge_type = "nominal"

    return f'<span class="badge badge-{badge_type}">{status_text}</span>'


def render_availability_gauge(availability_pct: float) -> go.Figure:
    """Create a high-contrast dark Plotly radial gauge chart for fleet availability."""
    bar_color = (
        THEME_COLORS["status_nominal"] if availability_pct >= 75.0
        else THEME_COLORS["status_warning"] if availability_pct >= 60.0
        else THEME_COLORS["status_critical"]
    )

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=availability_pct,
        number={"suffix": "%", "font": {"size": 38, "color": "#FFFFFF", "family": "Inter"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#2E3B5E", "tickfont": {"color": "#94A3B8"}},
            "bar": {"color": bar_color, "thickness": 0.28},
            "bgcolor": "#1C2541",
            "borderwidth": 1,
            "bordercolor": "#2E3B5E",
            "steps": [
                {"range": [0, 60], "color": "rgba(239, 68, 68, 0.15)"},
                {"range": [60, 75], "color": "rgba(245, 158, 11, 0.15)"},
                {"range": [75, 100], "color": "rgba(16, 185, 129, 0.15)"},
            ],
            "threshold": {
                "line": {"color": "#5BC0BE", "width": 3},
                "thickness": 0.8,
                "value": 75.0
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=220,
        margin={"l": 20, "r": 20, "t": 20, "b": 10},
    )
    return fig


def render_status_donut(status_counts: Dict[str, int]) -> go.Figure:
    """Create a dark-themed operational status donut chart."""
    labels = list(status_counts.keys())
    values = list(status_counts.values())

    color_map = {
        "Available": THEME_COLORS["status_nominal"],
        "In Maintenance": THEME_COLORS["status_warning"],
        "Under Inspection": THEME_COLORS["status_info"],
        "Grounded": THEME_COLORS["status_critical"],
    }
    colors = [color_map.get(lbl, "#94A3B8") for lbl in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#0B132B", width=2)),
        textinfo="label+value",
        textfont=dict(color="#FFFFFF", size=12),
        hoverinfo="label+percent",
    )])

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        height=220,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
    )
    return fig


def render_telemetry_chart(
    telemetry_df: pd.DataFrame,
    sensor_col: str,
    sensor_label: str,
    unit: str,
    warning_thresh: Optional[float] = None,
    critical_thresh: Optional[float] = None
) -> go.Figure:
    """Create an interactive time-series line chart for sensor telemetry with thresholds."""
    df_plot = telemetry_df.sort_values(by="timestamp").copy()

    fig = go.Figure()

    # Main telemetry line
    fig.add_trace(go.Scatter(
        x=df_plot["timestamp"],
        y=df_plot[sensor_col],
        mode="lines+markers",
        name=sensor_label,
        line=dict(color="#5BC0BE", width=2.5),
        marker=dict(size=4, color="#6FFFE9"),
        hovertemplate=f"<b>%{{x|%Y-%m-%d %H:%M}}</b><br>{sensor_label}: %{{y:.1f}} {unit}<extra></extra>"
    ))

    # Warning threshold horizontal line
    if warning_thresh is not None:
        fig.add_hline(
            y=warning_thresh,
            line_dash="dash",
            line_color=THEME_COLORS["status_warning"],
            annotation_text=f"Warning ({warning_thresh} {unit})",
            annotation_position="bottom right",
            annotation_font_color=THEME_COLORS["status_warning"],
            annotation_font_size=10
        )

    # Critical threshold horizontal line
    if critical_thresh is not None:
        fig.add_hline(
            y=critical_thresh,
            line_dash="dot",
            line_color=THEME_COLORS["status_critical"],
            annotation_text=f"Critical ({critical_thresh} {unit})",
            annotation_position="top right",
            annotation_font_color=THEME_COLORS["status_critical"],
            annotation_font_size=10
        )

    fig.update_layout(
        paper_bgcolor="#1C2541",
        plot_bgcolor="#1C2541",
        height=260,
        margin={"l": 40, "r": 20, "t": 30, "b": 30},
        xaxis=dict(
            showgrid=True,
            gridcolor="#2E3B5E",
            tickfont=dict(color="#94A3B8", size=10),
            title_font=dict(color="#94A3B8")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#2E3B5E",
            tickfont=dict(color="#94A3B8", size=10),
            title=f"{sensor_label} ({unit})",
            title_font=dict(color="#94A3B8", size=11)
        ),
        legend=dict(font=dict(color="#FFFFFF")),
    )
    return fig
