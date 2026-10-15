"""MCP Server implementation for SentinelFlow.

Exposes search, read, draft, and publish operations over standard JSON-RPC 2.0 / MCP HTTP endpoint,
enabling ArmorIQ CLI discovery and standard MCP client connections.
"""

import json
import logging
from typing import Dict, Any
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from sentinelflow.mcp_tools import MCP_TOOL_SCHEMAS, execute_tool

logger = logging.getLogger(__name__)


async def handle_mcp_rpc(request: Request) -> JSONResponse:
    """Handle incoming JSON-RPC 2.0 MCP requests."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
            status_code=400,
        )

    method = body.get("method")
    req_id = body.get("id")
    params = body.get("params", {})

    # 1. Initialize
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "SentinelFlow-MCP",
                    "version": "1.0.0",
                },
            },
            "id": req_id,
        })

    # 2. Tools List
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {
                "tools": MCP_TOOL_SCHEMAS,
            },
            "id": req_id,
        })

    # 3. Tool Invocation
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            res = execute_tool(tool_name, arguments)
            return JSONResponse({
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(res, default=str)},
                    ],
                },
                "id": req_id,
            })
        except Exception as e:
            return JSONResponse({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": req_id,
            })

    # Unknown method
    return JSONResponse(
        {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method '{method}' not found"}, "id": req_id},
        status_code=404,
    )


routes = [
    Route("/", handle_mcp_rpc, methods=["POST", "GET"]),
    Route("/sse", handle_mcp_rpc, methods=["POST", "GET"]),
    Route("/mcp", handle_mcp_rpc, methods=["POST", "GET"]),
]

app = Starlette(debug=False, routes=routes)


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Launch the MCP server with Uvicorn."""
    import uvicorn
    print(f"Starting SentinelFlow MCP Server on http://{host}:{port}/sse ...")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_server()
