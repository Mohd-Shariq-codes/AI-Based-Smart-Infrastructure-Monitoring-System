
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "infrastructure.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:

        # Inspection records table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id TEXT UNIQUE,
                building_name TEXT NOT NULL,
                inspection_date TEXT NOT NULL,
                inspector_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Registered infrastructure table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS infrastructures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                infrastructure_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Healthy',
                condition TEXT NOT NULL DEFAULT 'Good',
                last_inspection TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # AI image analysis history table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS ai_analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT UNIQUE NOT NULL,
                original_image TEXT NOT NULL,
                annotated_image TEXT NOT NULL,
                crack_count INTEGER NOT NULL DEFAULT 0,
                detections_json TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
    print(f"Database location: {DATABASE_PATH}")

    with get_connection() as connection:
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """).fetchall()

        print("Available tables:")
        for table in tables:
            print(f"- {table['name']}")
