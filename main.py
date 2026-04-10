#!/usr/bin/env python3
"""Grant Application PR Analysis Pipeline.

Reads JSON grant applications, analyzes them via LLM API,
and produces a PR calendar + strategic PR brief (JSON + Excel).

Usage:
    python main.py                           # uses defaults from config / env
    python main.py --input data/apps.json    # custom input file
    python main.py --output results          # custom output directory
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from src.config import Config
from src.demo import run_demo_pipeline
from src.llm_client import LLMClient
from src.output_generator import save_excel, save_json
from src.pipeline import process_application

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def load_applications(path: str) -> list[dict[str, Any]]:
    """Load applications from a JSON file.

    Supports both a JSON array of applications and a single application object.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Could be a single application or a wrapper with a list inside
        # Try common wrapper keys
        for key in ("applications", "items", "data", "projects"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Treat as single application
        return [data]

    raise ValueError(f"Unexpected JSON structure in {path}: expected list or dict")


def run(config: Config, demo: bool = False) -> None:
    """Run the full pipeline."""
    logger.info("Loading applications from %s", config.input_path)
    applications = load_applications(config.input_path)
    logger.info("Loaded %d application(s)", len(applications))

    if demo:
        logger.info("Running in DEMO mode (no LLM API calls)")
        run_demo_pipeline(applications, config)
        return

    if not config.api_key:
        logger.error(
            "API key not set. Set ANTHROPIC_API_KEY environment variable "
            "or use --demo for demo mode."
        )
        sys.exit(1)

    llm = LLMClient(config)

    all_results: list[dict[str, Any]] = []
    all_calendar: list[dict[str, Any]] = []
    all_brief: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for i, app in enumerate(applications, 1):
        project_id = app.get("id") or app.get("project_name", f"app_{i}")
        logger.info("=" * 60)
        logger.info("Processing %d/%d: %s", i, len(applications), project_id)

        try:
            result = process_application(app, llm, config)
            all_results.append(result)
            all_calendar.extend(result["calendar_events"])
            all_brief.extend(result["brief_opportunities"])

            if result["status"] == "error":
                errors.append({"project_id": project_id, "error": result["error"]})

        except Exception as e:
            logger.error("FATAL error processing %s: %s", project_id, e, exc_info=True)
            errors.append({"project_id": project_id, "error": str(e)})
            # Continue with next application
            continue

    # Summary
    logger.info("=" * 60)
    logger.info("Pipeline complete:")
    logger.info("  Applications processed: %d", len(all_results))
    logger.info("  Calendar events: %d", len(all_calendar))
    logger.info("  Brief opportunities: %d", len(all_brief))
    logger.info("  Errors: %d", len(errors))

    cal_accepted = [r for r in all_calendar if r.get("quality_status") == "accepted"]
    cal_review = [r for r in all_calendar if r.get("quality_status") == "review"]
    cal_rejected = [r for r in all_calendar if r.get("quality_status") == "rejected"]
    logger.info(
        "  Calendar breakdown: %d accepted, %d review, %d rejected",
        len(cal_accepted), len(cal_review), len(cal_rejected),
    )

    # Save outputs
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Full JSON output
    output_data = {
        "summary": {
            "total_applications": len(applications),
            "processed": len(all_results),
            "errors": len(errors),
            "calendar_events_total": len(all_calendar),
            "calendar_accepted": len(cal_accepted),
            "calendar_review": len(cal_review),
            "calendar_rejected": len(cal_rejected),
            "brief_opportunities_total": len(all_brief),
        },
        "calendar": all_calendar,
        "brief": all_brief,
        "per_project": [
            {
                "project_id": r["project_id"],
                "project_name": r["project_name"],
                "status": r["status"],
                "error": r["error"],
                "calendar_events": r["calendar_events"],
                "brief_opportunities": r["brief_opportunities"],
                "validation_errors": r["validation_errors"],
            }
            for r in all_results
        ],
        "errors": errors,
    }

    json_path = str(output_dir / "results.json")
    save_json(output_data, json_path)
    logger.info("JSON saved to %s", json_path)

    excel_path = str(output_dir / "results.xlsx")
    save_excel(all_calendar, all_brief, excel_path)
    logger.info("Excel saved to %s", excel_path)

    if errors:
        logger.warning("Some applications had errors:")
        for err in errors:
            logger.warning("  %s: %s", err["project_id"], err["error"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PR Calendar & Media Potential Analysis for Grant Applications"
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="Path to JSON file with applications (default: data/sample_applications.json)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="LLM model name override",
    )
    parser.add_argument(
        "--min-pr-score",
        type=int,
        default=None,
        help="Minimum PR score threshold (default: 5)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode without LLM API calls (generates sample output)",
    )
    args = parser.parse_args()

    config = Config()
    if args.input:
        config.input_path = args.input
    if args.output:
        config.output_dir = args.output
    if args.model:
        config.model = args.model
    if args.min_pr_score is not None:
        config.min_pr_score = args.min_pr_score

    run(config, demo=args.demo)


if __name__ == "__main__":
    main()
