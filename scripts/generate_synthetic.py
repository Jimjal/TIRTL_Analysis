#!/usr/bin/env python3
"""
generate_synthetic.py - Synthetic FASTQ Generator for TIRTL-seq

Generates synthetic paired-end FASTQ files (R1/R2) with known barcodes
for testing the demultiplex pipeline.

AC-003 Requirements:
- Generate FASTQ with barcodes from examples/ or root barcode files
- Illumina-compliant header format
- Output to build/ directory

Usage:
    python3 scripts/generate_synthetic.py [options]

Options:
    --output-dir DIR    Output directory (default: build/)
    --num-reads N       Number of reads per well/plate combo (default: 10)
    --read-length N     Length of random sequence portion (default: 100)
    --wells N           Number of wells to include (default: 3)
    --plates N          Number of plates to include (default: 2)
    --noise-reads N     Number of noise reads (unknown barcodes) (default: 5)
    --seed N            Random seed for reproducibility (default: 42)
"""

import argparse
import csv
import gzip
import os
import random
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic TIRTL-seq FASTQ files"
    )
    parser.add_argument(
        "--output-dir", type=str, default="build",
        help="Output directory (default: build/)"
    )
    parser.add_argument(
        "--num-reads", type=int, default=10,
        help="Number of reads per well/plate combination (default: 10)"
    )
    parser.add_argument(
        "--read-length", type=int, default=100,
        help="Length of random sequence portion (default: 100)"
    )
    parser.add_argument(
        "--wells", type=int, default=3,
        help="Number of wells to include (default: 3)"
    )
    parser.add_argument(
        "--plates", type=int, default=2,
        help="Number of plates to include (default: 2)"
    )
    parser.add_argument(
        "--noise-reads", type=int, default=5,
        help="Number of noise reads with unknown barcodes (default: 5)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--well-barcode-file", type=str, default=None,
        help="Path to well barcode CSV (default: auto-detect)"
    )
    parser.add_argument(
        "--plate-barcode-file", type=str, default=None,
        help="Path to plate barcode CSV (default: auto-detect)"
    )
    return parser.parse_args()


