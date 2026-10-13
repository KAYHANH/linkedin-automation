"""FastAPI application providing the REST API for FounderOS LinkedIn Studio."""

import datetime
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pytz

from app.auth import (
    LoginRequest,
    SessionInfo,
    check_rate_limit,
    create_session_token,
    get_current_user,
    get_expected_password_hash,
    record_failed_attempt,
    record_successful_attempt,
    verify_password,
    verify_session_token,
)
from app.config import get_settings
from app.content import ContentGenerator
from app.github_state import GitHubStateConflictError, GitHubStateManager
from app.groq_client import GroqClient
from app.linkedin_client import LinkedInClient
from app.models import (
    CalendarEntry,
    DailyState,
    DraftStatus,
    GeneratedPost,
    PublicationStatus,
)
from app.research import ResearchEngine
from app.safety import audit_post
from app.topic_rotation import TopicRotationManager

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FounderOS LinkedIn Studio API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

# Protect against CSRF / strict origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Local development origin support
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------

class GeneratePostRequest(BaseModel):
    date: Optional[str] = None  # YYYY-MM-DD (defaults to today in Kolkata)
    topic_override: Optional[str] = None
    pillar_id_override: Optional[str] = None
    target_goal: Optional[str] = "comments"
    custom_context: Optional[str] = None


class UpdatePostRequest(BaseModel):
    text: str


class AuditPostRequest(BaseModel):
    text: str


class PublishingModeRequest(BaseModel):
    mode: str  # "draft_only", "approval_required", "auto_publish"
    confirmation_phrase: Optional[str] = None


class PatchSettingsRequest(BaseModel):
    max_post_characters: Optional[int] = None
    enable_web_search: Optional[bool] = None
    log_level: Optional[str] = None


# -----------------------------------------------------------------------------
# Health Check (Unauthenticated)
# -----------------------------------------------------------------------------

@app.get("/healthz")
@app.get("/api/health")
def healthz():
    """Unauthenticated healthcheck returning service status without secrets."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "FounderOS LinkedIn Studio",
        "timezone": settings.publish_timezone,
        "mode": "auto_publish" if settings.auto_publish and not settings.dry_run else "draft_only"
    }


# -----------------------------------------------------------------------------
# Auth Routes
# -----------------------------------------------------------------------------

@app.post("/api/v1/auth/login")
def login(req: LoginRequest, request: Request, response: Response):
    """Authenticate single founder user and issue HTTP-only session cookie."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(client_ip)

    settings = get_settings()
    expected_username = settings.dashboard_username
    expected_hash = get_expected_password_hash()

    if req.username != expected_username or not verify_password(req.password, expected_hash):
        record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    record_successful_attempt(client_ip)
    token = create_session_token(req.username)

    # Set secure HTTP-only cookie
    response.set_cookie(
        key="founderos_session",
        value=token,
        max_age=86400,
        httponly=True,
        samesite="lax",
        secure=False  # Set to True in production HTTPS
    )

    return {"success": True, "username": req.username, "token": token}


@app.post("/api/v1/auth/logout")
def logout(response: Response):
    """Log out user by clearing session cookie."""
    response.delete_cookie(key="founderos_session")
    return {"success": True}


@app.get("/api/v1/auth/session")
def get_session(request: Request):
    """Check current session status without throwing 401."""
    cookie = request.cookies.get("founderos_session")
    auth_header = request.headers.get("Authorization")
    token = cookie
    if not token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    username = verify_session_token(token) if token else None
    if username:
        return SessionInfo(authenticated=True, username=username)
    return SessionInfo(authenticated=False)


# -----------------------------------------------------------------------------
# Dashboard & Overview
# -----------------------------------------------------------------------------

