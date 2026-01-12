#!/usr/bin/env python3
"""
recon_fastq.py - FASTQ Reconnaissance Tool for TIRTL-seq

Analyzes FASTQ files to determine barcode positions and structure.
Helps lock down demultiplex parameters before running full pipeline.

AC-002 Requirements:
- Accept R1/R2 input (optional I1/I2)
- Analyze header structure (detect index presence)
- Sample reads and count sequence slice frequencies
- Output analysis to help identify barcode positions

Usage:
    python3 scripts/recon_fastq.py --r1 <R1.fq.gz> --r2 <R2.fq.gz> [options]

Options:
    --r1 FILE           R1 FASTQ file (required)
    --r2 FILE           R2 FASTQ file (required)
    --i1 FILE           I1 index FASTQ file (optional)
    --i2 FILE           I2 index FASTQ file (optional)
    --sample-size N     Number of reads to sample (default: 1000)
    --window-size N     Size of sequence window to analyze (default: 20)
    --top-n N           Show top N most frequent sequences (default: 10)
    --output FILE       Output report file (default: stdout)
    --json FILE         Output JSON report file (optional)
"""

import argparse
import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="FASTQ Reconnaissance Tool for TIRTL-seq"
    )
    parser.add_argument(
        "--r1", type=str, required=True,
        help="R1 FASTQ file (required)"
    )
    parser.add_argument(
        "--r2", type=str, required=True,
        help="R2 FASTQ file (required)"
    )
    parser.add_argument(
        "--i1", type=str, default=None,
        help="I1 index FASTQ file (optional)"
    )
    parser.add_argument(
        "--i2", type=str, default=None,
        help="I2 index FASTQ file (optional)"
    )
    parser.add_argument(
        "--sample-size", type=int, default=1000,
        help="Number of reads to sample (default: 1000)"
    )
    parser.add_argument(
        "--window-size", type=int, default=20,
        help="Size of sequence window to analyze (default: 20)"
    )
    parser.add_argument(
        "--top-n", type=int, default=10,
        help="Show top N most frequent sequences (default: 10)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output report file (default: stdout)"
    )
    parser.add_argument(
        "--json", type=str, default=None,
        help="Output JSON report file (optional)"
    )
    return parser.parse_args()


def open_fastq(filepath):
    """Open FASTQ file, handling gzip compression."""
    path = Path(filepath)
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return open(path, "r")


def parse_illumina_header(header):
    """
    Parse Illumina FASTQ header format.

    Format: @<instrument>:<run>:<flowcell>:<lane>:<tile>:<x>:<y> <read>:<filtered>:<control>:<index>

    Returns dict with parsed fields or None if not Illumina format.
    """
    # Remove @ prefix
    header = header.lstrip("@").strip()

    # Split into instrument part and read info part
    parts = header.split(" ")

    result = {
        "raw": header,
        "is_illumina": False,
        "has_index": False,
        "index": None,
        "instrument_info": None,
        "read_info": None,
    }

    if len(parts) >= 1:
        # Parse instrument info: instrument:run:flowcell:lane:tile:x:y
        inst_parts = parts[0].split(":")
        if len(inst_parts) >= 7:
            result["is_illumina"] = True
            result["instrument_info"] = {
                "instrument": inst_parts[0],
                "run": inst_parts[1],
                "flowcell": inst_parts[2],
                "lane": inst_parts[3],
                "tile": inst_parts[4],
                "x": inst_parts[5],
                "y": inst_parts[6],
            }

    if len(parts) >= 2:
        # Parse read info: read:filtered:control:index
        read_parts = parts[1].split(":")
        if len(read_parts) >= 4:
            result["read_info"] = {
                "read_number": read_parts[0],
                "is_filtered": read_parts[1],
                "control": read_parts[2],
                "index": read_parts[3],
            }
            if read_parts[3] and read_parts[3] != "0":
                result["has_index"] = True
                result["index"] = read_parts[3]

    return result


