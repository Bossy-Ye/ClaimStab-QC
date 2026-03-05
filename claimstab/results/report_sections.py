from __future__ import annotations

from typing import Final

REPORT_SECTION_IDS: Final[tuple[str, ...]] = (
    "summary",
    "evidence_chain",
    "device_summary",
    "claim_table",
    "naive_comparison",
    "rq_summary",
    "experiment_summary",
    "delta_sweep",
    "cost_curve",
    "diagnostics",
    "robustness_map",
    "auxiliary_claims",
)


def available_sections_text() -> str:
    return ",".join(REPORT_SECTION_IDS)


def parse_sections_arg(raw: str) -> set[str] | None:
    values = {token.strip() for token in raw.split(",") if token.strip()}
    return values or None


def is_section_enabled(section_id: str, selected: set[str] | None) -> bool:
    return selected is None or section_id in selected