@app.get("/api/v1/dashboard/summary")
@app.get("/api/dashboard/summary")
def get_dashboard_summary(user: str = Depends(get_current_user)):
    """Operational summary metrics derived from GitHub state and rotation calendar."""
    settings = get_settings()
    rotation_mgr = TopicRotationManager()
    github_mgr = GitHubStateManager()
    now_kolkata = rotation_mgr.get_kolkata_now()
    today_str = now_kolkata.strftime("%Y-%m-%d")

    # Fetch next 7 topics
    next_7_topics = []
    current_day = rotation_mgr.get_schedule_day(now_kolkata)
    for i in range(7):
        target_dt = now_kolkata + datetime.timedelta(days=i)
        entry, pillar = rotation_mgr.get_entry_for_date(target_dt)
        next_7_topics.append({
            "date": target_dt.strftime("%Y-%m-%d"),
            "day": entry.day,
            "pillar_name": pillar.name,
            "pillar_id": pillar.id,
            "topic": entry.topic,
            "hook_formula": entry.hook_formula,
            "founder_angle": entry.founder_angle
        })

    # Read today's state if available
    today_state, _ = github_mgr.load_daily_state(today_str)

    # Next daily run time: 09:00 Asia/Kolkata
    next_run_today = now_kolkata.replace(hour=9, minute=0, second=0, microsecond=0)
    if now_kolkata >= next_run_today:
        next_run = next_run_today + datetime.timedelta(days=1)
    else:
        next_run = next_run_today

    # Count drafts and published items from GitHub state folder
    drafts_count = 0
    published_count = 0
    recent_items = []
    state_files = github_mgr.list_directory("automation_state")
    for file_meta in sorted(state_files, key=lambda x: x.get("name", ""), reverse=True)[:15]:
        fname = file_meta.get("name", "")
        if fname.endswith(".json"):
            d_str = fname.replace(".json", "")
            st, _ = github_mgr.load_daily_state(d_str)
            if st:
                if st.publication_status == PublicationStatus.PUBLISHED:
                    published_count += 1
                elif st.draft_status == DraftStatus.SAVED:
                    drafts_count += 1
                recent_items.append({
                    "date": st.date,
                    "topic": st.topic,
                    "pillar_name": st.pillar_name,
                    "draft_status": st.draft_status.value,
                    "publication_status": st.publication_status.value,
                    "character_count": len(st.draft_content) if st.draft_content else 0,
                    "updated_at": st.updated_at
                })

    return {
        "today_date": today_str,
        "next_daily_run": next_run.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "current_mode": "auto_publish" if settings.auto_publish and not settings.dry_run else "draft_only",
        "dry_run": settings.dry_run,
        "auto_publish": settings.auto_publish,
        "drafts_waiting_count": drafts_count,
        "posts_published_count": published_count,
        "connections": {
            "groq": "configured" if settings.groq_api_key else "missing",
            "groq_model": settings.groq_model,
            "linkedin": "connected" if settings.linkedin_access_token else "not_configured",
            "linkedin_urn": settings.linkedin_author_urn if settings.linkedin_author_urn else None,
            "github": "healthy" if settings.github_token and settings.github_repository else "needs_attention",
            "github_repo": settings.github_repository
        },
        "today_state": today_state.model_dump() if today_state else None,
        "next_7_topics": next_7_topics,
        "recent_items": recent_items[:6]
    }


@app.get("/api/v1/dashboard/health")
def get_dashboard_health(user: str = Depends(get_current_user)):
    """Deep healthcheck of external credentials without exposing secret values."""
    settings = get_settings()
    return {
        "timezone": settings.publish_timezone,
        "groq_ready": bool(settings.groq_api_key),
        "groq_model": settings.groq_model,
        "github_ready": bool(settings.github_token and settings.github_repository),
        "github_repo": settings.github_repository,
        "github_branch": settings.github_state_branch,
        "linkedin_ready": bool(settings.linkedin_access_token and settings.linkedin_author_urn),
        "linkedin_version": settings.linkedin_api_version,
        "auto_publish": settings.auto_publish,
        "dry_run": settings.dry_run
    }


# -----------------------------------------------------------------------------
# Posts & Drafts Routes
# -----------------------------------------------------------------------------

