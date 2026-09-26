from __future__ import annotations

import hashlib
import json
import csv
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_data import (  # noqa: E402
    ALL_SITES_PATH,
    MANIFEST_PATH,
    build_artifacts,
    validate_repository,
)


class DataPipelineTests(unittest.TestCase):
    def test_build_is_deterministic(self) -> None:
        first_artifacts, first_manifest = build_artifacts(ROOT)
        second_artifacts, second_manifest = build_artifacts(ROOT)

        self.assertEqual(first_artifacts, second_artifacts)
        self.assertEqual(first_manifest, second_manifest)

    def test_expected_counts_and_categories(self) -> None:
        _, manifest = build_artifacts(ROOT)

        self.assertEqual(
            manifest["counts_by_category"],
            {
                "landfill": 2323,
                "superfund": 1924,
            },
        )
        self.assertEqual(manifest["total_rows"], 4247)

    def test_superfund_merge_counts_and_metadata(self) -> None:
        artifacts, manifest = build_artifacts(ROOT)
        merge = manifest["superfund_merge"]

        self.assertEqual(merge["new_npl_source_row_count"], 47199)
        self.assertEqual(merge["npl_unique_epa_ids"], 1721)
        self.assertEqual(
            merge["npl_status_counts"],
            {"Final NPL": 1260, "Proposed NPL": 28, "Deleted NPL": 433},
        )
        self.assertEqual(merge["filtered_saa_source_row_count"], 48)
        self.assertEqual(merge["overlapping_epa_ids"], 3)
        self.assertEqual(merge["npl_only_sites"], 1718)
        self.assertEqual(merge["saa_non_npl_sites"], 45)
        self.assertEqual(merge["saa_only_sites_added"], 4)
        self.assertEqual(merge["legacy_source_row_count"], 1908)
        self.assertEqual(merge["legacy_npl_overlap"], 1709)
        self.assertEqual(merge["legacy_saa_overlap"], 44)
        self.assertEqual(merge["new_npl_sites_added"], 12)
        self.assertEqual(merge["legacy_only_sites_retained"], 158)
        self.assertEqual(merge["final_unique_superfund_site_count"], 1924)
        self.assertEqual(merge["dedupe_key"], "EPA ID")
        self.assertEqual(
            merge["coordinate_precedence"],
            "NEW NPL coordinate > legacy boundary coordinate > SAA coordinate",
        )

        rows = list(csv.DictReader(io.StringIO(artifacts[ALL_SITES_PATH].decode("utf-8"))))
        superfund_rows = [row for row in rows if row["category"] == "superfund"]
        metadata = [json.loads(row["metadata_json"]) for row in superfund_rows]
        self.assertEqual(len({item["external_id"] for item in metadata}), 1924)
        self.assertEqual(sum(item["saa"] is True for item in metadata), 48)
        self.assertNotIn("superfund_npl", {row["category"] for row in rows})
        self.assertIn("DEN000306877", {item["external_id"] for item in metadata})

        with (ROOT / "data/snapshots/superfund_npl.csv").open(newline="") as handle:
            npl_rows = list(csv.DictReader(handle))
        with (ROOT / "data/snapshots/superfund_saa.csv").open(newline="") as handle:
            saa_rows = list(csv.DictReader(handle))
        npl_by_id = {json.loads(row["metadata_json"])["external_id"]: row for row in npl_rows}
        saa_ids = {json.loads(row["metadata_json"])["external_id"] for row in saa_rows}
        output_by_id = {json.loads(row["metadata_json"])["external_id"]: row for row in superfund_rows}
        for epa_id in set(npl_by_id) & saa_ids:
            self.assertEqual(output_by_id[epa_id]["lat"], npl_by_id[epa_id]["lat"])
            self.assertEqual(output_by_id[epa_id]["lon"], npl_by_id[epa_id]["lon"])

    def test_manifest_hashes_match_generated_outputs(self) -> None:
        artifacts, manifest = build_artifacts(ROOT)

        for path_text, details in manifest["outputs"].items():
            payload = artifacts[Path(path_text)]
            self.assertEqual(hashlib.sha256(payload).hexdigest(), details["sha256"])
            self.assertEqual(len(payload), details["bytes"])

        serialized_manifest = json.loads(artifacts[MANIFEST_PATH])
        self.assertEqual(serialized_manifest, manifest)
        self.assertIn(ALL_SITES_PATH, artifacts)

    def test_checked_in_bundle_is_current(self) -> None:
        manifest = validate_repository(ROOT)
        self.assertTrue(manifest["dataset_version"].startswith("snapshot-"))


if __name__ == "__main__":
    unittest.main()
