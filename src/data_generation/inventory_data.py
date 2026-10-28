"""Synthetic Spare Parts Inventory Catalog Generator.

Generates realistic spare parts mapped to aircraft subsystems with stock quantities,
reorder thresholds, lead times, unit costs in INR, and operational stock statuses.
"""

from typing import Dict, List
import pandas as pd

from config.settings import RANDOM_SEED


def generate_spare_parts_data(seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate spare parts inventory master records.

    Returns:
        pd.DataFrame: spare_parts table records
    """
    parts_catalog = [
        # Turbofan Engine Parts
        {
            "part_id": "PRT-ENG-01",
            "part_name": "High-Pressure Turbine Rotor Blade Set",
            "compatible_component_type": "Turbofan Engine",
            "stock_quantity": 4,
            "reorder_threshold": 6,
            "lead_time_days": 28,
            "unit_cost_inr": 2850000.0,
        },
        {
            "part_id": "PRT-ENG-02",
            "part_name": "Full Authority Digital Engine Controller (FADEC)",
            "compatible_component_type": "Turbofan Engine",
            "stock_quantity": 2,
            "reorder_threshold": 3,
            "lead_time_days": 45,
            "unit_cost_inr": 4200000.0,
        },
        {
            "part_id": "PRT-ENG-03",
            "part_name": "Turbine Bearings & High-Temp Lubrication Kit",
            "compatible_component_type": "Turbofan Engine",
            "stock_quantity": 12,
            "reorder_threshold": 5,
            "lead_time_days": 14,
            "unit_cost_inr": 380000.0,
        },
        {
            "part_id": "PRT-ENG-04",
            "part_name": "Afterburner Fuel Spray Ring Nozzle",
            "compatible_component_type": "Turbofan Engine",
            "stock_quantity": 0,  # Critical shortage scenario
            "reorder_threshold": 4,
            "lead_time_days": 35,
            "unit_cost_inr": 890000.0,
        },

        # Hydraulic Actuator Parts
        {
            "part_id": "PRT-HYD-01",
            "part_name": "Primary Flight Control Electro-Hydraulic Servo Valve",
            "compatible_component_type": "Hydraulic Actuator",
            "stock_quantity": 3,
            "reorder_threshold": 5,
            "lead_time_days": 21,
            "unit_cost_inr": 1150000.0,
        },
        {
            "part_id": "PRT-HYD-02",
            "part_name": "High-Pressure Hydraulic Seal & Gasket Overhaul Kit",
            "compatible_component_type": "Hydraulic Actuator",
            "stock_quantity": 18,
            "reorder_threshold": 8,
            "lead_time_days": 10,
            "unit_cost_inr": 145000.0,
        },
        {
            "part_id": "PRT-HYD-03",
            "part_name": "Variable Displacement Hydraulic Pump Assembly",
            "compatible_component_type": "Hydraulic Actuator",
            "stock_quantity": 1,  # Low stock
            "reorder_threshold": 3,
            "lead_time_days": 30,
            "unit_cost_inr": 1820000.0,
        },

        # Avionics & Radar Parts
        {
            "part_id": "PRT-AVN-01",
            "part_name": "AESA Radar Gallium Nitride (GaN) T/R Module",
            "compatible_component_type": "Avionics & Radar System",
            "stock_quantity": 8,
            "reorder_threshold": 6,
            "lead_time_days": 40,
            "unit_cost_inr": 3100000.0,
        },
        {
            "part_id": "PRT-AVN-02",
            "part_name": "Integrated Core Processor / Mission Computer Board",
            "compatible_component_type": "Avionics & Radar System",
            "stock_quantity": 0,  # Out of stock
            "reorder_threshold": 2,
            "lead_time_days": 50,
            "unit_cost_inr": 5400000.0,
        },
        {
            "part_id": "PRT-AVN-03",
            "part_name": "Inertial Navigation Laser Gyroscope Sensor Unit",
            "compatible_component_type": "Avionics & Radar System",
            "stock_quantity": 5,
            "reorder_threshold": 3,
            "lead_time_days": 25,
            "unit_cost_inr": 2250000.0,
        },

        # Auxiliary Power Unit (APU) Parts
        {
            "part_id": "PRT-APU-01",
            "part_name": "APU High-Speed Starter Generator",
            "compatible_component_type": "Auxiliary Power Unit (APU)",
            "stock_quantity": 6,
            "reorder_threshold": 4,
            "lead_time_days": 18,
            "unit_cost_inr": 950000.0,
        },
        {
            "part_id": "PRT-APU-02",
            "part_name": "Gas Turbine Compressor Impeller Wheel",
            "compatible_component_type": "Auxiliary Power Unit (APU)",
            "stock_quantity": 2,  # Low stock
            "reorder_threshold": 3,
            "lead_time_days": 30,
            "unit_cost_inr": 1350000.0,
        },

        # Landing Gear Assembly Parts
        {
            "part_id": "PRT-LGR-01",
            "part_name": "Main Landing Gear Carbon-Carbon Brake Disk Pack",
            "compatible_component_type": "Landing Gear Assembly",
            "stock_quantity": 14,
            "reorder_threshold": 6,
            "lead_time_days": 12,
            "unit_cost_inr": 480000.0,
        },
        {
            "part_id": "PRT-LGR-02",
            "part_name": "Oleo-Pneumatic Shock Strut Seal Kit",
            "compatible_component_type": "Landing Gear Assembly",
            "stock_quantity": 9,
            "reorder_threshold": 5,
            "lead_time_days": 15,
            "unit_cost_inr": 210000.0,
        },
        {
            "part_id": "PRT-LGR-03",
            "part_name": "Hydraulic Gear Retraction & Lock Actuator",
            "compatible_component_type": "Landing Gear Assembly",
            "stock_quantity": 3,
            "reorder_threshold": 3,
            "lead_time_days": 24,
            "unit_cost_inr": 1650000.0,
        },
    ]

    records: List[Dict] = []
    for p in parts_catalog:
        qty = p["stock_quantity"]
        thresh = p["reorder_threshold"]

        if qty == 0:
            status = "Out of Stock"
        elif qty <= thresh:
            status = "Low Stock"
        else:
            status = "In Stock"

        record = dict(p)
        record["status"] = status
        records.append(record)

    return pd.DataFrame(records)
