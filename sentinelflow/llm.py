"""LLM Integration Layer for SentinelFlow.

Uses configured Gemini provider (gemini-2.5-flash) for genuine model reasoning.
If unavailable or unconfigured, falls back to an explicitly labeled DEVELOPMENT MODE.
"""

import logging
from typing import Optional, Dict, Any
from sentinelflow.config import get_llm_api_key

logger = logging.getLogger(__name__)


class LLMClient:
    """Manages LLM generation with genuine provider integration and labeled dev fallback."""

    def __init__(self):
        self.api_key = get_llm_api_key()
        self.provider_client = None
        self.is_live_provider = False
        self.model_name = "gemini-2.5-flash"
        self._init_provider()

    def _init_provider(self):
        """Initialize Google GenAI client if key is configured."""
        if not self.api_key:
            logger.warning("LLM_API_KEY is not set. Operating in [DEVELOPMENT MODE].")
            return

        try:
            from google import genai
            self.provider_client = genai.Client(api_key=self.api_key)
            self.is_live_provider = True
            logger.info(f"Connected to live Gemini provider ({self.model_name}).")
        except Exception as e:
            logger.warning(f"Could not initialize live GenAI client: {e}. Falling back to dev mode.")
            self.is_live_provider = False

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Generate response from Gemini model or labeled development fallback."""
        if self.is_live_provider and self.provider_client:
            try:
                config: Dict[str, Any] = {}
                if system_instruction:
                    config["system_instruction"] = system_instruction

                response = self.provider_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config if config else None,
                )
                text = response.text or ""
                return {
                    "text": text,
                    "provider": "google-genai",
                    "model": self.model_name,
                    "is_dev_mode": False,
                }
            except Exception as e:
                logger.error(f"Live Gemini invocation failed: {e}. Using labeled dev fallback.")

        # Labeled development fallback (Explicitly labeled, never pretending to be live)
        dev_note = "[DEVELOPMENT MODE - SYNTHETIC AGENT REASONING]\n"
        fallback_text = f"{dev_note}Processed input: {prompt[:120]}...\nSynthesized least-privilege analysis complete."
        return {
            "text": fallback_text,
            "provider": "development_mode",
            "model": "dev-synthetic-v1",
            "is_dev_mode": True,
        }


# Singleton LLM instance
llm = LLMClient()