def find_project_root():
    """Find project root by looking for _milestone directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "_milestone").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent


def load_well_barcodes(filepath):
    """Load well barcodes from CSV file."""
    barcodes = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            barcodes.append({
                "row": row["Row"],
                "column": row["Column"],
                "i5_name": row["i5_name"],
                "i5_sequence": row["i5_sequence"],
                "i7_name": row["i7_name"],
                "i7_sequence": row["i7_sequence"],
            })
    return barcodes


def load_plate_barcodes(filepath):
    """Load plate barcodes from CSV file.

    Note: TIRTL plate barcodes have a common Nextera adapter prefix (33bp).
    The unique plate-identifying portion starts at position 33.
    We extract both the full sequence and the unique portion for use.
    """
    # Common Nextera adapter prefix length
    ADAPTER_PREFIX_LEN = 33

    barcodes = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            full_seq = row["sequence"]
            # Use the full sequence (Adapter + Unique) as the prefix
            # This ensures R1 starts with TCGTCGGCAG... as expected by documentation
            barcodes.append({
                "name": row["name"],
                "sequence": full_seq,
                "unique_prefix": full_seq[:50],  # Use first 50bp (Adapter + ID)
            })
    return barcodes


def generate_random_sequence(length):
    """Generate a random DNA sequence."""
    return "".join(random.choices("ACGT", k=length))


def generate_quality_string(length, min_qual=30, max_qual=40):
    """Generate a quality string with high-quality scores."""
    quals = [random.randint(min_qual, max_qual) for _ in range(length)]
    return "".join(chr(q + 33) for q in quals)


def generate_illumina_header(instrument, run, flowcell, lane, tile, x, y,
                             read_num, is_filtered, control, index):
    """
    Generate Illumina-format FASTQ header.

    Format: @<instrument>:<run>:<flowcell>:<lane>:<tile>:<x>:<y> <read>:<filtered>:<control>:<index>

    Example: @M00123:1:000000000-A1B2C:1:1101:15234:1234 1:N:0:ATCACG+GCTAGC
    """
    return f"@{instrument}:{run}:{flowcell}:{lane}:{tile}:{x}:{y} {read_num}:{is_filtered}:{control}:{index}"


class SyntheticFASTQGenerator:
    """Generate synthetic FASTQ files with known barcodes."""

    def __init__(self, well_barcodes, plate_barcodes, seed=42):
        self.well_barcodes = well_barcodes
        self.plate_barcodes = plate_barcodes
        self.seed = seed
        random.seed(seed)

        # Illumina header components
        self.instrument = "M00123"
        self.run = 1
        self.flowcell = "000000000-SYNTH"
        self.lane = 1
        self.tile = 1101
        self.read_counter = 0

    def _next_coords(self):
        """Generate next x, y coordinates."""
        self.read_counter += 1
        x = 10000 + (self.read_counter % 10000)
        y = 10000 + (self.read_counter // 10000)
        return x, y

    def generate_read_pair(self, well, plate, read_length):
        """
        Generate a paired-end read with embedded barcodes.

        TIRTL-seq structure (simplified for synthetic data):
        R1: [plate_barcode_prefix] + [random_insert] + [well_i5_suffix]
        R2: [well_i7_prefix] + [random_insert]

        The actual barcode positions will be determined by recon tool.
        For synthetic data, we embed them at predictable positions.
        """
        x, y = self._next_coords()

        # Create index string for header (i5+i7)
        index_str = f"{well['i5_name']}+{well['i7_name']}"

        # Generate headers
        header_r1 = generate_illumina_header(
            self.instrument, self.run, self.flowcell, self.lane,
            self.tile, x, y, 1, "N", 0, index_str
        )
        header_r2 = generate_illumina_header(
            self.instrument, self.run, self.flowcell, self.lane,
            self.tile, x, y, 2, "N", 0, index_str
        )

        # Generate sequences with barcodes
        # R1: unique plate barcode prefix (12bp) + random insert
        # Using unique_prefix which is the plate-identifying portion after adapter
        plate_prefix = plate["unique_prefix"]
        prefix_len = len(plate_prefix)
        random_insert_r1 = generate_random_sequence(read_length - prefix_len)
        seq_r1 = plate_prefix + random_insert_r1

        # R2: well i7 barcode (first 10bp) + random insert
        well_prefix = well["i7_name"]
        random_insert_r2 = generate_random_sequence(read_length - 10)
        seq_r2 = well_prefix + random_insert_r2

        # Generate quality strings
        qual_r1 = generate_quality_string(len(seq_r1))
        qual_r2 = generate_quality_string(len(seq_r2))

        return (
            (header_r1, seq_r1, qual_r1),
            (header_r2, seq_r2, qual_r2)
        )

    def generate_noise_read(self, read_length):
        """
        Generate a noise read pair with random (non-matching) barcodes.

        These reads have barcodes that don't match any known well/plate,
        simulating sequencing noise or unknown samples.
        """
        x, y = self._next_coords()

        # Generate random 10bp "barcodes" that are unlikely to match known ones
        fake_i5 = generate_random_sequence(10)
        fake_i7 = generate_random_sequence(10)
        index_str = f"{fake_i5}+{fake_i7}"

        # Generate headers
        header_r1 = generate_illumina_header(
            self.instrument, self.run, self.flowcell, self.lane,
            self.tile, x, y, 1, "N", 0, index_str
        )
        header_r2 = generate_illumina_header(
            self.instrument, self.run, self.flowcell, self.lane,
            self.tile, x, y, 2, "N", 0, index_str
        )

        # Generate fully random sequences (no valid barcode prefix)
        seq_r1 = generate_random_sequence(read_length)
        seq_r2 = generate_random_sequence(read_length)

        # Generate quality strings
        qual_r1 = generate_quality_string(len(seq_r1))
        qual_r2 = generate_quality_string(len(seq_r2))

        return (
            (header_r1, seq_r1, qual_r1),
            (header_r2, seq_r2, qual_r2)
        )

    def generate_fastq(self, output_dir, num_reads, read_length,
                       num_wells, num_plates, noise_reads=0):
        """Generate synthetic FASTQ files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Select subset of barcodes
        wells = self.well_barcodes[:num_wells]
        plates = self.plate_barcodes[:num_plates]

        r1_path = output_path / "synthetic_R1.fq.gz"
        r2_path = output_path / "synthetic_R2.fq.gz"

        # Track what we generate for verification
        manifest = []

        with gzip.open(r1_path, "wt") as f1, gzip.open(r2_path, "wt") as f2:
            for well in wells:
                for plate in plates:
                    for _ in range(num_reads):
                        r1, r2 = self.generate_read_pair(well, plate, read_length)

                        # Write R1
                        f1.write(f"{r1[0]}\n{r1[1]}\n+\n{r1[2]}\n")
                        # Write R2
                        f2.write(f"{r2[0]}\n{r2[1]}\n+\n{r2[2]}\n")

                    manifest.append({
                        "well": f"{well['row']}{well['column']}",
                        "plate": plate["name"],
                        "i5_name": well["i5_name"],
                        "i7_name": well["i7_name"],
                        "plate_prefix": plate["unique_prefix"],
                        "num_reads": num_reads,
                    })

            # Generate noise reads (unknown barcodes)
            for _ in range(noise_reads):
                r1, r2 = self.generate_noise_read(read_length)
                f1.write(f"{r1[0]}\n{r1[1]}\n+\n{r1[2]}\n")
                f2.write(f"{r2[0]}\n{r2[1]}\n+\n{r2[2]}\n")

        # Add noise entry to manifest
        if noise_reads > 0:
            manifest.append({
                "well": "UNKNOWN",
                "plate": "UNKNOWN",
                "i5_name": "RANDOM",
                "i7_name": "RANDOM",
                "plate_prefix": "RANDOM",
                "num_reads": noise_reads,
            })

        # Write manifest
        manifest_path = output_path / "synthetic_manifest.csv"
        with open(manifest_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "well", "plate", "i5_name", "i7_name", "plate_prefix", "num_reads"
            ])
            writer.writeheader()
            writer.writerows(manifest)

        known_reads = num_wells * num_plates * num_reads
        total_reads = known_reads + noise_reads

        return {
            "r1_path": str(r1_path),
            "r2_path": str(r2_path),
            "manifest_path": str(manifest_path),
            "total_reads": total_reads,
            "known_reads": known_reads,
            "noise_reads": noise_reads,
            "wells_used": num_wells,
            "plates_used": num_plates,
        }


