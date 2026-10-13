"""Editorial auditing, humanizer heuristics, and safety verification."""

import re
from typing import Dict, List, Optional, Tuple
from app.models import AuditIssue, AuditResult

# ------------------------------------------------------------------------------
# 1. Forensic Leakage Patterns (Strictly Forbidden - Automatic Blocker)
# ------------------------------------------------------------------------------
FORENSIC_PATTERNS = [
    (r"\boaicite\b", "ChatGPT citation token leakage (oaicite)"),
    (r"\bcontentReference\b", "Model internal content reference token"),
    (r"\bturn\d+search\d+\b", "Search tool internal iteration token"),
    (r"\battached_file\b", "Internal file attachment marker"),
    (r"\bgrok_card\b", "Model card metadata leakage"),
    (r"\boai_citation\b", "OpenAI citation artifact"),
    (r"\[Your Name\]|\[Your Company\]|\[Insert [^]]+\]|\[Describe [^]]+\]", "Unfilled bracket template / placeholder"),
    (r"As of my (last update|knowledge cutoff|training cutoff)", "Knowledge cutoff disclaimer"),
    (r"I cannot provide (real-time|current|up-to-date)", "Model capability disclaimer"),
]

# ------------------------------------------------------------------------------
# 2. Strict AI Tells & Reveal Bridges (Blocker if present)
# ------------------------------------------------------------------------------
REVEAL_BRIDGES = [
    (r"\bThe result\?", "Cliche reveal bridge ('The result?')"),
    (r"\bPlot twist:", "Cliche reveal bridge ('Plot twist:')"),
    (r"\bHere's the kicker:", "Cliche reveal bridge ('Here's the kicker:')"),
    (r"\bLet that sink in\b", "Cliche reveal bridge ('Let that sink in')"),
    (r"\bThat's the real story\b", "Cliche reveal bridge ('That's the real story')"),
    (r"\bDoing the heavy lifting\b", "Overused AI idiom ('Doing the heavy lifting')"),
    (r"\bBuilt different\b", "Overused AI slang ('Built different')"),
    (r"\bHere's what nobody tells you\b", "Curiosity-gap AI tell ('Here's what nobody tells you')"),
]

SINCERITY_ANNOUNCEMENTS = [
    (r"\bLet me be honest\b", "False vulnerability marker ('Let me be honest')"),
    (r"\bI'll be real\b", "False vulnerability marker ('I'll be real')"),
    (r"\bHonestly\?", "False vulnerability marker ('Honestly?')"),
    (r"\bTo be direct\b", "False vulnerability marker ('To be direct')"),
    (r"\bConfession:\b", "Manufactured confession marker ('Confession:')"),
    (r"\bCan I be vulnerable for a second\b", "False vulnerability marker ('Can I be vulnerable...')"),
]

NEGATIVE_PARALLELISM = [
    (r"\bIt's not (?:just )?[^,.\n]+,\s*it's\b", "Negative parallelism ('It's not X, it's Y')"),
    (r"\bStop (?:doing )?[^,.\n]+,\s*start\b", "Negative parallelism ('Stop X, start Y')"),
]

# ------------------------------------------------------------------------------
# 3. AI Vocabulary Density Scoring
# ------------------------------------------------------------------------------
AI_VOCAB_LIST = [
    "delve", "tapestry", "realm", "foster", "leverage", "harness", "robust",
    "revolutionize", "game-changer", "pivotal", "paramount", "multifaceted",
    "holistic", "landscape", "synergy", "supercharge", "nuanced", "streamline",
    "elevate", "seamless", "testament", "beacon"
]


def scrub_em_dashes(text: str) -> str:
    """
    Cap em dashes at approximately 1 per 100 words (max 2 per post).
    Replace excess em dashes with commas or colons. Never split with a period.
    Also normalizes double hyphens ('--') to commas.
    """
    words = len(text.split())
    cap = max(1, min(2, round(words / 100)))

    # Replace double hyphens first
    scrubbed = text.replace(" -- ", ", ").replace("--", ", ")

    em_dashes = [m.start() for m in re.finditer(r"—", scrubbed)]
    if len(em_dashes) > cap:
        # Keep the first 'cap' occurrences, replace subsequent ones with commas
        chars = list(scrubbed)
        for idx in em_dashes[cap:]:
            chars[idx] = ","
        scrubbed = "".join(chars)

    return scrubbed


def scrub_formatting(text: str) -> str:
    """Normalize formatting, double spaces, and em dashes."""
    text = scrub_em_dashes(text)
    # Normalize multiple blank lines to double newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace on lines
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def check_vocabulary_density(paragraph: str) -> List[str]:
    """Return all AI vocabulary hits within a single paragraph."""
    hits = []
    p_lower = paragraph.lower()
    for word in AI_VOCAB_LIST:
        if re.search(rf"\b{re.escape(word)}\b", p_lower):
            hits.append(word)
    return hits