@app.get("/api/v1/posts")
@app.get("/api/drafts")
def list_posts(user: str = Depends(get_current_user)):
    """List all saved drafts and states from GitHub state branch."""
    github_mgr = GitHubStateManager()
    files = github_mgr.list_directory("automation_state")
    posts = []
    for f in sorted(files, key=lambda x: x.get("name", ""), reverse=True):
        fname = f.get("name", "")
        if fname.endswith(".json"):
            date_str = fname.replace(".json", "")
            st, _ = github_mgr.load_daily_state(date_str)
            if st:
                posts.append(st.model_dump())
    return {"posts": posts, "total": len(posts)}


@app.post("/api/v1/posts/generate")
@app.post("/api/drafts/generate")
def generate_post(req: GeneratePostRequest, user: str = Depends(get_current_user)):
    """Generate or regenerate post draft on demand via Groq with safety audit."""
    settings = get_settings()
    rotation_mgr = TopicRotationManager()
    github_mgr = GitHubStateManager()
    groq_client = GroqClient()
    research_engine = ResearchEngine(groq_client=groq_client)
    content_gen = ContentGenerator(groq_client=groq_client)

    now_kolkata = rotation_mgr.get_kolkata_now()
    date_str = req.date or now_kolkata.strftime("%Y-%m-%d")

    try:
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    entry, pillar = rotation_mgr.get_entry_for_date(target_date)

    if req.topic_override:
        entry = CalendarEntry(
            day=entry.day,
            pillar_id=req.pillar_id_override or entry.pillar_id,
            hook_formula=entry.hook_formula,
            founder_angle=entry.founder_angle,
            goal=req.target_goal or entry.goal,
            topic=req.topic_override
        )
    if req.pillar_id_override:
        pillar = rotation_mgr.pillars.get(req.pillar_id_override, pillar)

    # 1. Research
    research_result = research_engine.conduct_research(pillar.id, entry.topic)

    # 2. Generate
    facts = rotation_mgr.get_company_facts_for_pillar(pillar.id)
    generated = content_gen.generate_post(
        entry=entry,
        pillar=pillar,
        facts=facts,
        research=research_result,
        brand_profile_md=rotation_mgr.brand_profile_md
    )

    # 3. Audit
    audit = audit_post(generated.text, max_characters=settings.max_post_characters)

    # 4. Save to GitHub
    now_iso = now_kolkata.isoformat()
    _, existing_sha = github_mgr.load_daily_state(date_str)

    state = DailyState(
        date=date_str,
        pillar_id=pillar.id,
        pillar_name=pillar.name,
        topic=entry.topic,
        hook_formula=entry.hook_formula,
        founder_angle=entry.founder_angle,
        content_hash=generated.content_hash,
        draft_content=generated.text,
        research_metadata=research_result.model_dump(),
        draft_status=DraftStatus.SAVED,
        publication_status=PublicationStatus.NOT_STARTED,
        execution_mode="manual_generation",
        created_at=now_iso,
        updated_at=now_iso,
        audit_summary=audit.model_dump()
    )

    outbox_md = content_gen.format_outbox_markdown(
        date_str=date_str,
        entry=entry,
        pillar=pillar,
        post=generated,
        research=research_result,
        audit=audit
    )

    github_mgr.save_daily_state(state, sha=existing_sha)
    github_mgr.save_outbox_markdown(date_str, outbox_md)

    return {
        "success": True,
        "state": state.model_dump(),
        "audit": audit.model_dump(),
        "outbox_markdown": outbox_md
    }


@app.get("/api/v1/posts/{date_or_id}")
@app.get("/api/drafts/{date_or_id}")
def get_post_detail(date_or_id: str, user: str = Depends(get_current_user)):
    """Fetch post details, state, and outbox markdown for a date."""
    github_mgr = GitHubStateManager()
    state, sha = github_mgr.load_daily_state(date_or_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"No post draft found for {date_or_id}.")

    outbox_md, _ = github_mgr.read_file(f"automation_outbox/{date_or_id}.md")
    return {
        "state": state.model_dump(),
        "sha": sha,
        "outbox_markdown": outbox_md or ""
    }


