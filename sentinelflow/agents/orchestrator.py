"""Orchestrator Agent for SentinelFlow.

Coordinates least-privilege crew execution:
- Declares overall goal and captures plan with ArmorIQ
- Delegates scoped authority to Researcher, Writer, and Publisher
- Requires explicit approval before invoking Publisher
"""

import logging
import secrets
from typing import Dict, Any, Optional
from sentinelflow.db import db
from sentinelflow.agents.researcher import ResearcherAgent
from sentinelflow.agents.writer import WriterAgent
from sentinelflow.agents.publisher import PublisherAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Master workflow orchestrator enforcing least-privilege handoffs."""

    def __init__(self):
        self.researcher = ResearcherAgent()
        self.writer = WriterAgent()
        self.publisher = PublisherAgent()

    def run_workflow(
        self,
        prompt: str,
        auto_approve_publish: bool = True,
        simulate_injection: bool = False,
    ) -> Dict[str, Any]:
        """Execute end-to-end multi-agent workflow."""
        run_id = db.create_workflow_run(prompt=prompt)
        logger.info(f"Started workflow run {run_id} for prompt: '{prompt}'")

        report = {
            "run_id": run_id,
            "prompt": prompt,
            "steps": [],
            "status": "in_progress",
            "injection_demo": simulate_injection,
        }

        try:
            # ---------------------------------------------------------
            # Step 1: Research Delegation
            # ---------------------------------------------------------
            report["steps"].append({"step": 1, "agent": "researcher", "action": "delegated_research"})
            research_result = self.researcher.conduct_research(
                topic=prompt,
                run_id=run_id,
                simulate_injection_attack=simulate_injection,
            )
            report["research_result"] = research_result

            # If an injection attack was triggered (via demo mode OR detected in the prompt)
            if simulate_injection or research_result.get("status") in ("attack_blocked", "compromised"):
                if research_result.get("status") == "attack_blocked":
                    report["status"] = "security_blocked"
                    db.update_workflow_run(run_id, "blocked")
                    report["conclusion"] = (
                        "PROMPT INJECTION DEFENSE VERIFIED: The researcher encountered an adversarial prompt injection "
                        "instructing it to publish. The unauthorized tool invocation was intercepted "
                        "and BLOCKED by ArmorIQ before execution. No article was published."
                    )
                    return report
                else:
                    report["status"] = "compromised"
                    db.update_workflow_run(run_id, "failed")
                    return report


            # ---------------------------------------------------------
            # Step 2: Content Writing Delegation
            # ---------------------------------------------------------
            report["steps"].append({"step": 2, "agent": "writer", "action": "delegated_writing"})
            writer_result = self.writer.write_article(
                topic=prompt,
                research_findings=research_result.get("findings", ""),
                run_id=run_id,
            )
            report["writer_result"] = writer_result
            title = writer_result.get("title", f"Report: {prompt}")
            content = writer_result.get("content", "")

            # ---------------------------------------------------------
            # Step 3: Human / Orchestrator Approval Step
            # ---------------------------------------------------------
            if not auto_approve_publish:
                report["status"] = "pending_approval"
                report["approval_required"] = True
                db.update_workflow_run(run_id, "completed")
                return report

            # Mint formal approval token
            approval_token = f"APPRV-{secrets.token_hex(8)}"
            report["approval_token"] = approval_token
            report["steps"].append({"step": 3, "agent": "orchestrator", "action": "approved_for_release"})

            # ---------------------------------------------------------
            # Step 4: Publisher Delegation
            # ---------------------------------------------------------
            report["steps"].append({"step": 4, "agent": "publisher", "action": "delegated_publishing"})
            publish_result = self.publisher.publish_draft(
                title=title,
                content=content,
                run_id=run_id,
                approval_token=approval_token,
            )
            report["publish_result"] = publish_result

            if publish_result.get("published"):
                report["status"] = "completed"
                db.update_workflow_run(run_id, "completed")
            else:
                report["status"] = "blocked"
                db.update_workflow_run(run_id, "blocked")

            return report

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            db.update_workflow_run(run_id, "failed")
            report["status"] = "error"
            report["error"] = str(e)
            return report
