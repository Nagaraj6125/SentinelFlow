"""Publisher Agent for SentinelFlow.

The ONLY agent possessing the capability to publish articles.
Must be explicitly authorized by orchestrator approval workflow.
"""

import logging
from typing import Dict, Any, Optional
from sentinelflow.agents.base import BaseAgent
from sentinelflow.db import db

logger = logging.getLogger(__name__)


class PublisherAgent(BaseAgent):
    """Publisher agent with restricted publishing authority."""

    def __init__(self):
        super().__init__(
            name="publisher",
            role="Release Publisher",
            allowed_tools=["publish_article"],
        )

    def publish_draft(
        self,
        title: str,
        content: str,
        run_id: str,
        approval_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish article draft with required approval token."""
        self.initialize_session(
            run_id=run_id,
            goal=f"Publish approved article '{title}'",
        )

        # Gate on explicit approval token
        if not approval_token or not approval_token.startswith("APPRV-"):
            reason = "Publisher rejected action: Missing or invalid management approval token."
            logger.warning(reason)
            db.log_security_event(
                run_id=run_id,
                agent_name=self.name,
                attempted_tool="publish_article",
                parameters={"title": title},
                reason=reason,
                enforcement_action="block",
                blocked=True,
            )
            return {
                "status": "rejected",
                "reason": reason,
                "published": False,
            }

        # Invoke guarded publishing tool
        outcome = self.invoke_tool(
            "publish_article",
            {
                "title": title,
                "content": content,
                "run_id": run_id,
                "approval_token": approval_token,
            },
        )

        return {
            "status": "published" if outcome.allowed else "blocked",
            "published": outcome.allowed,
            "title": title,
            "approval_token": approval_token,
            "result": outcome.result,
        }