def audit_post(text: str, max_characters: int = 2200) -> AuditResult:
    """
    Comprehensive editorial and safety audit of a LinkedIn post draft.
    Evaluates forensic leakage, reveal bridges, hook quality, length,
    links, hashtags, and vocabulary density.
    """
    blockers: List[AuditIssue] = []
    warnings: List[AuditIssue] = []

    clean_text = text.strip()
    char_count = len(clean_text)

    # 1. Forensic tier check
    for pattern, reason in FORENSIC_PATTERNS:
        matches = re.findall(pattern, clean_text, flags=re.IGNORECASE)
        if matches:
            blockers.append(AuditIssue(
                severity="BLOCKER",
                rule="forensic_leakage",
                message=f"Model leakage detected: {reason}",
                offending_text=matches[0]
            ))

    # 2. Strict reveal bridges & sincerity announcements
    for pattern, reason in REVEAL_BRIDGES:
        matches = re.findall(pattern, clean_text, flags=re.IGNORECASE)
        if matches:
            blockers.append(AuditIssue(
                severity="BLOCKER",
                rule="reveal_bridge",
                message=reason,
                offending_text=matches[0]
            ))

    for pattern, reason in SINCERITY_ANNOUNCEMENTS:
        matches = re.findall(pattern, clean_text, flags=re.IGNORECASE)
        if matches:
            blockers.append(AuditIssue(
                severity="BLOCKER",
                rule="sincerity_announcement",
                message=reason,
                offending_text=matches[0]
            ))

    for pattern, reason in NEGATIVE_PARALLELISM:
        matches = re.findall(pattern, clean_text, flags=re.IGNORECASE)
        if matches:
            warnings.append(AuditIssue(
                severity="WARNING",
                rule="negative_parallelism",
                message=reason,
                offending_text=matches[0]
            ))

    # 3. Hook rules (first 210 characters / first line)
    lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
    if lines:
        first_line = lines[0]
        # Rule: Never open with a question (-34% engagement penalty)
        if first_line.endswith("?") or re.match(r"^(have you ever|why do|what if|is it time|are you)\b", first_line, re.IGNORECASE):
            blockers.append(AuditIssue(
                severity="BLOCKER",
                rule="hook_question_opener",
                message="Post opens with a question. Never open with a question (move questions to the close).",
                offending_text=first_line
            ))

        # Rule: Never open with all-caps shouting
        if len(first_line) > 15 and first_line.isupper():
            blockers.append(AuditIssue(
                severity="BLOCKER",
                rule="hook_all_caps",
                message="First line is in all-caps shouting.",
                offending_text=first_line
            ))

    # 4. Length checks
    if char_count < 300:
        blockers.append(AuditIssue(
            severity="BLOCKER",
            rule="length_under_minimum",
            message=f"Post is too short ({char_count} chars). Minimum recommended length is 300 characters."
        ))
    elif char_count > max_characters:
        blockers.append(AuditIssue(
            severity="BLOCKER",
            rule="length_exceeds_maximum",
            message=f"Post exceeds configured maximum ({char_count} > {max_characters} chars)."
        ))
    elif char_count < 700 or char_count > 1600:
        warnings.append(AuditIssue(
            severity="WARNING",
            rule="length_outside_sweet_spot",
            message=f"Post length ({char_count} chars) is outside the 900-1300 sweet spot, but within valid bounds."
        ))

    # 5. External links check
    if re.search(r"https?://[^\s]+", clean_text):
        blockers.append(AuditIssue(
            severity="BLOCKER",
            rule="external_link_in_body",
            message="External URL detected in post body. Move all links to the first comment to avoid algorithm penalty."
        ))

    # 6. Hashtags count check
    hashtags = re.findall(r"#\w+", clean_text)
    if len(hashtags) > 3:
        warnings.append(AuditIssue(
            severity="WARNING",
            rule="excessive_hashtags",
            message=f"Too many hashtags detected ({len(hashtags)} > 2). Keep hashtags to at most 0-2 at the end."
        ))

    # 7. Vocabulary density per paragraph
    paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
    for idx, p in enumerate(paragraphs):
        hits = check_vocabulary_density(p)
        if len(hits) >= 3:
            blockers.append(AuditIssue(
                severity="BLOCKER",
                rule="ai_vocab_density",
                message=f"Paragraph {idx + 1} has excessive AI vocabulary markers (count: {len(hits)}: {', '.join(hits)}).",
                offending_text=p[:100] + "..."
            ))
        elif len(hits) == 2:
            warnings.append(AuditIssue(
                severity="WARNING",
                rule="ai_vocab_density_warning",
                message=f"Paragraph {idx + 1} has 2 AI vocabulary markers ({', '.join(hits)}). Consider simplifying."
            ))

    # Apply automated safe scrubbing
    scrubbed = scrub_formatting(clean_text)

    return AuditResult(
        passed=(len(blockers) == 0),
        blockers=blockers,
        warnings=warnings,
        original_text=clean_text,
        scrubbed_text=scrubbed,
        character_count=len(scrubbed)
    )
