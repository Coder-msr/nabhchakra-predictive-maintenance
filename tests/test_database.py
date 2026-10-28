"""Unit tests for the Database Schema and DatabaseManager."""

import sqlite3
import pytest
import pandas as pd
from src.database.db_manager import DatabaseManager


@pytest.fixture
def test_db(tmp_path):
    """Provide a fresh, isolated temporary SQLite DatabaseManager instance for each test."""
    db_file = tmp_path / "test_nabhchakra.db"
    db = DatabaseManager(db_file)
    db.init_db()
    return db


def test_schema_creates_all_tables(test_db):
    """Ensure all 8 core tables are successfully created."""
    expected_tables = [
        "aircraft",
        "components",
        "sensor_telemetry",
        "fault_events",
        "spare_parts",
        "maintenance_teams",
        "maintenance_records",
        "maintenance_schedules",
    ]
    counts = test_db.get_table_counts()
    for table in expected_tables:
        assert test_db.table_exists(table), f"Table {table} does not exist"
        assert counts[table] == 0


def test_insert_and_query_aircraft(test_db):
    """Verify inserting and querying aircraft records via fetch_one, fetch_all, and query_to_df."""
    sql_insert = """
    INSERT INTO aircraft (aircraft_id, tail_number, model_type, role, squadron_id, commission_date, total_flight_hours, total_flight_cycles, operational_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    row_count = test_db.execute_query(sql_insert, (
        "AF-FTR-01", "SB-001", "Su-30MKI", "Air Superiority", "No. 102 Squadron", "2018-03-15", 1450.5, 920, "Available"
    ))
    assert row_count == 1

    # Test fetch_one
    ac = test_db.fetch_one("SELECT * FROM aircraft WHERE aircraft_id = ?", ("AF-FTR-01",))
    assert ac is not None
    assert ac["aircraft_id"] == "AF-FTR-01"
    assert ac["tail_number"] == "SB-001"
    assert ac["total_flight_hours"] == 1450.5

    # Test query_to_df
    df = test_db.query_to_df("SELECT * FROM aircraft;")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["model_type"] == "Su-30MKI"


def test_foreign_key_enforcement(test_db):
    """Verify that inserting a component referencing a non-existent aircraft raises an IntegrityError."""
    sql_bad_component = """
    INSERT INTO components (component_id, aircraft_id, component_type, serial_number, installed_date, operating_hours, health_index, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute_query(sql_bad_component, (
            "CMP-ENG-999", "NON-EXISTENT-AC", "Turbofan Engine", "SN-9999", "2020-01-01", 100.0, 95.0, "Nominal"
        ))


def test_check_constraint_enforcement(test_db):
    """Verify CHECK constraint failure for invalid operational_status."""
    sql_bad_status = """
    INSERT INTO aircraft (aircraft_id, tail_number, model_type, role, squadron_id, commission_date, operational_status)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute_query(sql_bad_status, (
            "AF-FTR-02", "SB-002", "Rafale", "Omnirole Fighter", "No. 17 Squadron", "2021-01-01", "InvalidStatus"
        ))


def test_cascading_delete(test_db):
    """Verify that deleting an aircraft cascades to components and telemetry."""
    # Insert aircraft
    test_db.execute_query(
        "INSERT INTO aircraft (aircraft_id, tail_number, model_type, role, squadron_id, commission_date) VALUES (?, ?, ?, ?, ?, ?);",
        ("AF-FTR-03", "SB-003", "Tejas Mk1A", "Light Combat Fighter", "No. 45 Squadron", "2022-05-10")
    )
    # Insert component
    test_db.execute_query(
        "INSERT INTO components (component_id, aircraft_id, component_type, serial_number, installed_date) VALUES (?, ?, ?, ?, ?);",
        ("CMP-ENG-003", "AF-FTR-03", "Turbofan Engine", "SN-003-E", "2022-05-10")
    )
    # Insert telemetry
    test_db.execute_query(
        """INSERT INTO sensor_telemetry 
        (aircraft_id, component_id, timestamp, engine_temp_c, vibration_rms, oil_pressure_psi, hydraulic_pressure_bar, operating_cycles)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
        ("AF-FTR-03", "CMP-ENG-003", "2026-10-28T08:00:00", 720.0, 1.2, 60.0, 205.0, 45)
    )

    assert test_db.fetch_one("SELECT COUNT(*) as c FROM components WHERE aircraft_id = 'AF-FTR-03';")["c"] == 1
    assert test_db.fetch_one("SELECT COUNT(*) as c FROM sensor_telemetry WHERE aircraft_id = 'AF-FTR-03';")["c"] == 1

    # Delete parent aircraft
    test_db.execute_query("DELETE FROM aircraft WHERE aircraft_id = 'AF-FTR-03';")

    # Verify children cascaded
    assert test_db.fetch_one("SELECT COUNT(*) as c FROM components WHERE aircraft_id = 'AF-FTR-03';")["c"] == 0
    assert test_db.fetch_one("SELECT COUNT(*) as c FROM sensor_telemetry WHERE aircraft_id = 'AF-FTR-03';")["c"] == 0


def test_transaction_rollback_on_error(test_db):
    """Ensure that an unhandled error inside a transaction rolls back uncommitted changes."""
    # Pre-check
    initial_count = test_db.fetch_one("SELECT COUNT(*) as c FROM aircraft;")["c"]

    with pytest.raises(Exception):
        with test_db.get_connection() as conn:
            conn.execute(
                "INSERT INTO aircraft (aircraft_id, tail_number, model_type, role, squadron_id, commission_date) VALUES (?, ?, ?, ?, ?, ?);",
                ("AF-FTR-04", "SB-004", "Mirage 2000", "Multi-Role", "No. 7 Squadron", "2019-01-01")
            )
            # Intentional syntax/query error
            conn.execute("INSERT INTO non_existent_table VALUES (1, 2, 3);")

    # Verify rolled back
    after_count = test_db.fetch_one("SELECT COUNT(*) as c FROM aircraft;")["c"]
    assert after_count == initial_count


def test_reset_db(test_db):
    """Verify reset_db completely empties tables while keeping schema."""
    test_db.execute_query(
        "INSERT INTO aircraft (aircraft_id, tail_number, model_type, role, squadron_id, commission_date) VALUES (?, ?, ?, ?, ?, ?);",
        ("AF-FTR-05", "SB-005", "C-130J", "Tactical Transport", "No. 77 Squadron", "2020-01-01")
    )
    assert test_db.get_table_counts()["aircraft"] == 1

    test_db.reset_db()
    counts = test_db.get_table_counts()
    assert counts["aircraft"] == 0
    assert test_db.table_exists("aircraft")
