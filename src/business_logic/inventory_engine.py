"""Spare Parts Inventory Analysis and Supply Chain Engine.

Monitors subsystem stock availability, detects component replenishment bottlenecks,
and models stock shortages that impact ongoing or scheduled maintenance work orders.
"""

from typing import Dict, List, Optional
import pandas as pd


class InventoryEngine:
    """Evaluates spare parts readiness, shortages, and maintenance schedule bottlenecks."""

    @staticmethod
    def get_inventory_summary(spare_parts_df: pd.DataFrame) -> Dict:
        """Compute high-level inventory metrics."""
        total_types = len(spare_parts_df)
        total_units = int(spare_parts_df["stock_quantity"].sum())
        out_of_stock_count = int((spare_parts_df["stock_quantity"] == 0).sum())
        low_stock_count = int((
            (spare_parts_df["stock_quantity"] > 0) &
            (spare_parts_df["stock_quantity"] <= spare_parts_df["reorder_threshold"])
        ).sum())
        in_stock_count = total_types - (out_of_stock_count + low_stock_count)

        total_value_inr = float((spare_parts_df["stock_quantity"] * spare_parts_df["unit_cost_inr"]).sum())
        avg_lead_time_days = float(spare_parts_df["lead_time_days"].mean())

        return {
            "total_part_types": total_types,
            "total_units_in_stock": total_units,
            "in_stock_count": in_stock_count,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "stock_health_pct": round(float((in_stock_count / total_types) * 100), 1) if total_types > 0 else 0.0,
            "total_valuation_inr": total_value_inr,
            "avg_lead_time_days": round(avg_lead_time_days, 1),
        }

    @staticmethod
    def get_shortage_alerts(spare_parts_df: pd.DataFrame) -> List[Dict]:
        """Generate actionable alerts for parts at or below their reorder threshold."""
        alerts = []
        shortage_parts = spare_parts_df[
            spare_parts_df["stock_quantity"] <= spare_parts_df["reorder_threshold"]
        ].sort_values(by="stock_quantity", ascending=True)

        for _, part in shortage_parts.iterrows():
            qty = int(part["stock_quantity"])
            thresh = int(part["reorder_threshold"])
            lead_time = int(part["lead_time_days"])
            p_name = part["part_name"]
            c_type = part["compatible_component_type"]

            if qty == 0:
                severity = "Critical"
                msg = f"Zero stock for {p_name} ({c_type}). Expected replenishment delay: {lead_time} days."
            else:
                severity = "Warning"
                msg = f"Low stock ({qty}/{thresh} threshold) for {p_name}. Order lead time: {lead_time} days."

            alerts.append({
                "part_id": part["part_id"],
                "part_name": p_name,
                "component_type": c_type,
                "stock_quantity": qty,
                "reorder_threshold": thresh,
                "lead_time_days": lead_time,
                "severity": severity,
                "alert_message": msg,
            })

        return alerts

    @staticmethod
    def check_schedule_bottlenecks(
        schedules_df: pd.DataFrame,
        spare_parts_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Cross-reference maintenance schedules with parts stock to identify supply bottlenecks."""
        if schedules_df.empty:
            return schedules_df

        parts_map = spare_parts_df.set_index("part_id").to_dict(orient="index")

        enriched_schedules = schedules_df.copy()
        part_statuses = []
        bottleneck_flags = []
        estimated_delays = []

        for _, sched in enriched_schedules.iterrows():
            part_id = sched.get("required_part_id")
            if not part_id or part_id not in parts_map:
                part_statuses.append("Not Required / Unknown")
                bottleneck_flags.append(False)
                estimated_delays.append(0)
            else:
                part_info = parts_map[part_id]
                qty = part_info["stock_quantity"]
                lead_days = part_info["lead_time_days"]

                if qty == 0:
                    part_statuses.append("Out of Stock")
                    bottleneck_flags.append(True)
                    estimated_delays.append(lead_days)
                elif qty <= part_info["reorder_threshold"]:
                    part_statuses.append("Low Stock")
                    bottleneck_flags.append(False)
                    estimated_delays.append(0)
                else:
                    part_statuses.append("In Stock")
                    bottleneck_flags.append(False)
                    estimated_delays.append(0)

        enriched_schedules["part_status"] = part_statuses
        enriched_schedules["is_bottlenecked"] = bottleneck_flags
        enriched_schedules["estimated_delay_days"] = estimated_delays

        return enriched_schedules

    @staticmethod
    def simulate_stock_change(
        spare_parts_df: pd.DataFrame,
        part_id: str,
        delta_quantity: int
    ) -> pd.DataFrame:
        """Create a modified in-memory copy of spare parts with an updated stock quantity."""
        updated_df = spare_parts_df.copy()
        idx = updated_df[updated_df["part_id"] == part_id].index

        if not idx.empty:
            current_qty = updated_df.loc[idx[0], "stock_quantity"]
            new_qty = max(0, current_qty + delta_quantity)
            thresh = updated_df.loc[idx[0], "reorder_threshold"]

            if new_qty == 0:
                new_status = "Out of Stock"
            elif new_qty <= thresh:
                new_status = "Low Stock"
            else:
                new_status = "In Stock"

            updated_df.loc[idx[0], "stock_quantity"] = new_qty
            updated_df.loc[idx[0], "status"] = new_status

        return updated_df
