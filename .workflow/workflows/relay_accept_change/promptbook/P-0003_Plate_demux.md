# P-0003 — Plate-code Demultiplex (Multi-plate Split)

## 0. Metadata
- Workflow Slug: relay_accept_change
- Created: 2026-01-15
- Last Updated: 2026-01-15
- Status: **Complete**
- Source: Converted from `_milestone/M-0003_Plate_demux_v2.ipynb`
- Active Roles Mapping (current):
  - Implementer: Antigravity
  - Validator: Antigravity
  - Specifier: User
- Skills Used: None

## 1. Background / Context

- **Context**: M-0002 split raw reads into per-well FASTQ files (`well_A01.fastq.gz`). However, these files may contain reads from multiple plates mixed together if plates were multiplexed on the same run.
- **Goal**: Implement Plate Demultiplexing to further split the M-0002 output files by **Plate Code**.
- **Output**: A directory structure `out/plate_<ID>/well_<ID>.fastq.gz`, separating reads by unique (Plate, Well) combinations.

### Source of Truth: Barcode & Data Structure

| Type | Source File | Location | Sequence Used for Matching |
|------|-------------|----------|----------------------------|
| **Well Barcode** | `TIRTL_barcode_well.csv` | **R2 Start** (0-10bp) | 10bp i5+i7 pairs (handled in M-0002) |
| **Plate Barcode** | `TIRTL_barcode_plate.csv` | **R1 Start** (0-50bp) | **50bp** Prefix (33bp Adapter + ~17bp Unique ID) |

> **Note**: While the unique variable region is short (6-8bp), the implementation strictly matches the full **50bp** prefix for high specificity.

## 2. Requirements Summary
- REQ-001: Create `scripts/run_plate_demux.py` wrapping `demultiplex` (jfjlaros)
- REQ-002: Accept M-0002 output directory and Plate Barcode CSV as input
- REQ-003: Output `plate_<ID>/well_<ID>.fastq.gz` structure with `plate_UNKNOWN/` for unmatched
- REQ-004: Generate `plate_demux_stats.tsv` summary
- REQ-005: Update verification to run full chain: Synthetic Gen -> Well Demux -> Plate Demux -> Verify

## 3. Tasks
- TASK-001: Verification Update (Synthetic Data)
  - Update `scripts/generate_synthetic.py` to support multi-plate generation (full 50bp R1 prefixes)
  - Verify generator produces distinct plate prefixes
  - **Status**: ✅ Complete

- TASK-002: Plate Demux Script Implementation
  - Create `scripts/run_plate_demux.py`
  - Logic: Iterate over input well files -> subprocess call `demultiplex` -> Organize output
  - **Status**: ✅ Complete

- TASK-003: Verification Logic Integration
  - Update `scripts/verify.py` to add `verify_m0003()`
  - Run full pipeline: Gen -> M-0002 -> M-0003 -> Check
  - **Status**: ✅ Complete

- TASK-004: Documentation & Final Verification
  - Update docs with Plate Demux usage
  - Run final verification and fill Acceptance Summary
  - **Status**: ✅ Complete

## 4. Acceptance Criteria
- AC-001 (Interface): `scripts/run_plate_demux.py` exists and is executable
  - Arguments: `--input-dir` (M-0002 output), `--barcodes`, `--output-dir`

- AC-002 (Functionality):
  - Splits `well_A01.fastq.gz` into `plate_X/well_A01.fastq.gz` and `plate_Y/well_A01.fastq.gz` based on R1 50bp prefix
  - Correctly handles unknown plate codes (into `plate_UNKNOWN/`)

- AC-003 (Data Integrity):
  - Output files are valid gzip
  - Total reads (Sum of all plates + unknown) exactly match input reads from M-0002

- AC-004 (Reporting):
  - Generates `plate_demux_stats.tsv` with `plate_id`, `well_id`, `read_count`

- AC-005 (Automation):
  - `scripts/verify.py` updated to run full chain: Synthetic Gen (Multi-plate) -> Well Demux -> Plate Demux -> Verify Counts

## 5. Constraints
- CON-001: Use `TIRTL_analyse` conda environment
- CON-002: Must preserve R1/R2 pairing uniqueness
- CON-003: Files verified: Sourced from R1 output of M-0002

### Output Conventions
- Directory Format: `plate_<PlateName>/` (e.g., `plate_MP_V4_Ca_P5_UD01/`)
- File Naming: `well_<WellID>.fastq.gz` (e.g., `well_A01.fastq.gz`)
- Unknowns: Placed in `plate_UNKNOWN/`
- Stats File: `plate_demux_stats.tsv` (columns: `plate_id`, `well_id`, `read_count`)

## 6. Deliverables
- DELIV-001: `scripts/run_plate_demux.py` - Wrapper script for plate-code demultiplexing
- DELIV-002: Updated `scripts/generate_synthetic.py` - Multi-plate support with full 50bp R1 prefixes
- DELIV-003: Updated `scripts/verify.py` - With `verify_m0003_full_cycle` checks

## 7. Change Log (append-only; Implementer)
- 2026-01-15 [CHANGE] v1 Initial R3 Pipeline specification for Plate Demux
  - Files: `scripts/run_plate_demux.py`, `scripts/generate_synthetic.py`, `scripts/verify.py`
  - Commands: `python scripts/verify.py --milestone M-0003`
- 2026-01-15 [CHANGE] v2 Documentation Revision
  - Added 'Source of Truth' table (Section 3)
  - Clarified Plate Barcode matching length (50bp prefix)
  - Mapped verification checks to ACs
  - Corrected output structure descriptions
  - No code changes

## 8. Validation Report (append-only; Validator)
### Validation Run 1 (2026-01-15 12:34)
- Environment: `TIRTL_analyse` conda environment, macOS
- Commands executed: `python scripts/verify.py --milestone M-0003`

| Item | Status | Evidence | Notes |
|------|--------|----------|-------|
| AC-001 | PASS | Checks 3-7 | `scripts/run_plate_demux.py exists`, `--help runs`, arguments work |
| AC-002 | PASS | Checks 8-13 | Plate output directories created, correct sorting, UNKNOWN handling |
| AC-003 | PASS | Check 14 | All output files are valid gzip |
| AC-004 | PASS | Checks 15-19 | `plate_demux_stats.tsv` exists, stats sum matches input (100% accounting) |
| AC-005 | PASS | 19/19 checks | Full pipeline verified |

#### Summary
- Overall: **PASS** (19/19 checks passed)
- Log: `logs/M-0003-verify-20260115-1234.txt`
- Summary: `logs/M-0003-verify-20260115-1234.summary.json`

### Verification Scenario
1. Generate synthetic data: 2 Plates (PlateA, PlateB), 2 Wells (A01, B01). Total 4 combinations + noise.
2. Run M-0002 (Well Demux) -> Expect `well_A01` (mixed PlateA/B) and `well_B01`.
3. Run M-0003 (Plate Demux) -> Expect `plate_PlateA/well_A01`, `plate_PlateB/well_A01`, etc.
4. Verify counts match inputs.

## 9. Appendix — Chat Digest
(No cross-AI chat for this milestone)
