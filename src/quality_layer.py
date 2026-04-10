"""Quality layer: structure check, reliability check, status marking.

Each record gets:
- quality_status: "accepted" | "review" | "rejected"
- quality_comment: human-readable explanation
- quality_flags: list of specific issues found
"""

from __future__ import annotations

import re
from typing import Any

from .config import Config
from .validators import PRBriefOpportunity, PRCalendarEvent

# Phrases that indicate vague/generic LLM output
VAGUE_PHRASES = [
    "широкая аудитория",
    "может быть интересно",
    "возможно привлечёт внимание",
    "различные мероприятия",
    "важное событие",
    "значимое мероприятие",
]


def assess_calendar_event(
    event: PRCalendarEvent, config: Config
) -> dict[str, Any]:
    """Assess a single PR calendar event and return annotated dict."""
    record = event.model_dump()
    flags: list[str] = []

    # 1. PR score filter
    if event.pr_score < config.min_pr_score:
        flags.append(f"low_pr_score ({event.pr_score} < {config.min_pr_score})")

    # 2. Internal activity keyword check
    combined_text = f"{event.title} {event.why_it_matters}".lower()
    for kw in config.internal_keywords:
        if kw.lower() in combined_text:
            flags.append(f"internal_keyword_match: '{kw}'")
            break

    # 3. Vague description check
    for phrase in VAGUE_PHRASES:
        if phrase in event.why_it_matters.lower():
            flags.append(f"vague_description: '{phrase}'")
            break

    # 4. Title too short or too generic
    if len(event.title) < 10:
        flags.append("title_too_short")

    # 5. Date validation
    if not re.match(r"\d{4}-\d{2}-\d{2}", event.date):
        flags.append("non_standard_date_format")

    # Determine status
    if any("low_pr_score" in f for f in flags):
        status = "rejected"
        comment = f"PR Score ниже порога ({event.pr_score}/{config.min_pr_score})"
    elif any("internal_keyword" in f for f in flags):
        status = "rejected"
        comment = "Обнаружены маркеры внутренней/операционной деятельности"
    elif len(flags) >= 2:
        status = "review"
        comment = "Множественные замечания — требует ручной проверки"
    elif flags:
        status = "review"
        comment = f"Замечание: {flags[0]}"
    else:
        status = "accepted"
        comment = "Прошёл все проверки"

    record["quality_status"] = status
    record["quality_comment"] = comment
    record["quality_flags"] = flags
    return record


def assess_brief_opportunity(
    opp: PRBriefOpportunity, config: Config
) -> dict[str, Any]:
    """Assess a single PR brief opportunity and return annotated dict."""
    record = opp.model_dump()
    flags: list[str] = []

    # 1. Vague media_potential
    for phrase in VAGUE_PHRASES:
        if phrase in opp.media_potential.lower():
            flags.append(f"vague_media_potential: '{phrase}'")
            break

    # 2. Effort level validation (already done by Pydantic, but double-check)
    if opp.effort_level not in config.valid_effort_levels:
        flags.append(f"invalid_effort_level: {opp.effort_level}")

    # 3. Recommendation too short
    if len(opp.recommendation) < 15:
        flags.append("recommendation_too_short")

    # 4. Category check
    if len(opp.category) < 3:
        flags.append("category_too_short")

    # Determine status
    if len(flags) >= 2:
        status = "review"
        comment = "Множественные замечания — требует ручной проверки"
    elif flags:
        status = "review"
        comment = f"Замечание: {flags[0]}"
    else:
        status = "accepted"
        comment = "Прошёл все проверки"

    record["quality_status"] = status
    record["quality_comment"] = comment
    record["quality_flags"] = flags
    return record


def run_quality_check(
    calendar_events: list[PRCalendarEvent],
    brief_opportunities: list[PRBriefOpportunity],
    config: Config,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run full quality assessment on both result sets.

    Returns (assessed_calendar, assessed_brief).
    """
    assessed_cal = [assess_calendar_event(e, config) for e in calendar_events]
    assessed_brief = [assess_brief_opportunity(o, config) for o in brief_opportunities]
    return assessed_cal, assessed_brief
