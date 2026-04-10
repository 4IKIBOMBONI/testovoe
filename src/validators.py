"""Pydantic models for validating LLM output structure."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PRCalendarEvent(BaseModel):
    """Single event in the PR calendar."""

    date: str = Field(..., description="Event date in YYYY-MM-DD or similar format")
    title: str = Field(..., min_length=3, description="Short clear headline")
    event_type: str = Field(..., min_length=2, description="Event type")
    pr_score: int = Field(..., ge=1, le=10, description="PR score 1-10")
    why_it_matters: str = Field(..., min_length=5, description="Why this is newsworthy")
    how_to_strengthen: Optional[str] = Field(None, description="How to amplify")
    pr_format: Optional[str] = Field(None, description="Recommended PR format")

    @field_validator("date")
    @classmethod
    def normalize_date(cls, v: str) -> str:
        v = v.strip()
        # Accept dates in common formats, try to keep YYYY-MM-DD
        if not v:
            raise ValueError("Date cannot be empty")
        return v

    @field_validator("pr_score", mode="before")
    @classmethod
    def coerce_pr_score(cls, v):
        if isinstance(v, str):
            v = int(v)
        return v


class PRBriefOpportunity(BaseModel):
    """Single opportunity in the strategic PR brief."""

    title: str = Field(..., min_length=3, description="Short title")
    category: str = Field(..., min_length=2, description="Category")
    media_potential: str = Field(..., min_length=5, description="Why media would be interested")
    timing: str = Field(..., min_length=2, description="When to pitch this story")
    effort_level: str = Field(..., description="low / medium / high")
    media_formats: str = Field(..., min_length=3, description="Suitable formats")
    recommendation: str = Field(..., min_length=5, description="Practical recommendation")

    @field_validator("effort_level")
    @classmethod
    def normalize_effort(cls, v: str) -> str:
        v = v.strip().lower()
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            # try fuzzy match
            for a in allowed:
                if a in v:
                    return a
            raise ValueError(f"effort_level must be one of {allowed}, got '{v}'")
        return v


def validate_calendar_events(raw_items: list[dict]) -> tuple[list[PRCalendarEvent], list[dict]]:
    """Validate a list of raw dicts as PRCalendarEvent.

    Returns (valid_events, invalid_items_with_errors).
    """
    valid, invalid = [], []
    for item in raw_items:
        try:
            event = PRCalendarEvent(**item)
            valid.append(event)
        except Exception as e:
            invalid.append({"item": item, "error": str(e)})
    return valid, invalid


def validate_brief_opportunities(raw_items: list[dict]) -> tuple[list[PRBriefOpportunity], list[dict]]:
    """Validate a list of raw dicts as PRBriefOpportunity.

    Returns (valid_opportunities, invalid_items_with_errors).
    """
    valid, invalid = [], []
    for item in raw_items:
        try:
            opp = PRBriefOpportunity(**item)
            valid.append(opp)
        except Exception as e:
            invalid.append({"item": item, "error": str(e)})
    return valid, invalid
