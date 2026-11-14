import pytest

from forgeai.database import (
    add_project_event,
    create_project,
    initialize_database,
    list_project_events,
    list_projects,
)


def test_database_initialization_is_idempotent(tmp_path):
    db = tmp_path / "forgeai.db"
    initialize_database(db)
    initialize_database(db)
    assert list_projects(db) == []


def test_create_and_list_project(tmp_path):
    db = tmp_path / "forgeai.db"
    initialize_database(db)
    project_id = create_project(db, "Clinic Booking", "Appointment scheduling platform")
    projects = list_projects(db)
    assert len(projects) == 1
    assert projects[0]["id"] == project_id
    assert projects[0]["name"] == "Clinic Booking"
    assert projects[0]["brief"] == "Appointment scheduling platform"


def test_project_name_must_not_be_empty(tmp_path):
    db = tmp_path / "forgeai.db"
    initialize_database(db)
    with pytest.raises(ValueError, match="Project name"):
        create_project(db, "   ")


def test_project_creation_and_events_are_recorded(tmp_path):
    db = tmp_path / "forgeai.db"
    initialize_database(db)
    project_id = create_project(db, "Inventory Platform")
    add_project_event(db, project_id, "requirements_started", "Initial discovery")
    events = list_project_events(db, project_id)
    assert [event["event_type"] for event in events] == ["requirements_started", "project_created"]
