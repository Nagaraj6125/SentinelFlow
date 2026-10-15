"""Base Agent class for SentinelFlow crew."""

import logging
from typing import Dict, Any, List, Optional
from sentinelflow.armoriq_guard import guard, AgentSessionContext, EnforcementOutcome

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all crew members, ensuring ArmorIQ protection on tool calls."""

    def __init__(self, name: str, role: str, allowed_tools: List[str]):
        self.name = name
        self.role = role
        self.allowed_tools = list(allowed_tools)
        self.session_context: Optional[AgentSessionContext] = None

    def initialize_session(self, run_id: str, goal: str) -> AgentSessionContext:
        """Bind an ArmorIQ session with declared tools and intent token."""
        self.session_context = guard.create_agent_session(
            agent_name=self.name,
            allowed_tools=self.allowed_tools,
            goal=goal,
            run_id=run_id,
        )
        return self.session_context

    def invoke_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> EnforcementOutcome:
        """Invoke tool through ArmorIQ guard."""
        if not self.session_context:
            raise RuntimeError(f"Agent '{self.name}' invoked '{tool_name}' before session initialization.")
        return guard.execute_guarded_tool(
            ctx=self.session_context,
            tool_name=tool_name,
            tool_args=tool_args,
        )
