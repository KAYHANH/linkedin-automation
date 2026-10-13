"""Content generation engine implementing upstream editorial frameworks."""

import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.groq_client import GroqClient
from app.models import AuditResult, CalendarEntry, ContentPillar, GeneratedPost, ResearchResult
from app.safety import audit_post, scrub_formatting

logger = logging.getLogger(__name__)

# Upstream reference: hook formulas & founder angles documentation
FORMULA_DESCRIPTIONS = {
    "F1": "Platform Risk Anaphora (Repetitive structure emphasizing dependency on single vendors/tools, followed by the resilient architecture solution)",
    "F2": "R.I.P. Obituary (Declaring the end of an era or outdated practice, e.g. manual spreadsheets in travel, replaced by structured software)",
    "F3": "Year-over-Year Pivot (Comparing what was believed 12 months ago to the hard-won perspective held today)",
    "F4": "Time-Anchor Confession (Specific, dated, uncomfortable operational fact or lesson without manufactured 'let me be honest' framing)",
    "F5": "Self-Proving Meta (Demonstrating a principle by showing the actual discipline in public)",
    "F7": "Odd-Precision Money / Resource Ledger (Number-first line with a named referent, breaking down exact operational costs or time)",
    "F8": "Paid-vs-Free Reversal (Challenging expensive traditional credentials vs genuine skills mastery)",
    "F10": "Contrarian + Historical Receipts (Challenging industry consensus with historical engineering precedent and technical principles)",
    "F11": "Emotional Cold-Open (A real, grounded moment with high operational stakes stated plainly)",
    "F12": "Permission Slip (Constructive encouragement grounded in a concrete fact, e.g. for aspiring developers)",
    "F13": "Bait-and-Switch Reversal (A policy or architecture change that initially seemed like a limitation but turned into a major advantage)",
    "F15": "Explain-to-Kids (Demystifying complex engineering concepts using clear, jargon-free analogies)",
    "F16": "Status-Strip Humility (Senior technical perspective speaking with warmth and practical accessibility rather than distance)",
    "F17": "Controlled A/B Anecdote (One-variable comparison between two engineering approaches or workflows)",
    "F18": "False-Binary Dissolve (Showing that two obvious extremes both fail, revealing the pragmatic middle path)",
    "F19": "Anecdote-Meets-Evidence Bridge (Grounding an operational observation with technical data and principles)",
    "F20": "Diverging-Curves Close (Contrasting two strategic approaches that start close but diverge dramatically over time)",
}

FOUNDER_ANGLES = {
    "A1": "Reprice the Category (Reframing an unglamorous tool or service as high-leverage software infrastructure)",
    "A2": "Content Became Pipeline (Quietly reframing technical writing as relationship and trust infrastructure)",
    "A3": "Audience of One (Writing directly for a specific practitioner, engineer, or partner)",
    "A4": "Scarce-Shots Math (How a lean startup founder must ration focus and avoid feature bloat)",
    "A5": "Unglamorous Bet (Solving dull, back-office operational headaches rather than chasing hype)",
    "A6": "Limit of Delegation (Where automation helps vs where the founder must retain direct human judgment)",
    "A7": "Designed Serendipity (Creating opportunities by consistently sharing practical, unpolished work)",
    "A8": "Evasive-Sentence (Spotting phrases industry people repeat that conceal deeper inefficiencies)",
    "A9": "Delegation Line (Drawing clear boundaries between what AI handles vs human craftsmanship)",
    "A10": "Learning Gate (Strict evaluation criteria before adopting new tools or frameworks)",
}