def read_fastq_sample(filepath, sample_size):
    """Read a sample of reads from FASTQ file."""
    reads = []
    count = 0

    with open_fastq(filepath) as f:
        while count < sample_size:
            # Read 4 lines per record
            header = f.readline().strip()
            if not header:
                break
            seq = f.readline().strip()
            plus = f.readline().strip()
            qual = f.readline().strip()

            if header and seq:
                reads.append({
                    "header": header,
                    "sequence": seq,
                    "quality": qual,
                })
                count += 1

    return reads


def analyze_headers(reads):
    """Analyze header structure across sampled reads."""
    results = {
        "total_sampled": len(reads),
        "illumina_format_count": 0,
        "has_index_count": 0,
        "index_patterns": Counter(),
        "instruments": Counter(),
        "flowcells": Counter(),
    }

    for read in reads:
        parsed = parse_illumina_header(read["header"])

        if parsed["is_illumina"]:
            results["illumina_format_count"] += 1

            if parsed["instrument_info"]:
                results["instruments"][parsed["instrument_info"]["instrument"]] += 1
                results["flowcells"][parsed["instrument_info"]["flowcell"]] += 1

        if parsed["has_index"]:
            results["has_index_count"] += 1
            results["index_patterns"][parsed["index"]] += 1

    return results


def analyze_sequence_windows(reads, window_size, positions=None):
    """
    Analyze sequence content at different positions.

    Returns frequency counts for sequence windows at each position.
    """
    if positions is None:
        # Default: analyze start and end positions
        positions = [
            ("start", 0, window_size),
            ("start+20", 20, 20 + window_size),
            ("start+40", 40, 40 + window_size),
        ]

    results = {}

    for name, start, end in positions:
        counter = Counter()
        valid_count = 0

        for read in reads:
            seq = read["sequence"]
            if len(seq) >= end:
                window = seq[start:end]
                counter[window] += 1
                valid_count += 1

        results[name] = {
            "position": f"{start}-{end}",
            "valid_reads": valid_count,
            "unique_sequences": len(counter),
            "frequencies": counter,
        }

    return results


def analyze_barcode_candidates(window_results, known_barcodes=None):
    """
    Identify potential barcode positions based on sequence frequency patterns.

    Barcode regions typically show:
    - High frequency for a small set of sequences (the barcodes)
    - Low frequency for random sequences
    """
    candidates = []

    for position_name, data in window_results.items():
        freqs = data["frequencies"]
        total = sum(freqs.values())
        unique = data["unique_sequences"]

        if total == 0:
            continue

        # Get top sequences
        top_seqs = freqs.most_common(20)

        # Calculate concentration ratio (how much top sequences dominate)
        top_10_count = sum(count for _, count in top_seqs[:10])
        concentration = top_10_count / total if total > 0 else 0

        # Calculate entropy-like measure
        # Low unique count + high concentration = likely barcode
        is_candidate = (
            unique < total * 0.5 and  # Less than 50% unique
            concentration > 0.5       # Top 10 cover >50% of reads
        )

        candidates.append({
            "position": position_name,
            "range": data["position"],
            "unique_sequences": unique,
            "total_reads": total,
            "concentration_ratio": round(concentration, 3),
            "is_barcode_candidate": is_candidate,
            "top_sequences": [(seq, count, round(count/total*100, 1))
                             for seq, count in top_seqs[:10]],
        })

    return candidates


