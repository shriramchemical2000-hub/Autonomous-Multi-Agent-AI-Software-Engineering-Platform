"""SQLite persistence for projects and their audit events."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def _connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: str | Path) -> None:
    """Create database tables; safe to call repeatedly."""
    with _connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                brief TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'created',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS project_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_project_events_project_id
            ON project_events(project_id);
            """
        )


def create_project(database_path: str | Path, name: str, brief: str = "") -> int:
    """Create a project and its initial event; return its ID."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Project name cannot be empty.")
    with _connect(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO projects (name, brief) VALUES (?, ?)",
            (clean_name, brief.strip()),
        )
        project_id = int(cursor.lastrowid)
        connection.execute(
            "INSERT INTO project_events (project_id, event_type, details) VALUES (?, ?, ?)",
            (project_id, "project_created", "Project workspace created."),
        )
        return project_id


def list_projects(database_path: str | Path) -> list[dict[str, Any]]:
    with _connect(database_path) as connection:
        rows = connection.execute(
            """SELECT id, name, brief, status, created_at, updated_at
               FROM projects ORDER BY updated_at DESC, id DESC"""
        ).fetchall()
        return [dict(row) for row in rows]


def add_project_event(database_path: str | Path, project_id: int, event_type: str, details: str = "") -> int:
    if not event_type.strip():
        raise ValueError("Event type cannot be empty.")
    with _connect(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO project_events (project_id, event_type, details) VALUES (?, ?, ?)",
            (project_id, event_type.strip(), details.strip()),
        )
        connection.execute(
            "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (project_id,),
        )
        return int(cursor.lastrowid)


def list_project_events(database_path: str | Path, project_id: int) -> list[dict[str, Any]]:
    with _connect(database_path) as connection:
        rows = connection.execute(
            """SELECT id, project_id, event_type, details, created_at
               FROM project_events WHERE project_id = ? ORDER BY id DESC"""
        , (project_id,)).fetchall()
        return [dict(row) for row in rows]
