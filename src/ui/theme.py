"""Aerospace Command Center Theme Tokens and Custom CSS for Streamlit."""

import streamlit as st


def apply_theme():
    """Inject custom CSS for the dark navy aerospace command-center interface."""
    custom_css = """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global Typography & Palette */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main Container Padding & Background */
    .stApp {
        background-color: #0B132B;
        color: #F8FAFC;
    }

    /* Header styling */
    .command-header {
        background: linear-gradient(135deg, #1C2541 0%, #0F172A 100%);
        border: 1px solid #2E3B5E;
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .command-title {
        color: #FFFFFF;
        font-size: 26px;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .command-subtitle {
        color: #94A3B8;
        font-size: 14px;
        margin-top: 6px;
    }
    .disclaimer-badge {
        display: inline-block;
        background-color: rgba(91, 192, 190, 0.12);
        color: #5BC0BE;
        border: 1px solid rgba(91, 192, 190, 0.35);
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        letter-spacing: 0.5px;
        margin-top: 8px;
    }

    /* KPI Cards */
    .kpi-card {
        background: #1C2541;
        border: 1px solid #2E3B5E;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .kpi-card:hover {
        border-color: #5BC0BE;
        transform: translateY(-2px);
    }
    .kpi-title {
        font-size: 12px;
        font-weight: 600;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.1;
    }
    .kpi-delta {
        font-size: 12px;
        margin-top: 6px;
    }
    .kpi-delta-nominal { color: #10B981; }
    .kpi-delta-warning { color: #F59E0B; }
    .kpi-delta-critical { color: #EF4444; }
    .kpi-delta-info { color: #5BC0BE; }

    /* Status Pill Badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.3px;
        text-align: center;
    }
    .badge-available, .badge-nominal, .badge-low {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.35);
    }
    .badge-maintenance, .badge-warning, .badge-moderate, .badge-medium {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.35);
    }
    .badge-grounded, .badge-critical, .badge-elevated {
        background-color: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.35);
    }
    .badge-inspection, .badge-info {
        background-color: rgba(59, 130, 246, 0.15);
        color: #60A5FA;
        border: 1px solid rgba(59, 130, 246, 0.35);
    }

    /* Streamlit Tables & DataFrames */
    [data-testid="stDataFrame"] {
        border: 1px solid #2E3B5E;
        border-radius: 6px;
        overflow: hidden;
    }

    /* Section Headers */
    .section-header {
        font-size: 18px;
        font-weight: 600;
        color: #FFFFFF;
        border-bottom: 2px solid #2E3B5E;
        padding-bottom: 8px;
        margin-top: 24px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Sidebar Customization */
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }

    /* Alert callouts */
    .command-alert {
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 14px;
        font-size: 13px;
        line-height: 1.4;
    }
    .alert-critical {
        background-color: rgba(239, 68, 68, 0.12);
        border: 1px solid #EF4444;
        color: #FCA5A5;
    }
    .alert-warning {
        background-color: rgba(245, 158, 11, 0.12);
        border: 1px solid #F59E0B;
        color: #FCD34D;
    }
    .alert-info {
        background-color: rgba(91, 192, 190, 0.12);
        border: 1px solid #5BC0BE;
        color: #99F6E4;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
