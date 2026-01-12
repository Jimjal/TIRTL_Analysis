# TIRTL-seq Demultiplex Analysis

This repository contains tools and configurations for demultiplexing TIRTL-seq (T cell Receptor Identification by Targeted Ligation) sequencing data.

## Project Status

| Milestone | Task | Status | Description |
|-----------|------|--------|-------------|
| M-0001 | T-001 | Done | Initialize repo structure and templates |
| M-0001 | T-002 | Pending | Implement synthetic data generator |
| M-0001 | T-003 | Pending | Implement recon tool |
| M-0001 | T-004 | Pending | Implement verification script |
| M-0001 | T-005 | Pending | Final review and doc update |

## Directory Structure

```
.
├── TIRTL_barcode_plate.csv   # Plate barcodes (12 entries)
├── TIRTL_barcode_well.csv    # Well barcodes (96 entries)
├── docs/
│   └── demux_plan.md         # Demultiplex strategy document
├── examples/
│   ├── plate_barcodes.csv    # Format specification examples
│   └── well_barcodes.csv     # Format specification examples
├── scripts/
│   └── verify.sh             # Verification script
└── logs/                     # Verification logs
```

## Barcode File Formats

### Well Barcodes (`TIRTL_barcode_well.csv`)

Each row represents a unique well position in a 96-well plate.

| Column | Description |
|--------|-------------|
| `Row` | A-H (96-well plate row) |
| `Column` | 1-12 (96-well plate column) |
| `i5_name` | 10bp index name (used as identifier) |
| `i5_sequence` | Full i5 adapter+index sequence |
| `i7_name` | 10bp index name (used as identifier) |
| `i7_sequence` | Full i7 adapter+index sequence |

The `i5_name` and `i7_name` represent the unique 10bp barcodes that identify each well. These are embedded within the full adapter sequences.

**Example:**
```csv
Row,Column,i5_name,i5_sequence,i7_name,i7_sequence
A,1,TTGGTACGCG,AATGATACGGCGACCACCGAGATCTACACTTGGTACGCGTCGTCGGCAGCGTC,ATAGGCGCTC,CAAGCAGAAGACGGCATACGAGATATAGGCGCTCGTCTCGTGGGCTCGG
```

### Plate Barcodes (`TIRTL_barcode_plate.csv`)

Each row represents a unique plate barcode for multiplexed TIRTL-seq runs.

| Column | Description |
|--------|-------------|
| `name` | Plate barcode identifier |
| `sequence` | Full adapter sequence containing the plate-specific barcode |

**Name format:** `MP_V4_Ca_P5_UD01`
- `MP_V4`: Mouse Protocol Version 4
- `Ca`/`Cb`: Chain type (alpha/beta for TCR)
- `P5`: P5 adapter side
- `UD01-06`: Unique Dual index number

The plate barcode is embedded within the sequence and identifies which plate the sample came from.

**Example:**
```csv
name,sequence
MP_V4_Ca_P5_UD01,TCGTCGGCAGCGTCAGATGTGTATAAGAGACAGAGAACCTCGCCACAGCAGGTTCTGGGTTCTG
```

## Quick Start

### Run Verification
```bash
./scripts/verify.sh
```

This will check:
- Directory structure exists
- Barcode files are properly formatted
- Documentation templates are in place

Logs are saved to `logs/M-0001-verify-YYYYMMDD-HHMM.txt`

## Requirements

- Bash shell (macOS/Linux)
- No external dependencies for T-001

## License

Internal use only.
