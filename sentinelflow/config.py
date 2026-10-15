"""Configuration management for SentinelFlow.

Safely loads environment variables, guarantees secret privacy,
and validates external service configurations.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load local .env
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


def get_armoriq_api_key() -> str:
    """Return ArmorIQ API Key."""
    return os.getenv("ARMORIQ_API_KEY", "").strip()


def get_llm_api_key() -> str:
    """Return Gemini LLM API Key."""
    return os.getenv("LLM_API_KEY", "").strip()


def get_supabase_url() -> str:
    """Return Supabase project URL."""
    return os.getenv("SUPABASE_URL", "").strip()


def get_supabase_publishable_key() -> str:
    """Return Supabase publishable key."""
    return os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()


def mask_secret(secret: Optional[str]) -> str:
    """Mask sensitive string to prevent secret exposure in logs or UI."""
    if not secret:
        return "[NOT SET]"
    if len(secret) <= 8:
        return "********"
    return f"{secret[:4]}...{secret[-4:]}"


def validate_config() -> Dict[str, Any]:
    """Validate presence and basic health of environment credentials."""
    armoriq_key = get_armoriq_api_key()
    llm_key = get_llm_api_key()
    supabase_url = get_supabase_url()
    supabase_key = get_supabase_publishable_key()

    return {
        "armoriq": {
            "configured": bool(armoriq_key),
            "masked": mask_secret(armoriq_key),
            "valid_prefix": armoriq_key.startswith("ak_"),
        },
        "llm": {
            "configured": bool(llm_key),
            "masked": mask_secret(llm_key),
            "provider": "google-genai (Gemini 2.5 Flash)",
        },
        "supabase": {
            "configured": bool(supabase_url and supabase_key),
            "url_set": bool(supabase_url),
            "key_masked": mask_secret(supabase_key),
        },
    }
