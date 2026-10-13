"""Data models and schemas for Groq-powered LinkedIn automation."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecutionMode(str, Enum):
    """Execution mode of the automation runner."""
    CHECK_CONFIG = "check-config"
    DRY_RUN = "dry-run"
    DRAFT = "draft"
    PUBLISH = "publish"


class PublicationStatus(str, Enum):
    """Lifecycle status of publishing a post."""
    NOT_STARTED = "not_started"
    CLAIMED = "claimed"
    PUBLISHED = "published"
    FAILED = "failed"
    UNKNOWN = "unknown"  # Ambiguous timeout/network drop; requires manual reconciliation


class DraftStatus(str, Enum):
    """Lifecycle status of drafting a post."""
    NOT_GENERATED = "not_generated"
    GENERATED = "generated"
    AUDITED = "audited"
    SAVED = "saved"


class ContentPillar(BaseModel):
    """Definition of a content pillar."""
    id: str
    name: str
    category: str = "Authority"
    description: str
    preferred_formulas: List[str] = Field(default_factory=list)
    preferred_angles: List[str] = Field(default_factory=list)
    primary_goal: str = "comments"
    sample_topics: List[str] = Field(default_factory=list)


class CalendarEntry(BaseModel):
    """A day in the 30-day rotation calendar."""
    day: int
    pillar_id: str
    hook_formula: str
    founder_angle: str
    goal: str
    topic: str


class ResearchSource(BaseModel):
    """Metadata for an external research source."""
    title: str
    url: Optional[str] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    claim: str


class ResearchResult(BaseModel):
    """Output from the research stage."""
    is_live_search: bool = False
    query: str
    summary: str
    sources: List[ResearchSource] = Field(default_factory=list)
    fallback_reason: Optional[str] = None


class AuditIssue(BaseModel):
    """An issue detected during editorial and safety audit."""
    severity: str  # "BLOCKER" or "WARNING"
    rule: str
    message: str
    offending_text: Optional[str] = None


class AuditResult(BaseModel):
    """Result of humanizer and safety auditing."""
    passed: bool
    blockers: List[AuditIssue] = Field(default_factory=list)
    warnings: List[AuditIssue] = Field(default_factory=list)
    original_text: str
    scrubbed_text: str
    character_count: int

    @property
    def has_blockers(self) -> bool:
        return len(self.blockers) > 0


class GeneratedPost(BaseModel):
    """A generated LinkedIn post draft with editorial metadata."""
    text: str
    hook: str
    closing_question: Optional[str] = None
    hashtags: List[str] = Field(default_factory=list)
    formula_used: str
    angle_used: str
    pillar_id: str
    character_count: int
    content_hash: str
    research_summary: Optional[str] = None


class DailyState(BaseModel):
    """Durable state stored in GitHub for a single day."""
    date: str  # YYYY-MM-DD in Asia/Kolkata
    pillar_id: str
    pillar_name: str
    topic: str
    hook_formula: str
    founder_angle: str
    content_hash: Optional[str] = None
    draft_content: Optional[str] = None
    research_metadata: Optional[Dict[str, Any]] = None
    draft_status: DraftStatus = DraftStatus.NOT_GENERATED
    publication_status: PublicationStatus = PublicationStatus.NOT_STARTED
    linkedin_post_id: Optional[str] = None
    execution_mode: Optional[str] = None
    created_at: str
    updated_at: str
    error_summary: Optional[str] = None
    audit_summary: Optional[Dict[str, Any]] = None


class LinkedInPostResponse(BaseModel):
    """Result of attempting to publish to LinkedIn."""
    success: bool
    status_code: int
    post_id: Optional[str] = None
    is_ambiguous_timeout: bool = False
    error_message: Optional[str] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
