# TIRTL-seq Demultiplex Analysis

This repository contains tools and configurations for demultiplexing TIRTL-seq (T cell Receptor Identification by Targeted Ligation) sequencing data.

## Project Status

**M-0001 Status: COMPLETE** - All acceptance criteria verified.
**M-0002 Status: IN PROGRESS** - Analysis and Planning.

## Directory Structure

```
.
├── TIRTL_barcode_plate.csv   # Plate barcodes (12 entries)
├── TIRTL_barcode_well.csv    # Well barcodes (96 entries)
├── build/                    # Generated synthetic data (gitignored)
├── docs/
│   └── demux_plan.md         # Demultiplex strategy document
├── examples/
│   ├── plate_barcodes.csv    # Format specification examples
│   └── well_barcodes.csv     # Format specification examples
├── scripts/
│   ├── generate_synthetic.py # Synthetic FASTQ generator
│   ├── recon_fastq.py        # FASTQ reconnaissance tool
│   ├── verify.py             # Python verification script (AC-004)
│   └── verify.sh             # Bash verification script
└── logs/                     # Verification logs
```

## Barcode File Formats

### Well Barcodes (`TIRTL_barcode_well.csv`)

Each row represents a unique well position in a 96-well plate.

| Column          | Description                          |
| --------------- | ------------------------------------ |
| `Row`         | A-H (96-well plate row)              |
| `Column`      | 1-12 (96-well plate column)          |
| `i5_name`     | 10bp index name (used as identifier) |
| `i5_sequence` | Full i5 adapter+index sequence       |
| `i7_name`     | 10bp index name (used as identifier) |
| `i7_sequence` | Full i7 adapter+index sequence       |

The `i5_name` and `i7_name` represent the unique 10bp barcodes that identify each well. These are embedded within the full adapter sequences.

**Example:**

```csv
Row,Column,i5_name,i5_sequence,i7_name,i7_sequence
A,1,TTGGTACGCG,AATGATACGGCGACCACCGAGATCTACACTTGGTACGCGTCGTCGGCAGCGTC,ATAGGCGCTC,CAAGCAGAAGACGGCATACGAGATATAGGCGCTCGTCTCGTGGGCTCGG
```

### Plate Barcodes (`TIRTL_barcode_plate.csv`)

Each row represents a unique plate barcode for multiplexed TIRTL-seq runs.

| Column       | Description                                                 |
| ------------ | ----------------------------------------------------------- |
| `name`     | Plate barcode identifier                                    |
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

### Generate Synthetic Test Data

```bash
python3 scripts/generate_synthetic.py
```

Options:

- `--output-dir DIR` — Output directory (default: `build/`)
- `--num-reads N` — Reads per well/plate combination (default: 10)
- `--wells N` — Number of wells to include (default: 3)
- `--plates N` — Number of plates to include (default: 2)
- `--seed N` — Random seed for reproducibility (default: 42)

Output files:

- `build/synthetic_R1.fq.gz` — R1 reads with plate barcode prefix
- `build/synthetic_R2.fq.gz` — R2 reads with well i7 barcode prefix
- `build/synthetic_manifest.csv` — Manifest of generated combinations

### Run FASTQ Reconnaissance

```bash
python3 scripts/recon_fastq.py --r1 <R1.fq.gz> --r2 <R2.fq.gz>
```

Options:

- `--sample-size N` — Number of reads to sample (default: 1000)
- `--window-size N` — Sequence window size to analyze (default: 20)
- `--top-n N` — Show top N frequent sequences (default: 10)
- `--output FILE` — Output text report file
- `--json FILE` — Output JSON report file

The recon tool analyzes FASTQ files to:

- Detect Illumina header format and index presence
- Identify barcode candidate positions by sequence frequency
- Help determine demultiplex parameters

### Run Verification

**Python version (recommended):**

```bash
python3 scripts/verify.py
```

**Bash version:**

```bash
./scripts/verify.sh
```

The verification implements a closed-loop workflow:

1. Generate synthetic data with known barcodes
2. Run recon tool to analyze the data
3. Assert recon correctly identified barcode positions
4. Output verification logs and JSON summary

Checks performed:

- Directory structure exists (AC-001)
- Barcode files are properly formatted (AC-001)
- Recon tool analyzes FASTQ and identifies barcodes (AC-002)
- Synthetic data generator works correctly (AC-003)
- Closed-loop verification passes (AC-004)

Logs are saved to `logs/M-0001-verify-YYYYMMDD-HHMM.txt`

## Requirements

- [Conda](https://docs.conda.io/en/latest/miniconda.html) (Miniconda or Anaconda)
- Python 3.6+
- **Windows Users**: [Microsoft Visual C++ 14.0+ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) are required to compile `tssv`/`demultiplex`.

## Environment Setup

### Step 1: Create Conda Environment (First Time Only)

**Windows (PowerShell/CMD):**

```powershell
conda create -n TIRTL_analyse python=3.10 -y
conda activate TIRTL_analyse
```

**macOS (Terminal/zsh):**

```bash
conda create -n TIRTL_analyse python=3.10 -y
conda activate TIRTL_analyse
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:

- `demultiplex` (jfjlaros) - Core demultiplexing tool
- Dependencies: biopython, dict-trie, fastools, jit-open, tssv

### Step 3: Verify Installation

```bash
demultiplex --version
```

Expected output: `demultiplex version X.Y.Z`

### Platform-Specific Notes

**Windows:**

- Use PowerShell or Git Bash for best compatibility
- Scripts are invoked with `python` (not `python3`)

**macOS:**

- Use Terminal with zsh or bash
- Scripts can use `python3` or `python` (after conda activation)

### Troubleshooting

**"demultiplex: command not found"**

Ensure the conda environment is activated:

```bash
conda activate TIRTL_analyse
```

If still not found, reinstall:

```bash
pip uninstall demultiplex -y
pip install demultiplex
```

## License

Internal use only.
