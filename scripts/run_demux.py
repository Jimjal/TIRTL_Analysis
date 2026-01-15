#!/usr/bin/env python3
"""
run_demux.py - Well-code demultiplexing wrapper for TIRTL-seq

Wraps the jfjlaros/demultiplex tool to split FASTQ files by well barcode (UDI).
Produces per-well FASTQ files and a stats summary.

AC-001 Requirements:
- Accepts --r1, --barcodes, --output-dir arguments
- Prints help with --help

AC-002 Requirements:
- Produces well_<row><col>.fastq.gz for each known well
- Produces unknown.fastq.gz for unmatched reads

AC-004 Requirements:
- Generates demux_stats.tsv with columns: well_id, read_count, percent

Usage:
    conda activate TIRTL_analyse
    python scripts/run_demux.py --r1 input_R1.fq.gz --barcodes barcodes.csv --output-dir out/

Environment:
    Requires TIRTL_analyse conda environment with demultiplex installed.
"""

import argparse
import csv
import gzip
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Well-code demultiplexing wrapper for TIRTL-seq",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/run_demux.py --r1 data/R1.fq.gz --barcodes TIRTL_barcode_well.csv --output-dir out/

Environment:
    Requires TIRTL_analyse conda environment with demultiplex installed.
    Run: conda activate TIRTL_analyse
"""
    )
    parser.add_argument(
        "--r1", required=True, type=str,
        help="Path to R1 FASTQ file (gzipped)"
    )
    parser.add_argument(
        "--r2", type=str, default=None,
        help="Path to R2 FASTQ file (gzipped, optional)"
    )
    parser.add_argument(
        "--barcodes", required=True, type=str,
        help="Path to well barcode CSV file"
    )
    parser.add_argument(
        "--output-dir", required=True, type=str,
        help="Output directory for demultiplexed files"
    )
    parser.add_argument(
        "--mismatch", type=int, default=1,
        help="Number of allowed mismatches (default: 1)"
    )
    parser.add_argument(
        "--keep-temp", action="store_true",
        help="Keep temporary files for debugging"
    )
    return parser.parse_args()


def check_demultiplex():
    """Check if demultiplex is installed and accessible."""
    try:
        result = subprocess.run(
            ["demultiplex", "--help"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def load_well_barcodes(filepath):
    """
    Load well barcodes from CSV file.

    Expected format:
    Row,Column,i5_name,i5_sequence,i7_name,i7_sequence
    A,1,TTGGTACGCG,...,ATAGGCGCTC,...

    Returns dict mapping well_id (e.g., "A01") to barcode string (e.g., "TTGGTACGCG+ATAGGCGCTC")
    """
    barcodes = {}
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Format well ID as RowCol (e.g., A01, B12)
            row_letter = row["Row"]
            col_num = int(row["Column"])
            well_id = f"{row_letter}{col_num:02d}"

            # Barcode is i5_name+i7_name (matches Illumina header format)
            barcode = f"{row['i5_name']}+{row['i7_name']}"
            barcodes[well_id] = barcode

    return barcodes


def create_demux_barcode_file(barcodes, output_path):
    """
    Create barcode file in demultiplex format.

    Format: name barcode
    Example: A01 TTGGTACGCG+ATAGGCGCTC
    """
    with open(output_path, "w") as f:
        for well_id, barcode in sorted(barcodes.items()):
            f.write(f"{well_id} {barcode}\n")


def count_reads_in_fastq(filepath):
    """Count number of reads in a FASTQ file (gzipped or plain)."""
    count = 0

    if filepath.endswith(".gz"):
        opener = gzip.open
    else:
        opener = open

    try:
        with opener(filepath, "rt") as f:
            for line in f:
                if line.startswith("@"):
                    count += 1
    except Exception:
        # If file doesn't exist or is empty, return 0
        return 0

    # FASTQ has 4 lines per read, but we're counting @ lines
    # Actually, we need to be more careful - @ can appear in quality lines
    # Let's count lines and divide by 4
    count = 0
    try:
        with opener(filepath, "rt") as f:
            for _ in f:
                count += 1
    except Exception:
        return 0

    return count // 4


def run_demultiplex(r1_path, r2_path, barcode_file, output_dir, mismatch):
    """
    Run the demultiplex tool.

    Returns True if successful, False otherwise.
    """
    cmd = [
        "demultiplex", "demux",
        "--format", "x",  # Extract barcode from last colon-separated field
        "-m", str(mismatch),
        "-p", output_dir,
        barcode_file,
        r1_path
    ]

    if r2_path:
        cmd.append(r2_path)

    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR: demultiplex failed with code {result.returncode}")
        print(f"STDERR: {result.stderr}")
        return False

    return True


def organize_output_files(temp_dir, output_dir, r1_basename, r2_basename, barcodes):
    """
    Rename and organize output files from demultiplex.

    demultiplex creates files like: synthetic_R1_A01.fq.gz
    We want: well_A01.fastq.gz (AC-002 format)

    Returns dict mapping well_id to read count.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    temp_path = Path(temp_dir)
    read_counts = {}

    # Process each well
    for well_id in barcodes.keys():
        # Find R1 file for this well
        r1_pattern = f"{r1_basename}_{well_id}.fq.gz"
        r1_src = temp_path / r1_pattern

        if r1_src.exists():
            # AC-002: well_<row><col>.fastq.gz format
            r1_dst = output_path / f"well_{well_id}.fastq.gz"
            shutil.copy2(r1_src, r1_dst)
            read_counts[well_id] = count_reads_in_fastq(str(r1_dst))

            # Process R2 if exists (append to same file or create separate)
            if r2_basename:
                r2_pattern = f"{r2_basename}_{well_id}.fq.gz"
                r2_src = temp_path / r2_pattern
                if r2_src.exists():
                    r2_dst = output_path / f"well_{well_id}_R2.fastq.gz"
                    shutil.copy2(r2_src, r2_dst)

    # Process unknown reads (AC-002: unknown.fastq.gz)
    unknown_r1_pattern = f"{r1_basename}_UNKNOWN.fq.gz"
    unknown_r1_src = temp_path / unknown_r1_pattern

    if unknown_r1_src.exists():
        unknown_r1_dst = output_path / "unknown.fastq.gz"
        shutil.copy2(unknown_r1_src, unknown_r1_dst)
        read_counts["UNKNOWN"] = count_reads_in_fastq(str(unknown_r1_dst))

        if r2_basename:
            unknown_r2_pattern = f"{r2_basename}_UNKNOWN.fq.gz"
            unknown_r2_src = temp_path / unknown_r2_pattern
            if unknown_r2_src.exists():
                unknown_r2_dst = output_path / "unknown_R2.fastq.gz"
                shutil.copy2(unknown_r2_src, unknown_r2_dst)

    return read_counts


