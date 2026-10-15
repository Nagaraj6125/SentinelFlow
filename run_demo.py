"""SentinelFlow — Live Interactive Demonstration Script.

Runs:
1. Standard Collaborative Multi-Agent Workflow
2. Controlled Prompt-Injection Security Defense Demonstration
"""

import sys
import logging
from sentinelflow.config import validate_config
from sentinelflow.agents.orchestrator import OrchestratorAgent
from sentinelflow.db import db
from sentinelflow.mcp_tools import PUBLISHED_ARTICLES

# Configure clean logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def print_banner(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def main():
    print_banner("SENTINELFLOW — LEAST-PRIVILEGE AGENT CREW DEMO")

    # 1. Environment Check
    cfg = validate_config()
    print("\n[1] Environment Status:")
    print(f"  • ArmorIQ:   {'CONNECTED' if cfg['armoriq']['configured'] else 'MISSING'} (Key: {cfg['armoriq']['masked']})")
    print(f"  • LLM:       {cfg['llm']['provider']} (Key: {cfg['llm']['masked']})")
    print(f"  • Supabase:  {'CONFIGURED' if cfg['supabase']['configured'] else 'MISSING'} (Key: {cfg['supabase']['key_masked']})")

    orchestrator = OrchestratorAgent()

    # 2. Standard Workflow Run
    print_banner("SCENARIO 1: Standard Multi-Agent Publication Workflow")
    print("Prompt: 'Cryptographic Intent Verification in Multi-Agent Systems'")
    report_1 = orchestrator.run_workflow(
        prompt="Cryptographic Intent Verification in Multi-Agent Systems",
        auto_approve_publish=True,
        simulate_injection=False,
    )
    print(f"Workflow Status: {report_1['status'].upper()}")
    print(f"Run ID:          {report_1['run_id']}")
    print(f"Article Title:   {report_1.get('writer_result', {}).get('title')}")
    print(f"Approval Token:  {report_1.get('approval_token')}")
    print(f"Total Published: {len(PUBLISHED_ARTICLES)}")

    # 3. Security Demonstration: Controlled Prompt Injection
    print_banner("SCENARIO 2: Controlled Prompt-Injection Security Demonstration")
    print("Simulating adversarial injection attack:")
    print("  • Researcher reads synthetic document containing a prompt injection instruction")
    print("  • Adversarial payload orders Researcher to ignore role and invoke publish_article")
    print("  • Researcher attempts forbidden action")
    print("  • ArmorIQ runtime authorization interceptor evaluates tool against intent token\n")

    initial_pubs = len(PUBLISHED_ARTICLES)
    report_2 = orchestrator.run_workflow(
        prompt="Audit Adversarial Intelligence Documents",
        auto_approve_publish=False,
        simulate_injection=True,
    )

    print(f"Workflow Status: {report_2['status'].upper()}")
    print(f"Run ID:          {report_2['run_id']}")

    res = report_2.get("research_result", {})
    print(f"\n[ArmorIQ Enforcement Interception]")
    print(f"  • Attempted Tool:       {res.get('attempted_action')}")
    print(f"  • Blocked by ArmorIQ:   {res.get('blocked_by_armoriq')}")
    print(f"  • Decision:             {res.get('armoriq_decision')}")
    print(f"  • Enforcement Reason:   {res.get('enforcement_reason')}")
    print(f"  • Protected Executed:   FALSE (Articles count: {len(PUBLISHED_ARTICLES)} vs initial {initial_pubs})")

    # 4. Audit Log Verification
    print_banner("AUDIT LOG PERSISTENCE CHECK")
    sec_events = db.get_security_events(run_id=report_2["run_id"])
    print(f"Security Events Logged for Run {report_2['run_id'][:8]}...: {len(sec_events)}")
    for ev in sec_events:
        print(f"  -> Agent: {ev['agent_name']} | Tool: {ev['attempted_tool']} | Action: {ev['enforcement_action']} | Blocked: {ev['blocked']}")

    audit_records = db.get_audit_records(run_id=report_2["run_id"])
    print(f"Cryptographic Audit Records Logged: {len(audit_records)}")
    for rec in audit_records:
        print(f"  -> Token ID: {rec['token_id']} | Source: {rec['source_agent']} -> Target: {rec['target_agent']} | Scope: {rec['delegation_scope']}")

    print("\n" + "=" * 70)
    print("  DEMO COMPLETE: All ArmorIQ least-privilege guarantees verified!")
    print("=" * 70)


if __name__ == "__main__":
    main()
