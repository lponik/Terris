"""Deterministic risk scoring logic for the analyze endpoint."""

from __future__ import annotations

from typing import Any



def _points_from_distance(distance_miles: float | None, thresholds: list[tuple[float, float]]) -> float:
    if distance_miles is None:
        return 0.0
    for distance_threshold, points in thresholds:
        if distance_miles < distance_threshold:
            return points
    return 0.0



def _industrial_points_1mi(count: int) -> float:
    if count >= 25:
        return 2.0
    if count >= 10:
        return 1.5
    if count >= 1:
        return 1.0
    return 0.0



def _industrial_points_3mi(count: int) -> float:
    if count >= 200:
        return 2.0
    if count >= 75:
        return 1.5
    if count >= 10:
        return 1.0
    return 0.0



def _industrial_points_10mi(count: int) -> float:
    if count >= 1500:
        return 1.5
    if count >= 600:
        return 1.0
    if count >= 200:
        return 0.5
    return 0.0



def _industrial_proximity_points(distance_miles: float | None) -> float:
    if distance_miles is None:
        return 0.0
    if distance_miles < 0.5:
        return 1.0
    if distance_miles < 1.5:
        return 0.5
    return 0.0



def _band_from_total(total: float) -> str:
    if total <= 3.3:
        return "Low"
    if total <= 6.6:
        return "Moderate"
    return "High"



def _build_top_drivers(
    landfill_points: float,
    military_points: float,
    industrial_points: float,
    superfund_points: float,
    nearest_landfill_miles: float | None,
    nearest_military_miles: float | None,
    nearest_superfund_miles: float | None,
    industrial_count_1mi: int,
    industrial_count_3mi: int,
    industrial_count_10mi: int,
    nearest_industrial_miles: float | None,
) -> list[str]:
    driver_rows: list[tuple[float, str]] = []

    if landfill_points > 0.0:
        distance = "unknown"
        if nearest_landfill_miles is not None:
            distance = f"{nearest_landfill_miles:.2f} mi"
        driver_rows.append(
            (landfill_points, f"Landfill proximity: nearest landfill at {distance} ({landfill_points:.1f} pts)")
        )

    if military_points > 0.0:
        distance = "unknown"
        if nearest_military_miles is not None:
            distance = f"{nearest_military_miles:.2f} mi"
        driver_rows.append(
            (military_points, f"Military base proximity: nearest base at {distance} ({military_points:.1f} pts)")
        )

    if industrial_points > 0.0:
        distance_text = ""
        if nearest_industrial_miles is not None:
            distance_text = f"; nearest industrial at {nearest_industrial_miles:.2f} mi"
        driver_rows.append(
            (
                industrial_points,
                (
                    "Industrial density: "
                    f"{industrial_count_1mi} sites within 1 mi, "
                    f"{industrial_count_3mi} within 3 mi, "
                    f"{industrial_count_10mi} within 10 mi"
                    f"{distance_text} "
                    f"({industrial_points:.1f} pts)"
                ),
            )
        )

    if superfund_points > 0.0:
        distance = "unknown"
        if nearest_superfund_miles is not None:
            distance = f"{nearest_superfund_miles:.2f} mi"
        driver_rows.append(
            (
                superfund_points,
                f"Superfund proximity: nearest NPL site at {distance} ({superfund_points:.1f} pts)",
            )
        )

    if not driver_rows:
        return ["No elevated proximity or industrial density signals in configured radii."]

    driver_rows.sort(key=lambda row: (-row[0], row[1]))
    return [row[1] for row in driver_rows]



def compute_score(signals: dict[str, Any]) -> dict[str, Any]:
    """Compute a deterministic 0-10 risk score from precomputed signals."""
    landfill_distance = signals.get("nearest_landfill_miles")
    military_distance = signals.get("nearest_military_base_miles")
    industrial_count_1mi = int(signals.get("industrial_count_1mi", 0))
    industrial_count_3mi = int(signals.get("industrial_count_3mi", 0))
    industrial_count_10mi = int(signals.get("industrial_count_10mi", 0))
    nearest_industrial_miles = signals.get("nearest_industrial_frs_miles")
    nearest_superfund_miles = signals.get("nearest_superfund_npl_miles")

    landfill_points = _points_from_distance(
        landfill_distance,
        [
            (1.0, 3.0),
            (3.0, 2.0),
            (10.0, 1.0),
        ],
    )

    military_points = _points_from_distance(
        military_distance,
        [
            (1.0, 3.0),
            (5.0, 2.0),
            (15.0, 1.0),
        ],
    )

    industrial_points_raw = (
        _industrial_points_1mi(industrial_count_1mi)
        + _industrial_points_3mi(industrial_count_3mi)
        + _industrial_points_10mi(industrial_count_10mi)
        + _industrial_proximity_points(nearest_industrial_miles)
    )
    industrial_points = min(6.0, industrial_points_raw)

    superfund_points = _points_from_distance(
        nearest_superfund_miles,
        [
            (1.0, 4.0),
            (3.0, 3.0),
            (10.0, 2.0),
            (25.0, 1.0),
        ],
    )

    total_score = landfill_points + military_points + industrial_points + superfund_points
    total_score = max(0.0, min(10.0, total_score))

    band = _band_from_total(total_score)
    top_drivers = _build_top_drivers(
        landfill_points=landfill_points,
        military_points=military_points,
        industrial_points=industrial_points,
        superfund_points=superfund_points,
        nearest_landfill_miles=landfill_distance,
        nearest_military_miles=military_distance,
        nearest_superfund_miles=nearest_superfund_miles,
        industrial_count_1mi=industrial_count_1mi,
        industrial_count_3mi=industrial_count_3mi,
        industrial_count_10mi=industrial_count_10mi,
        nearest_industrial_miles=nearest_industrial_miles,
    )

    meta: dict[str, Any] = {}
    existing_meta = signals.get("meta")
    if isinstance(existing_meta, dict):
        meta.update(existing_meta)
    meta["scoring_version"] = "v2"

    return {
        "total": round(total_score, 2),
        "breakdown": {
            "landfill_proximity": round(landfill_points, 2),
            "military_proximity": round(military_points, 2),
            "industrial_density": round(industrial_points, 2),
            "superfund_proximity": round(superfund_points, 2),
        },
        "band": band,
        "top_drivers": top_drivers,
        "meta": meta,
    }