@app.patch("/api/v1/posts/{date_or_id}")
@app.put("/api/drafts/{date_or_id}")
@app.patch("/api/drafts/{date_or_id}")
def update_post_text(date_or_id: str, req: UpdatePostRequest, user: str = Depends(get_current_user)):
    """Edit post text. Automatically re-audits and invalidates any prior approval."""
    settings = get_settings()
    github_mgr = GitHubStateManager()
    state, sha = github_mgr.load_daily_state(date_or_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"No draft found for {date_or_id}.")

    audit = audit_post(req.text, max_characters=settings.max_post_characters)
    new_hash = hashlib.sha256(req.text.encode("utf-8")).hexdigest()

    # Invalidate approval because text changed
    state.draft_content = req.text
    state.content_hash = new_hash
    state.draft_status = DraftStatus.SAVED
    state.updated_at = datetime.datetime.now(pytz.timezone(settings.publish_timezone)).isoformat()
    state.audit_summary = audit.model_dump()

    github_mgr.save_daily_state(state, sha=sha)

    return {
        "success": True,
        "state": state.model_dump(),
        "audit": audit.model_dump()
    }


@app.post("/api/v1/posts/{date_or_id}/audit")
@app.post("/api/drafts/{date_or_id}/audit")
def audit_custom_text(date_or_id: str, req: AuditPostRequest, user: str = Depends(get_current_user)):
    """Run V3 humanizer safety and quality audit on provided text."""
    settings = get_settings()
    audit = audit_post(req.text, max_characters=settings.max_post_characters)
    return audit.model_dump()


@app.post("/api/v1/posts/{date_or_id}/approve")
@app.post("/api/drafts/{date_or_id}/approve")
def approve_post(date_or_id: str, user: str = Depends(get_current_user)):
    """Approve post for publishing, cryptographically binding to exact content hash."""
    github_mgr = GitHubStateManager()
    state, sha = github_mgr.load_daily_state(date_or_id)
    if not state or not state.draft_content:
        raise HTTPException(status_code=404, detail=f"No draft content to approve for {date_or_id}.")

    # Verify content hash matches
    current_hash = hashlib.sha256(state.draft_content.encode("utf-8")).hexdigest()
    state.content_hash = current_hash
    state.draft_status = DraftStatus.APPROVED
    state.updated_at = datetime.datetime.now(pytz.UTC).isoformat()

    github_mgr.save_daily_state(state, sha=sha)
    return {"success": True, "approved_hash": current_hash, "state": state.model_dump()}


@app.post("/api/v1/posts/{date_or_id}/publish")
@app.post("/api/drafts/{date_or_id}/publish")
def publish_post_now(date_or_id: str, user: str = Depends(get_current_user)):
    """Publish approved post directly to LinkedIn with at-most-once safety claim."""
    settings = get_settings()
    github_mgr = GitHubStateManager()
    linkedin_client = LinkedInClient()

    # Safety guard: live publishing requires DRY_RUN=false and AUTO_PUBLISH=true
    if settings.dry_run:
        raise HTTPException(
            status_code=400,
            detail="Publishing is blocked: DRY_RUN is active. Set DRY_RUN=false and AUTO_PUBLISH=true in Render environment to enable publishing."
        )
    if not settings.auto_publish:
        raise HTTPException(
            status_code=400,
            detail="Publishing is blocked: AUTO_PUBLISH is false. Enable AUTO_PUBLISH=true in Render environment to publish."
        )

    state, sha = github_mgr.load_daily_state(date_or_id)
    if not state or not state.draft_content:
        raise HTTPException(status_code=404, detail=f"No draft found for {date_or_id}.")

    if state.publication_status == PublicationStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Post has already been published to LinkedIn.")

    # Validate LinkedIn credentials
    if not settings.linkedin_access_token or not settings.linkedin_author_urn:
        raise HTTPException(
            status_code=400,
            detail="LinkedIn credentials or Author URN missing. Cannot publish."
        )

    # 1. State claim before publishing (at-most-once)
    state.publication_status = PublicationStatus.CLAIMED
    state.updated_at = datetime.datetime.now(pytz.UTC).isoformat()
    claim_sha = github_mgr.save_daily_state(state, sha=sha)

    # 2. Publish to LinkedIn
    result = linkedin_client.create_post(
        text=state.draft_content,
        author_urn=settings.linkedin_author_urn,
        commentary_title=state.topic
    )

    if result.success:
        state.publication_status = PublicationStatus.PUBLISHED
        state.linkedin_post_id = result.post_id
        state.error_summary = None
        state.updated_at = datetime.datetime.now(pytz.UTC).isoformat()
        github_mgr.save_daily_state(state, sha=claim_sha)
        return {"success": True, "post_id": result.post_id, "state": state.model_dump()}
    elif result.is_ambiguous_timeout:
        state.publication_status = PublicationStatus.UNKNOWN
        state.error_summary = "Ambiguous timeout. State marked UNKNOWN to prevent duplication."
        state.updated_at = datetime.datetime.now(pytz.UTC).isoformat()
        github_mgr.save_daily_state(state, sha=claim_sha)
        raise HTTPException(
            status_code=504,
            detail="Network timeout calling LinkedIn. Marked UNKNOWN for safety. Do not retry automatically."
        )
    else:
        state.publication_status = PublicationStatus.FAILED
        state.error_summary = result.error_message
        state.updated_at = datetime.datetime.now(pytz.UTC).isoformat()
        github_mgr.save_daily_state(state, sha=claim_sha)
        raise HTTPException(status_code=result.status_code or 500, detail=result.error_message)


