"""Module E — Spare Parts Inventory.

Subsystem parts catalog, stockout alerts, replenishment lead-time tracking,
and interactive simulated stock adjustments.
"""

import pandas as pd
import streamlit as st

from src.business_logic.inventory_engine import InventoryEngine
from src.ui.components import (
    render_header,
    render_kpi_card,
    render_status_badge,
)
from src.ui.session_state import (
    initialize_session,
    load_base_tables,
)
from src.ui.theme import apply_theme

st.set_page_config(page_title="Spare Parts Inventory — NABHCHAKRA", page_icon="⚡", layout="wide")
apply_theme()
initialize_session()

render_header(
    title="Spare Parts Inventory & Logistics",
    subtitle="Subsystem Component Readiness, Lead-Time Tracking, and Supply Chain Bottleneck Analysis"
)

# Load data
tables = load_base_tables()
parts_df = tables["spare_parts"]
schedules_df = tables["maintenance_schedules"]

# If session state has custom simulated stock, use that
if "custom_parts_df" not in st.session_state:
    st.session_state["custom_parts_df"] = parts_df.copy()

current_parts_df = st.session_state["custom_parts_df"]

# Compute inventory metrics
inv_summary = InventoryEngine.get_inventory_summary(current_parts_df)
alerts = InventoryEngine.get_shortage_alerts(current_parts_df)

# 1. High-Level Inventory KPI Cards
i1, i2, i3, i4, i5 = st.columns(5)
with i1:
    render_kpi_card("Total Line Items", f"{inv_summary['total_part_types']}", delta="All Subsystems", delta_type="info")
with i2:
    render_kpi_card("Units in Stock", f"{inv_summary['total_units_in_stock']}", delta=f"{inv_summary['stock_health_pct']}% Healthy", delta_type="nominal")
with i3:
    render_kpi_card("Low Stock Parts", f"{inv_summary['low_stock_count']}", delta="At/Below Threshold", delta_type="warning")
with i4:
    render_kpi_card("Out of Stock (Zero)", f"{inv_summary['out_of_stock_count']}", delta="Immediate Bottleneck", delta_type="critical")
with i5:
    render_kpi_card("Avg Replenishment", f"{inv_summary['avg_lead_time_days']} days", delta=f"₹{inv_summary['total_valuation_inr']/1e7:.2f} Cr Inventory", delta_type="info")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# 2. Critical Shortage Alerts
if alerts:
    st.markdown('<div class="section-header">Active Supply Shortage Alerts</div>', unsafe_allow_html=True)
    for a in alerts:
        a_class = "alert-critical" if a["severity"] == "Critical" else "alert-warning"
        icon = "🚨" if a["severity"] == "Critical" else "⚠️"
        st.markdown(
            f"""
            <div class="command-alert {a_class}">
                {icon} <b>{a['severity'].upper()} ALERT:</b> [{a['part_id']}] {a['part_name']} — Available: <b>{a['stock_quantity']}</b> (Reorder Point: {a['reorder_threshold']}). Lead Time: <b>{a['lead_time_days']} days</b>.
            </div>
            """,
            unsafe_allow_html=True
        )

# 3. Interactive Simulated Stock Adjustment
st.markdown('<div class="section-header">Simulated Stock Replenishment & Order Adjustment</div>', unsafe_allow_html=True)

st.write("Test the impact of receiving an emergency shipment or encountering an unexpected part deficit:")

sim_col1, sim_col2, sim_col3 = st.columns([2, 1, 1])

with sim_col1:
    part_select = st.selectbox(
        "Select Part to Adjust",
        options=current_parts_df["part_id"] + " — " + current_parts_df["part_name"] + " (Current: " + current_parts_df["stock_quantity"].astype(str) + ")"
    )
    selected_part_id = part_select.split(" — ")[0]

with sim_col2:
    adjustment = st.number_input("Quantity Adjustment (+/-)", min_value=-20, max_value=50, value=5, step=1)

with sim_col3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("Apply Simulated Adjustment", type="primary"):
        st.session_state["custom_parts_df"] = InventoryEngine.simulate_stock_change(
            current_parts_df, selected_part_id, int(adjustment)
        )
        st.success(f"Simulated stock adjustment of {adjustment:+d} applied to {selected_part_id}!")
        st.rerun()

if st.button("Reset Simulated Stock to Initial Baseline"):
    st.session_state["custom_parts_df"] = parts_df.copy()
    st.info("Inventory restored to initial baseline.")
    st.rerun()

# 4. Master Spare Parts Catalog
st.markdown('<div class="section-header">Master Spare Parts Catalog</div>', unsafe_allow_html=True)

# Filter by component type
cat_filter = st.selectbox("Filter by Compatible Subsystem", options=["All"] + sorted(current_parts_df["compatible_component_type"].unique()))
df_display = current_parts_df.copy()
if cat_filter != "All":
    df_display = df_display[df_display["compatible_component_type"] == cat_filter]

# Format cost in INR
df_display["Cost (INR)"] = df_display["unit_cost_inr"].apply(lambda x: f"₹{x:,.0f}")

st.dataframe(
    df_display[[
        "part_id", "part_name", "compatible_component_type", "stock_quantity",
        "reorder_threshold", "lead_time_days", "Cost (INR)", "status"
    ]].rename(columns={
        "part_id": "Part ID",
        "part_name": "Part Nomenclature",
        "compatible_component_type": "Compatible Subsystem",
        "stock_quantity": "Stock Qty",
        "reorder_threshold": "Reorder Level",
        "lead_time_days": "Lead Time (Days)",
        "status": "Stock Status"
    }),
    use_container_width=True,
    hide_index=True
)
