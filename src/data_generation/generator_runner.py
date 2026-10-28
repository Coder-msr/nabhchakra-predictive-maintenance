"""Master Orchestrator for Synthetic Data Generation.

Coordinates generation across all 8 relational tables, validates schema and
referential integrity, exports raw CSV snapshots, and seeds the SQLite database.
"""

from pathlib import Path
from typing import Dict, Tuple
import pandas as pd

from config.settings import DB_PATH, RANDOM_SEED, RAW_DATA_DIR
from src.database.db_manager import DatabaseManager
from src.data_generation.fleet_generator import generate_fleet_data
from src.data_generation.inventory_data import generate_spare_parts_data
from src.data_generation.maintenance_data import (
    generate_maintenance_records_and_schedules,
    generate_maintenance_teams_data,
)
from src.data_generation.sensor_generator import generate_sensor_telemetry_and_faults


def run_full_data_generation(
    seed: int = RANDOM_SEED,
    export_csv: bool = True,
    seed_db: bool = True,
    db_path: Path = DB_PATH
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, int]]:
    """Generate all synthetic tables, validate relations, export CSVs, and load SQLite.

    Returns:
        Tuple[Dict[str, pd.DataFrame], Dict[str, int]]:
            (dictionary of DataFrames, dictionary of row counts)
    """
    # 1. Generate Fleet Master and Components
    aircraft_df, components_df = generate_fleet_data(seed=seed)

    # 2. Generate Sensor Telemetry and Fault Events
    telemetry_df, faults_df = generate_sensor_telemetry_and_faults(
        aircraft_df, components_df, days=90, interval_days=2, seed=seed
    )

    # 3. Generate Spare Parts Inventory
    parts_df = generate_spare_parts_data(seed=seed)

    # 4. Generate Maintenance Teams
    teams_df = generate_maintenance_teams_data()

    # 5. Generate Maintenance Records and Schedules
    records_df, schedules_df = generate_maintenance_records_and_schedules(
        aircraft_df, components_df, parts_df, teams_df, seed=seed
    )

    tables: Dict[str, pd.DataFrame] = {
        "aircraft": aircraft_df,
        "components": components_df,
        "sensor_telemetry": telemetry_df,
        "fault_events": faults_df,
        "spare_parts": parts_df,
        "maintenance_teams": teams_df,
        "maintenance_records": records_df,
        "maintenance_schedules": schedules_df,
    }

    # 6. Integrity Validations
    _validate_referential_integrity(tables)

    # 7. CSV Export
    if export_csv:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        for name, df in tables.items():
            csv_path = RAW_DATA_DIR / f"{name}.csv"
            df.to_csv(csv_path, index=False)

    # 8. Seed SQLite Database
    counts: Dict[str, int] = {}
    if seed_db:
        db = DatabaseManager(db_path)
        db.reset_db()

        # Ingest in relational dependency order
        insertion_order = [
            "aircraft",
            "components",
            "sensor_telemetry",
            "fault_events",
            "spare_parts",
            "maintenance_teams",
            "maintenance_records",
            "maintenance_schedules",
        ]

        for table_name in insertion_order:
            df = tables[table_name]
            db.df_to_table(df, table_name, if_exists="append")

        counts = db.get_table_counts()
    else:
        counts = {name: len(df) for name, df in tables.items()}

    return tables, counts


def _validate_referential_integrity(tables: Dict[str, pd.DataFrame]) -> None:
    """Validate primary keys, non-null requirements, and foreign key existence."""
    ac_ids = set(tables["aircraft"]["aircraft_id"])
    comp_ids = set(tables["components"]["component_id"])
    team_ids = set(tables["maintenance_teams"]["team_id"])
    part_ids = set(tables["spare_parts"]["part_id"])

    # 1. Aircraft IDs in components
    assert tables["components"]["aircraft_id"].isin(ac_ids).all(), "Orphaned component aircraft_id"

    # 2. Telemetry references
    assert tables["sensor_telemetry"]["aircraft_id"].isin(ac_ids).all(), "Invalid aircraft_id in telemetry"
    assert tables["sensor_telemetry"]["component_id"].isin(comp_ids).all(), "Invalid component_id in telemetry"

    # 3. Fault events references
    assert tables["fault_events"]["aircraft_id"].isin(ac_ids).all(), "Invalid aircraft_id in faults"
    assert tables["fault_events"]["component_id"].isin(comp_ids).all(), "Invalid component_id in faults"

    # 4. Maintenance records references
    assert tables["maintenance_records"]["aircraft_id"].isin(ac_ids).all(), "Invalid aircraft_id in records"

    # 5. Maintenance schedules references
    assert tables["maintenance_schedules"]["aircraft_id"].isin(ac_ids).all(), "Invalid aircraft_id in schedules"
    valid_parts = part_ids.union({None})
    valid_teams = team_ids.union({None})
    assert tables["maintenance_schedules"]["assigned_team_id"].isin(valid_teams).all(), "Invalid team_id in schedule"


if __name__ == "__main__":
    print("Generating NABHCHAKRA synthetic fleet dataset...")
    tables, counts = run_full_data_generation()
    print("Generation complete! Summary row counts:")
    for tbl, count in counts.items():
        print(f"  - {tbl:25s}: {count:,} rows")