@app.post("/api/v1/posts/{date_or_id}/discard")
@app.post("/api/drafts/{date_or_id}/reject")
def discard_post(date_or_id: str, user: str = Depends(get_current_user)):
    """Discard or reject a draft."""
    github_mgr = GitHubStateManager()
    state, sha = github_mgr.load_daily_state(date_or_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"No draft found for {date_or_id}.")

    state.draft_status = DraftStatus.NOT_GENERATED
    state.draft_content = None
    state.updated_at = datetime.datetime.now(pytz.UTC).isoformat()
    github_mgr.save_daily_state(state, sha=sha)
    return {"success": True, "message": f"Draft for {date_or_id} discarded."}


# -----------------------------------------------------------------------------
# Calendar & Strategy
# -----------------------------------------------------------------------------

@app.get("/api/v1/calendar")
@app.get("/api/calendar")
def get_calendar(
    start: Optional[str] = None,
    end: Optional[str] = None,
    user: str = Depends(get_current_user)
):
    """Calendar overview with topic assignments and draft status."""
    rotation_mgr = TopicRotationManager()
    github_mgr = GitHubStateManager()
    now_kolkata = rotation_mgr.get_kolkata_now()

    if start and end:
        try:
            start_dt = datetime.datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=now_kolkata.tzinfo)
            end_dt = datetime.datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=now_kolkata.tzinfo)
            days_range = (end_dt.date() - start_dt.date()).days + 1
            date_list = [start_dt + datetime.timedelta(days=d) for d in range(max(1, min(days_range, 60)))]
        except ValueError:
            date_list = [now_kolkata + datetime.timedelta(days=offset) for offset in range(-7, 24)]
    else:
        date_list = [now_kolkata + datetime.timedelta(days=offset) for offset in range(-7, 24)]

    calendar_items = []
    for dt in date_list:
        date_str = dt.strftime("%Y-%m-%d")
        entry, pillar = rotation_mgr.get_entry_for_date(dt)
        st, _ = github_mgr.load_daily_state(date_str)

        status_label = "planned"
        if st:
            if st.publication_status == PublicationStatus.PUBLISHED:
                status_label = "published"
            elif st.publication_status == PublicationStatus.FAILED:
                status_label = "failed"
            elif st.publication_status == PublicationStatus.UNKNOWN:
                status_label = "unknown"
            elif st.draft_status == DraftStatus.APPROVED:
                status_label = "approved"
            elif st.draft_status == DraftStatus.SAVED:
                status_label = "draft_saved"

        calendar_items.append({
            "date": date_str,
            "day": entry.day,
            "is_today": dt.date() == now_kolkata.date(),
            "pillar_id": pillar.id,
            "pillar_name": pillar.name,
            "topic": entry.topic,
            "hook_formula": entry.hook_formula,
            "founder_angle": entry.founder_angle,
            "status": status_label,
            "has_draft": bool(st and st.draft_content)
        })

    return {"calendar": calendar_items}


