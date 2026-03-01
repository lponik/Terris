"""Deterministic confidence heuristics for report generation."""

from __future__ import annotations

from .models import AnalyzeResponse


def compute_confidence(analyze_result: AnalyzeResponse) -> tuple[str, str]:
    """Compute a deterministic confidence level and rationale."""
    breakdown = analyze_result.score.breakdown
    signals = analyze_result.signals

    categories_with_points = sum(
        1
        for points in (
            float(breakdown.landfill_proximity),
            float(breakdown.military_proximity),
            float(breakdown.industrial_density),
            float(breakdown.superfund_proximity),
        )
        if points > 0.0
    )

    industrial_density_points = float(breakdown.industrial_density)
    any_nearest_under_1_mi = any(
        distance is not None and distance < 1.0
        for distance in (
            signals.nearest_landfill_miles,
            signals.nearest_military_base_miles,
            signals.nearest_superfund_npl_miles,
        )
    )
    all_counts_zero = all(
        int(value) == 0
        for value in (
            signals.industrial_count_1mi,
            signals.industrial_count_3mi,
            signals.industrial_count_10mi,
            signals.superfund_count_3mi,
        )
    )

    if categories_with_points >= 3 or (any_nearest_under_1_mi and industrial_density_points > 0.0):
        return (
            "High",
            "High confidence because multiple deterministic categories contribute or close proximity and "
            "industrial density signals co-occur.",
        )

    if categories_with_points == 2 or industrial_density_points > 0.0:
        return (
            "Moderate",
            "Moderate confidence because two categories contribute or industrial density adds supporting signal.",
        )

    if categories_with_points <= 1 and all_counts_zero and not any_nearest_under_1_mi:
        return (
            "Low",
            "Low confidence because only limited categories contribute and nearby count/proximity signals are sparse.",
        )

    return (
        "Low",
        "Low confidence because deterministic signals are limited for this location.",
    )
