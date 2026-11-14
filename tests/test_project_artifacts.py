import pytest

from forgeai.database import (
    create_project,
    get_latest_project_artifact,
    initialize_database,
    list_project_events,
    review_project_artifact,
    save_project_artifact,
)


def test_artifact_versions_are_persisted_and_latest_is_returned(tmp_path):
    db = tmp_path / "forgeai.db"
    initialize_database(db)
    project_id = create_project(db, "ForgeAI Demo", "Build a demo application.")

    first_id = save_project_artifact(db, project_id, "requirements", {"product_name": "Demo v1"})
    second_id = save_project_artifact(db, project_id, "requirements", {"product_name": "Demo v2"})

    latest = get_latest_project_artifact(db, project_id, "requirements")
    assert latest is not None
    assert latest["id"] == second_id
    assert latest["version"] == 2
    assert latest["content"] == {"product_name": "Demo v2"}
    assert latest["review_status"] == "pending"
    assert first_id != second_id


def test_human_review_decision_and_notes_are_persisted(tmp_path):
    db = tmp_path / "forgeai.db"
    initialize_database(db)
    project_id = create_project(db, "Review Demo", "A test brief.")
    artifact_id = save_project_artifact(db, project_id, "requirements", {"product_name": "Review Demo"})

    review_project_artifact(db, artifact_id, "changes_requested", "Clarify the user roles.")
    latest = get_latest_project_artifact(db, project_id, "requirements")

    assert latest is not None
    assert latest["review_status"] == "changes_requested"
    assert latest["review_notes"] == "Clarify the user roles."
    events = list_project_events(db, project_id)
    assert any(event["event_type"] == "human_review" for event in events)


def test_review_rejects_unsupported_decision(tmp_path):
    db = tmp_path / "forgeai.db"
    initialize_database(db)
    project_id = create_project(db, "Decision Demo")
    artifact_id = save_project_artifact(db, project_id, "requirements", {"product_name": "Decision Demo"})

    with pytest.raises(ValueError, match="Decision must"):
        review_project_artifact(db, artifact_id, "maybe")


def test_artifact_requires_existing_project(tmp_path):
    db = tmp_path / "forgeai.db"
    initialize_database(db)
    with pytest.raises(ValueError, match="does not exist"):
        save_project_artifact(db, 999, "requirements", {"product_name": "Missing"})
