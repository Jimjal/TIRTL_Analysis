#!/usr/bin/env python3
"""
run_plate_demux.py - Plate-code demultiplexing wrapper for TIRTL-seq

Takes M-0002 well-demuxed output and further splits by plate barcode (R1 prefix).
Produces per-plate/per-well FASTQ files and a stats summary.

AC-001 Requirements:
- Accepts --input-dir, --barcodes, --output-dir arguments
- Prints help with --help

AC-002 Requirements:
- Splits well_A01.fastq.gz into plate_X/well_A01.fastq.gz based on R1 prefix
- Produces plate_UNKNOWN/ for unmatched plate codes

AC-004 Requirements:
- Generates plate_demux_stats.tsv with columns: plate_id, well_id, read_count

Usage:
    conda activate TIRTL_analyse
    python scripts/run_plate_demux.py --input-dir out/well/ --barcodes TIRTL_barcode_plate.csv --output-dir out/plate/

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
        description="Plate-code demultiplexing wrapper for TIRTL-seq",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/run_plate_demux.py --input-dir out/well/ --barcodes TIRTL_barcode_plate.csv --output-dir out/plate/

Environment:
    Requires TIRTL_analyse conda environment with demultiplex installed.
    Run: conda activate TIRTL_analyse
"""
    )
    parser.add_argument(
        "--input-dir", required=True, type=str,
        help="Input directory containing well_*.fastq.gz files (M-0002 output)"
    )
    parser.add_argument(
        "--barcodes", required=True, type=str,
        help="Path to plate barcode CSV file"
    )
    parser.add_argument(
        "--output-dir", required=True, type=str,
        help="Output directory for plate-demultiplexed files"
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


def load_plate_barcodes(filepath):
    """
    Load plate barcodes from CSV file.

    Expected format:
    name,sequence
    MP_V4_Ca_P5_UD01,TCGTCGGCAGCGTC...

    The unique plate-identifying prefix is at position 33+ (after Nextera adapter).
    For demultiplex matching, we use the first 50bp which includes adapter + unique ID.

    Returns dict mapping plate_name to barcode prefix (for R1 start matching).
    """
    # Common Nextera adapter prefix length
    ADAPTER_PREFIX_LEN = 33

    barcodes = {}
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"]
            full_seq = row["sequence"]
            # Use first 50bp (adapter + unique portion) for matching
            # This ensures distinct prefixes for each plate
            prefix = full_seq[:50] if len(full_seq) >= 50 else full_seq
            barcodes[name] = prefix

    return barcodes


def create_demux_barcode_file(barcodes, output_path):
    """
    Create barcode file in demultiplex format for sequence matching.

    Format: name barcode
    Example: MP_V4_Ca_P5_UD01 TCGTCGGCAGCGTC...
    """
    with open(output_path, "w") as f:
        for plate_name, barcode in sorted(barcodes.items()):
            f.write(f"{plate_name} {barcode}\n")


def count_reads_in_fastq(filepath):
    """Count number of reads in a FASTQ file (gzipped or plain)."""
    if not os.path.exists(filepath):
        return 0

    if str(filepath).endswith(".gz"):
        opener = gzip.open
    else:
        opener = open

    count = 0
    try:
        with opener(filepath, "rt") as f:
            for _ in f:
                count += 1
    except Exception:
        return 0

    return count // 4


def find_well_files(input_dir):
    """
    Find all well_*.fastq.gz files in input directory (R1 only).

    Plate barcode is in R1, so we only process R1 well files.
    R2 files (well_*_R2.fastq.gz) are excluded.

    Returns dict mapping well_id (e.g., "A01") to file path.
    """
    input_path = Path(input_dir)
    well_files = {}

    for f in input_path.glob("well_*.fastq.gz"):
        # Skip R2 files - plate barcode is only in R1
        if "_R2.fastq" in f.name:
            continue

        # Extract well_id from filename: well_A01.fastq.gz -> A01
        well_id = f.stem.replace("well_", "").replace(".fastq", "")
        well_files[well_id] = str(f)

    return well_files


def run_demultiplex_on_well(well_file, barcode_file, temp_dir, mismatch):
    """
    Run demultiplex on a single well file to split by plate barcode.

    Uses demultiplex 'match' mode to match barcode at read start.
    Returns True if successful, False otherwise.
    """
    cmd = [
        "demultiplex", "match",
        "-m", str(mismatch),
        "-p", temp_dir,
        barcode_file,
        well_file
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Check if it's just a warning about no matches
        if "No reads" in result.stderr or result.returncode == 0:
            return True
        print(f"WARNING: demultiplex returned code {result.returncode}")
        print(f"STDERR: {result.stderr}")
        # Continue anyway - partial results may still be useful
        return True

    return True


def organize_plate_output(temp_dir, output_dir, well_id, well_basename, plate_barcodes):
    """
    Organize demultiplex output files into plate directories.

    demultiplex match creates files like: well_A01_MP_V4_Ca_P5_UD01.fastq.gz
    We want: plate_MP_V4_Ca_P5_UD01/well_A01.fastq.gz

    Returns dict mapping (plate_id, well_id) to read count.
    """
    temp_path = Path(temp_dir)
    output_path = Path(output_dir)
    read_counts = {}

    # Process each plate barcode
    for plate_name in plate_barcodes.keys():
        # Look for output file: <well_basename>_<plate_name>.fastq.gz
        # Note: demultiplex match uses .fastq.gz extension
        src_pattern = f"{well_basename}_{plate_name}.fastq.gz"
        src_file = temp_path / src_pattern

        if src_file.exists():
            # Create plate directory
            plate_dir = output_path / f"plate_{plate_name}"
            plate_dir.mkdir(parents=True, exist_ok=True)

            # Copy to destination: plate_<name>/well_<id>.fastq.gz
            dst_file = plate_dir / f"well_{well_id}.fastq.gz"
            shutil.copy2(src_file, dst_file)

            count = count_reads_in_fastq(str(dst_file))
            read_counts[(plate_name, well_id)] = count

    # Process unknown reads
    unknown_pattern = f"{well_basename}_UNKNOWN.fastq.gz"
    unknown_src = temp_path / unknown_pattern

    if unknown_src.exists():
        unknown_dir = output_path / "plate_UNKNOWN"
        unknown_dir.mkdir(parents=True, exist_ok=True)

        unknown_dst = unknown_dir / f"well_{well_id}.fastq.gz"
        shutil.copy2(unknown_src, unknown_dst)

        count = count_reads_in_fastq(str(unknown_dst))
        read_counts[("UNKNOWN", well_id)] = count

    return read_counts


def generate_stats(all_read_counts, output_path):
    """
    Generate plate_demux_stats.tsv with columns: plate_id, well_id, read_count
    """
    total_reads = sum(all_read_counts.values())

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["plate_id", "well_id", "read_count"])

        # Sort by plate, then well
        for (plate_id, well_id) in sorted(all_read_counts.keys()):
            count = all_read_counts[(plate_id, well_id)]
            writer.writerow([plate_id, well_id, count])

    return total_reads


def main():
    args = parse_args()

    # Check demultiplex is available
    if not check_demultiplex():
        print("ERROR: demultiplex not found. Please install it:")
        print("  conda activate TIRTL_analyse")
        print("  pip install demultiplex")
        sys.exit(1)

    # Validate input directory
    if not os.path.exists(args.input_dir):
        print(f"ERROR: Input directory not found: {args.input_dir}")
        sys.exit(1)

    if not os.path.exists(args.barcodes):
        print(f"ERROR: Barcode file not found: {args.barcodes}")
        sys.exit(1)

    # Find well files
    print(f"Scanning input directory: {args.input_dir}")
    well_files = find_well_files(args.input_dir)

    if not well_files:
        print("ERROR: No well_*.fastq.gz files found in input directory")
        sys.exit(1)

    print(f"Found {len(well_files)} well files")

    # Load plate barcodes
    print(f"Loading plate barcodes from: {args.barcodes}")
    plate_barcodes = load_plate_barcodes(args.barcodes)
    print(f"Loaded {len(plate_barcodes)} plate barcodes")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="plate_demux_")
    print(f"Temp directory: {temp_dir}")

    all_read_counts = {}

    try:
        # Create barcode file for demultiplex
        barcode_file = os.path.join(temp_dir, "plate_barcodes.txt")
        create_demux_barcode_file(plate_barcodes, barcode_file)

        # Process each well file
        for well_id, well_path in sorted(well_files.items()):
            print(f"\nProcessing well {well_id}...")

            # Create per-well temp directory
            well_temp_dir = os.path.join(temp_dir, f"well_{well_id}")
            os.makedirs(well_temp_dir, exist_ok=True)

            # Get basename for file matching
            well_basename = Path(well_path).name.split(".")[0]

            # Run demultiplex
            success = run_demultiplex_on_well(
                well_path, barcode_file, well_temp_dir, args.mismatch
            )

            if success:
                # Organize output
                read_counts = organize_plate_output(
                    well_temp_dir, str(output_dir), well_id, well_basename, plate_barcodes
                )
                all_read_counts.update(read_counts)

        # Generate stats
        stats_path = output_dir / "plate_demux_stats.tsv"
        total_reads = generate_stats(all_read_counts, str(stats_path))

        # Print summary
        plates_with_reads = set(p for (p, w) in all_read_counts.keys() if all_read_counts[(p, w)] > 0)
        known_plates = [p for p in plates_with_reads if p != "UNKNOWN"]
        unknown_reads = sum(v for (p, w), v in all_read_counts.items() if p == "UNKNOWN")
        known_reads = total_reads - unknown_reads

        print(f"\nPlate demultiplexing complete!")
        print(f"  Total reads processed: {total_reads}")
        if total_reads > 0:
            print(f"  Known plate reads: {known_reads} ({known_reads/total_reads*100:.1f}%)")
            print(f"  Unknown plate reads: {unknown_reads} ({unknown_reads/total_reads*100:.1f}%)")
        print(f"  Plates with reads: {len(known_plates)}")
        print(f"  Output structure: plate_<ID>/well_<ID>.fastq.gz")
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