def generate_stats(read_counts, output_path):
    """
    Generate demux_stats.tsv with columns: well_id, read_count, percent
    """
    total_reads = sum(read_counts.values())

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["well_id", "read_count", "percent"])

        for well_id in sorted(read_counts.keys()):
            count = read_counts[well_id]
            percent = (count / total_reads * 100) if total_reads > 0 else 0
            writer.writerow([well_id, count, f"{percent:.2f}"])

    return total_reads


def main():
    args = parse_args()

    # Check demultiplex is available
    if not check_demultiplex():
        print("ERROR: demultiplex not found. Please install it:")
        print("  conda activate TIRTL_analyse")
        print("  pip install demultiplex")
        sys.exit(1)

    # Validate input files
    if not os.path.exists(args.r1):
        print(f"ERROR: R1 file not found: {args.r1}")
        sys.exit(1)

    if args.r2 and not os.path.exists(args.r2):
        print(f"ERROR: R2 file not found: {args.r2}")
        sys.exit(1)

    if not os.path.exists(args.barcodes):
        print(f"ERROR: Barcode file not found: {args.barcodes}")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load barcodes
    print(f"Loading barcodes from: {args.barcodes}")
    barcodes = load_well_barcodes(args.barcodes)
    print(f"Loaded {len(barcodes)} well barcodes")

    # Create temp directory for demultiplex output
    temp_dir = tempfile.mkdtemp(prefix="demux_")
    print(f"Temp directory: {temp_dir}")

    try:
        # Create barcode file for demultiplex
        barcode_file = os.path.join(temp_dir, "barcodes.txt")
        create_demux_barcode_file(barcodes, barcode_file)

        # Get basenames for file matching
        r1_basename = Path(args.r1).name.split(".")[0]
        r2_basename = Path(args.r2).name.split(".")[0] if args.r2 else None

        # Run demultiplex
        print("\nRunning demultiplex...")
        success = run_demultiplex(
            args.r1, args.r2, barcode_file, temp_dir, args.mismatch
        )

        if not success:
            print("ERROR: Demultiplexing failed")
            sys.exit(1)

        # Organize output files
        print("\nOrganizing output files...")
        read_counts = organize_output_files(
            temp_dir, str(output_dir), r1_basename, r2_basename, barcodes
        )

        # Generate stats
        stats_path = output_dir / "demux_stats.tsv"
        total_reads = generate_stats(read_counts, str(stats_path))

        # Print summary
        wells_with_reads = sum(1 for k, v in read_counts.items() if v > 0 and k != "UNKNOWN")
        unknown_reads = read_counts.get("UNKNOWN", 0)
        known_reads = total_reads - unknown_reads

        print(f"\nDemultiplexing complete!")
        print(f"  Total reads: {total_reads}")
        if total_reads > 0:
            print(f"  Known reads: {known_reads} ({known_reads/total_reads*100:.1f}%)")
            print(f"  Unknown reads: {unknown_reads} ({unknown_reads/total_reads*100:.1f}%)")
        else:
            print(f"  Known reads: 0")
            print(f"  Unknown reads: 0")
        print(f"  Wells with reads: {wells_with_reads}")
        print(f"  Output files: well_<ID>.fastq.gz, unknown.fastq.gz")
        print(f"  Stats file: {stats_path}")
        print(f"  Output directory: {output_dir}")

    finally:
        # Clean up temp directory
        if not args.keep_temp:
            shutil.rmtree(temp_dir)
        else:
            print(f"\nTemp files kept at: {temp_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