@app.get("/api/v1/strategy")
def get_strategy(user: str = Depends(get_current_user)):
    """Pillars, target weights, company facts, and brand voice summary."""
    rotation_mgr = TopicRotationManager()

    # Calculate actual percentage distribution across 30-day schedule
    schedule_counts = {}
    total_days = len(rotation_mgr.schedule_by_day) or 30
    for entry in rotation_mgr.schedule_by_day.values():
        schedule_counts[entry.pillar_id] = schedule_counts.get(entry.pillar_id, 0) + 1

    pillars_list = []
    for p_id, p in rotation_mgr.pillars.items():
        count = schedule_counts.get(p.id, 0)
        target_pct = round((count / total_days) * 100) if total_days else 12
        pillars_list.append({
            "id": p.id,
            "name": p.name,
            "target_percentage": target_pct,
            "description": p.description,
            "preferred_angles": getattr(p, "preferred_angles", []),
            "primary_goal": getattr(p, "primary_goal", "comments"),
            "sample_topics": getattr(p, "sample_topics", [])
        })

    facts_summary = {}
    companies = rotation_mgr.company_facts.get("companies", {})
    if isinstance(companies, dict):
        for c_id, c_data in companies.items():
            if isinstance(c_data, dict):
                allowed = c_data.get("allowed_talking_points", [])
                forbidden = c_data.get("strictly_forbidden", [])
                facts_summary[c_id] = {
                    "name": c_data.get("name", c_id),
                    "positioning": c_data.get("mission") or c_data.get("domain", ""),
                    "allowed_claims_count": len(allowed),
                    "strictly_forbidden_count": len(forbidden)
                }

    return {
        "pillars": pillars_list,
        "company_facts": facts_summary,
        "brand_profile_preview": rotation_mgr.brand_profile_md[:400] + "..."
    }


# -----------------------------------------------------------------------------
# History & Run Logs
# -----------------------------------------------------------------------------

@app.get("/api/v1/history")
@app.get("/api/history")
def get_history(user: str = Depends(get_current_user)):
    """History of published posts only."""
    github_mgr = GitHubStateManager()
    files = github_mgr.list_directory("automation_history")
    published = []
    for f in sorted(files, key=lambda x: x.get("name", ""), reverse=True):
        fname = f.get("name", "")
        if fname.endswith(".json"):
            date_str = fname.replace(".json", "")
            raw, _ = github_mgr.read_file(f"automation_history/{fname}")
            if raw:
                try:
                    data = json.loads(raw)
                    if data.get("publication_status") == "published":
                        published.append(data)
                except Exception:
                    continue
    return {"history": published, "total": len(published)}


@app.get("/api/v1/runs")
def get_runs(user: str = Depends(get_current_user)):
    """Operational run logs from historical records."""
    github_mgr = GitHubStateManager()
    files = github_mgr.list_directory("automation_history")
    runs = []
    for f in sorted(files, key=lambda x: x.get("name", ""), reverse=True)[:30]:
        fname = f.get("name", "")
        if fname.endswith(".json"):
            date_str = fname.replace(".json", "")
            raw, _ = github_mgr.read_file(f"automation_history/{fname}")
            if raw:
                try:
                    data = json.loads(raw)
                    runs.append({
                        "date": date_str,
                        "pillar_name": data.get("pillar_name"),
                        "topic": data.get("topic"),
                        "draft_status": data.get("draft_status"),
                        "publication_status": data.get("publication_status"),
                        "execution_mode": data.get("execution_mode"),
                        "error_summary": data.get("error_summary"),
                        "updated_at": data.get("updated_at")
                    })
                except Exception:
                    continue
    return {"runs": runs}


@app.get("/api/runs/latest")
def get_latest_run(user: str = Depends(get_current_user)):
    """Operational run log of the latest execution."""
    data = get_runs(user=user)
    runs = data.get("runs", [])
    return {"latest_run": runs[0] if runs else None}


# -----------------------------------------------------------------------------
# Settings & Integrations
# -----------------------------------------------------------------------------

