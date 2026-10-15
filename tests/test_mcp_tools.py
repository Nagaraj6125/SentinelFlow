"""Tests for MCP Tools layer."""

from sentinelflow.mcp_tools import (
    search_sources,
    read_source,
    create_draft,
    publish_article,
    execute_tool,
    PUBLISHED_ARTICLES,
    MCP_TOOL_SCHEMAS,
)


def test_mcp_tool_schemas():
    """Verify MCP tools conform to schema definition."""
    names = [t["name"] for t in MCP_TOOL_SCHEMAS]
    assert "search_sources" in names
    assert "read_source" in names
    assert "create_draft" in names
    assert "publish_article" in names


def test_search_sources():
    """Test searching approved knowledge base."""
    results = search_sources("NIST")
    assert len(results) > 0
    assert any("NIST" in r["title"] for r in results)


def test_read_source():
    """Test reading source content."""
    doc = read_source("src_001")
    assert "content" in doc
    assert "NIST" in doc["title"]


def test_create_draft():
    """Test creating an article draft."""
    res = create_draft(
        title="Zero Trust Multi-Agent Systems",
        content="Article content regarding zero trust architecture.",
        run_id="test_run_1",
    )
    assert res["status"] == "draft"
    assert res["title"] == "Zero Trust Multi-Agent Systems"


def test_publish_article():
    """Test executing publishing operation."""
    res = publish_article(
        title="Official Security Advisory",
        content="Advisory details...",
        run_id="test_run_2",
        approval_token="APPRV-12345678",
    )
    assert res["status"] == "published"
    assert len(PUBLISHED_ARTICLES) == 1
    assert PUBLISHED_ARTICLES[0]["title"] == "Official Security Advisory"


def test_mcp_server_json_rpc():
    """Verify standard MCP server handles initialize, tools/list, and tools/call."""
    from starlette.testclient import TestClient
    from sentinelflow.mcp_server import app

    client = TestClient(app)

    # 1. Initialize
    init_res = client.post("/sse", json={"jsonrpc": "2.0", "method": "initialize", "id": 1})
    assert init_res.status_code == 200
    assert init_res.json()["result"]["serverInfo"]["name"] == "SentinelFlow-MCP"

    # 2. Tools list
    tools_res = client.post("/sse", json={"jsonrpc": "2.0", "method": "tools/list", "id": 2})
    assert tools_res.status_code == 200
    tools = [t["name"] for t in tools_res.json()["result"]["tools"]]
    assert "search_sources" in tools
    assert "publish_article" in tools

    # 3. Tool call
    call_res = client.post("/sse", json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "search_sources", "arguments": {"query": "NIST"}},
        "id": 3,
    })
    assert call_res.status_code == 200
    content = call_res.json()["result"]["content"]
    assert len(content) > 0
    assert "NIST" in content[0]["text"]

