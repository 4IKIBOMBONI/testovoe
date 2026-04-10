"""Main analysis pipeline: orchestrates the full flow for one application."""

from __future__ import annotations

import logging
from typing import Any

from .config import Config
from .data_extractor import extract_application_context, get_project_id
from .json_parser import extract_json_from_response
from .llm_client import LLMClient
from .prompts import PR_CALENDAR_PROMPT, STRATEGIC_BRIEF_PROMPT
from .quality_layer import run_quality_check
from .validators import (
    validate_brief_opportunities,
    validate_calendar_events,
)

logger = logging.getLogger(__name__)


def process_application(
    app: dict[str, Any],
    llm: LLMClient,
    config: Config,
) -> dict[str, Any]:
    """Process a single grant application through the full pipeline.

    Returns a dict with:
    - project_id
    - project_name
    - calendar_events: assessed list
    - brief_opportunities: assessed list
    - validation_errors: any items that failed validation
    - status: "success" | "partial" | "error"
    - error: error message if status == "error"
    """
    project_id = get_project_id(app)
    project_name = app.get("project_name", project_id)
    logger.info("Processing application: %s", project_id)

    result: dict[str, Any] = {
        "project_id": project_id,
        "project_name": project_name,
        "calendar_events": [],
        "brief_opportunities": [],
        "validation_errors": [],
        "status": "success",
        "error": None,
    }

    # Step 1: Extract context
    context = extract_application_context(app)
    logger.info("Extracted context for %s (%d chars)", project_id, len(context))

    # Step 2: PR Calendar
    calendar_ok = _run_calendar_analysis(context, project_id, llm, config, result)

    # Step 3: Strategic Brief
    brief_ok = _run_brief_analysis(context, project_id, llm, config, result)

    if not calendar_ok and not brief_ok:
        result["status"] = "error"
    elif not calendar_ok or not brief_ok:
        result["status"] = "partial"

    return result


def _run_calendar_analysis(
    context: str,
    project_id: str,
    llm: LLMClient,
    config: Config,
    result: dict[str, Any],
) -> bool:
    """Run PR calendar analysis. Returns True on success."""
    try:
        prompt = PR_CALENDAR_PROMPT.format(context=context)
        raw_response = llm.call(prompt)
        raw_items = extract_json_from_response(raw_response)
        valid_events, invalid = validate_calendar_events(raw_items)

        if invalid:
            result["validation_errors"].extend(
                {"type": "calendar", "project_id": project_id, **err} for err in invalid
            )
            logger.warning(
                "%s: %d calendar items failed validation", project_id, len(invalid)
            )

        # Quality check (uses both calendar and brief, but brief may be empty here)
        assessed_cal, _ = run_quality_check(valid_events, [], config)

        # Tag with project_id
        for rec in assessed_cal:
            rec["project_id"] = project_id

        result["calendar_events"] = assessed_cal
        accepted = sum(1 for r in assessed_cal if r["quality_status"] == "accepted")
        logger.info(
            "%s: %d calendar events (%d accepted, %d review, %d rejected)",
            project_id,
            len(assessed_cal),
            accepted,
            sum(1 for r in assessed_cal if r["quality_status"] == "review"),
            sum(1 for r in assessed_cal if r["quality_status"] == "rejected"),
        )
        return True

    except Exception as e:
        logger.error("%s: Calendar analysis failed — %s", project_id, e)
        result["error"] = f"Calendar: {e}"
        return False


def _run_brief_analysis(
    context: str,
    project_id: str,
    llm: LLMClient,
    config: Config,
    result: dict[str, Any],
) -> bool:
    """Run strategic brief analysis. Returns True on success."""
    try:
        prompt = STRATEGIC_BRIEF_PROMPT.format(context=context)
        raw_response = llm.call(prompt)
        raw_items = extract_json_from_response(raw_response)
        valid_opps, invalid = validate_brief_opportunities(raw_items)

        if invalid:
            result["validation_errors"].extend(
                {"type": "brief", "project_id": project_id, **err} for err in invalid
            )
            logger.warning(
                "%s: %d brief items failed validation", project_id, len(invalid)
            )

        # Quality check
        _, assessed_brief = run_quality_check([], valid_opps, config)

        for rec in assessed_brief:
            rec["project_id"] = project_id

        result["brief_opportunities"] = assessed_brief
        accepted = sum(1 for r in assessed_brief if r["quality_status"] == "accepted")
        logger.info(
            "%s: %d brief opportunities (%d accepted, %d review)",
            project_id,
            len(assessed_brief),
            accepted,
            sum(1 for r in assessed_brief if r["quality_status"] == "review"),
        )
        return True

    except Exception as e:
        logger.error("%s: Brief analysis failed — %s", project_id, e)
        err_msg = f"Brief: {e}"
        result["error"] = (
            f"{result['error']}; {err_msg}" if result.get("error") else err_msg
        )
        return False
