"""Thread-safe SQLite Database Manager for NABHCHAKRA.

Provides connection pooling semantics, transactional integrity, foreign-key enforcement,
and convenient helpers for Pandas DataFrames and parameterized queries.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from config.settings import DB_PATH
from src.database.schema import CREATE_TABLES_SQL, DROP_TABLES_SQL


class DatabaseManager:
    """Manages connections, migrations, and transactional queries for NABHCHAKRA SQLite database."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """Context manager providing an auto-committing, foreign-key-enabled SQLite connection."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False
        )
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create all tables and indexes if they do not already exist."""
        with self.get_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)

    def reset_db(self) -> None:
        """Drop all tables and recreate the empty schema (useful for test resets)."""
        with self.get_connection() as conn:
            conn.executescript(DROP_TABLES_SQL)
            conn.executescript(CREATE_TABLES_SQL)

    def execute_query(self, sql: str, params: Union[Tuple, List, Dict] = ()) -> int:
        """Execute an INSERT, UPDATE, or DELETE query and return affected row count."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.rowcount

    def executemany(self, sql: str, params_list: List[Union[Tuple, Dict]]) -> int:
        """Execute a parameterized query across multiple parameter sets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, params_list)
            return cursor.rowcount

    def fetch_all(self, sql: str, params: Union[Tuple, List, Dict] = ()) -> List[Dict[str, Any]]:
        """Fetch all results as a list of dictionaries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def fetch_one(self, sql: str, params: Union[Tuple, List, Dict] = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single result as a dictionary, or None if not found."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def query_to_df(self, sql: str, params: Union[Tuple, List, Dict] = ()) -> pd.DataFrame:
        """Execute a SELECT query and return results directly as a Pandas DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def df_to_table(self, df: pd.DataFrame, table_name: str, if_exists: str = "append") -> int:
        """Insert a Pandas DataFrame directly into a target SQLite table."""
        with self.get_connection() as conn:
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            return len(df)

    def table_exists(self, table_name: str) -> bool:
        """Verify whether a given table exists in the database."""
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
        res = self.fetch_one(sql, (table_name,))
        return res is not None

    def get_table_counts(self) -> Dict[str, int]:
        """Return row counts for all application tables."""
        tables = [
            "aircraft",
            "components",
            "sensor_telemetry",
            "fault_events",
            "spare_parts",
            "maintenance_teams",
            "maintenance_records",
            "maintenance_schedules",
        ]
        counts = {}
        for table in tables:
            if self.table_exists(table):
                res = self.fetch_one(f"SELECT COUNT(*) as cnt FROM {table};")
                counts[table] = res["cnt"] if res else 0
            else:
                counts[table] = 0
        return counts
