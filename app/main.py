"""Main CLI entry point orchestrating LinkedIn daily automation."""

import argparse
import datetime
import logging
import sys
from typing import Optional
import pytz

from app.config import get_settings
from app.content import ContentGenerator
from app.github_state import GitHubStateConflictError, GitHubStateManager
from app.linkedin_client import LinkedInClient
from app.models import DailyState, DraftStatus, ExecutionMode, PublicationStatus
from app.research import ResearchEngine
from app.safety import audit_post
from app.topic_rotation import TopicRotationManager

# Configure root logger with secret redaction filter
class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        settings = get_settings()
        if isinstance(record.msg, str):
            record.msg = settings.redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: settings.redact(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(settings.redact(str(a)) for a in record.args)
        return True


logger = logging.getLogger("linkedin_automation")


def configure_logging(level_name: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.setLevel(level_name.upper())
    root.handlers = [handler]


def run_check_config() -> int:
    """Validate system configuration across all modes without exposing secrets."""
    settings = get_settings()
    print("=" * 60)
    print("GROQ-LINKEDIN AUTOMATION CONFIGURATION CHECK")
    print("=" * 60)
    print(f"Timezone:               {settings.publish_timezone}")
    print(f"Groq Model:             {settings.groq_model}")
    print(f"Groq API Key Set:       {'Yes' if settings.groq_api_key else 'NO'}")
    print(f"LinkedIn Token Set:     {'Yes' if settings.linkedin_access_token else 'NO'}")
    print(f"LinkedIn Author URN:    {settings.linkedin_author_urn or 'NOT SET'}")
    print(f"LinkedIn API Version:   {settings.linkedin_api_version}")
    print(f"LinkedIn Endpoint:      {settings.linkedin_endpoint_style}")
    print(f"GitHub Repository:      {settings.github_repository or 'NOT SET'}")
    print(f"GitHub Token Set:       {'Yes' if settings.github_token else 'NO'}")
    print(f"GitHub State Branch:    {settings.github_state_branch}")
    print(f"AUTO_PUBLISH:           {settings.auto_publish}")
    print(f"DRY_RUN:                {settings.dry_run}")
    print(f"ENABLE_WEB_SEARCH:      {settings.enable_web_search}")
    print(f"MAX_POST_CHARACTERS:    {settings.max_post_characters}")
    print("-" * 60)

    # Validate readiness per mode
    modes = ["dry-run", "draft", "publish"]
    has_issues = False
    for mode in modes:
        report = settings.validate_for_mode(mode)
        missing = report["missing"]
        warnings = report["warnings"]
        status = "READY" if not missing else "BLOCKED"
        print(f"Mode [{mode.upper()}]: {status}")
        if missing:
            has_issues = True
            for m in missing:
                print(f"  - MISSING: {m}")
        if warnings:
            for w in warnings:
                print(f"  - WARNING: {w}")

    print("=" * 60)
    return 1 if (has_issues and not settings.dry_run) else 0


def run_automation(mode: ExecutionMode, target_date_override: Optional[datetime.datetime] = None) -> int:
    """Main execution pipeline."""
    settings = get_settings()
    rotation_mgr = TopicRotationManager()
    research_engine = ResearchEngine()
    content_gen = ContentGenerator()
    github_mgr = GitHubStateManager()
    linkedin_client = LinkedInClient()

    # 1. Determine India date and topic
    dt = target_date_override or rotation_mgr.get_current_kolkata_date()
    date_str, entry, pillar, facts = rotation_mgr.get_topic_for_date(dt)
    now_iso = dt.isoformat()

    logger.info("Executing automation in mode: %s for Date: %s", mode.value, date_str)
    logger.info("Schedule Day %d | Pillar: %s | Formula: %s", entry.day, pillar.name, entry.hook_formula)

    # 2. Check configuration prerequisites
    report = settings.validate_for_mode(mode.value)
    if report["missing"]:
        for m in report["missing"]:
            logger.error("Configuration requirement unmet: %s", m)
        return 1

    # 3. Check for existing daily state (Duplicate Prevention)
    existing_state: Optional[DailyState] = None
    state_sha: Optional[str] = None
    if mode in (ExecutionMode.DRAFT, ExecutionMode.PUBLISH):
        existing_state, state_sha = github_mgr.load_daily_state(date_str)
        if existing_state:
            logger.info("Loaded existing state for %s: draft_status=%s, publication_status=%s",
                        date_str, existing_state.draft_status.value, existing_state.publication_status.value)

            # Strict guard against duplicate publication
            if existing_state.publication_status == PublicationStatus.PUBLISHED:
                logger.warning("Post for %s is ALREADY PUBLISHED (LinkedIn Post ID: %s). Stopping to prevent duplicates.",
                               date_str, existing_state.linkedin_post_id)
                return 0
            if existing_state.publication_status == PublicationStatus.CLAIMED:
                logger.error("Post for %s is currently in CLAIMED status. Possible concurrent worker or previous unconfirmed run. Refusing to post.",
                             date_str)
                return 1
            if existing_state.publication_status == PublicationStatus.UNKNOWN:
                logger.critical("Post for %s has UNKNOWN publication status (ambiguous network timeout). Manual reconciliation required before any new runs.",
                                date_str)
                return 1

    # 4. Research stage
    logger.info("Starting research stage for topic: '%s'", entry.topic)
    research_result = research_engine.conduct_research(pillar.id, entry.topic)
    logger.info("Research completed (Live Search: %s). Sources: %d", research_result.is_live_search, len(research_result.sources))

    # 5. Content generation stage (if draft not already prepared)
    if existing_state and existing_state.draft_content and existing_state.draft_status == DraftStatus.SAVED:
        logger.info("Reusing existing saved draft from state for %s", date_str)
        final_post_text = existing_state.draft_content
        audit = audit_post(final_post_text, max_characters=settings.max_post_characters)
        post_obj = None
    else:
        logger.info("Generating new post draft via Groq...")
        generated_post = content_gen.generate_post(
            entry=entry,
            pillar=pillar,
            facts=facts,
            research=research_result,
            brand_profile_md=rotation_mgr.brand_profile_md
        )
        final_post_text = generated_post.text
        audit = audit_post(final_post_text, max_characters=settings.max_post_characters)
        post_obj = generated_post

    logger.info("Post prepared. Length: %d chars. Audit Passed: %s", len(final_post_text), audit.passed)

    # 6. Branch based on Mode
    if mode == ExecutionMode.DRY_RUN:
        print("\n" + "=" * 60)
        print(f"DRY RUN COMPLETE — NO GITHUB OR LINKEDIN WRITES PERFORMED")
        print("=" * 60)
        print(f"Date:               {date_str} (Schedule Day {entry.day}/30)")
        print(f"Pillar:             {pillar.name} ({pillar.id})")
        print(f"Topic:              {entry.topic}")
        print(f"Formula:            {entry.hook_formula}")
        print(f"Founder Angle:      {entry.founder_angle}")
        print(f"Target Goal:        {entry.goal}")
        print(f"Characters:         {len(final_post_text)}")
        print(f"Audit Status:       {'PASSED' if audit.passed else 'FAILED WITH BLOCKERS'}")
        if audit.blockers:
            print("Blockers:")
            for b in audit.blockers:
                print(f"  - [{b.rule}] {b.message}")
        if audit.warnings:
            print("Warnings:")
            for w in audit.warnings:
                print(f"  - [{w.rule}] {w.message}")
        print("\n--- GENERATED POST TEXT ---")
        print(final_post_text)
        print("=" * 60 + "\n")
        return 0

    elif mode == ExecutionMode.DRAFT:
        logger.info("Saving draft and state to GitHub branch '%s'...", settings.github_state_branch)
        new_state = DailyState(
            date=date_str,
            pillar_id=pillar.id,
            pillar_name=pillar.name,
            topic=entry.topic,
            hook_formula=entry.hook_formula,
            founder_angle=entry.founder_angle,
            content_hash=post_obj.content_hash if post_obj else existing_state.content_hash,
            draft_content=final_post_text,
            research_metadata=research_result.model_dump(),
            draft_status=DraftStatus.SAVED,
            publication_status=PublicationStatus.NOT_STARTED,
            linkedin_post_id=None,
            execution_mode=mode.value,
            created_at=existing_state.created_at if existing_state else now_iso,
            updated_at=now_iso,
            audit_summary=audit.model_dump()
        )

        outbox_md = content_gen.format_outbox_markdown(
            date_str=date_str,
            entry=entry,
            pillar=pillar,
            post=post_obj or generated_post,
            research=research_result,
            audit=audit
        )

        try:
            github_mgr.save_daily_state(new_state, sha=state_sha)
            github_mgr.save_outbox_markdown(date_str, outbox_md)
            logger.info("Successfully recorded draft to GitHub for %s.", date_str)
            return 0
        except GitHubStateConflictError:
            logger.error("Concurrency conflict saving draft to GitHub. Another process modified state.")
            return 1

    elif mode == ExecutionMode.PUBLISH:
        # Strict pre-flight checks
        if not settings.auto_publish or settings.dry_run:
            logger.error("Publishing rejected by safety guards: AUTO_PUBLISH=%s, DRY_RUN=%s.",
                         settings.auto_publish, settings.dry_run)
            return 1

        logger.info("Initiating publishing workflow. Claiming state in GitHub first...")

        # Step A: Claim the state in GitHub before making the LinkedIn API call
        claimed_state = DailyState(
            date=date_str,
            pillar_id=pillar.id,
            pillar_name=pillar.name,
            topic=entry.topic,
            hook_formula=entry.hook_formula,
            founder_angle=entry.founder_angle,
            content_hash=post_obj.content_hash if post_obj else existing_state.content_hash,
            draft_content=final_post_text,
            research_metadata=research_result.model_dump(),
            draft_status=DraftStatus.SAVED,
            publication_status=PublicationStatus.CLAIMED,
            linkedin_post_id=None,
            execution_mode=mode.value,
            created_at=existing_state.created_at if existing_state else now_iso,
            updated_at=now_iso,
            audit_summary=audit.model_dump()
        )

        try:
            claimed_sha = github_mgr.save_daily_state(claimed_state, sha=state_sha)
        except Exception as e:
            logger.critical("Failed to claim daily post state in GitHub: %s. REFUSING to call LinkedIn API.", e)
            return 1

        # Step B: Call LinkedIn API once
        logger.info("State claimed in GitHub. Calling LinkedIn API endpoint (%s)...", settings.linkedin_endpoint_style)
        pub_response = linkedin_client.publish_text_post(final_post_text)

        # Step C: Record confirmed outcome
        if pub_response.success:
            logger.info("LinkedIn post successfully created! ID: %s. Updating GitHub state to PUBLISHED...", pub_response.post_id)
            published_state = claimed_state.model_copy(update={
                "publication_status": PublicationStatus.PUBLISHED,
                "linkedin_post_id": pub_response.post_id,
                "updated_at": datetime.datetime.now(pytz.timezone(settings.publish_timezone)).isoformat()
            })
            github_mgr.save_daily_state(published_state, sha=claimed_sha)
            return 0
        elif pub_response.is_ambiguous_timeout:
            logger.critical("AMBIGUOUS TIMEOUT calling LinkedIn API! Updating state to UNKNOWN and halting.")
            unknown_state = claimed_state.model_copy(update={
                "publication_status": PublicationStatus.UNKNOWN,
                "error_summary": pub_response.error_message,
                "updated_at": datetime.datetime.now(pytz.timezone(settings.publish_timezone)).isoformat()
            })
            github_mgr.save_daily_state(unknown_state, sha=claimed_sha)
            return 1
        else:
            logger.error("LinkedIn API publishing failed with status %d: %s", pub_response.status_code, pub_response.error_message)
            failed_state = claimed_state.model_copy(update={
                "publication_status": PublicationStatus.FAILED,
                "error_summary": pub_response.error_message,
                "updated_at": datetime.datetime.now(pytz.timezone(settings.publish_timezone)).isoformat()
            })
            github_mgr.save_daily_state(failed_state, sha=claimed_sha)
            return 1

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Groq-Powered Daily LinkedIn Automation on Render")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-config", action="store_true", help="Validate environment without exposing secrets")
    group.add_argument("--dry-run", action="store_true", help="Generate and audit post without GitHub or LinkedIn writes")
    group.add_argument("--draft", action="store_true", help="Generate and save draft to GitHub state branch without publishing")
    group.add_argument("--publish", action="store_true", help="Execute daily scheduled job and publish to LinkedIn if enabled")

    parser.add_argument("--date", type=str, default=None, help="Optional date override (format: YYYY-MM-DD)")
    parser.add_argument("--log-level", type=str, default=None, help="Logging level override (DEBUG, INFO, WARNING, ERROR)")

    args = parser.parse_args()

    settings = get_settings()
    log_level = args.log_level or settings.log_level
    configure_logging(log_level)

    if args.check_config:
        sys.exit(run_check_config())

    target_date = None
    if args.date:
        try:
            tz = pytz.timezone(settings.publish_timezone)
            naive_dt = datetime.datetime.strptime(args.date, "%Y-%m-%d")
            target_date = tz.localize(naive_dt)
        except Exception as e:
            logger.error("Invalid date argument '%s': %e", args.date, e)
            sys.exit(1)

    if args.dry_run:
        mode = ExecutionMode.DRY_RUN
    elif args.draft:
        mode = ExecutionMode.DRAFT
    elif args.publish:
        mode = ExecutionMode.PUBLISH
    else:
        sys.exit(1)

    sys.exit(run_automation(mode=mode, target_date_override=target_date))


if __name__ == "__main__":
    main()