def format_report(r1_analysis, r2_analysis, i1_analysis=None, i2_analysis=None):
    """Format analysis results into a readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("TIRTL-seq FASTQ Reconnaissance Report")
    lines.append("=" * 60)
    lines.append("")

    # R1 Analysis
    lines.append("-" * 40)
    lines.append("R1 Analysis")
    lines.append("-" * 40)
    lines.append("")

    # Header analysis
    h = r1_analysis["headers"]
    lines.append(f"Header Structure:")
    lines.append(f"  Sampled reads: {h['total_sampled']}")
    lines.append(f"  Illumina format: {h['illumina_format_count']} ({h['illumina_format_count']/h['total_sampled']*100:.1f}%)")
    lines.append(f"  Has index in header: {h['has_index_count']} ({h['has_index_count']/h['total_sampled']*100:.1f}%)")

    if h["index_patterns"]:
        lines.append(f"  Top index patterns:")
        for idx, count in h["index_patterns"].most_common(5):
            lines.append(f"    {idx}: {count}")
    lines.append("")

    # Sequence analysis
    lines.append("Sequence Window Analysis:")
    for candidate in r1_analysis["barcode_candidates"]:
        status = "BARCODE CANDIDATE" if candidate["is_barcode_candidate"] else "likely random"
        lines.append(f"\n  Position {candidate['position']} ({candidate['range']}):")
        lines.append(f"    Unique sequences: {candidate['unique_sequences']}")
        lines.append(f"    Concentration ratio: {candidate['concentration_ratio']} [{status}]")
        lines.append(f"    Top sequences:")
        for seq, count, pct in candidate["top_sequences"][:5]:
            lines.append(f"      {seq}: {count} ({pct}%)")

    lines.append("")

    # R2 Analysis
    lines.append("-" * 40)
    lines.append("R2 Analysis")
    lines.append("-" * 40)
    lines.append("")

    h = r2_analysis["headers"]
    lines.append(f"Header Structure:")
    lines.append(f"  Sampled reads: {h['total_sampled']}")
    lines.append(f"  Illumina format: {h['illumina_format_count']} ({h['illumina_format_count']/h['total_sampled']*100:.1f}%)")
    lines.append(f"  Has index in header: {h['has_index_count']} ({h['has_index_count']/h['total_sampled']*100:.1f}%)")
    lines.append("")

    lines.append("Sequence Window Analysis:")
    for candidate in r2_analysis["barcode_candidates"]:
        status = "BARCODE CANDIDATE" if candidate["is_barcode_candidate"] else "likely random"
        lines.append(f"\n  Position {candidate['position']} ({candidate['range']}):")
        lines.append(f"    Unique sequences: {candidate['unique_sequences']}")
        lines.append(f"    Concentration ratio: {candidate['concentration_ratio']} [{status}]")
        lines.append(f"    Top sequences:")
        for seq, count, pct in candidate["top_sequences"][:5]:
            lines.append(f"      {seq}: {count} ({pct}%)")

    lines.append("")
    lines.append("=" * 60)
    lines.append("End of Report")
    lines.append("=" * 60)

    return "\n".join(lines)


def run_recon(r1_path, r2_path, i1_path=None, i2_path=None,
              sample_size=1000, window_size=20, top_n=10):
    """Run full reconnaissance analysis."""

    results = {
        "r1": None,
        "r2": None,
        "i1": None,
        "i2": None,
        "summary": {},
    }

    # Analyze R1
    print(f"Analyzing R1: {r1_path}", file=sys.stderr)
    r1_reads = read_fastq_sample(r1_path, sample_size)
    r1_headers = analyze_headers(r1_reads)
    r1_windows = analyze_sequence_windows(r1_reads, window_size)
    r1_candidates = analyze_barcode_candidates(r1_windows)

    results["r1"] = {
        "file": str(r1_path),
        "reads_sampled": len(r1_reads),
        "headers": r1_headers,
        "windows": {k: {**v, "frequencies": dict(v["frequencies"].most_common(top_n))}
                   for k, v in r1_windows.items()},
        "barcode_candidates": r1_candidates,
    }

    # Analyze R2
    print(f"Analyzing R2: {r2_path}", file=sys.stderr)
    r2_reads = read_fastq_sample(r2_path, sample_size)
    r2_headers = analyze_headers(r2_reads)
    r2_windows = analyze_sequence_windows(r2_reads, window_size)
    r2_candidates = analyze_barcode_candidates(r2_windows)

    results["r2"] = {
        "file": str(r2_path),
        "reads_sampled": len(r2_reads),
        "headers": r2_headers,
        "windows": {k: {**v, "frequencies": dict(v["frequencies"].most_common(top_n))}
                   for k, v in r2_windows.items()},
        "barcode_candidates": r2_candidates,
    }

    # Analyze I1 if provided
    if i1_path:
        print(f"Analyzing I1: {i1_path}", file=sys.stderr)
        i1_reads = read_fastq_sample(i1_path, sample_size)
        i1_headers = analyze_headers(i1_reads)
        i1_windows = analyze_sequence_windows(i1_reads, window_size,
                                               [("full", 0, window_size)])
        i1_candidates = analyze_barcode_candidates(i1_windows)

        results["i1"] = {
            "file": str(i1_path),
            "reads_sampled": len(i1_reads),
            "headers": i1_headers,
            "windows": {k: {**v, "frequencies": dict(v["frequencies"].most_common(top_n))}
                       for k, v in i1_windows.items()},
            "barcode_candidates": i1_candidates,
        }

    # Analyze I2 if provided
    if i2_path:
        print(f"Analyzing I2: {i2_path}", file=sys.stderr)
        i2_reads = read_fastq_sample(i2_path, sample_size)
        i2_headers = analyze_headers(i2_reads)
        i2_windows = analyze_sequence_windows(i2_reads, window_size,
                                               [("full", 0, window_size)])
        i2_candidates = analyze_barcode_candidates(i2_windows)

        results["i2"] = {
            "file": str(i2_path),
            "reads_sampled": len(i2_reads),
            "headers": i2_headers,
            "windows": {k: {**v, "frequencies": dict(v["frequencies"].most_common(top_n))}
                       for k, v in i2_windows.items()},
            "barcode_candidates": i2_candidates,
        }

    # Generate summary
    results["summary"] = {
        "r1_has_index_in_header": r1_headers["has_index_count"] > 0,
        "r2_has_index_in_header": r2_headers["has_index_count"] > 0,
        "r1_barcode_positions": [c["position"] for c in r1_candidates if c["is_barcode_candidate"]],
        "r2_barcode_positions": [c["position"] for c in r2_candidates if c["is_barcode_candidate"]],
    }

    return results


def main():
    args = parse_args()

    # Validate input files exist
    for path, name in [(args.r1, "R1"), (args.r2, "R2")]:
        if not Path(path).exists():
            print(f"ERROR: {name} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    for path, name in [(args.i1, "I1"), (args.i2, "I2")]:
        if path and not Path(path).exists():
            print(f"ERROR: {name} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    # Run analysis
    results = run_recon(
        args.r1, args.r2, args.i1, args.i2,
        args.sample_size, args.window_size, args.top_n
    )

    # Generate text report
    report = format_report(results["r1"], results["r2"], results.get("i1"), results.get("i2"))

    # Output text report
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report saved to: {args.output}", file=sys.stderr)
    else:
        print(report)

    # Output JSON if requested
    if args.json:
        # Convert Counter objects for JSON serialization
        def convert_counters(obj):
            if isinstance(obj, Counter):
                return dict(obj)
            elif isinstance(obj, dict):
                return {k: convert_counters(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_counters(i) for i in obj]
            return obj

        json_results = convert_counters(results)
        with open(args.json, "w") as f:
            json.dump(json_results, f, indent=2)
        print(f"JSON report saved to: {args.json}", file=sys.stderr)

    # Print summary to stderr
    print("\n--- Summary ---", file=sys.stderr)
    print(f"R1 barcode candidates: {results['summary']['r1_barcode_positions']}", file=sys.stderr)
    print(f"R2 barcode candidates: {results['summary']['r2_barcode_positions']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
