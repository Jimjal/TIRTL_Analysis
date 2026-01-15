# TIRTL-seq Demultiplex Plan

## 1. Overview

This document describes the demultiplexing strategy for TIRTL-seq data.

**Status**: Well Demux Implemented (M-0002 Complete)

---

## 2. Data Structure

### 2.1 Input Files
- **R1/R2**: Paired-end FASTQ files (`.fq.gz`)
- **I1/I2**: Index reads (if available, embedded in header)

### 2.2 Barcode Structure

**Well Barcodes** (96 unique combinations):
- Location: **R2 start position (0-10bp)**
- Length: **10bp** (i5 and i7 indices)
- Reference: `TIRTL_barcode_well.csv`
- Format: Row (A-H) + Column (1-12) mapped to i5/i7 index pairs

**Plate Barcodes** (12 unique):
- Location: **R1 start position (0-20bp)**
- Length: **~20bp** prefix (part of longer adapter sequence)
- Reference: `TIRTL_barcode_plate.csv`
- Format: `MP_V4_Ca/Cb_P5_UD01-06`

---

## 3. Barcode Position Analysis

### 3.1 Header Structure

Based on recon tool analysis:
- **Format**: Standard Illumina
- **Pattern**: `@<instrument>:<run>:<flowcell>:<lane>:<tile>:<x>:<y> <read>:<filtered>:<control>:<index>`
- **Index in Header**: Yes (i5+i7 combined, e.g., `TTGGTACGCG+ATAGGCGCTC`)

### 3.2 Sequence Structure

**R1 Analysis**:
| Position | Content | Concentration |
|----------|---------|---------------|
| 0-10bp | Plate barcode prefix (`TCGTCGGCAG...`) | 100% (constant) |
| 10-20bp | Plate-specific sequence | High concentration |
| 20+bp | Insert sequence | Random |

**R2 Analysis**:
| Position | Content | Concentration |
|----------|---------|---------------|
| 0-10bp | Well i7 barcode | High concentration (3 unique in test) |
| 10+bp | Insert sequence | Random |

### 3.3 Recon Tool Usage

To analyze new FASTQ files:
```bash
python3 scripts/recon_fastq.py \
    --r1 <R1.fq.gz> \
    --r2 <R2.fq.gz> \
    --sample-size 1000 \
    --window-size 10 \
    --output recon_report.txt \
    --json recon_report.json
```

Key outputs to examine:
- `BARCODE CANDIDATE` positions indicate constant/barcode regions
- `concentration_ratio > 0.5` suggests barcode presence
- Top sequences at each position help identify barcode patterns

---

## 4. Demultiplex Strategy

### 4.1 Tool Selection
- **Primary Tool**: `demultiplex` (jfjlaros)
- **Reason**: Python-based, supports dual indexing, configurable mismatch tolerance

### 4.2 Recommended Parameters
Based on recon analysis:
- `--mismatch`: 1 (allow 1 mismatch for error tolerance)
- `--indel`: 0 (no indels expected in barcodes)
- `--output-format`: fastq.gz

### 4.3 Barcode Extraction Strategy
1. **Well identification**: Extract i7 from R2 positions 0-10
2. **Plate identification**: Match R1 prefix against plate barcode sequences
3. **Output**: Demux to `{plate}_{well}/` directories

---

## 5. Execution Plan

### 5.1 Environment Setup

**IMPORTANT**: All commands must be run in the `TIRTL_analyse` conda environment.

```bash
# Activate environment
conda activate TIRTL_analyse

# Verify demultiplex is installed
demultiplex --help
```

**ARM64 (Apple Silicon) Note**: If installing on M1/M2/M3 Mac, use the patched tssv:
```bash
pip install scripts/patches/tssv-1.1.2-arm64/
```

### 5.2 Well Demux Command (M-0002)

Use the `run_demux.py` wrapper script for well-code demultiplexing:

```bash
conda activate TIRTL_analyse

python scripts/run_demux.py \
    --r1 <R1.fq.gz> \
    --barcodes TIRTL_barcode_well.csv \
    --output-dir out/well_demux/
```

**Options**:
- `--r1`: R1 FASTQ file (required)
- `--r2`: R2 FASTQ file (optional, for paired-end)
- `--barcodes`: Well barcode CSV file (required)
- `--output-dir`: Output directory (required)
- `--mismatch`: Allowed mismatches (default: 1)

**Output Files**:
- `well_<ID>.fastq.gz`: Reads for each well (e.g., `well_A01.fastq.gz`)
- `unknown.fastq.gz`: Unmatched reads
- `demux_stats.tsv`: Read counts per well

### 5.3 Verification

Run the verification script to validate the demux workflow:

```bash
conda activate TIRTL_analyse

# Verify M-0002 implementation
python scripts/verify.py --milestone M-0002

# View results
cat logs/M-0002-verify-*.summary.json
```

### 5.4 Post-processing
1. Review `demux_stats.tsv` for read distribution
2. Check unknown reads percentage (should be < 10%)
3. Verify all expected wells have reads

---

## 6. Validation Criteria

### M-0001 (Recon)
- [x] Recon tool identifies barcode positions correctly
- [x] Synthetic data validates closed-loop workflow

### M-0002 (Well Demux)
- [x] `run_demux.py` exists and runs with --help
- [x] Produces `well_<ID>.fastq.gz` for each well
- [x] Produces `unknown.fastq.gz` for unmatched reads
- [x] All output files are valid gzip
- [x] `demux_stats.tsv` has correct columns (well_id, read_count, percent)
- [x] Read count sum matches input reads (no data loss)
- [x] `verify.py --milestone M-0002` passes all checks

### Future (Real Data)
- [ ] All expected well+plate combinations found in real data
- [ ] Undetermined reads < 10%
- [ ] Read quality preserved after demux

---

## 7. Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-01-12 | v0.1 | Initial template created (T-001) |
| 2026-01-12 | v0.2 | Updated with recon analysis results (T-005) |
| 2026-01-14 | v0.3 | Added M-0002 well demux implementation (T-004) |
