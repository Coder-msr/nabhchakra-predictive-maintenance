"""Central configuration and constants for NABHCHAKRA.

All values, thresholds, and baseline parameters used across data generation,
predictive modeling, maintenance prioritization, and UI presentation are defined here.
"""

from pathlib import Path

# ==============================================================================
# DIRECTORY STRUCTURE & PATHS
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "nabhchakra.db"
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "failure_risk_model.joblib"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

# Ensure runtime directories exist
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# GENERAL SYSTEM PARAMETERS
# ==============================================================================
APP_TITLE = "NABHCHAKRA — Air Power Decision Platform"
APP_SUBTITLE = "Predictive Maintenance & Fleet Availability Decision Platform"
RANDOM_SEED = 42

# Clear disclaimer for research and academic hackathon demonstration
DISCLAIMER_TEXT = (
    "RESEARCH & DEMONSTRATION PROTOTYPE: All data, metrics, sensor values, "
    "and predictions within NABHCHAKRA are synthetic estimates derived from "
    "mathematical models. This platform does not utilize classified military data, "
    "operational flight logs, or certified aerospace engineering limits. Final "
    "airworthiness decisions remain strictly human-in-the-loop."
)

# ==============================================================================
# FLEET CONFIGURATION
# ==============================================================================
FLEET_SIZE = 28  # Balanced synthetic fleet size for fast, responsive MVP execution

AIRCRAFT_MODELS = {
    "Su-30MKI": {"role": "Air Superiority / Strike", "base_engines": 2, "avg_flight_hrs_month": 45},
    "Rafale": {"role": "Omnirole Fighter", "base_engines": 2, "avg_flight_hrs_month": 40},
    "Tejas Mk1A": {"role": "Light Combat Fighter", "base_engines": 1, "avg_flight_hrs_month": 35},
    "Mirage 2000": {"role": "Multi-Role Fighter", "base_engines": 1, "avg_flight_hrs_month": 30},
    "C-130J": {"role": "Tactical Transport", "base_engines": 4, "avg_flight_hrs_month": 55},
    "Netra AEW&C": {"role": "Airborne Early Warning", "base_engines": 2, "avg_flight_hrs_month": 30},
}

SQUADRONS = [
    "No. 102 Squadron (Trisonics)",
    "No. 17 Squadron (Golden Arrows)",
    "No. 45 Squadron (Flying Daggers)",
    "No. 7 Squadron (Battle Axes)",
    "No. 77 Squadron (Veiled Vipers)",
]

COMPONENT_TYPES = [
    "Turbofan Engine",
    "Hydraulic Actuator",
    "Avionics & Radar System",
    "Auxiliary Power Unit (APU)",
    "Landing Gear Assembly",
]

# ==============================================================================
# SYNTHETIC SENSOR THRESHOLDS (Non-certified illustrative telemetry boundaries)
# ==============================================================================
SENSOR_THRESHOLDS = {
    "engine_temp_c": {
        "unit": "°C",
        "nominal_min": 620.0,
        "nominal_max": 820.0,
        "warning_max": 875.0,
        "critical_max": 930.0,
    },
    "vibration_rms": {
        "unit": "mm/s",
        "nominal_min": 0.6,
        "nominal_max": 2.5,
        "warning_max": 3.6,
        "critical_max": 4.8,
    },
    "oil_pressure_psi": {
        "unit": "PSI",
        "nominal_min": 50.0,
        "nominal_max": 75.0,
        "warning_min": 40.0,
        "critical_min": 32.0,
    },
    "hydraulic_pressure_bar": {
        "unit": "bar",
        "nominal_min": 195.0,
        "nominal_max": 215.0,
        "warning_min": 185.0,
        "critical_min": 170.0,
    },
    "anomaly_score": {
        "unit": "Index",
        "nominal_max": 0.40,
        "warning_max": 0.70,
        "critical_max": 1.00,
    },
}

# ==============================================================================
# PREDICTIVE MAINTENANCE ML CONFIGURATION
# ==============================================================================
PREDICTION_WINDOW_DAYS = 30  # Predict failure risk in next 30 days/cycles
ML_TEST_SPLIT_RATIO = 0.25
CLASSIFICATION_THRESHOLD = 0.50

RISK_TIERS = {
    "Low": (0.00, 0.35),
    "Moderate": (0.35, 0.65),
    "Elevated": (0.65, 0.85),
    "Critical": (0.85, 1.00),
}

# ==============================================================================
# MAINTENANCE PRIORITY WEIGHTING MATRIX
# ==============================================================================
# Priority Score = w1*Risk + w2*Overdue + w3*SparesShortage + w4*Criticality
PRIORITY_WEIGHTS = {
    "failure_risk": 0.40,
    "inspection_overdue": 0.25,
    "spare_parts_shortage": 0.20,
    "mission_criticality": 0.15,
}

# ==============================================================================
# UI COLOR PALETTE & THEME TOKENS (Aerospace Command Center)
# ==============================================================================
THEME_COLORS = {
    "background_dark": "#0B132B",
    "card_bg": "#1C2541",
    "card_border": "#2E3B5E",
    "accent_cyan": "#5BC0BE",
    "accent_glow": "#6FFFE9",
    "text_primary": "#FFFFFF",
    "text_secondary": "#A0AEC0",
    "status_nominal": "#10B981",   # Emerald Green
    "status_warning": "#F59E0B",   # Amber
    "status_critical": "#EF4444",  # Crimson Red
    "status_info": "#3B82F6",      # Cobalt Blue
}
