"""Deterministic fallback report builder."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import AnalyzeResponse


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _driver_rows(analyze_result: AnalyzeResponse) -> list[dict[str, str]]:
    top_drivers = [item for item in analyze_result.score.top_drivers if isinstance(item, str) and item.strip()]
    if top_drivers:
        return [
            {
                "title": f"Driver {index + 1}",
                "detail": (
                    f"{driver}. This is a deterministic proximity or density signal and is not a contamination finding."
                ),
            }
            for index, driver in enumerate(top_drivers[:3])
        ]

    breakdown = analyze_result.score.breakdown
    fallback_candidates: list[tuple[str, float]] = [
        ("Landfill proximity", float(breakdown.landfill_proximity)),
        ("Military base proximity", float(breakdown.military_proximity)),
        ("Industrial density", float(breakdown.industrial_density)),
        ("Superfund proximity", float(breakdown.superfund_proximity)),
    ]
    fallback_candidates.sort(key=lambda row: row[1], reverse=True)

    rows = [
        {
            "title": label,
            "detail": f"Contributes {points:.1f} deterministic score points at this location.",
        }
        for label, points in fallback_candidates
        if points > 0
    ]
    if rows:
        return rows[:3]

    return [
        {
            "title": "No major drivers",
            "detail": "Configured proximity and density signals are low at this point.",
        }
    ]


def _site_type_context(analyze_result: AnalyzeResponse) -> list[dict[str, str]]:
    breakdown = analyze_result.score.breakdown
    rows: list[dict[str, str]] = []

    include_landfill = bool(analyze_result.evidence.landfill) or float(breakdown.landfill_proximity) > 0
    include_military = bool(analyze_result.evidence.military_base) or float(breakdown.military_proximity) > 0
    include_industrial = bool(analyze_result.evidence.industrial_frs) or float(breakdown.industrial_density) > 0
    include_superfund = bool(analyze_result.evidence.superfund_npl) or float(breakdown.superfund_proximity) > 0

    if include_landfill:
        rows.append(
            {
                "site_type": "Landfills",
                "what_it_can_indicate": "Proximity can indicate potential environmental burden context for follow-up.",
            }
        )
    if include_military:
        rows.append(
            {
                "site_type": "Military Bases",
                "what_it_can_indicate": (
                    "Nearby installations may reflect historical industrial activity context in the surrounding area."
                ),
            }
        )
    if include_industrial:
        rows.append(
            {
                "site_type": "Industrial Facilities",
                "what_it_can_indicate": (
                    "Higher facility density can indicate elevated exposure-proxy context, not measured contamination."
                ),
            }
        )
    if include_superfund:
        rows.append(
            {
                "site_type": "Superfund NPL Sites",
                "what_it_can_indicate": "Nearby NPL listings can indicate known remediation history nearby.",
            }
        )

    return rows


def _driver_strings(analyze_result: AnalyzeResponse) -> list[str]:
    rows = _driver_rows(analyze_result)
    return [row["detail"] for row in rows if isinstance(row.get("detail"), str) and row["detail"].strip()]


def _site_context_text(analyze_result: AnalyzeResponse) -> str:
    contexts = _site_type_context(analyze_result)
    if not contexts:
        return (
            "Nearby configured site categories are sparse at this location. "
            "This remains a screening-only proximity signal."
        )
    labels = ", ".join(item["site_type"] for item in contexts[:4])
    return (
        f"Nearby categories contributing context include: {labels}. "
        "This tool is proximity-based and does not detect contamination."
    )


def _build_deterministic_explanation(
    analyze_result: AnalyzeResponse,
    confidence: tuple[str, str],
) -> dict[str, Any]:
    confidence_level, confidence_rationale = confidence
    return {
        "summary": (
            f"Terris assigned a deterministic screening score of {analyze_result.score.total:.2f}/10 "
            f"({analyze_result.score.band}) using fixed proximity and density rules. "
            "This is a screening signal and does not detect contamination."
        ),
        "top_drivers": _driver_strings(analyze_result),
        "site_context": _site_context_text(analyze_result),
        "recommended_next_steps": [
            "Review EPA ECHO and state environmental records for nearby listed facilities.",
            "Check EPA Superfund pages for site status and remediation updates.",
            "Use local monitoring data or certified lab testing for location-specific confirmation.",
        ],
        "confidence": (
            f"{confidence_level}: {confidence_rationale} "
            "Confidence describes signal coverage and agreement, not contamination certainty."
        ),
        "limitations": (
            "This method uses proximity and density proxies only; it does not measure contaminants, "
            "exposure dose, health outcomes, or legal compliance."
        ),
    }


def build_fallback_report(
    analyze_result: AnalyzeResponse,
    confidence: tuple[str, str],
    note: str,
    *,
    cached: bool = False,
    cache_key: str = "",
) -> dict[str, Any]:
    """Build a safe deterministic report response."""
    confidence_level, confidence_rationale = confidence
    explanation = _build_deterministic_explanation(analyze_result, confidence)

    return {
        "summary": explanation["summary"],
        "top_drivers_explained": _driver_rows(analyze_result),
        "site_type_context": _site_type_context(analyze_result),
        "recommended_next_steps": [
            {
                "action": explanation["recommended_next_steps"][0],
                "why": "Official records provide current compliance and permit context for listed sites.",
            },
            {
                "action": explanation["recommended_next_steps"][1],
                "why": "Superfund pages summarize site history, status, and remediation milestones.",
            },
            {
                "action": explanation["recommended_next_steps"][2],
                "why": "Measured local data is the best way to confirm site-specific water quality conditions.",
            },
        ],
        "limitations": [
            explanation["limitations"],
            "Distance and density proxies should be interpreted with official records and local testing.",
            "Confidence reflects signal coverage and agreement, not clinical or legal conclusions.",
        ],
        "confidence": {
            "level": confidence_level,
            "rationale": confidence_rationale,
        },
        "meta": {
            "ai_used": False,
            "ai_fallback": False,
            "cached": cached,
            "cache_key": cache_key,
            "model": None,
            "generated_at": _now_iso_utc(),
            "note": note,
        },
    }
