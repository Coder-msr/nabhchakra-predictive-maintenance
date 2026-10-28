"""Data Preprocessing and Feature Engineering Pipeline for Predictive Maintenance.

Transforms time-series telemetry, maintenance records, and aircraft master data
into structured, stationary tabular feature vectors with strict time-cutoff windowing
to eliminate target data leakage.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from config.settings import DB_PATH, PROCESSED_DATA_DIR, RANDOM_SEED
from src.database.db_manager import DatabaseManager


FEATURE_COLUMNS = [
    "temp_mean_30d",
    "temp_std_30d",
    "temp_max_30d",
    "temp_trend_slope",
    "vib_mean_30d",
    "vib_std_30d",
    "vib_max_30d",
    "vib_trend_slope",
    "oil_mean_30d",
    "oil_std_30d",
    "oil_min_30d",
    "hyd_mean_30d",
    "hyd_std_30d",
    "hyd_min_30d",
    "anomaly_score_mean_14d",
    "anomaly_score_max_14d",
    "latest_anomaly_score",
    "comp_operating_hours",
    "aircraft_flight_hours",
    "aircraft_flight_cycles",
    "comp_health_index",
    # Encoded component types
    "comp_type_Turbofan Engine",
    "comp_type_Hydraulic Actuator",
    "comp_type_Avionics & Radar System",
    "comp_type_Auxiliary Power Unit (APU)",
    "comp_type_Landing Gear Assembly",
]

TARGET_COLUMN = "target_maintenance_required_30d"


class TelemetryFeatureEngineer:
    """Extracts leakage-free tabular feature vectors and target labels from relational data."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_manager = DatabaseManager(db_path or DB_PATH)

    def load_data(self) -> Dict[str, pd.DataFrame]:
        """Load required relational tables from SQLite into memory."""
        data = {
            "aircraft": self.db_manager.query_to_df("SELECT * FROM aircraft;"),
            "components": self.db_manager.query_to_df("SELECT * FROM components;"),
            "sensor_telemetry": self.db_manager.query_to_df("SELECT * FROM sensor_telemetry ORDER BY timestamp ASC;"),
            "fault_events": self.db_manager.query_to_df("SELECT * FROM fault_events;"),
            "maintenance_records": self.db_manager.query_to_df("SELECT * FROM maintenance_records;"),
        }
        # Parse timestamps to datetime
        data["sensor_telemetry"]["timestamp"] = pd.to_datetime(data["sensor_telemetry"]["timestamp"])
        if not data["fault_events"].empty:
            data["fault_events"]["detected_timestamp"] = pd.to_datetime(data["fault_events"]["detected_timestamp"])
        if not data["maintenance_records"].empty:
            data["maintenance_records"]["start_time"] = pd.to_datetime(data["maintenance_records"]["start_time"])

        return data

    def extract_features_at_cutoff(
        self,
        cutoff_date: pd.Timestamp,
        data: Dict[str, pd.DataFrame],
        window_days: int = 30,
        forward_days: int = 30,
        is_inference: bool = False
    ) -> pd.DataFrame:
        """Extract historical features up to cutoff_date and forward target label.

        Strict leakage prevention:
        - Features are derived ONLY from telemetry <= cutoff_date.
        - Target label is derived ONLY from events in (cutoff_date, cutoff_date + forward_days].
        """
        telemetry = data["sensor_telemetry"]
        components = data["components"]
        aircraft = data["aircraft"].set_index("aircraft_id")
        faults = data["fault_events"]

        history_start = cutoff_date - pd.Timedelta(days=window_days)
        recent_14d_start = cutoff_date - pd.Timedelta(days=14)
        forward_end = cutoff_date + pd.Timedelta(days=forward_days)

        # Slice past telemetry strictly <= cutoff_date
        past_telemetry = telemetry[
            (telemetry["timestamp"] >= history_start) & (telemetry["timestamp"] <= cutoff_date)
        ]

        # Forward telemetry and faults strictly > cutoff_date (for target generation)
        forward_telemetry = telemetry[
            (telemetry["timestamp"] > cutoff_date) & (telemetry["timestamp"] <= forward_end)
        ]
        forward_faults = faults[
            (faults["detected_timestamp"] > cutoff_date) & (faults["detected_timestamp"] <= forward_end)
        ] if not faults.empty else pd.DataFrame()

        rows = []

        for _, comp in components.iterrows():
            c_id = comp["component_id"]
            ac_id = comp["aircraft_id"]
            c_type = comp["component_type"]

            comp_past = past_telemetry[past_telemetry["component_id"] == c_id]
            if comp_past.empty:
                continue

            # Rolling statistics over past 30 days
            temp_mean = float(comp_past["engine_temp_c"].mean())
            temp_std = float(comp_past["engine_temp_c"].std()) if len(comp_past) > 1 else 0.0
            temp_max = float(comp_past["engine_temp_c"].max())

            vib_mean = float(comp_past["vibration_rms"].mean())
            vib_std = float(comp_past["vibration_rms"].std()) if len(comp_past) > 1 else 0.0
            vib_max = float(comp_past["vibration_rms"].max())

            oil_mean = float(comp_past["oil_pressure_psi"].mean())
            oil_std = float(comp_past["oil_pressure_psi"].std()) if len(comp_past) > 1 else 0.0
            oil_min = float(comp_past["oil_pressure_psi"].min())

            hyd_mean = float(comp_past["hydraulic_pressure_bar"].mean())
            hyd_std = float(comp_past["hydraulic_pressure_bar"].std()) if len(comp_past) > 1 else 0.0
            hyd_min = float(comp_past["hydraulic_pressure_bar"].min())

            # Trend slopes (simple linear trend across available observation steps)
            n_obs = len(comp_past)
            x_steps = np.arange(n_obs)
            if n_obs > 2:
                temp_slope = float(np.polyfit(x_steps, comp_past["engine_temp_c"].values, 1)[0])
                vib_slope = float(np.polyfit(x_steps, comp_past["vibration_rms"].values, 1)[0])
            else:
                temp_slope, vib_slope = 0.0, 0.0

            # Recent 14d window metrics
            comp_14d = comp_past[comp_past["timestamp"] >= recent_14d_start]
            if not comp_14d.empty:
                anomaly_mean_14d = float(comp_14d["anomaly_score"].mean())
                anomaly_max_14d = float(comp_14d["anomaly_score"].max())
            else:
                anomaly_mean_14d, anomaly_max_14d = 0.0, 0.0

            latest_anomaly = float(comp_past.iloc[-1]["anomaly_score"])

            # Aircraft context
            ac_info = aircraft.loc[ac_id] if ac_id in aircraft.index else {}
            ac_hrs = float(ac_info.get("total_flight_hours", 0.0))
            ac_cycles = int(ac_info.get("total_flight_cycles", 0))

            feature_dict = {
                "cutoff_date": cutoff_date.strftime("%Y-%m-%d"),
                "aircraft_id": ac_id,
                "component_id": c_id,
                "component_type": c_type,
                "temp_mean_30d": round(temp_mean, 2),
                "temp_std_30d": round(temp_std, 2),
                "temp_max_30d": round(temp_max, 2),
                "temp_trend_slope": round(temp_slope, 4),
                "vib_mean_30d": round(vib_mean, 2),
                "vib_std_30d": round(vib_std, 2),
                "vib_max_30d": round(vib_max, 2),
                "vib_trend_slope": round(vib_slope, 4),
                "oil_mean_30d": round(oil_mean, 2),
                "oil_std_30d": round(oil_std, 2),
                "oil_min_30d": round(oil_min, 2),
                "hyd_mean_30d": round(hyd_mean, 2),
                "hyd_std_30d": round(hyd_std, 2),
                "hyd_min_30d": round(hyd_min, 2),
                "anomaly_score_mean_14d": round(anomaly_mean_14d, 3),
                "anomaly_score_max_14d": round(anomaly_max_14d, 3),
                "latest_anomaly_score": round(latest_anomaly, 3),
                "comp_operating_hours": float(comp["operating_hours"]),
                "aircraft_flight_hours": ac_hrs,
                "aircraft_flight_cycles": ac_cycles,
                "comp_health_index": float(comp["health_index"]),
            }

            # One-hot encode component type
            for ct in [
                "Turbofan Engine",
                "Hydraulic Actuator",
                "Avionics & Radar System",
                "Auxiliary Power Unit (APU)",
                "Landing Gear Assembly"
            ]:
                feature_dict[f"comp_type_{ct}"] = 1 if c_type == ct else 0

            # Target label calculation (if not in pure inference mode)
            if not is_inference:
                # 1. Did a fault event occur in forward window?
                has_forward_fault = False
                if not forward_faults.empty:
                    has_forward_fault = not forward_faults[
                        forward_faults["component_id"] == c_id
                    ].empty

                # 2. Did forward telemetry degrade significantly (severe anomaly or critical temperature)?
                comp_forward = forward_telemetry[forward_telemetry["component_id"] == c_id]
                has_forward_anomaly = False
                if not comp_forward.empty:
                    max_forward_anomaly = comp_forward["anomaly_score"].max()
                    max_forward_temp = comp_forward["engine_temp_c"].max()
                    max_forward_vib = comp_forward["vibration_rms"].max()
                    if max_forward_anomaly >= 0.70 or max_forward_temp >= 900.0 or max_forward_vib >= 4.0:
                        has_forward_anomaly = True

                target = 1 if (has_forward_fault or has_forward_anomaly) else 0
                feature_dict[TARGET_COLUMN] = target

            rows.append(feature_dict)

        return pd.DataFrame(rows)

    def build_dataset(self) -> pd.DataFrame:
        """Construct multi-period historical dataset across sliding observation dates."""
        data = self.load_data()
        telemetry = data["sensor_telemetry"]

        min_time = telemetry["timestamp"].min()
        max_time = telemetry["timestamp"].max()

        # Observation points with 30-day past window and 30-day forward window
        cutoffs = [
            min_time + pd.Timedelta(days=30),  # Day 30
            min_time + pd.Timedelta(days=45),  # Day 45
            min_time + pd.Timedelta(days=60),  # Day 60
        ]

        dfs = []
        for cutoff in cutoffs:
            if cutoff + pd.Timedelta(days=30) <= max_time:
                df_slice = self.extract_features_at_cutoff(
                    cutoff_date=cutoff,
                    data=data,
                    window_days=30,
                    forward_days=30,
                    is_inference=False
                )
                dfs.append(df_slice)

        full_df = pd.concat(dfs, ignore_index=True)
        return full_df

    def split_train_test_by_aircraft(
        self,
        df: pd.DataFrame,
        test_size: float = 0.25,
        random_state: int = RANDOM_SEED
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Group-aware train/test split ensuring zero aircraft overlap between train and test sets."""
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        train_idx, test_idx = next(gss.split(df, groups=df["aircraft_id"]))

        train_df = df.iloc[train_idx].copy().reset_index(drop=True)
        test_df = df.iloc[test_idx].copy().reset_index(drop=True)

        return train_df, test_df

    def extract_latest_fleet_features(self) -> pd.DataFrame:
        """Extract the most up-to-date feature set as of the latest telemetry timestamp for live inference."""
        data = self.load_data()
        latest_timestamp = data["sensor_telemetry"]["timestamp"].max()

        df_latest = self.extract_features_at_cutoff(
            cutoff_date=latest_timestamp,
            data=data,
            window_days=30,
            forward_days=0,
            is_inference=True
        )
        return df_latest


def run_preprocessing_pipeline() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Execute preprocessing pipeline, export processed datasets to disk, and return splits."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    engineer = TelemetryFeatureEngineer()

    print("Building historical feature dataset...")
    full_df = engineer.build_dataset()

    print(f"Total dataset shape: {full_df.shape}. Positive target class ratio: {full_df[TARGET_COLUMN].mean():.1%}")

    train_df, test_df = engineer.split_train_test_by_aircraft(full_df)
    print(f"Train samples: {len(train_df)} across {train_df['aircraft_id'].nunique()} aircraft")
    print(f"Test samples : {len(test_df)} across {test_df['aircraft_id'].nunique()} aircraft")

    # Export to disk
    train_path = PROCESSED_DATA_DIR / "train_features.csv"
    test_path = PROCESSED_DATA_DIR / "test_features.csv"
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"Exported to {train_path} and {test_path}")
    return train_df, test_df


if __name__ == "__main__":
    run_preprocessing_pipeline()
