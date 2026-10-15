"""Tests for ArmorIQ runtime authorization and enforcement."""

from sentinelflow.armoriq_guard import guard
from sentinelflow.mcp_tools import PUBLISHED_ARTICLES
from sentinelflow.db import db


def test_researcher_allowed_tool():
    """Researcher can invoke search_sources within its delegated scope."""
    ctx = guard.create_agent_session(
        agent_name="researcher",
        allowed_tools=["search_sources", "read_source"],
        goal="Search security references",
        run_id="test_armoriq_allow",
    )
    outcome = guard.execute_guarded_tool(
        ctx=ctx,
        tool_name="search_sources",
        tool_args={"query": "security"},
    )
    assert outcome.allowed is True
    assert outcome.blocked is False
    assert outcome.action == "allow"
    assert isinstance(outcome.result, list)


def test_researcher_unauthorized_publishing_blocked():
    """Researcher attempting publish_article MUST be blocked by ArmorIQ."""
    initial_published_count = len(PUBLISHED_ARTICLES)
    ctx = guard.create_agent_session(
        agent_name="researcher",
        allowed_tools=["search_sources", "read_source"],
        goal="Attempt unauthorized publishing",
        run_id="test_armoriq_block",
    )
    outcome = guard.execute_guarded_tool(
        ctx=ctx,
        tool_name="publish_article",
        tool_args={"title": "Unauthorized Leak", "content": "Sensitive data"},
    )

    # 1. Enforcement verification
    assert outcome.allowed is False
    assert outcome.blocked is True
    assert outcome.action == "block"
    assert "publish_article" in outcome.reason or "delegation" in outcome.reason.lower() or "not in" in outcome.reason.lower() or "not declared" in outcome.reason.lower()

    # 2. Protected action did NOT execute
    assert len(PUBLISHED_ARTICLES) == initial_published_count

    # 3. Security event recorded in audit database
    sec_events = db.get_security_events(run_id="test_armoriq_block")
    assert len(sec_events) > 0
    assert sec_events[0]["attempted_tool"] == "publish_article"
    assert sec_events[0]["blocked"] is True


def test_writer_unauthorized_publishing_blocked():
    """Writer attempting publish_article MUST also be blocked by ArmorIQ."""
    initial_published_count = len(PUBLISHED_ARTICLES)
    ctx = guard.create_agent_session(
        agent_name="writer",
        allowed_tools=["create_draft"],
        goal="Draft article",
        run_id="test_writer_block",
    )
    outcome = guard.execute_guarded_tool(
        ctx=ctx,
        tool_name="publish_article",
        tool_args={"title": "Writer Direct Release", "content": "Unapproved"},
    )

    assert outcome.allowed is False
    assert outcome.blocked is True
    assert len(PUBLISHED_ARTICLES) == initial_published_count
