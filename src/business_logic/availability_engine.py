"""Fleet Availability Analytics Engine.

Calculates standard aerospace fleet readiness metrics (FMC, PMC, NMC, Availability %),
decomposes planned vs. unplanned downtime, and forecasts availability trends.
"""

from typing import Dict, List, Optional
import pandas as pd


class FleetAvailabilityEngine:
    """Calculates fleet readiness, mission capability ratios, and downtime analytics."""

    @staticmethod
    def calculate_current_availability(
        aircraft_df: pd.DataFrame,
        prioritized_components_df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """Compute authoritative fleet availability KPIs."""
        total_fleet = len(aircraft_df)
        if total_fleet == 0:
            return {
                "total_aircraft": 0,
                "fmc_count": 0,
                "pmc_count": 0,
                "nmc_count": 0,
                "availability_pct": 0.0,
                "fmc_pct": 0.0,
                "pmc_pct": 0.0,
                "nmc_pct": 0.0,
                "available_status_count": 0,
                "maintenance_status_count": 0,
                "grounded_status_count": 0,
                "inspection_status_count": 0,
            }

        # Status counts
        status_counts = aircraft_df["operational_status"].value_counts().to_dict()
        available_cnt = status_counts.get("Available", 0)
        maint_cnt = status_counts.get("In Maintenance", 0)
        grounded_cnt = status_counts.get("Grounded", 0)
        inspect_cnt = status_counts.get("Under Inspection", 0)

        # Identify aircraft with elevated/critical component failure risks
        critical_risk_aircraft = set()
        elevated_risk_aircraft = set()

        if prioritized_components_df is not None and not prioritized_components_df.empty:
            crit_rows = prioritized_components_df[
                (prioritized_components_df["predicted_risk_prob"] >= 0.70) |
                (prioritized_components_df["priority_category"] == "Critical")
            ]
            critical_risk_aircraft = set(crit_rows["aircraft_id"])

            elev_rows = prioritized_components_df[
                (prioritized_components_df["predicted_risk_prob"] >= 0.40) &
                (prioritized_components_df["predicted_risk_prob"] < 0.70)
            ]
            elevated_risk_aircraft = set(elev_rows["aircraft_id"])

        # Determine FMC, PMC, NMC for each aircraft
        fmc_list, pmc_list, nmc_list = [], [], []

        for _, ac in aircraft_df.iterrows():
            ac_id = ac["aircraft_id"]
            op_status = ac["operational_status"]

            if op_status in ("Grounded", "In Maintenance") or ac_id in critical_risk_aircraft:
                nmc_list.append(ac_id)
            elif op_status == "Under Inspection" or ac_id in elevated_risk_aircraft:
                pmc_list.append(ac_id)
            else:
                fmc_list.append(ac_id)

        fmc = len(fmc_list)
        pmc = len(pmc_list)
        nmc = len(nmc_list)

        # Standard readiness formula: (FMC + 0.5 * PMC) / Total * 100
        avail_pct = round(((fmc + 0.5 * pmc) / total_fleet) * 100, 1)
        fmc_pct = round((fmc / total_fleet) * 100, 1)
        pmc_pct = round((pmc / total_fleet) * 100, 1)
        nmc_pct = round((nmc / total_fleet) * 100, 1)

        return {
            "total_aircraft": total_fleet,
            "fmc_count": fmc,
            "pmc_count": pmc,
            "nmc_count": nmc,
            "availability_pct": avail_pct,
            "fmc_pct": fmc_pct,
            "pmc_pct": pmc_pct,
            "nmc_pct": nmc_pct,
            "available_status_count": available_cnt,
            "maintenance_status_count": maint_cnt,
            "grounded_status_count": grounded_cnt,
            "inspection_status_count": inspect_cnt,
            "fmc_aircraft_ids": fmc_list,
            "pmc_aircraft_ids": pmc_list,
            "nmc_aircraft_ids": nmc_list,
        }

    @staticmethod
    def get_availability_by_model(
        aircraft_df: pd.DataFrame,
        prioritized_components_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Compute readiness metrics grouped by aircraft model."""
        rows = []
        for model_name, group in aircraft_df.groupby("model_type"):
            res = FleetAvailabilityEngine.calculate_current_availability(group, prioritized_components_df)
            rows.append({
                "model_type": model_name,
                "role": group.iloc[0]["role"],
                "total_aircraft": res["total_aircraft"],
                "fmc": res["fmc_count"],
                "pmc": res["pmc_count"],
                "nmc": res["nmc_count"],
                "availability_pct": res["availability_pct"],
            })

        df_model = pd.DataFrame(rows)
        return df_model.sort_values(by="availability_pct", ascending=False).reset_index(drop=True)

    @staticmethod
    def get_availability_by_squadron(
        aircraft_df: pd.DataFrame,
        prioritized_components_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Compute readiness metrics grouped by squadron."""
        rows = []
        for sq_name, group in aircraft_df.groupby("squadron_id"):
            res = FleetAvailabilityEngine.calculate_current_availability(group, prioritized_components_df)
            rows.append({
                "squadron_id": sq_name,
                "total_aircraft": res["total_aircraft"],
                "fmc": res["fmc_count"],
                "pmc": res["pmc_count"],
                "nmc": res["nmc_count"],
                "availability_pct": res["availability_pct"],
            })

        df_sq = pd.DataFrame(rows)
        return df_sq.sort_values(by="availability_pct", ascending=False).reset_index(drop=True)

    @staticmethod
    def calculate_downtime_decomposition(
        maintenance_records_df: pd.DataFrame,
        aircraft_df: pd.DataFrame
    ) -> Dict:
        """Decompose historical maintenance downtime into Planned vs Unplanned hours."""
        if maintenance_records_df.empty:
            return {"planned_hours": 0.0, "unplanned_hours": 0.0, "planned_pct": 50.0, "unplanned_pct": 50.0}

        # Calculate durations from start_time and end_time
        df_records = maintenance_records_df.dropna(subset=["start_time", "end_time"]).copy()
        df_records["start"] = pd.to_datetime(df_records["start_time"])
        df_records["end"] = pd.to_datetime(df_records["end_time"])
        df_records["duration_hrs"] = (df_records["end"] - df_records["start"]).dt.total_seconds() / 3600.0

        planned_mask = df_records["maintenance_type"].isin(["Scheduled", "Pre-Flight Inspection", "Overhaul"])
        unplanned_mask = df_records["maintenance_type"] == "Unscheduled"

        planned_hrs = round(float(df_records[planned_mask]["duration_hrs"].sum()), 1)
        unplanned_hrs = round(float(df_records[unplanned_mask]["duration_hrs"].sum()), 1)
        total_hrs = planned_hrs + unplanned_hrs

        if total_hrs > 0:
            planned_pct = round((planned_hrs / total_hrs) * 100, 1)
            unplanned_pct = round((unplanned_hrs / total_hrs) * 100, 1)
        else:
            planned_pct, unplanned_pct = 0.0, 0.0

        return {
            "total_downtime_hours": total_hrs,
            "planned_hours": planned_hrs,
            "unplanned_hours": unplanned_hrs,
            "planned_pct": planned_pct,
            "unplanned_pct": unplanned_pct,
        }
