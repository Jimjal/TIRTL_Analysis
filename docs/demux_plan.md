# TIRTL-seq Demultiplex Plan

## 1. Overview

This document describes the demultiplexing strategy for TIRTL-seq data.

**Status**: Pending Recon Tool Analysis

---

## 2. Data Structure

### 2.1 Input Files
- **R1/R2**: Paired-end FASTQ files (`.fq.gz`)
- **I1/I2**: Index reads (if available)

### 2.2 Barcode Structure
<!-- TODO: Fill in after running recon_fastq.py -->

**Well Barcodes**:
- Location: TBD
- Length: TBD
- Reference: `examples/well_barcodes.csv`

**Plate Barcodes**:
- Location: TBD
- Length: TBD
- Reference: `examples/plate_barcodes.csv`

---

## 3. Barcode Position Analysis

<!-- TODO: Results from recon_fastq.py will be summarized here -->

### 3.1 Header Structure
- TBD

### 3.2 Sequence Structure
- TBD

---

## 4. Demultiplex Strategy

### 4.1 Tool Selection
- **Primary Tool**: `demultiplex` (jfjlaros)
- **Reason**: TBD

### 4.2 Parameters
<!-- TODO: Lock down after recon analysis -->
- `--mismatch`: TBD
- `--indel`: TBD
- `--output-format`: TBD

---

## 5. Execution Plan

### 5.1 Pre-processing
- TBD

### 5.2 Demux Command
```bash
# TODO: Final command after recon
```

### 5.3 Post-processing
- TBD

---

## 6. Validation Criteria

- [ ] All expected well+plate combinations found
- [ ] Undetermined reads < X%
- [ ] Read quality preserved

---

## 7. Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-01-12 | v0.1 | Initial template created (T-001) |