class ContentGenerator:
    """Orchestrates Groq prompt building, post drafting, and humanizer safety audits."""

    def __init__(self, groq_client: Optional[GroqClient] = None):
        self.groq_client = groq_client or GroqClient()

    def generate_post(
        self,
        entry: CalendarEntry,
        pillar: ContentPillar,
        facts: Dict[str, Any],
        research: ResearchResult,
        brand_profile_md: str
    ) -> GeneratedPost:
        """
        Generate, audit, and return a validated LinkedIn post.
        Uses a two-pass approach if initial audit detects remediable blockers.
        """
        settings = get_settings()

        system_prompt = self._build_system_prompt(brand_profile_md, facts)
        user_prompt = self._build_user_prompt(entry, pillar, research, facts)

        logger.info("Generating post draft for day %d (%s) using Groq...", entry.day, pillar.name)

        raw_json_str = self.groq_client.generate_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.6,
            max_tokens=1400,
            response_format={"type": "json_object"}
        )

        parsed_data = self._parse_json_response(raw_json_str)
        draft_text = parsed_data.get("post_text", "").strip()

        # Audit pass 1
        audit = audit_post(draft_text, max_characters=settings.max_post_characters)

        # If audit fails with blockers, perform an automated repair pass with Groq
        if not audit.passed:
            logger.warning("Audit pass 1 found blockers: %s. Initiating repair pass...", [b.message for b in audit.blockers])
            draft_text = self._repair_draft(
                original_draft=draft_text,
                audit=audit,
                system_prompt=system_prompt,
                entry=entry
            )
            audit = audit_post(draft_text, max_characters=settings.max_post_characters)

        final_text = audit.scrubbed_text
        content_hash = hashlib.sha256(final_text.encode("utf-8")).hexdigest()

        return GeneratedPost(
            text=final_text,
            hook=parsed_data.get("hook", final_text.split("\n")[0]),
            closing_question=parsed_data.get("closing_question"),
            hashtags=parsed_data.get("hashtags", []),
            formula_used=entry.hook_formula,
            angle_used=entry.founder_angle,
            pillar_id=pillar.id,
            character_count=len(final_text),
            content_hash=content_hash,
            research_summary=research.summary
        )

    def _build_system_prompt(self, brand_profile_md: str, facts: Dict[str, Any]) -> str:
        """Construct the system prompt incorporating voice rules and strict factual boundaries."""
        company_info = facts.get("company")
        allowed_points = facts.get("allowed_talking_points", [])
        strictly_forbidden = facts.get("strictly_forbidden", [])

        allowed_text = "\n".join(f"- {pt}" for pt in allowed_points)
        forbidden_text = "\n".join(f"- {fb}" for fb in strictly_forbidden)

        return (
            "You are an expert LinkedIn post author and personal branding architect for a thoughtful Indian software founder and systems architect.\n\n"
            "### BRAND & VOICE GUIDELINES:\n"
            f"{brand_profile_md}\n\n"
            "### VERIFIED FACTUAL BOUNDARIES (NON-NEGOTIABLE):\n"
            f"Allowed Company Context:\n{json.dumps(company_info, indent=2) if company_info else 'General tech and architecture topic (No company pitch)'}\n\n"
            f"Allowed Talking Points:\n{allowed_text}\n\n"
            f"STRICTLY FORBIDDEN:\n{forbidden_text}\n"
            "- NEVER invent customer names, specific revenue numbers, user counts, funding, fake partnerships, or personal quotes.\n"
            "- NEVER use reveal bridges ('The result?', 'Plot twist:', 'Here\\'s what', 'Let that sink in').\n"
            "- NEVER use negative parallelism ('It\\'s not X, it\\'s Y', 'Stop X, start Y').\n"
            "- NEVER use sincerity announcements ('Let me be honest', 'Honestly?', 'Confession:').\n"
            "- NEVER open with a question. The first line must be a statement, contrarian observation, or number.\n"
            "- Double line breaks between 1-2 sentence paragraphs for mobile readability.\n"
            "- Output strictly valid JSON matching the requested schema."
        )

    def _build_user_prompt(
        self,
        entry: CalendarEntry,
        pillar: ContentPillar,
        research: ResearchResult,
        facts: Dict[str, Any]
    ) -> str:
        """Construct the user prompt for the daily topic."""
        formula_info = FORMULA_DESCRIPTIONS.get(entry.hook_formula, entry.hook_formula)
        angle_info = FOUNDER_ANGLES.get(entry.founder_angle, entry.founder_angle)

        return (
            f"Write a high-quality, thoughtful LinkedIn post for today's scheduled rotation.\n\n"
            f"Content Pillar: {pillar.name} ({pillar.category})\n"
            f"Topic: {entry.topic}\n"
            f"Hook Formula to use: {entry.hook_formula} - {formula_info}\n"
            f"Founder Angle to use: {entry.founder_angle} - {angle_info}\n"
            f"Primary Reaction Goal: {entry.goal}\n\n"
            f"Technical Research & Fact Grounding:\n{research.summary}\n\n"
            "Requirements:\n"
            "1. Length: Target between 900 and 1,300 characters (max 2,000 characters).\n"
            "2. First line: Hook in the first 210 characters. Must be a bold statement or number-first fact. NO QUESTIONS in line 1.\n"
            "3. Structure: 1-2 sentences per paragraph, separated by double newlines.\n"
            "4. Close: End with a meaningful, open-ended discussion question for practitioners.\n"
            "5. Hashtags: At most 0-2 relevant hashtags at the bottom.\n"
            "6. Links: Absolutely zero URLs in the body.\n\n"
            "Respond ONLY with a JSON object with these keys:\n"
            "{\n"
            '  "hook": "The opening 1-2 lines",\n'
            '  "post_text": "The entire formatted post ready to publish",\n'
            '  "closing_question": "The question at the end",\n'
            '  "hashtags": ["#tag1", "#tag2"]\n'
            "}"
        )

    def _repair_draft(
        self,
        original_draft: str,
        audit: AuditResult,
        system_prompt: str,
        entry: CalendarEntry
    ) -> str:
        """Perform a second pass with Groq to correct detected blockers."""
        blocker_descriptions = "\n".join(f"- [{b.rule}]: {b.message} (Found: '{b.offending_text or 'N/A'}')" for b in audit.blockers)

        repair_prompt = (
            f"The draft below was evaluated by our editorial audit and failed with these blockers:\n"
            f"{blocker_descriptions}\n\n"
            f"Original Draft:\n\"\"\"\n{original_draft}\n\"\"\"\n\n"
            f"Rewrite the post to fix ALL listed blockers while preserving the core insight and tone.\n"
            f"- If the hook opened with a question, rewrite it into a strong statement or number-first observation.\n"
            f"- Remove any reveal bridges ('The result?', 'Plot twist:', etc.).\n"
            f"- Remove any negative parallelism ('It\\'s not X, it\\'s Y').\n"
            f"- Ensure length is between 900 and 1,300 characters.\n"
            f"- Ensure 0-2 hashtags at end, and NO links in the body.\n\n"
            f"Return JSON:\n{{\"post_text\": \"The complete rewritten post\"}}"
        )

        try:
            repaired_json = self.groq_client.generate_chat_completion(
                system_prompt=system_prompt,
                user_prompt=repair_prompt,
                temperature=0.3,
                max_tokens=1400,
                response_format={"type": "json_object"}
            )
            parsed = self._parse_json_response(repaired_json)
            return parsed.get("post_text", original_draft)
        except Exception as e:
            logger.error("Draft repair pass encountered an error: %s. Using original draft.", e)
            return original_draft

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Safely parse JSON response from Groq, stripping markdown blocks if present."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: regex search for JSON block
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"Failed to parse valid JSON from Groq response: {text[:200]}")

    def format_outbox_markdown(
        self,
        date_str: str,
        entry: CalendarEntry,
        pillar: ContentPillar,
        post: GeneratedPost,
        research: ResearchResult,
        audit: AuditResult
    ) -> str:
        """Format a rich Markdown document for saving into the GitHub automation_outbox."""
        sources_md = "\n".join(f"- **{s.title}** ({s.publisher or 'Web'}): {s.url or 'N/A'}\n  *Claim:* {s.claim}" for s in research.sources) or "- No external web sources (Evergreen fundamentals)."

        issues_md = ""
        if audit.warnings:
            issues_md = "\n### Audit Warnings (Passed with caveats):\n" + "\n".join(f"- [{w.rule}] {w.message}" for w in audit.warnings)

        return (
            f"# Daily LinkedIn Draft: {date_str}\n\n"
            f"- **Date:** {date_str} (Asia/Kolkata)\n"
            f"- **Day in Schedule:** {entry.day} / 30\n"
            f"- **Pillar:** {pillar.name} ({pillar.id})\n"
            f"- **Topic:** {entry.topic}\n"
            f"- **Hook Formula:** {entry.hook_formula}\n"
            f"- **Founder Angle:** {entry.founder_angle}\n"
            f"- **Target Engagement Goal:** {entry.goal}\n"
            f"- **Character Count:** {post.character_count} chars\n"
            f"- **Content Hash (SHA-256):** `{post.content_hash}`\n"
            f"- **Live Web Search:** {'Yes' if research.is_live_search else 'No (Evergreen Context)'}\n"
            f"{issues_md}\n\n"
            f"## Research Grounding\n"
            f"{research.summary}\n\n"
            f"### Sources Consulted:\n"
            f"{sources_md}\n\n"
            f"---\n\n"
            f"## Post Content\n\n"
            f"```text\n"
            f"{post.text}\n"
            f"```\n"
        )
