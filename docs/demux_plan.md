# TIRTL-seq Demultiplex Plan

## 1. Overview

This document describes the demultiplexing strategy for TIRTL-seq data.

**Status**: Recon Complete - Ready for Demux Parameter Lock-down

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

### 5.1 Pre-processing
1. Run recon tool on sample of real data
2. Verify barcode positions match synthetic data patterns
3. Adjust window sizes if needed

### 5.2 Demux Command
```bash
# Example command (adjust paths as needed)
demultiplex demux \
    --input-r1 <R1.fq.gz> \
    --input-r2 <R2.fq.gz> \
    --barcodes TIRTL_barcode_well.csv \
    --mismatch 1 \
    --output-dir demux_output/
```

### 5.3 Post-processing
1. Count reads per well/plate combination
2. Calculate demux efficiency
3. Flag wells with low read counts

---

## 6. Validation Criteria

- [x] Recon tool identifies barcode positions correctly
- [x] Synthetic data validates closed-loop workflow
- [ ] All expected well+plate combinations found in real data
- [ ] Undetermined reads < 10%
- [ ] Read quality preserved after demux

---

## 7. Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-01-12 | v0.1 | Initial template created (T-001) |
| 2026-01-12 | v0.2 | Updated with recon analysis results (T-005) |
