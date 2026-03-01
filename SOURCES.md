# Data Sources

Raw files in this repository were **manually downloaded by the user** and are processed fully offline.

Last updated: February 28, 2026

## Source Inventory

| Dataset | Provider | Download page/source | Expected raw filename in `data/raw` |
|---|---|---|---|
| FRS National Facility File | U.S. EPA (Facility Registry Service) | Placeholder: `<EPA FRS download URL>` | `NATIONAL_FACILITY_FILE.CSV` |
| FRS National Program File | U.S. EPA (Facility Registry Service) | Placeholder: `<EPA FRS program URL>` | `NATIONAL_PROGRAM_FILE.CSV` (optional; preferred for Option A filtering) |
| Military Bases | U.S. DOT BTS / NTAD | Placeholder: `<BTS/NTAD military bases URL>` | `NTAD_Military_Bases_5442727609563115285.csv` |
| LMOP Landfill Data | U.S. EPA LMOP | Placeholder: `<EPA LMOP landfill data URL>` | `landfilllmopdata.xlsx` |

## Notes

- Processing scripts do **not** fetch data from the internet.
- `data/raw` contents are treated as authoritative local inputs.
- `scripts/rebuild_industrial_filtered.py` filters `industrial_frs` to facilities with relevant FRS program participation
  (TRI, RCRA, CERCLA/Superfund-related keyword matches).
- If the National Program file is unavailable, filtering falls back to program text fields in the National Facility file.
- `scripts/rebuild_industrial_reduced_no_program.py` supports a no-program-file proxy approach:
  stage-1 high-signal industry filter (NAICS or facility-name keywords) plus stage-2 grid capping
  (0.05 degree, max 10 facilities per cell) to prevent score saturation while preserving national coverage.
- This proxy approach is not direct PFAS confirmation.
- This filtering step reduces facility count and improves scoring signal quality.
- Previous source-link handling included unstable/broken links; this reset uses explicit placeholders so links can be refreshed intentionally.
