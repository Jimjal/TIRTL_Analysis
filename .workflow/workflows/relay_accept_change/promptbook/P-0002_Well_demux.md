# P-0002 — Well-code Demultiplex (384 UDI Split)

## 0. Metadata
- Workflow Slug: relay_accept_change
- Created: 2026-01-13
- Last Updated: 2026-01-15
- Status: **Complete**
- Source: Converted from `_milestone/M-0002_Well_demux_v1.ipynb`
- Active Roles Mapping (current):
  - Implementer: Antigravity
  - Validator: Antigravity
  - Specifier: User
- Skills Used: None

## 1. Background / Context

- M-0001 completed: Locked `demultiplex (jfjlaros)` as the core tool.
- **Goal**: Implement the first stage of demultiplexing: splitting raw reads by **Well Code (384 UDI)**.
- Output: Individual FASTQ files per well, plus a counts summary table. Unknown/unmatched reads must be preserved.

## 2. Requirements Summary
- REQ-001: Wrap `demultiplex` (jfjlaros) in a python script (`scripts/run_demux.py`)
- REQ-002: Accept R1 FASTQ (optional R2) and Barcode CSV as input
- REQ-003: Output `out/well/<ID>.fq.gz`, `out/unknown.fq.gz`, `stats.tsv`
- REQ-004: Reproducible verification via `scripts/verify.py`

## 3. Tasks
- TASK-001: Environment & Mock Setup
  - Ensure `demultiplex` is installed in `TIRTL_analyse` env
  - Verify tool runs on Windows (powershell/cmd) and macOS (zsh)
  - Update `scripts/generate_synthetic.py` if necessary
  - **Status**: ✅ Complete

- TASK-002: Demux Wrapper Implementation
  - Create `scripts/run_demux.py`
  - Implement barcode table parsing (CSV -> `demultiplex` format)
  - Implement subprocess call to `demultiplex`
  - Implement file renaming/organizing logic
  - Implement stats generation
  - **Status**: ✅ Complete

- TASK-003: Verification Logic
  - Update `scripts/verify.py` to include `verify_demux_well()`
  - Implement checks for AC-002, AC-003, AC-004
  - **Status**: ✅ Complete

- TASK-004: Documentation & Final Polish
  - Update `docs/` with usage instructions
  - Run final full verification
  - **Status**: ✅ Complete

## 4. Acceptance Criteria
- AC-001 (Interface): `scripts/run_demux.py` exists and is executable
  - Accepts `--r1`, `--barcodes`, `--output-dir` arguments
  - Prints help with `--help`

- AC-002 (Functionality): Running on synthetic data (3 known wells + noise) produces:
  - Precise output files: `well_<row><col>.fastq.gz` for each known well
  - `unknown.fastq.gz` for noise

- AC-003 (Data Integrity):
  - Output FASTQ files are valid gzip files
  - R1/R2 pairing is preserved (same number of reads in both files per well)

- AC-004 (Reporting):
  - Generates `demux_stats.tsv` with columns: `well_id`, `read_count`, `percent`
  - Sum of all well counts + unknown count equals total input reads

- AC-005 (Automation):
  - `scripts/verify.py` runs the full cycle (Synthetic Gen -> Demux -> Check) with exit code 0
  - Verification produces a JSON summary log

## 5. Constraints
- CON-001: **Environment**: STRICTLY use `TIRTL_analyse` conda environment. DO NOT install packages into `base` environment.
- CON-002: **OS Support**: Must support both Windows and macOS.
- CON-003: Handle missing dependencies gracefully (provide setup instructions if `demultiplex` is missing).
- CON-004: No real data in repo (synthetic only).

## 6. Deliverables
- DELIV-001: `scripts/run_demux.py` - Wrapper script for well-code demultiplexing
- DELIV-002: Updated `scripts/verify.py` - With `verify_m0002_full_cycle` checks
- DELIV-003: Updated `docs/demux_plan.md` - Usage instructions and environment setup
- DELIV-004: `scripts/patches/tssv-1.1.2-arm64/` - ARM64 compatibility patch for tssv dependency
- DELIV-005: Updated `requirements.txt` - ARM64 installation notes

## 7. Change Log (append-only; Implementer)
- 2026-01-13 [CHANGE] v1 Initial Draft
- 2026-01-14 [CHANGE] v2 Refined tasks, ACs, verification limits. Aligned with R3 Pipeline.
  - Files: `scripts/run_demux.py`, `scripts/verify.py`
- 2026-01-15 [CHANGE] v2.1 Added strict environment (TIRTL_analyse) and OS (Win/Mac) constraints.
  - Files: All deliverables completed
  - Commands: `python scripts/verify.py --milestone M-0002`

## 8. Validation Report (append-only; Validator)
### Validation Run 1 (2026-01-15 11:35)
- Environment: `TIRTL_analyse` conda environment, macOS
- Commands executed: `python scripts/verify.py --milestone M-0002`

| Item | Status | Evidence | Notes |
|------|--------|----------|-------|
| AC-001 | PASS | Verification checks 2-6 | Interface working |
| AC-002 | PASS | Verification checks 7-12 | Well files + unknown.fastq.gz created |
| AC-003 | PASS | Verification checks 13-17 | Valid gzip files |
| AC-004 | PASS | Verification checks 18-23 | demux_stats.tsv with correct counts |
| AC-005 | PASS | 23/23 checks passed | Full cycle verified |

#### Summary
- Overall: **PASS** (23/23 checks passed)
- Log: `logs/M-0002-verify-20260115-1135.txt`
- Summary: `logs/M-0002-verify-20260115-1135.summary.json`

## 9. Appendix — Chat Digest
(No cross-AI chat for this milestone)
