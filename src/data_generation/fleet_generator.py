"""Synthetic Fleet and Aircraft Component Generator.

Produces 28 realistic multi-role aircraft and their core subsystem components
with consistent IDs, operating hours, cycles, and initial health indices.
"""

from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from config.settings import AIRCRAFT_MODELS, COMPONENT_TYPES, FLEET_SIZE, RANDOM_SEED, SQUADRONS


def generate_fleet_data(seed: int = RANDOM_SEED) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate synthetic aircraft and component master records.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (aircraft_df, components_df)
    """
    random.seed(seed)
    np.random.seed(seed)

    # Distribute aircraft count across models
    models_distribution = [
        ("Su-30MKI", 6),
        ("Rafale", 6),
        ("Tejas Mk1A", 5),
        ("Mirage 2000", 4),
        ("C-130J", 4),
        ("Netra AEW&C", 3),
    ]

    aircraft_records: List[Dict] = []
    component_records: List[Dict] = []

    aircraft_counter = 1
    component_counter = 1
    base_date = datetime(2026, 10, 1)

    for model_name, count in models_distribution:
        model_info = AIRCRAFT_MODELS[model_name]
        role = model_info["role"]

        for _ in range(count):
            ac_id = f"AF-{aircraft_counter:03d}"
            # Tail number prefix based on model
            tail_prefix = model_name[:2].upper()
            tail_number = f"IAF-{tail_prefix}-{100 + aircraft_counter}"

            squadron = SQUADRONS[(aircraft_counter - 1) % len(SQUADRONS)]

            # Commission date: 2 to 8 years prior
            commission_days_ago = random.randint(700, 2800)
            commission_date = (base_date - timedelta(days=commission_days_ago)).strftime("%Y-%m-%d")

            # Flight hours & cycles
            flight_hours = round(float(np.random.uniform(650.0, 3100.0)), 1)
            flight_cycles = int(flight_hours * np.random.uniform(0.60, 0.78))

            # Operational status assignment (synthetic operational distribution)
            # ~70% Available, ~15% In Maintenance, ~10% Under Inspection, ~5% Grounded
            status_rand = random.random()
            if status_rand < 0.70:
                op_status = "Available"
            elif status_rand < 0.85:
                op_status = "In Maintenance"
            elif status_rand < 0.95:
                op_status = "Under Inspection"
            else:
                op_status = "Grounded"

            # Inspections
            last_inspection_days = random.randint(10, 120)
            last_insp_date = (base_date - timedelta(days=last_inspection_days)).strftime("%Y-%m-%d")
            # Next inspection usually due at 90-120 days interval
            next_insp_days = 90 - last_inspection_days
            next_insp_date = (base_date + timedelta(days=next_insp_days)).strftime("%Y-%m-%d")

            aircraft_records.append({
                "aircraft_id": ac_id,
                "tail_number": tail_number,
                "model_type": model_name,
                "role": role,
                "squadron_id": squadron,
                "commission_date": commission_date,
                "total_flight_hours": flight_hours,
                "total_flight_cycles": flight_cycles,
                "operational_status": op_status,
                "last_inspection_date": last_insp_date,
                "next_inspection_due": next_insp_date,
            })

            # Generate 5 major components per aircraft
            for comp_type in COMPONENT_TYPES:
                comp_id = f"CMP-{component_counter:04d}"
                comp_prefix = comp_type[:3].upper()
                serial_num = f"SN-{comp_prefix}-{1000 + component_counter}"

                installed_days = min(commission_days_ago, random.randint(180, 1200))
                installed_date = (base_date - timedelta(days=installed_days)).strftime("%Y-%m-%d")
                comp_operating_hours = round(float(flight_hours * np.random.uniform(0.40, 0.98)), 1)

                # Health index based on aircraft status & some degradation
                if op_status == "Grounded":
                    health_idx = round(float(np.random.uniform(25.0, 52.0)), 1)
                    comp_status = "Critical" if health_idx < 40 else "Degraded"
                elif op_status == "In Maintenance":
                    health_idx = round(float(np.random.uniform(48.0, 74.0)), 1)
                    comp_status = "Under Repair" if random.random() < 0.5 else "Degraded"
                elif op_status == "Under Inspection":
                    health_idx = round(float(np.random.uniform(65.0, 84.0)), 1)
                    comp_status = "Degraded" if health_idx < 72 else "Nominal"
                else:
                    # Available
                    health_idx = round(float(np.random.uniform(78.0, 99.5)), 1)
                    comp_status = "Nominal"

                component_records.append({
                    "component_id": comp_id,
                    "aircraft_id": ac_id,
                    "component_type": comp_type,
                    "serial_number": serial_num,
                    "installed_date": installed_date,
                    "operating_hours": comp_operating_hours,
                    "health_index": health_idx,
                    "status": comp_status,
                })
                component_counter += 1

            aircraft_counter += 1

    aircraft_df = pd.DataFrame(aircraft_records)
    components_df = pd.DataFrame(component_records)

    return aircraft_df, components_df
