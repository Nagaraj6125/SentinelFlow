"""Database and audit trail layer for SentinelFlow.

Provides Supabase PostgREST client operations with Row Level Security (RLS)
readiness, complemented by an in-memory/JSON local state cache to guarantee
100% operational continuity even before remote SQL migrations are executed.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from sentinelflow.config import get_supabase_url, get_supabase_publishable_key

logger = logging.getLogger(__name__)

# Local persistence directory
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
LOCAL_STORE_FILE = DATA_DIR / "sentinelflow_store.json"


class SentinelDB:
    """Manages workflow persistence, security audit logs, and agent history."""
    LOCAL_STORE_FILE = LOCAL_STORE_FILE

    def __init__(self):
        self.supabase_client = None
        self._supabase_available = False
        self._local_store: Dict[str, List[Dict[str, Any]]] = {
            "workflow_runs": [],
            "articles_draft": [],
            "agent_events": [],
            "security_events": [],
            "audit_records": [],
        }
        self._load_local_store()
        self._init_supabase()

    def _init_supabase(self):
        """Initialize Supabase client if configured."""
        url = get_supabase_url()
        key = get_supabase_publishable_key()
        if url and key:
            try:
                from supabase import create_client
                self.supabase_client = create_client(url, key)
                self._supabase_available = True
                logger.info("Supabase client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase client: {e}")
                self._supabase_available = False

    def _load_local_store(self):
        """Load local store from JSON file if present."""
        if LOCAL_STORE_FILE.exists():
            try:
                with open(LOCAL_STORE_FILE, "r", encoding="utf-8") as f:
                    self._local_store = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load local store: {e}")

    def _save_local_store(self):
        """Save local store to disk."""
        try:
            with open(LOCAL_STORE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._local_store, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not save local store: {e}")

    def is_supabase_live(self) -> bool:
        """Check if Supabase remote table is reachable."""
        if not self._supabase_available or not self.supabase_client:
            return False
        try:
            res = self.supabase_client.table("workflow_runs").select("id").limit(1).execute()
            return True
        except Exception:
            return False

    # 1. Workflow Runs
    def create_workflow_run(self, prompt: str) -> str:
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": run_id,
            "prompt": prompt,
            "status": "running",
            "created_at": now,
            "updated_at": now,
        }
        self._local_store["workflow_runs"].insert(0, record)
        self._save_local_store()

        if self._supabase_available:
            try:
                self.supabase_client.table("workflow_runs").insert(record).execute()
            except Exception as e:
                logger.info(f"Supabase write skipped (migration pending): {e}")

        return run_id

    def update_workflow_run(self, run_id: str, status: str):
        now = datetime.now(timezone.utc).isoformat()
        for r in self._local_store["workflow_runs"]:
            if r["id"] == run_id:
                r["status"] = status
                r["updated_at"] = now
                break
        self._save_local_store()

        if self._supabase_available:
            try:
                self.supabase_client.table("workflow_runs").update(
                    {"status": status, "updated_at": now}
                ).eq("id", run_id).execute()
            except Exception as e:
                logger.info(f"Supabase update skipped: {e}")

    def get_workflow_runs(self) -> List[Dict[str, Any]]:
        if self._supabase_available:
            try:
                res = self.supabase_client.table("workflow_runs").select("*").order("created_at", desc=True).execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        return self._local_store["workflow_runs"]

    # 2. Articles Draft
    def create_draft(self, run_id: str, title: str, content: str, author_agent: str = "writer") -> str:
        draft_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": draft_id,
            "run_id": run_id,
            "title": title,
            "content": content,
            "status": "draft",
            "author_agent": author_agent,
            "created_at": now,
            "updated_at": now,
        }
        self._local_store["articles_draft"].insert(0, record)
        self._save_local_store()

        if self._supabase_available:
            try:
                self.supabase_client.table("articles_draft").insert(record).execute()
            except Exception as e:
                logger.info(f"Supabase draft insert skipped: {e}")

        return draft_id

    def update_draft_status(self, draft_id: str, status: str):
        now = datetime.now(timezone.utc).isoformat()
        for d in self._local_store["articles_draft"]:
            if d["id"] == draft_id:
                d["status"] = status
                d["updated_at"] = now
                break
        self._save_local_store()

        if self._supabase_available:
            try:
                self.supabase_client.table("articles_draft").update(
                    {"status": status, "updated_at": now}
                ).eq("id", draft_id).execute()
            except Exception as e:
                logger.info(f"Supabase draft update skipped: {e}")

    def get_drafts(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._supabase_available:
            try:
                query = self.supabase_client.table("articles_draft").select("*").order("created_at", desc=True)
                if run_id:
                    query = query.eq("run_id", run_id)
                res = query.execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        drafts = self._local_store["articles_draft"]
        if run_id:
            return [d for d in drafts if d.get("run_id") == run_id]
        return drafts

    # 3. Agent Events
    def log_agent_event(
        self,
        run_id: str,
        agent_name: str,
        action: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        status: str = "success",
    ) -> str:
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": event_id,
            "run_id": run_id,
            "agent_name": agent_name,
            "action": action,
            "parameters": parameters,
            "result": result,
            "status": status,
            "created_at": now,
        }
        self._local_store["agent_events"].insert(0, record)
        self._save_local_store()

        if self._supabase_available:
            try:
                self.supabase_client.table("agent_events").insert(record).execute()
            except Exception as e:
                logger.info(f"Supabase agent_events skipped: {e}")

        return event_id

    def get_agent_events(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._supabase_available:
            try:
                query = self.supabase_client.table("agent_events").select("*").order("created_at", desc=True)
                if run_id:
                    query = query.eq("run_id", run_id)
                res = query.execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        events = self._local_store["agent_events"]
        if run_id:
            return [e for e in events if e.get("run_id") == run_id]
        return events

    # 4. Security Events (ArmorIQ Enforced Blocks)
    def log_security_event(
        self,
        run_id: str,
        agent_name: str,
        attempted_tool: str,
        parameters: Dict[str, Any],
        reason: str,
        enforcement_action: str = "block",
        blocked: bool = True,
    ) -> str:
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": event_id,
            "run_id": run_id,
            "agent_name": agent_name,
            "attempted_tool": attempted_tool,
            "parameters": parameters,
            "reason": reason,
            "enforcement_action": enforcement_action,
            "blocked": blocked,
            "created_at": now,
        }
        self._local_store["security_events"].insert(0, record)
        self._save_local_store()

        if self._supabase_available:
            try:
                self.supabase_client.table("security_events").insert(record).execute()
            except Exception as e:
                logger.info(f"Supabase security_events skipped: {e}")

        return event_id

    def get_security_events(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._supabase_available:
            try:
                query = self.supabase_client.table("security_events").select("*").order("created_at", desc=True)
                if run_id:
                    query = query.eq("run_id", run_id)
                res = query.execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        events = self._local_store["security_events"]
        if run_id:
            return [e for e in events if e.get("run_id") == run_id]
        return events

    # 5. Cryptographic Audit Records
    def log_audit_record(
        self,
        run_id: str,
        token_id: Optional[str],
        plan_hash: Optional[str],
        delegation_scope: List[str],
        source_agent: str,
        target_agent: Optional[str] = None,
        verification_status: str = "valid",
    ) -> str:
        record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": record_id,
            "run_id": run_id,
            "token_id": token_id or "local_token",
            "plan_hash": plan_hash or "n/a",
            "delegation_scope": delegation_scope,
            "source_agent": source_agent,
            "target_agent": target_agent,
            "verification_status": verification_status,
            "created_at": now,
        }
        self._local_store["audit_records"].insert(0, record)
        self._save_local_store()

        if self._supabase_available:
            try:
                self.supabase_client.table("audit_records").insert(record).execute()
            except Exception as e:
                logger.info(f"Supabase audit_records skipped: {e}")

        return record_id

    def get_audit_records(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._supabase_available:
            try:
                query = self.supabase_client.table("audit_records").select("*").order("created_at", desc=True)
                if run_id:
                    query = query.eq("run_id", run_id)
                res = query.execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        records = self._local_store["audit_records"]
        if run_id:
            return [r for r in records if r.get("run_id") == run_id]
        return records

    def sync_local_to_supabase(self) -> Dict[str, int]:
        """Synchronize all existing records from local store to remote Supabase tables."""
        synced_counts = {
            "workflow_runs": 0,
            "articles_draft": 0,
            "agent_events": 0,
            "security_events": 0,
            "audit_records": 0,
        }
        if not self._supabase_available or not self.supabase_client:
            return synced_counts

        for table_name in synced_counts.keys():
            records = self._local_store.get(table_name, [])
            for rec in records:
                try:
                    self.supabase_client.table(table_name).upsert(rec).execute()
                    synced_counts[table_name] += 1
                except Exception as e:
                    logger.debug(f"Sync skipped for {table_name}: {e}")
        return synced_counts


# Global database singleton
db = SentinelDB()

