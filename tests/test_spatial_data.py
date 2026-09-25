from __future__ import annotations

import csv
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.app.config import Settings
from backend.app.data_loader import (
    NEARBY_SITE_LIMIT,
    REQUIRED_COLUMNS,
    load_spatial_data,
)
from backend.app.geo import EARTH_RADIUS_MILES, haversine_distances_miles
from backend.app.main import _build_analyze_response


def _row(
    site_id: str,
    category: str,
    lat: float | str,
    lon: float | str,
) -> dict[str, str]:
    return {
        "id": site_id,
        "name": site_id.replace("_", " ").title(),
        "category": category,
        "lat": str(lat),
        "lon": str(lon),
        "state": "TS",
        "source": "test",
        "metadata_json": "{}",
    }


class SpatialDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.csv_path = Path(self.temp_dir.name) / "sites.csv"

    def _write_rows(
        self,
        rows: list[dict[str, str]],
        fieldnames: tuple[str, ...] = REQUIRED_COLUMNS,
    ) -> None:
        with self.csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _write_proximity_fixture(self) -> None:
        self._write_rows(
            [
                _row("landfill_1", "landfill", 0.0, 0.005),
                _row("landfill_2", "landfill", 0.0, 0.02),
                _row("landfill_3", "landfill", 0.0, 0.08),
                _row("landfill_outside", "landfill", 0.0, 0.2),
                _row("superfund_1", "superfund", 0.01, 0.0),
                _row("superfund_2", "superfund", 0.04, 0.0),
                _row("superfund_3", "superfund", 0.12, 0.0),
                _row("superfund_outside", "superfund", 0.25, 0.0),
            ]
        )

    def test_vectorized_distance_matches_scalar_haversine(self) -> None:
        query_lat, query_lon = 40.7128, -74.0060
        site_lats = np.array([34.0522, 41.8781, 47.6062], dtype=np.float64)
        site_lons = np.array([-118.2437, -87.6298, -122.3321], dtype=np.float64)
        site_lats_radians = np.radians(site_lats)

        actual = haversine_distances_miles(
            query_lat=query_lat,
            query_lon=query_lon,
            site_lats_radians=site_lats_radians,
            site_lons_radians=np.radians(site_lons),
            site_cos_lats=np.cos(site_lats_radians),
        )

        expected = [
            self._scalar_haversine(query_lat, query_lon, lat, lon)
            for lat, lon in zip(site_lats, site_lons, strict=True)
        ]
        np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-9)

    def test_proximity_analysis_reuses_distances_for_nearest_counts_and_sorting(self) -> None:
        self._write_proximity_fixture()
        result = load_spatial_data(str(self.csv_path)).analyze_point(0.0, 0.0)

        self.assertEqual(result.nearest_mapped_site["id"], "landfill_1")
        self.assertEqual(
            result.nearest_by_category["landfill"]["id"],
            "landfill_1",
        )
        self.assertEqual(
            result.nearest_by_category["superfund"]["id"],
            "superfund_1",
        )
        self.assertEqual(
            result.counts_within_miles["landfill"],
            {1.0: 1, 5.0: 2, 10.0: 3},
        )
        self.assertEqual(
            result.counts_within_miles["superfund"],
            {1.0: 1, 5.0: 2, 10.0: 3},
        )
        self.assertEqual(
            [site["id"] for site in result.nearby_sites],
            [
                "landfill_1",
                "superfund_1",
                "landfill_2",
                "superfund_2",
            ],
        )
        distances = [site["distance_miles"] for site in result.nearby_sites]
        self.assertEqual(distances, sorted(distances))

    def test_no_sites_within_display_radius_keeps_nearest_results(self) -> None:
        self._write_rows(
            [
                _row("landfill_far", "landfill", 0.0, 1.0),
                _row("superfund_far", "superfund", 1.0, 0.0),
            ]
        )

        result = load_spatial_data(str(self.csv_path)).analyze_point(0.0, 0.0)

        self.assertEqual(result.nearby_sites, [])
        self.assertEqual(
            result.counts_within_miles["landfill"],
            {1.0: 0, 5.0: 0, 10.0: 0},
        )
        self.assertEqual(
            result.counts_within_miles["superfund"],
            {1.0: 0, 5.0: 0, 10.0: 0},
        )
        self.assertEqual(result.nearest_by_category["landfill"]["id"], "landfill_far")
        self.assertEqual(
            result.nearest_by_category["superfund"]["id"],
            "superfund_far",
        )

    def test_nearby_results_are_bounded(self) -> None:
        rows = [
            _row(f"landfill_{index:02d}", "landfill", 0.0, index * 0.001)
            for index in range(1, 26)
        ]
        rows.append(_row("superfund_1", "superfund", 0.03, 0.0))
        self._write_rows(rows)

        result = load_spatial_data(str(self.csv_path)).analyze_point(0.0, 0.0)

        self.assertEqual(len(result.nearby_sites), NEARBY_SITE_LIMIT)
        self.assertEqual(result.nearby_sites[0]["id"], "landfill_01")

    def test_api_response_contains_proximity_contract_without_score(self) -> None:
        self._write_proximity_fixture()
        store = load_spatial_data(str(self.csv_path))

        response = _build_analyze_response(
            store,
            Settings(data_path=str(self.csv_path)),
            0.0,
            0.0,
        )
        payload = response.model_dump(mode="json")

        self.assertNotIn("score", payload)
        self.assertNotIn("signals", payload)
        self.assertEqual(payload["nearest_by_category"]["landfill"]["id"], "landfill_1")
        self.assertEqual(
            payload["nearest_by_category"]["superfund"]["id"],
            "superfund_1",
        )
        self.assertEqual(
            payload["counts_within_miles"]["landfill"],
            {"within_1_mile": 1, "within_5_miles": 2, "within_10_miles": 3},
        )
        self.assertEqual(payload["nearby_sites"][0]["category"], "landfill")
        self.assertEqual(payload["meta"]["nearby_radius_miles"], 5.0)
        self.assertTrue(
            all(site["distance_miles"] <= 5.0 for site in payload["nearby_sites"])
        )
        self.assertNotIn("military_base", str(payload))

    def test_loader_drops_invalid_coordinates(self) -> None:
        self._write_rows(
            [
                _row("landfill_valid", "landfill", 10.0, 10.0),
                _row("landfill_nan", "landfill", "nan", 10.0),
                _row("landfill_range", "landfill", 91.0, 10.0),
                _row("superfund_valid", "superfund", 30.0, 30.0),
            ]
        )

        store = load_spatial_data(str(self.csv_path))

        self.assertEqual(store.category_counts, {"landfill": 1, "superfund": 1})

    def test_loader_rejects_military_and_unknown_categories(self) -> None:
        self._write_rows(
            [
                _row("landfill", "landfill", 10.0, 10.0),
                _row("superfund", "superfund", 30.0, 30.0),
                _row("military", "military_base", 20.0, 20.0),
                _row("unknown", "industrial_frs", 40.0, 40.0),
            ]
        )

        with self.assertRaisesRegex(ValueError, "Unexpected categories"):
            load_spatial_data(str(self.csv_path))

    def test_loader_rejects_missing_columns(self) -> None:
        fieldnames = tuple(column for column in REQUIRED_COLUMNS if column != "source")
        self._write_rows([], fieldnames=fieldnames)

        with self.assertRaisesRegex(ValueError, "Dataset missing required columns"):
            load_spatial_data(str(self.csv_path))

    @staticmethod
    def _scalar_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat1_radians = math.radians(lat1)
        lat2_radians = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        haversine = (
            math.sin(delta_lat / 2.0) ** 2
            + math.cos(lat1_radians)
            * math.cos(lat2_radians)
            * math.sin(delta_lon / 2.0) ** 2
        )
        angular_distance = 2.0 * math.atan2(
            math.sqrt(haversine),
            math.sqrt(1.0 - haversine),
        )
        return EARTH_RADIUS_MILES * angular_distance


if __name__ == "__main__":
    unittest.main()
