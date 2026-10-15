"""Tests for database and audit trail persistence."""

from sentinelflow.db import db


def test_workflow_runs_crud():
    """Verify workflow runs creation and status update."""
    run_id = db.create_workflow_run("Test workflow run")
    assert run_id is not None

    runs = db.get_workflow_runs()
    assert any(r["id"] == run_id for r in runs)

    db.update_workflow_run(run_id, "completed")
    updated_runs = db.get_workflow_runs()
    target = next(r for r in updated_runs if r["id"] == run_id)
    assert target["status"] == "completed"


def test_draft_crud():
    """Verify draft creation and status updates."""
    run_id = db.create_workflow_run("Draft test run")
    draft_id = db.create_draft(
        run_id=run_id,
        title="Test Draft Title",
        content="Test content...",
        author_agent="writer",
    )
    assert draft_id is not None

    drafts = db.get_drafts(run_id=run_id)
    assert len(drafts) >= 1
    assert drafts[0]["title"] == "Test Draft Title"
    assert drafts[0]["status"] == "draft"

    db.update_draft_status(draft_id, "published")
    updated_drafts = db.get_drafts(run_id=run_id)
    assert updated_drafts[0]["status"] == "published"


def test_security_events_and_audit():
    """Verify security event logging and audit trails."""
    run_id = db.create_workflow_run("Security audit test")

    sec_id = db.log_security_event(
        run_id=run_id,
        agent_name="researcher",
        attempted_tool="publish_article",
        parameters={"fake": "arg"},
        reason="ArmorIQ scope block",
        enforcement_action="block",
        blocked=True,
    )
    assert sec_id is not None

    sec_events = db.get_security_events(run_id=run_id)
    assert len(sec_events) == 1
    assert sec_events[0]["blocked"] is True

    audit_id = db.log_audit_record(
        run_id=run_id,
        token_id="token_abc",
        plan_hash="hash_123",
        delegation_scope=["search_sources", "read_source"],
        source_agent="orchestrator",
        target_agent="researcher",
        verification_status="valid",
    )
    assert audit_id is not None

    audit_records = db.get_audit_records(run_id=run_id)
    assert len(audit_records) == 1
    assert audit_records[0]["token_id"] == "token_abc"
