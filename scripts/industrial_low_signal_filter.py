"""Shared low-signal industrial facility exclusion rules."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

LOW_SIGNAL_NAME_KEYWORDS = [
    "PUBLIC WATER",
    "DRINKING WATER",
    "WASTEWATER",
    "STORMWATER",
    "SEWER",
    "SANITARY",
    "UTILITY",
    "MUNICIPAL",
    "AUTHORITY",
    "TOWNSHIP",
    "BOROUGH",
    "CITY OF",
    "VILLAGE OF",
    "DEPARTMENT OF PUBLIC WORKS",
    "DPW",
    "PUMP STATION",
    "LIFT STATION",
    "TRANSFER STATION",
    "RECYCLING CENTER",
    "RECYCLING FACILITY",
    "MATERIALS RECOVERY FACILITY",
    "WATER",
    "WELL",
]

LOW_SIGNAL_WATER_CONTEXT_KEYWORDS = [
    "WATER",
    "WASTEWATER",
    "SEWER",
    "SANITARY",
    "PUBLIC WATER",
    "DRINKING WATER",
    "STORMWATER",
]

LOW_SIGNAL_PROGRAM_KEYWORDS = [
    "PUBLIC WATER SYSTEM",
    "SDWIS",
]

LOW_SIGNAL_NAICS_PREFIXES = [
    "2213",
    "22131",
    "22132",
    "22133",
]


def _split_codes(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[^A-Za-z0-9]+", value)
    return [part for part in parts if part]


def _has_water_context(name_upper: str) -> bool:
    return any(token in name_upper for token in LOW_SIGNAL_WATER_CONTEXT_KEYWORDS)


def match_low_signal_reason(
    *,
    facility_name: str | None,
    program_values: list[str] | None = None,
    naics_values: list[str] | None = None,
) -> str | None:
    """Return a deterministic reason string when a row is low-signal."""
    for value in program_values or []:
        text = str(value or "").upper()
        if not text:
            continue
        if "PUBLIC WATER SYSTEM" in text:
            return "program:PUBLIC WATER SYSTEM"
        if "SDWIS" in text:
            return "program:SDWIS"
        if re.search(r"\bPWS\b", text):
            return "program:PWS"

    for value in naics_values or []:
        text = str(value or "").strip().upper()
        if not text:
            continue
        for token in _split_codes(text):
            if any(token.startswith(prefix) for prefix in LOW_SIGNAL_NAICS_PREFIXES):
                return "naics:2213*"

    name_upper = str(facility_name or "").upper()
    for keyword in LOW_SIGNAL_NAME_KEYWORDS:
        if keyword in name_upper:
            return f"name:{keyword}"

    # Contextual exclusions: only remove these when water/sewer context is present.
    if "TREATMENT PLANT" in name_upper and _has_water_context(name_upper):
        return "name:TREATMENT PLANT+WATER_CONTEXT"
    if "DISTRIBUTION" in name_upper and _has_water_context(name_upper):
        return "name:DISTRIBUTION+WATER_CONTEXT"

    return None


def build_low_signal_rules() -> dict[str, Any]:
    return {
        "name_keywords": LOW_SIGNAL_NAME_KEYWORDS,
        "contextual_name_rules": {
            "TREATMENT PLANT_requires_any": LOW_SIGNAL_WATER_CONTEXT_KEYWORDS,
            "DISTRIBUTION_requires_any": LOW_SIGNAL_WATER_CONTEXT_KEYWORDS,
        },
        "program_keywords": LOW_SIGNAL_PROGRAM_KEYWORDS + ["PWS"],
        "naics_prefixes": LOW_SIGNAL_NAICS_PREFIXES,
    }


def build_low_signal_audit(
    *,
    method: str,
    removed_low_signal: int,
    removed_examples: list[str],
    enabled: bool,
) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "low_signal_filter_enabled": enabled,
        "removed_low_signal": int(removed_low_signal),
        "removed_examples": removed_examples[:20],
        "rules": build_low_signal_rules(),
    }
