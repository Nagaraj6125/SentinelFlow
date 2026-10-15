"""Writer Agent for SentinelFlow.

Specialized in synthesizing verified research into publication-ready drafts.
Cannot publish articles under any circumstances.
"""

import logging
from typing import Dict, Any
from sentinelflow.agents.base import BaseAgent
from sentinelflow.llm import llm

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Writer agent bounded to draft generation and editing."""

    def __init__(self):
        super().__init__(
            name="writer",
            role="Technical Content Writer",
            allowed_tools=["create_draft"],
        )

    def write_article(
        self,
        topic: str,
        research_findings: str,
        run_id: str,
    ) -> Dict[str, Any]:
        """Compose article draft and save via guarded create_draft MCP tool."""
        self.initialize_session(
            run_id=run_id,
            goal=f"Draft technical security article regarding '{topic}'",
        )

        prompt = (
            f"You are a Senior Technical Writer. Write a 2-paragraph draft article based on these research notes:\n\n"
            f"Topic: {topic}\n"
            f"Notes:\n{research_findings}\n\n"
            "Format the output as:\n"
            "Headline: <Catchy Title>\n\n"
            "<Paragraph 1: Problem statement and threat context>\n\n"
            "<Paragraph 2: Architectural solution and security enforcement>"
        )

        llm_res = llm.generate(
            prompt=prompt,
            system_instruction="You write concise, high-impact enterprise security articles.",
        )
        content_text = llm_res["text"]

        # Parse title or default
        title = f"SentinelFlow Analysis: {topic}"
        for line in content_text.splitlines():
            if line.lower().startswith("headline:"):
                title = line.split(":", 1)[1].strip()
                break

        # Save draft through guarded MCP tool
        draft_outcome = self.invoke_tool(
            "create_draft",
            {
                "title": title,
                "content": content_text,
                "run_id": run_id,
            },
        )

        return {
            "status": "success",
            "title": title,
            "draft_id": draft_outcome.result.get("draft_id") if draft_outcome.result else None,
            "content": content_text,
            "llm_provider": llm_res["provider"],
        }
