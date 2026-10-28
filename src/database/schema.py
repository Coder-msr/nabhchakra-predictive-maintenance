"""Relational Database Schema (DDL) for NABHCHAKRA.

Defines 8 core relational tables with foreign keys, checks, and performance indexes.
Engineered for SQLite (with strict foreign keys enabled).
"""

CREATE_TABLES_SQL = """
-- Enable Foreign Key constraints
PRAGMA foreign_keys = ON;

-- 1. AIRCRAFT MASTER TABLE
CREATE TABLE IF NOT EXISTS aircraft (
    aircraft_id TEXT PRIMARY KEY,
    tail_number TEXT NOT NULL UNIQUE,
    model_type TEXT NOT NULL,
    role TEXT NOT NULL,
    squadron_id TEXT NOT NULL,
    commission_date TEXT NOT NULL,
    total_flight_hours REAL NOT NULL DEFAULT 0.0 CHECK(total_flight_hours >= 0.0),
    total_flight_cycles INTEGER NOT NULL DEFAULT 0 CHECK(total_flight_cycles >= 0),
    operational_status TEXT NOT NULL DEFAULT 'Available' 
        CHECK(operational_status IN ('Available', 'In Maintenance', 'Grounded', 'Under Inspection')),
    last_inspection_date TEXT,
    next_inspection_due TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. AIRCRAFT COMPONENTS TABLE
CREATE TABLE IF NOT EXISTS components (
    component_id TEXT PRIMARY KEY,
    aircraft_id TEXT NOT NULL,
    component_type TEXT NOT NULL 
        CHECK(component_type IN (
            'Turbofan Engine', 
            'Hydraulic Actuator', 
            'Avionics & Radar System', 
            'Auxiliary Power Unit (APU)', 
            'Landing Gear Assembly'
        )),
    serial_number TEXT NOT NULL UNIQUE,
    installed_date TEXT NOT NULL,
    operating_hours REAL NOT NULL DEFAULT 0.0 CHECK(operating_hours >= 0.0),
    health_index REAL NOT NULL DEFAULT 100.0 CHECK(health_index >= 0.0 AND health_index <= 100.0),
    status TEXT NOT NULL DEFAULT 'Nominal' 
        CHECK(status IN ('Nominal', 'Degraded', 'Critical', 'Under Repair')),
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE
);

-- 3. SENSOR TELEMETRY TABLE (Historical & real-time time-series)
CREATE TABLE IF NOT EXISTS sensor_telemetry (
    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    aircraft_id TEXT NOT NULL,
    component_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    engine_temp_c REAL NOT NULL,
    vibration_rms REAL NOT NULL,
    oil_pressure_psi REAL NOT NULL,
    hydraulic_pressure_bar REAL NOT NULL,
    operating_cycles INTEGER NOT NULL,
    anomaly_score REAL NOT NULL DEFAULT 0.0 CHECK(anomaly_score >= 0.0 AND anomaly_score <= 1.0),
    is_anomaly INTEGER NOT NULL DEFAULT 0 CHECK(is_anomaly IN (0, 1)),
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE,
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE
);

-- 4. FAULT EVENTS TABLE
CREATE TABLE IF NOT EXISTS fault_events (
    fault_id TEXT PRIMARY KEY,
    aircraft_id TEXT NOT NULL,
    component_id TEXT NOT NULL,
    fault_code TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('Minor', 'Moderate', 'Critical')),
    detected_timestamp TEXT NOT NULL,
    description TEXT NOT NULL,
    is_resolved INTEGER NOT NULL DEFAULT 0 CHECK(is_resolved IN (0, 1)),
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE,
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE
);

-- 5. SPARE PARTS INVENTORY TABLE
CREATE TABLE IF NOT EXISTS spare_parts (
    part_id TEXT PRIMARY KEY,
    part_name TEXT NOT NULL,
    compatible_component_type TEXT NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
    reorder_threshold INTEGER NOT NULL DEFAULT 5 CHECK(reorder_threshold >= 0),
    lead_time_days INTEGER NOT NULL DEFAULT 14 CHECK(lead_time_days >= 0),
    unit_cost_inr REAL NOT NULL DEFAULT 0.0 CHECK(unit_cost_inr >= 0.0),
    status TEXT NOT NULL CHECK(status IN ('In Stock', 'Low Stock', 'Out of Stock'))
);

-- 6. MAINTENANCE TEAMS TABLE
CREATE TABLE IF NOT EXISTS maintenance_teams (
    team_id TEXT PRIMARY KEY,
    team_name TEXT NOT NULL,
    specialty TEXT NOT NULL,
    technician_count INTEGER NOT NULL DEFAULT 4 CHECK(technician_count > 0),
    max_concurrent_aircraft INTEGER NOT NULL DEFAULT 2 CHECK(max_concurrent_aircraft > 0),
    current_active_tasks INTEGER NOT NULL DEFAULT 0 CHECK(current_active_tasks >= 0)
);

-- 7. MAINTENANCE RECORDS TABLE
CREATE TABLE IF NOT EXISTS maintenance_records (
    record_id TEXT PRIMARY KEY,
    aircraft_id TEXT NOT NULL,
    component_id TEXT,
    maintenance_type TEXT NOT NULL 
        CHECK(maintenance_type IN ('Scheduled', 'Unscheduled', 'Pre-Flight Inspection', 'Overhaul')),
    start_time TEXT NOT NULL,
    end_time TEXT,
    technician_team_id TEXT,
    action_taken TEXT NOT NULL,
    status TEXT NOT NULL 
        CHECK(status IN ('Completed', 'In Progress', 'Scheduled', 'Deferred')),
    notes TEXT,
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE,
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE SET NULL,
    FOREIGN KEY (technician_team_id) REFERENCES maintenance_teams(team_id) ON DELETE SET NULL
);

-- 8. MAINTENANCE SCHEDULES TABLE
CREATE TABLE IF NOT EXISTS maintenance_schedules (
    schedule_id TEXT PRIMARY KEY,
    aircraft_id TEXT NOT NULL,
    component_id TEXT,
    planned_start TEXT NOT NULL,
    planned_duration_hours REAL NOT NULL DEFAULT 8.0 CHECK(planned_duration_hours > 0.0),
    priority_level TEXT NOT NULL CHECK(priority_level IN ('Critical', 'High', 'Medium', 'Low')),
    required_part_id TEXT,
    assigned_team_id TEXT,
    schedule_status TEXT NOT NULL DEFAULT 'Proposed' 
        CHECK(schedule_status IN ('Proposed', 'Confirmed', 'In Progress', 'Completed', 'Cancelled')),
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE,
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE SET NULL,
    FOREIGN KEY (required_part_id) REFERENCES spare_parts(part_id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_team_id) REFERENCES maintenance_teams(team_id) ON DELETE SET NULL
);

-- INDEXES FOR FAST ANALYTICS & TIME-SERIES QUERIES
CREATE INDEX IF NOT EXISTS idx_telemetry_aircraft_time 
    ON sensor_telemetry (aircraft_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_telemetry_comp_time 
    ON sensor_telemetry (component_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_components_aircraft 
    ON components (aircraft_id);

CREATE INDEX IF NOT EXISTS idx_maintenance_aircraft 
    ON maintenance_records (aircraft_id);

CREATE INDEX IF NOT EXISTS idx_maintenance_status 
    ON maintenance_records (status);

CREATE INDEX IF NOT EXISTS idx_schedules_aircraft 
    ON maintenance_schedules (aircraft_id);

CREATE INDEX IF NOT EXISTS idx_faults_aircraft 
    ON fault_events (aircraft_id);
"""

DROP_TABLES_SQL = """
PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS maintenance_schedules;
DROP TABLE IF EXISTS maintenance_records;
DROP TABLE IF EXISTS maintenance_teams;
DROP TABLE IF EXISTS spare_parts;
DROP TABLE IF EXISTS fault_events;
DROP TABLE IF EXISTS sensor_telemetry;
DROP TABLE IF EXISTS components;
DROP TABLE IF EXISTS aircraft;
PRAGMA foreign_keys = ON;
"""