def main():
    args = parse_args()

    # Find project root
    project_root = find_project_root()

    # Locate barcode files
    if args.well_barcode_file:
        well_file = Path(args.well_barcode_file)
    else:
        well_file = project_root / "TIRTL_barcode_well.csv"

    if args.plate_barcode_file:
        plate_file = Path(args.plate_barcode_file)
    else:
        plate_file = project_root / "TIRTL_barcode_plate.csv"

    # Validate files exist
    if not well_file.exists():
        print(f"ERROR: Well barcode file not found: {well_file}", file=sys.stderr)
        sys.exit(1)

    if not plate_file.exists():
        print(f"ERROR: Plate barcode file not found: {plate_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading well barcodes from: {well_file}")
    print(f"Loading plate barcodes from: {plate_file}")

    # Load barcodes
    well_barcodes = load_well_barcodes(well_file)
    plate_barcodes = load_plate_barcodes(plate_file)

    print(f"Loaded {len(well_barcodes)} well barcodes")
    print(f"Loaded {len(plate_barcodes)} plate barcodes")

    # Validate we have enough barcodes
    if len(well_barcodes) < args.wells:
        print(f"WARNING: Requested {args.wells} wells but only {len(well_barcodes)} available")
        args.wells = len(well_barcodes)

    if len(plate_barcodes) < args.plates:
        print(f"WARNING: Requested {args.plates} plates but only {len(plate_barcodes)} available")
        args.plates = len(plate_barcodes)

    # Determine output directory
    if os.path.isabs(args.output_dir):
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / args.output_dir

    # Generate synthetic data
    generator = SyntheticFASTQGenerator(well_barcodes, plate_barcodes, args.seed)

    print(f"\nGenerating synthetic FASTQ files...")
    print(f"  Output directory: {output_dir}")
    print(f"  Wells: {args.wells}")
    print(f"  Plates: {args.plates}")
    print(f"  Reads per combination: {args.num_reads}")
    print(f"  Noise reads: {args.noise_reads}")
    print(f"  Read length: {args.read_length}")
    print(f"  Random seed: {args.seed}")

    result = generator.generate_fastq(
        output_dir,
        args.num_reads,
        args.read_length,
        args.wells,
        args.plates,
        args.noise_reads
    )

    print(f"\nGeneration complete!")
    print(f"  R1: {result['r1_path']}")
    print(f"  R2: {result['r2_path']}")
    print(f"  Manifest: {result['manifest_path']}")
    print(f"  Known reads: {result['known_reads']}")
    print(f"  Noise reads: {result['noise_reads']}")
    print(f"  Total reads: {result['total_reads']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
