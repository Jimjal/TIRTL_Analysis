# P-0001 — TIRTL-seq Demultiplex Recon & Strategy Lock

## 0. Metadata
- Workflow Slug: relay_accept_change
- Created: 2026-01-07
- Last Updated: 2026-01-12
- Status: **Accepted**
- Source: Converted from `_milestone/M-0001_TIRTL_demux_recon_light_v1.ipynb`
- Active Roles Mapping (current):
  - Implementer: Antigravity
  - Validator: Antigravity
  - Specifier: User
- Skills Used: None

## 1. Background / Context

**Background**:
- Experiment uses **TIRTL-seq** technology, data format is `.fq.gz`.
- Barcode structure: **<well code> + <plate code>** combination.
- Selected tool: **`demultiplex` (jfjlaros)**.

**Goal**:
- Before running full demux, determine Barcode position (Header/Sequence/Index).
- Lock down `demultiplex` parameter strategy (Mismatch, Indel, Output format).
- Establish minimal reproducible verification environment.

## 2. Requirements Summary
- REQ-001: Develop Recon Tool to auto-analyze FASTQ Header and Read structure, reporting potential Barcode positions.
- REQ-002: Produce `docs/demux_plan.md` documenting the demux strategy based on recon results.
- REQ-003: Establish `examples/` directory with Well/Plate Barcode reference tables.
- REQ-004: Implement `scripts/verify.py` for automated verification using synthetic data.

## 3. Tasks
- TASK-001: Initialize Repo & Templates (AC-001)
  - Create `examples/` folder
  - Create placeholder `well_barcodes.csv` & `plate_barcodes.csv`
  - Create `docs/demux_plan.md` template
  - **Status**: ✅ Complete

- TASK-002: Implement Synthetic Data Generator (AC-003)
  - Create `scripts/generate_synthetic_data.py`
  - Logic: Random sequence + Known Adapter/Barcode injection
  - **Status**: ✅ Complete

- TASK-003: Implement Recon Tool (AC-002)
  - Create `scripts/recon_fastq.py`
  - Implement Header parsing logic
  - Implement Seq slice frequency counting
  - **Status**: ✅ Complete

- TASK-004: Implement Verification Script (AC-004)
  - Create `scripts/verify.py`
  - Integrate TASK-002 & TASK-003
  - Add logging and JSON summary output
  - **Status**: ✅ Complete

- TASK-005: Final Review & Doc Update (AC-001, AC-004)
  - Run verify script
  - Update `docs/demux_plan.md` with usage instructions
  - **Status**: ✅ Complete

## 4. Acceptance Criteria
- AC-001 (Repo Structure & Templates):
  1. `examples/well_barcodes.csv` and `examples/plate_barcodes.csv` exist with clear format documentation
  2. `scripts/` directory exists
  3. `docs/demux_plan.md` exists (with chapter placeholders initially)

- AC-002 (Recon Tool Implementation):
  1. Script `scripts/recon_fastq.py` is executable
  2. Input supports R1/R2 (optional I1/I2)
  3. Outputs Header structure analysis (index presence); samples first N bp of Reads for barcode position detection

- AC-003 (Synthetic Data Generator):
  1. Script `scripts/generate_synthetic.py` (or integrated in verify) runs
  2. Generates mini FASTQ (R1/R2) containing specified Barcodes from `examples/`
  3. Generated data Headers conform to standard Illumina format

- AC-004 (Verification Workflow):
  1. `scripts/verify.py` runs successfully (Exit Code 0)
  2. Closed loop: Verify script auto-generates synthetic data -> Runs Recon Tool -> Asserts Recon correctly identifies synthetic Barcode features (position/type)
  3. Outputs log `/logs/M-0001-verify-*.txt` and summary `.json`

## 5. Constraints
- CON-001: Prefer `demultiplex` (jfjlaros) ecosystem or Python native libraries
- CON-002: Repo must NOT contain real sample data; only synthetic data or local path references allowed
- CON-003: Cross-platform compatible (Mac/Linux)

## 6. Deliverables
- DELIV-001: `examples/well_barcodes.csv`
- DELIV-002: `examples/plate_barcodes.csv`
- DELIV-003: `docs/demux_plan.md`
- DELIV-004: `scripts/generate_synthetic.py`
- DELIV-005: `scripts/recon_fastq.py`
- DELIV-006: `scripts/verify.py`
- DELIV-007: `logs/M-0001-verify-*.txt` and `.json`

## 7. Change Log (append-only; Implementer)
- 2026-01-07 [CHANGE] v1 Initial Draft created (REQ-001~004)
- 2026-01-12 [CHANGE] v2 Refined by Antigravity. Added AC-001~004, Task T-001~005, Verification Plan. Standardized structure.
  - Files: `examples/`, `scripts/`, `docs/demux_plan.md`
- 2026-01-12 [CHANGE] v3 Final implementation complete. All tasks verified.
  - Files: All deliverables created
  - Commands: `python3 scripts/verify.py`

## 8. Validation Report (append-only; Validator)
### Validation Run 1 (2026-01-12)
- Environment: Python 3.x, Mac/Linux
- Commands executed: `python3 scripts/verify.py`

| Item | Status | Evidence | Notes |
|------|--------|----------|-------|
| AC-001 | PASS | Files exist in repo | Verified |
| AC-002 | PASS | `recon_fastq.py` runs, outputs structure | Verified |
| AC-003 | PASS | Synthetic data generated with correct headers | Verified |
| AC-004 | PASS | 32/32 checks passed | Log: `logs/M-0001-verify-*.txt` |

#### Summary
- Overall: **PASS** (32/32 checks verified)
- Gates passed: Yes
- Logs checked: Yes (`logs/M-0001-verify-*.txt` confirmed)

## 9. Appendix — Chat Digest
(No cross-AI chat for this milestone)
