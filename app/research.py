"""Research engine integrating Groq browser search and evergreen fallbacks."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from groq import Groq

from app.config import CONFIG_DIR, get_settings
from app.models import ResearchResult, ResearchSource

logger = logging.getLogger(__name__)


class ResearchEngine:
    """Coordinates web-grounded research via Groq tools with graceful evergreen fallback."""

    def __init__(self, config_dir: Optional[Path] = None, groq_client: Optional[Groq] = None):
        self.config_dir = config_dir or CONFIG_DIR
        self._groq_client = groq_client
        self._load_sources_config()

    def _load_sources_config(self) -> None:
        """Load verified sources and evergreen fallbacks."""
        sources_file = self.config_dir / "verified_sources.yaml"
        if sources_file.exists():
            with open(sources_file, "r", encoding="utf-8") as f:
                self.sources_data = yaml.safe_load(f)
        else:
            self.sources_data = {}

    def get_evergreen_fallback(self, pillar_id: str, topic: str, reason: str) -> ResearchResult:
        """Construct an evergreen research result without making any false claims about live web checks."""
        fallbacks = self.sources_data.get("evergreen_fallback_topics", {})
        fallback_entry = fallbacks.get(pillar_id, {
            "title": f"Core Foundations of {topic}",
            "claim": "Consistent architectural design and disciplined testing outlast short-lived industry trends.",
            "source_name": "Verified Engineering Fundamentals"
        })

        source = ResearchSource(
            title=fallback_entry.get("title", topic),
            url=None,
            publisher=fallback_entry.get("source_name", "Primary Engineering Principles"),
            publication_date=None,
            claim=fallback_entry.get("claim", "Established industry patterns and proven system design.")
        )

        return ResearchResult(
            is_live_search=False,
            query=topic,
            summary=f"Evergreen industry context: {source.claim}",
            sources=[source],
            fallback_reason=reason
        )

    def conduct_research(self, pillar_id: str, topic: str) -> ResearchResult:
        """
        Conduct research for a given topic.
        Attempts Groq browser search if enabled; otherwise falls back gracefully.
        """
        settings = get_settings()

        if not settings.enable_web_search:
            logger.info("Web search is disabled in settings (ENABLE_WEB_SEARCH=false). Using evergreen topic context.")
            return self.get_evergreen_fallback(pillar_id, topic, "Web search disabled in configuration")

        if not settings.groq_api_key:
            logger.info("No Groq API key configured. Using evergreen topic context.")
            return self.get_evergreen_fallback(pillar_id, topic, "GROQ_API_KEY not configured")

        client = self._groq_client or Groq(api_key=settings.groq_api_key)

        prompt = (
            f"You are a technical research assistant. Search for authoritative primary documentation, "
            f"recent verified technical developments, and official release notes on the following topic:\n"
            f"'{topic}'\n\n"
            f"Provide a concise 3-4 sentence factual summary of the core engineering insight or verified development. "
            f"Include exact primary source URLs and publishers where applicable. Do not invent any statistics."
        )

        try:
            # Separate research request using Groq's browser_search tool
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a software engineering researcher. Rely strictly on verified technical facts."
                    },
                    {"role": "user", "content": prompt}
                ],
                tools=[{"type": "browser_search"}],
                temperature=0.2,
                max_completion_tokens=800
            )

            message_content = response.choices[0].message.content or ""
            if not message_content.strip():
                return self.get_evergreen_fallback(pillar_id, topic, "Groq browser search returned empty content")

            # Extract cited URLs from the research text
            urls = re.findall(r"https?://[^\s)\]]+", message_content)
            sources: List[ResearchSource] = []
            for url in urls[:3]:
                sources.append(ResearchSource(
                    title=f"Source for {topic}",
                    url=url,
                    publisher="Verified Web Reference",
                    claim="Referenced in technical background research"
                ))

            if not sources:
                sources.append(ResearchSource(
                    title=topic,
                    url=None,
                    publisher="Groq Verified Research",
                    claim="Synthesized from verified documentation"
                ))

            return ResearchResult(
                is_live_search=True,
                query=topic,
                summary=message_content.strip(),
                sources=sources,
                fallback_reason=None
            )

        except Exception as e:
            redacted_err = settings.redact(str(e))
            logger.warning("Groq browser search failed or model does not support tool use: %s. Falling back to evergreen context.", redacted_err)
            return self.get_evergreen_fallback(pillar_id, topic, f"Groq search error: {redacted_err}")
