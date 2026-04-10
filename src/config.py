"""Pipeline configuration."""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # LLM API settings
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    # Retry settings
    max_retries: int = 3
    retry_base_delay: float = 2.0

    # Quality thresholds
    min_pr_score: int = 5
    required_calendar_fields: list[str] = field(default_factory=lambda: [
        "date", "title", "event_type", "pr_score", "why_it_matters",
    ])
    required_brief_fields: list[str] = field(default_factory=lambda: [
        "title", "category", "media_potential", "timing",
        "effort_level", "media_formats", "recommendation",
    ])
    valid_effort_levels: list[str] = field(default_factory=lambda: [
        "low", "medium", "high",
    ])

    # Paths
    input_path: str = os.getenv("INPUT_PATH", "data/sample_applications.json")
    output_dir: str = os.getenv("OUTPUT_DIR", "output")

    # Internal activity keywords — used for post-LLM filtering
    internal_keywords: list[str] = field(default_factory=lambda: [
        "отчётность", "отчетность", "планёрка", "планерка", "совещание",
        "закупка", "найм", "ремонт", "бухгалтер", "согласование",
        "внутренн", "техническ", "административн", "подготовка отчёт",
        "мониторинг", "сбор команды", "заключение договор",
    ])