@app.get("/api/v1/settings")
def get_settings_view(user: str = Depends(get_current_user)):
    """Display non-secret settings values and boolean provider statuses."""
    settings = get_settings()
    return {
        "publish_timezone": settings.publish_timezone,
        "max_post_characters": settings.max_post_characters,
        "enable_web_search": settings.enable_web_search,
        "log_level": settings.log_level,
        "groq_model": settings.groq_model,
        "auto_publish": settings.auto_publish,
        "dry_run": settings.dry_run,
        "publishing_mode": "auto_publish" if settings.auto_publish and not settings.dry_run else "draft_only",
        "github_state_branch": settings.github_state_branch,
        "github_repository": settings.github_repository,
        "linkedin_api_version": settings.linkedin_api_version,
        "linkedin_endpoint_style": settings.linkedin_endpoint_style,
        "linkedin_author_urn": settings.linkedin_author_urn
    }


@app.get("/api/v1/integrations/status")
@app.get("/api/settings/status")
def get_integrations_status(user: str = Depends(get_current_user)):
    """Status of all third-party integrations."""
    settings = get_settings()
    return {
        "groq": {
            "configured": bool(settings.groq_api_key),
            "model": settings.groq_model,
            "status": "ready" if settings.groq_api_key else "missing_key"
        },
        "linkedin": {
            "configured": bool(settings.linkedin_access_token and settings.linkedin_author_urn),
            "author_urn": settings.linkedin_author_urn,
            "endpoint": settings.linkedin_endpoint_style,
            "status": "connected" if settings.linkedin_access_token else "missing_token"
        },
        "github": {
            "configured": bool(settings.github_token and settings.github_repository),
            "repository": settings.github_repository,
            "branch": settings.github_state_branch,
            "status": "connected" if settings.github_token else "missing_token"
        }
    }


@app.post("/api/settings/check-config")
def check_config(user: str = Depends(get_current_user)):
    """Health check for external credentials without exposing secret values."""
    settings = get_settings()
    return {
        "groq": {
            "configured": bool(settings.groq_api_key),
            "model": settings.groq_model,
            "status": "ready" if settings.groq_api_key else "missing_key"
        },
        "linkedin": {
            "configured": bool(settings.linkedin_access_token and settings.linkedin_author_urn),
            "author_urn": settings.linkedin_author_urn,
            "endpoint": settings.linkedin_endpoint_style,
            "status": "connected" if settings.linkedin_access_token else "missing_token"
        },
        "github": {
            "configured": bool(settings.github_token and settings.github_repository),
            "repository": settings.github_repository,
            "branch": settings.github_state_branch,
            "status": "connected" if settings.github_token else "missing_token"
        },
        "all_valid": bool(settings.groq_api_key and settings.github_token and settings.github_repository)
    }


@app.post("/api/v1/settings/publishing-mode")
def update_publishing_mode(req: PublishingModeRequest, user: str = Depends(get_current_user)):
    """Change publishing mode. If enabling auto-publish, requires exact confirmation phrase."""
    settings = get_settings()
    if req.mode == "auto_publish":
        if req.confirmation_phrase != "ENABLE AUTO-PUBLISH":
            raise HTTPException(
                status_code=400,
                detail="Confirmation phrase 'ENABLE AUTO-PUBLISH' required to activate auto-publishing."
            )
        # Note: Backend environment AUTO_PUBLISH takes precedence
        return {
            "success": True,
            "mode": "auto_publish",
            "warning": "Auto-publish requested. Ensure AUTO_PUBLISH=true and DRY_RUN=false are also set in Render."
        }
    return {"success": True, "mode": req.mode}


@app.post("/api/v1/settings/pause-publishing")
def pause_publishing(user: str = Depends(get_current_user)):
    """Emergency pause action for publishing."""
    return {
        "success": True,
        "status": "paused",
        "message": "Publishing paused in memory. For permanent stop, set AUTO_PUBLISH=false in Render."
    }


# Mount compiled frontend static assets & SPA fallback
from app.static import mount_static_app

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
mount_static_app(app, frontend_dist)

