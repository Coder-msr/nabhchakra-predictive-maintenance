"""Synthetic Time-Series Sensor Telemetry and Fault Event Generator.

Generates 90 days of telemetry across aircraft components with realistic nominal bands,
sensor Gaussian noise, physics-inspired degradation signatures, and anomaly scores.
"""

from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from config.settings import RANDOM_SEED, SENSOR_THRESHOLDS


def generate_sensor_telemetry_and_faults(
    aircraft_df: pd.DataFrame,
    components_df: pd.DataFrame,
    days: int = 90,
    interval_days: int = 2,
    seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate time-series telemetry and associated fault events.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (sensor_telemetry_df, fault_events_df)
    """
    random.seed(seed)
    np.random.seed(seed)

    base_end_date = datetime(2026, 10, 28, 12, 0, 0)
    start_date = base_end_date - timedelta(days=days)
    num_steps = (days // interval_days) + 1

    telemetry_records: List[Dict] = []
    fault_records: List[Dict] = []
    fault_counter = 1

    # Map aircraft operational status
    ac_status_map = dict(zip(aircraft_df["aircraft_id"], aircraft_df["operational_status"]))

    # Determine which components have degrading behaviors (~20% of components)
    degrading_components = {}
    for _, comp in components_df.iterrows():
        comp_id = comp["component_id"]
        c_type = comp["component_type"]
        h_idx = comp["health_index"]
        ac_status = ac_status_map.get(comp["aircraft_id"], "Available")

        # If health index is low or aircraft is Grounded/Maintenance, force degradation
        if h_idx < 75.0 or ac_status in ("Grounded", "In Maintenance") or random.random() < 0.12:
            # Pick a degradation failure mode
            if c_type == "Turbofan Engine":
                mode = random.choice(["thermal_creep", "vibration_surge", "oil_starvation"])
            elif c_type == "Hydraulic Actuator":
                mode = "hydraulic_pressure_drop"
            elif c_type == "Auxiliary Power Unit (APU)":
                mode = random.choice(["vibration_surge", "thermal_creep"])
            elif c_type == "Landing Gear Assembly":
                mode = "vibration_surge"
            else:
                mode = "intermittent_anomaly"
            
            onset_step = random.randint(int(num_steps * 0.35), int(num_steps * 0.70))
            degrading_components[comp_id] = {"mode": mode, "onset": onset_step}

    # Generate telemetry snapshots
    for step in range(num_steps):
        current_time = start_date + timedelta(days=step * interval_days)
        time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

        for _, comp in components_df.iterrows():
            comp_id = comp["component_id"]
            ac_id = comp["aircraft_id"]
            c_type = comp["component_type"]

            # Nominal baselines
            temp = float(np.random.normal(710.0, 12.0))
            vib = float(np.random.normal(1.35, 0.18))
            oil = float(np.random.normal(63.0, 2.5))
            hyd = float(np.random.normal(205.0, 2.2))
            cycles_done = int(step * 3 + random.randint(1, 4))

            # Apply degradation if active
            is_degrading = comp_id in degrading_components
            if is_degrading:
                deg_info = degrading_components[comp_id]
                mode = deg_info["mode"]
                onset = deg_info["onset"]

                if step >= onset:
                    progress = (step - onset) / (num_steps - onset)
                    if mode == "thermal_creep":
                        temp += 160.0 * (progress ** 1.6)
                    elif mode == "vibration_surge":
                        vib += 3.2 * (progress ** 1.4)
                    elif mode == "oil_starvation":
                        oil -= 28.0 * (progress ** 1.3)
                    elif mode == "hydraulic_pressure_drop":
                        hyd -= 34.0 * (progress ** 1.5)
                    elif mode == "intermittent_anomaly":
                        if random.random() < 0.4:
                            temp += float(np.random.uniform(50.0, 110.0))
                            vib += float(np.random.uniform(0.8, 2.0))

            # Clamp physical limits
            temp = max(550.0, min(1000.0, temp))
            vib = max(0.2, min(7.0, vib))
            oil = max(15.0, min(100.0, oil))
            hyd = max(140.0, min(260.0, hyd))

            # Compute Anomaly Score (normalized deviation from nominal bounds)
            score_temp = max(0.0, (temp - 820.0) / 110.0)
            score_vib = max(0.0, (vib - 2.5) / 2.3)
            score_oil = max(0.0, (50.0 - oil) / 18.0, (oil - 75.0) / 15.0)
            score_hyd = max(0.0, (195.0 - hyd) / 25.0, (hyd - 215.0) / 30.0)

            raw_anomaly = max(score_temp, score_vib, score_oil, score_hyd)
            anomaly_score = float(np.clip(raw_anomaly + np.random.uniform(-0.03, 0.03), 0.0, 1.0))
            is_anomaly = 1 if anomaly_score >= 0.65 else 0

            telemetry_records.append({
                "aircraft_id": ac_id,
                "component_id": comp_id,
                "timestamp": time_str,
                "engine_temp_c": round(temp, 1),
                "vibration_rms": round(vib, 2),
                "oil_pressure_psi": round(oil, 1),
                "hydraulic_pressure_bar": round(hyd, 1),
                "operating_cycles": cycles_done,
                "anomaly_score": round(anomaly_score, 3),
                "is_anomaly": is_anomaly,
            })

            # If anomaly is severe and towards later stages, create a fault event record
            if anomaly_score >= 0.75 and random.random() < 0.25:
                fault_id = f"FLT-{fault_counter:04d}"
                fault_counter += 1

                if score_temp >= 0.65:
                    f_code = "EGT-EXCEED-01"
                    f_desc = f"Exhaust Gas Temperature exceeded threshold: {round(temp, 1)}°C"
                    sev = "Critical" if temp > 920.0 else "Moderate"
                elif score_vib >= 0.65:
                    f_code = "VIB-HARMONIC-02"
                    f_desc = f"Excessive vibration RMS detected: {round(vib, 2)} mm/s"
                    sev = "Critical" if vib > 4.5 else "Moderate"
                elif score_oil >= 0.65:
                    f_code = "OIL-PRESS-DEV"
                    f_desc = f"Abnormal oil pressure: {round(oil, 1)} PSI"
                    sev = "Moderate"
                else:
                    f_code = "HYD-PRESS-LOW"
                    f_desc = f"Hydraulic subsystem pressure loss: {round(hyd, 1)} bar"
                    sev = "Critical" if hyd < 175.0 else "Moderate"

                # Check if fault is already resolved
                is_res = 1 if step < num_steps - 5 and random.random() < 0.6 else 0

                fault_records.append({
                    "fault_id": fault_id,
                    "aircraft_id": ac_id,
                    "component_id": comp_id,
                    "fault_code": f_code,
                    "severity": sev,
                    "detected_timestamp": time_str,
                    "description": f_desc,
                    "is_resolved": is_res,
                })

    telemetry_df = pd.DataFrame(telemetry_records)
    faults_df = pd.DataFrame(fault_records)

    # De-duplicate faults on component & day to avoid excessive repeated records
    if not faults_df.empty:
        faults_df["date"] = faults_df["detected_timestamp"].str.slice(0, 10)
        faults_df = faults_df.drop_duplicates(subset=["component_id", "fault_code", "date"]).drop(columns=["date"])

    return telemetry_df, faults_df
