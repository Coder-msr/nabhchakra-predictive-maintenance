"""Maintenance Priority Assessment Engine.

Implements a transparent, explainable multi-criteria scoring system combining
predicted failure risk, inspection urgency, spare-part stock status, and subsystem criticality.
"""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from config.settings import PRIORITY_WEIGHTS


# Component subsystem criticality weights (illustrative synthetic ratings)
COMPONENT_CRITICALITY = {
    "Turbofan Engine": 1.00,
    "Hydraulic Actuator": 0.85,
    "Avionics & Radar System": 0.85,
    "Landing Gear Assembly": 0.75,
    "Auxiliary Power Unit (APU)": 0.60,
}


class PriorityEngine:
    """Calculates explainable maintenance priority scores and actionable recommendations."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or PRIORITY_WEIGHTS

    def calculate_inspection_urgency(self, next_inspection_due: Optional[str], as_of_date: Optional[str] = None) -> float:
        """Score inspection urgency based on days remaining until scheduled inspection."""
        if not next_inspection_due:
            return 0.50  # Unknown defaults to moderate urgency

        as_of = pd.to_datetime(as_of_date) if as_of_date else pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
        due = pd.to_datetime(next_inspection_due)
        days_remaining = (due - as_of).days

        if days_remaining < 0:
            return 1.00  # Overdue
        elif days_remaining <= 7:
            return 0.85  # Due within 1 week
        elif days_remaining <= 21:
            return 0.60  # Due within 3 weeks
        elif days_remaining <= 45:
            return 0.35  # Due within 1.5 months
        else:
            return 0.10  # Well within validity window

    def calculate_spare_part_urgency(self, part_status: str) -> float:
        """Score spare-part availability constraint."""
        if part_status == "Out of Stock":
            return 1.00  # Severe bottleneck
        elif part_status == "Low Stock":
            return 0.60  # Supply constraint
        else:
            return 0.10  # Plentiful stock

    def assess_component_priority(
        self,
        predicted_risk_prob: float,
        next_inspection_due: Optional[str],
        spare_part_status: str,
        component_type: str,
        as_of_date: Optional[str] = None
    ) -> Dict:
        """Compute composite priority score, category, breakdown, and recommended action."""
        # 1. Normalize individual factor scores
        score_risk = float(max(0.0, min(1.0, predicted_risk_prob)))
        score_overdue = self.calculate_inspection_urgency(next_inspection_due, as_of_date=as_of_date)
        score_spares = self.calculate_spare_part_urgency(spare_part_status)
        score_crit = COMPONENT_CRITICALITY.get(component_type, 0.70)

        # 2. Weighted sum
        composite = (
            self.weights["failure_risk"] * score_risk +
            self.weights["inspection_overdue"] * score_overdue +
            self.weights["spare_parts_shortage"] * score_spares +
            self.weights["mission_criticality"] * score_crit
        )
        composite = round(float(max(0.0, min(1.0, composite))), 3)

        # 3. Categorization
        if composite >= 0.70:
            category = "Critical"
        elif composite >= 0.52:
            category = "High"
        elif composite >= 0.35:
            category = "Medium"
        else:
            category = "Low"

        # 4. Action recommendation formulation
        recommendations = []
        if score_risk >= 0.65:
            recommendations.append("Prioritize technical diagnostics and sensor calibration.")
        if score_overdue >= 0.85:
            recommendations.append("Overdue inspection: schedule flight line engineering check.")
        if score_spares >= 0.80:
            recommendations.append("Expedite spare part replenishment to prevent maintenance hold.")
        if not recommendations:
            recommendations.append("Continue routine flight turnaround monitoring.")

        recommendation_text = " ".join(recommendations)

        return {
            "priority_score": composite,
            "priority_category": category,
            "action_recommendation": recommendation_text,
            "score_breakdown": {
                "risk_contribution": round(self.weights["failure_risk"] * score_risk, 3),
                "overdue_contribution": round(self.weights["inspection_overdue"] * score_overdue, 3),
                "spares_contribution": round(self.weights["spare_parts_shortage"] * score_spares, 3),
                "criticality_contribution": round(self.weights["mission_criticality"] * score_crit, 3),
            }
        }

    def evaluate_fleet_priorities(
        self,
        scored_fleet_df: pd.DataFrame,
        spare_parts_df: pd.DataFrame,
        aircraft_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Batch evaluate maintenance priorities for all fleet components."""
        # Map spare parts status by compatible component type
        part_status_map = {}
        for c_type, group in spare_parts_df.groupby("compatible_component_type"):
            # If any part for this component is Out of Stock, treat as severe
            statuses = set(group["status"])
            if "Out of Stock" in statuses:
                part_status_map[c_type] = "Out of Stock"
            elif "Low Stock" in statuses:
                part_status_map[c_type] = "Low Stock"
            else:
                part_status_map[c_type] = "In Stock"

        # Map inspection due dates
        insp_due_map = dict(zip(aircraft_df["aircraft_id"], aircraft_df["next_inspection_due"]))

        out_rows = []
        for _, row in scored_fleet_df.iterrows():
            ac_id = row["aircraft_id"]
            c_type = row["component_type"]
            prob = row.get("predicted_risk_prob", 0.0)
            next_insp = insp_due_map.get(ac_id, None)
            sp_status = part_status_map.get(c_type, "In Stock")

            assessment = self.assess_component_priority(
                predicted_risk_prob=prob,
                next_inspection_due=next_insp,
                spare_part_status=sp_status,
                component_type=c_type
            )

            row_dict = row.to_dict()
            row_dict["priority_score"] = assessment["priority_score"]
            row_dict["priority_category"] = assessment["priority_category"]
            row_dict["action_recommendation"] = assessment["action_recommendation"]
            row_dict["spare_part_status"] = sp_status
            out_rows.append(row_dict)

        df_prioritized = pd.DataFrame(out_rows)
        # Sort by priority score descending
        return df_prioritized.sort_values(by="priority_score", ascending=False).reset_index(drop=True)
