"""Configuration management and secret-safe settings loading."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
import pytz
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Groq API
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    # LinkedIn Official API
    linkedin_access_token: Optional[str] = Field(default=None, alias="LINKEDIN_ACCESS_TOKEN")
    linkedin_author_urn: Optional[str] = Field(default=None, alias="LINKEDIN_AUTHOR_URN")
    linkedin_api_version: str = Field(default="202501", alias="LINKEDIN_API_VERSION")
    linkedin_endpoint_style: str = Field(default="rest/posts", alias="LINKEDIN_ENDPOINT_STYLE")
    linkedin_client_id: Optional[str] = Field(default=None, alias="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: Optional[str] = Field(default=None, alias="LINKEDIN_CLIENT_SECRET")
    linkedin_refresh_token: Optional[str] = Field(default=None, alias="LINKEDIN_REFRESH_TOKEN")

    # GitHub REST API
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")
    github_repository: Optional[str] = Field(default=None, alias="GITHUB_REPOSITORY")
    github_state_branch: str = Field(default="automation-state", alias="GITHUB_STATE_BRANCH")

    # Operational guardrails
    auto_publish: bool = Field(default=False, alias="AUTO_PUBLISH")
    dry_run: bool = Field(default=True, alias="DRY_RUN")
    publish_timezone: str = Field(default="Asia/Kolkata", alias="PUBLISH_TIMEZONE")
    max_post_characters: int = Field(default=2200, alias="MAX_POST_CHARACTERS")
    enable_web_search: bool = Field(default=True, alias="ENABLE_WEB_SEARCH")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("publish_timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            pytz.timezone(v)
        except pytz.UnknownTimeZoneError:
            raise ValueError(f"Unknown timezone: {v}. Must be a valid IANA timezone like 'Asia/Kolkata'.")
        return v

    @field_validator("linkedin_author_urn")
    @classmethod
    def validate_author_urn(cls, v: Optional[str]) -> Optional[str]:
        if v and not (v.startswith("urn:li:person:") or v.startswith("urn:li:organization:")):
            raise ValueError(f"Invalid LINKEDIN_AUTHOR_URN: '{v}'. Must start with 'urn:li:person:' or 'urn:li:organization:'.")
        return v

    @field_validator("linkedin_endpoint_style")
    @classmethod
    def validate_endpoint_style(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in ("rest/posts", "v2/ugcposts"):
            raise ValueError(f"Unsupported LINKEDIN_ENDPOINT_STYLE: '{v}'. Allowed values are 'rest/posts' or 'v2/ugcPosts'.")
        return v_clean

    def get_active_secrets(self) -> Set[str]:
        """Collect all sensitive strings currently configured so they can be redacted."""
        secrets: Set[str] = set()
        for val in [
            self.groq_api_key,
            self.linkedin_access_token,
            self.linkedin_client_secret,
            self.linkedin_refresh_token,
            self.github_token,
        ]:
            if val and len(val.strip()) > 3:
                secrets.add(val.strip())
        return secrets

    def redact(self, text: str) -> str:
        """Redact sensitive keys/tokens from any text string."""
        if not text:
            return text
        redacted = text
        for secret in self.get_active_secrets():
            redacted = redacted.replace(secret, "[REDACTED]")

        # Also redact generic token patterns
        redacted = re.sub(r"gsk_[a-zA-Z0-9_-]{20,}", "[REDACTED_GROQ_KEY]", redacted)
        redacted = re.sub(r"ghp_[a-zA-Z0-9]{20,}", "[REDACTED_GITHUB_TOKEN]", redacted)
        redacted = re.sub(r"github_pat_[a-zA-Z0-9_]{20,}", "[REDACTED_GITHUB_TOKEN]", redacted)
        redacted = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]{15,}", "Bearer [REDACTED_TOKEN]", redacted)
        return redacted

    def validate_for_mode(self, mode: str) -> Dict[str, List[str]]:
        """Validate settings readiness for a specific execution mode."""
        missing: List[str] = []
        warnings: List[str] = []

        if mode in ("draft", "publish", "dry-run"):
            if not self.groq_api_key:
                missing.append("GROQ_API_KEY (Required for content generation)")

        if mode in ("draft", "publish"):
            if not self.github_token:
                missing.append("GITHUB_TOKEN (Required for reading/writing durable state)")
            if not self.github_repository:
                missing.append("GITHUB_REPOSITORY (Required, format: owner/repo)")

        if mode == "publish":
            if not self.auto_publish:
                missing.append("AUTO_PUBLISH must be set to 'true' to publish")
            if self.dry_run:
                missing.append("DRY_RUN must be set to 'false' to publish")
            if not self.linkedin_access_token:
                missing.append("LINKEDIN_ACCESS_TOKEN (Required for publishing)")
            if not self.linkedin_author_urn:
                missing.append("LINKEDIN_AUTHOR_URN (Required, format: urn:li:person:ID)")

        # Warnings for optional or best-practice items
        if mode != "publish" and not self.linkedin_access_token:
            warnings.append("LINKEDIN_ACCESS_TOKEN is not set (Publishing will be disabled)")
        if self.auto_publish and self.dry_run:
            warnings.append("AUTO_PUBLISH is true but DRY_RUN is also true (Dry run takes precedence; no publishing will occur)")

        return {"missing": missing, "warnings": warnings}


# Global singleton settings
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Retrieve or initialize the global Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
