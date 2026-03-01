#!/usr/bin/env python3
"""Deprecated helper.

This repository is intentionally offline for processing.
Raw source files must be manually downloaded into data/raw.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"


def main() -> int:
    print("Offline mode: automatic downloads are disabled.")
    print(f"Place manually downloaded source files in: {RAW_DIR}")
    print("Then run: python scripts/process_all.py --overwrite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
