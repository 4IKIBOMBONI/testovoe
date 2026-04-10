"""Extract meaningful blocks from a JSON grant application for LLM analysis."""

from __future__ import annotations

import json
from typing import Any


def extract_application_context(app: dict[str, Any]) -> str:
    """Convert a raw JSON application into a structured text block for LLM."""
    sections: list[str] = []

    # Header
    proj_id = app.get("id", "N/A")
    proj_name = app.get("project_name", "Без названия")
    org = app.get("organization", "")
    region = app.get("region", "")
    direction = app.get("grant_direction", "")
    amount = app.get("requested_amount", "")
    sections.append(
        f"# Проект: {proj_name}\n"
        f"ID: {proj_id} | Организация: {org} | Регион: {region}\n"
        f"Направление: {direction} | Запрашиваемая сумма: {amount}"
    )

    # Description
    desc = app.get("project_description", "")
    if desc:
        sections.append(f"## Описание проекта\n{desc}")

    # Target groups
    groups = app.get("target_groups", [])
    if groups:
        lines = [f"- {g.get('name', '?')}: {g.get('count', '?')} чел." for g in groups]
        sections.append("## Целевые группы\n" + "\n".join(lines))

    # Expected results
    results = app.get("expected_results", [])
    if results:
        lines = [f"- {r}" for r in results]
        sections.append("## Ожидаемые результаты\n" + "\n".join(lines))

    # Calendar plan — the most important block
    plan = app.get("calendar_plan", [])
    if plan:
        lines = []
        for step in plan:
            s = step.get("step", "?")
            title = step.get("title", "")
            start = step.get("start_date", "")
            end = step.get("end_date", "")
            desc_step = step.get("description", "")
            lines.append(f"{s}. {title} ({start} — {end})\n   {desc_step}")
        sections.append("## Календарный план\n" + "\n".join(lines))

    # Team
    team = app.get("team", [])
    if team:
        lines = [
            f"- {m.get('role', '?')}: {m.get('name', '?')} — {m.get('experience', '')}"
            for m in team
        ]
        sections.append("## Команда\n" + "\n".join(lines))

    # Partners
    partners = app.get("partners", [])
    if partners:
        lines = [f"- {p.get('name', '?')} ({p.get('type', '')})" for p in partners]
        sections.append("## Партнёры\n" + "\n".join(lines))

    # Budget
    budget = app.get("budget_summary", {})
    if budget:
        total = budget.get("total", "")
        own = budget.get("own_contribution", "")
        cats = ", ".join(budget.get("categories", []))
        sections.append(
            f"## Бюджет\nОбщий: {total} | Собственный вклад: {own}\n"
            f"Статьи: {cats}"
        )

    # Fallback: dump any other top-level keys not already covered
    known_keys = {
        "id", "project_name", "organization", "region", "grant_direction",
        "requested_amount", "project_description", "target_groups",
        "expected_results", "calendar_plan", "team", "partners", "budget_summary",
    }
    extra = {k: v for k, v in app.items() if k not in known_keys}
    if extra:
        sections.append(
            "## Дополнительные данные\n" + json.dumps(extra, ensure_ascii=False, indent=2)
        )

    return "\n\n".join(sections)


def get_project_id(app: dict[str, Any]) -> str:
    return app.get("id") or app.get("project_name", "unknown")
