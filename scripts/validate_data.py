#!/usr/bin/env python3
"""Read-only validation for the Terris snapshot and generated data bundle."""

from __future__ import annotations

import sys

from build_data import PipelineError, REPO_ROOT, validate_repository


def main() -> int:
    try:
        manifest = validate_repository(REPO_ROOT)
    except (OSError, PipelineError) as exc:
        print(f"DATA VALIDATION FAILED\n{exc}", file=sys.stderr)
        return 1

    counts = ", ".join(
        f"{category}={count}"
        for category, count in manifest["counts_by_category"].items()
    )
    print(
        f"DATA VALIDATION PASSED: {manifest['dataset_version']}, "
        f"{manifest['total_rows']} sites ({counts})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
