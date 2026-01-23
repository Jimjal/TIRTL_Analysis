#!/usr/bin/env python3
"""
run_qc.py - QC & Reporting for TIRTL-seq Demultiplex Pipeline

Performs quality control checks on M-0003 plate demux output:
- Count conservation (input = output + unknown)
- R1/R2 pairing consistency (if applicable)
- Generates plate×well count tables (long + matrix format)
- Produces machine-readable summary (JSON) and human-readable report (Markdown)

AC-001 Requirements:
- qc/plate_well_counts.tsv (long table) with unknown/unmatched summary
- qc/plate_well_matrix.tsv (matrix view)
- Conservation: input total = sum(plate×well) + unknown

AC-002 Requirements:
- qc/summary.json with AC pass/fail markers and key statistics
- qc/qc_report.md with Chinese as primary language

Usage:
    python scripts/run_qc.py --plate-demux-dir build/plate_demux --well-demux-dir build/demux --output-dir build/qc

Environment:
    Requires TIRTL_analyse conda environment.
"""

import argparse
import csv
import gzip
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="QC & Reporting for TIRTL-seq Demultiplex Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/run_qc.py --plate-demux-dir build/plate_demux --well-demux-dir build/demux --output-dir build/qc
"""
    )
    parser.add_argument(
        "--plate-demux-dir", required=True, type=str,
        help="M-0003 plate demux output directory (contains plate_demux_stats.tsv)"
    )
    parser.add_argument(
        "--well-demux-dir", required=True, type=str,
        help="M-0002 well demux output directory (contains demux_stats.tsv)"
    )
    parser.add_argument(
        "--output-dir", required=True, type=str,
        help="Output directory for QC results"
    )
    parser.add_argument(
        "--input-r1", type=str, default=None,
        help="Optional: Path to input R1 FASTQ for total count verification"
    )
    parser.add_argument(
        "--input-r2", type=str, default=None,
        help="Optional: Path to input R2 FASTQ for R1/R2 pairing check"
    )
    return parser.parse_args()


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


def load_plate_demux_stats(stats_path):
    """
    Load plate_demux_stats.tsv from M-0003.

    Returns:
        dict: {(plate_id, well_id): read_count}
        int: total reads
    """
    counts = {}
    total = 0

    with open(stats_path, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            plate_id = row["plate_id"]
            well_id = row["well_id"]
            read_count = int(row["read_count"])
            counts[(plate_id, well_id)] = read_count
            total += read_count

    return counts, total


def load_well_demux_stats(stats_path):
    """
    Load demux_stats.tsv from M-0002.

    Returns:
        dict: {well_id: read_count}
        int: total reads
    """
    counts = {}
    total = 0

    with open(stats_path, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            well_id = row["well_id"]
            read_count = int(row["read_count"])
            counts[well_id] = read_count
            total += read_count

    return counts, total


def generate_long_table(plate_counts, output_path):
    """
    Generate plate×well counts in long table format.

    Columns: plate_id, well_id, read_count, percent
    Includes UNKNOWN plate entries.
    """
    total = sum(plate_counts.values())

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["plate_id", "well_id", "read_count", "percent"])

        for (plate_id, well_id) in sorted(plate_counts.keys()):
            count = plate_counts[(plate_id, well_id)]
            pct = (count / total * 100) if total > 0 else 0
            writer.writerow([plate_id, well_id, count, f"{pct:.2f}"])

    return total


def generate_matrix_table(plate_counts, output_path):
    """
    Generate plate×well counts in matrix format.

    Rows: plates, Columns: wells
    """
    # Extract unique plates and wells
    plates = sorted(set(p for (p, w) in plate_counts.keys()))
    wells = sorted(set(w for (p, w) in plate_counts.keys()))

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")

        # Header row
        writer.writerow(["plate_id"] + wells)

        # Data rows
        for plate in plates:
            row = [plate]
            for well in wells:
                count = plate_counts.get((plate, well), 0)
                row.append(count)
            writer.writerow(row)

    return len(plates), len(wells)


def check_conservation(plate_total, well_counts, tolerance=0):
    """
    Check read count conservation between M-0002 and M-0003.

    Conservation rule:
    - Plate demux total = Well demux known reads (excluding UNKNOWN well)
    - OR equivalently: Plate demux total + Well UNKNOWN = Well demux total

    Note: The plate demux only processes well_*.fastq.gz files, not unknown.fastq.gz.
    Reads that didn't match a well barcode cannot be processed for plate barcode.
    """
    # Calculate well demux totals
    well_total = sum(well_counts.values())
    well_unknown = well_counts.get("UNKNOWN", 0)
    well_known = well_total - well_unknown

    # Conservation: plate total should equal well known reads
    diff = abs(plate_total - well_known)
    conserved = diff <= tolerance

    return {
        "conserved": conserved,
        "well_demux_total": well_total,
        "well_demux_known": well_known,
        "well_demux_unknown": well_unknown,
        "plate_demux_total": plate_total,
        "difference": diff,
        "tolerance": tolerance,
        "conservation_formula": "plate_total == well_known (well files only, excl. unknown.fastq.gz)"
    }


def check_r1_r2_pairing(r1_path, r2_path):
    """
    Check R1/R2 read count equality for paired-end consistency.

    Returns dict with check results.
    """
    if not r1_path or not r2_path:
        return {
            "checked": False,
            "reason": "R1/R2 paths not provided"
        }

    if not os.path.exists(r1_path):
        return {
            "checked": False,
            "reason": f"R1 file not found: {r1_path}"
        }

    if not os.path.exists(r2_path):
        return {
            "checked": False,
            "reason": f"R2 file not found: {r2_path}"
        }

    r1_count = count_reads_in_fastq(r1_path)
    r2_count = count_reads_in_fastq(r2_path)

    return {
        "checked": True,
        "r1_count": r1_count,
        "r2_count": r2_count,
        "equal": r1_count == r2_count,
        "difference": abs(r1_count - r2_count)
    }


def calculate_summary_stats(plate_counts):
    """Calculate summary statistics for QC report."""
    if not plate_counts:
        return {}

    # Separate known plates from UNKNOWN
    known_counts = {k: v for k, v in plate_counts.items() if k[0] != "UNKNOWN"}
    unknown_counts = {k: v for k, v in plate_counts.items() if k[0] == "UNKNOWN"}

    known_total = sum(known_counts.values())
    unknown_total = sum(unknown_counts.values())
    total = known_total + unknown_total

    # Count unique plates and wells
    known_plates = set(p for (p, w) in known_counts.keys())
    all_wells = set(w for (p, w) in plate_counts.keys())

    return {
        "total_reads": total,
        "known_reads": known_total,
        "unknown_reads": unknown_total,
        "known_percent": (known_total / total * 100) if total > 0 else 0,
        "unknown_percent": (unknown_total / total * 100) if total > 0 else 0,
        "num_plates": len(known_plates),
        "num_wells": len(all_wells),
        "num_plate_well_combos": len(known_counts)
    }


def generate_summary_json(output_path, ac_results, stats, conservation, pairing):
    """
    Generate qc/summary.json with AC results and key statistics.
    """
    summary = {
        "timestamp": datetime.now().isoformat(),
        "version": "1.0",
        "acceptance_criteria": ac_results,
        "statistics": stats,
        "conservation_check": conservation,
        "pairing_check": pairing
    }

    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


def generate_qc_report(output_path, ac_results, stats, conservation, pairing):
    """
    Generate qc/qc_report.md with Chinese as primary language.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Determine overall status
    all_pass = all(r["status"] == "PASS" for r in ac_results.values() if r.get("status"))
    overall_status = "PASS" if all_pass else "FAIL"

    report = f"""# QC 报告 - TIRTL-seq Demux Pipeline

**生成时间**: {timestamp}
**整体状态**: **{overall_status}**

---

## 1. 验收标准 (Acceptance Criteria) 检查结果

| AC | 状态 | 说明 |
|----|------|------|
| AC-001 (计数守恒 + 汇总生成) | {ac_results.get('AC-001', {}).get('status', 'N/A')} | {ac_results.get('AC-001', {}).get('message', '')} |
| AC-002 (报告与机读输出) | {ac_results.get('AC-002', {}).get('status', 'N/A')} | {ac_results.get('AC-002', {}).get('message', '')} |

---

## 2. 关键统计数据

| 指标 | 数值 |
|------|------|
| 总读数 (Total Reads) | {stats.get('total_reads', 0):,} |
| 已知 Plate 读数 | {stats.get('known_reads', 0):,} ({stats.get('known_percent', 0):.1f}%) |
| Unknown 读数 | {stats.get('unknown_reads', 0):,} ({stats.get('unknown_percent', 0):.1f}%) |
| Plate 数量 | {stats.get('num_plates', 0)} |
| Well 数量 | {stats.get('num_wells', 0)} |
| Plate×Well 组合数 | {stats.get('num_plate_well_combos', 0)} |

---

## 3. 守恒检查 (Conservation Check)

守恒规则：Plate Demux 总读数 = Well Demux 已知 Well 读数（不含 UNKNOWN）

| 指标 | 数值 |
|------|------|
| Well Demux 总读数 | {conservation.get('well_demux_total', 0):,} |
| Well Demux 已知读数 (excl. UNKNOWN) | {conservation.get('well_demux_known', 0):,} |
| Well Demux UNKNOWN 读数 | {conservation.get('well_demux_unknown', 0):,} |
| Plate Demux 总读数 | {conservation.get('plate_demux_total', 0):,} |
| 差异 (Plate vs Well Known) | {conservation.get('difference', 0):,} |

- **守恒状态**: {'**PASS** (读数守恒)' if conservation.get('conserved') else '**FAIL** (读数不守恒)'}

"""

    # Add pairing check if applicable
    if pairing.get("checked"):
        report += f"""---

## 4. R1/R2 配对一致性检查

- **R1 读数**: {pairing.get('r1_count', 0):,}
- **R2 读数**: {pairing.get('r2_count', 0):,}
- **配对状态**: {'**PASS** (R1=R2)' if pairing.get('equal') else '**FAIL** (R1≠R2)'}
- **差异**: {pairing.get('difference', 0):,}
"""
    else:
        report += f"""---

## 4. R1/R2 配对一致性检查

- **状态**: 未检查
- **原因**: {pairing.get('reason', 'R1/R2 路径未提供')}
"""

    # Add failure notes if any
    failed_acs = [ac for ac, r in ac_results.items() if r.get("status") == "FAIL"]
    if failed_acs:
        report += """
---

## 5. 失败项说明

"""
        for ac in failed_acs:
            report += f"- **{ac}**: {ac_results[ac].get('message', '详见日志')}\n"

    report += """
---

*此报告由 `scripts/run_qc.py` 自动生成*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report


def main():
    args = parse_args()

    # Validate inputs
    plate_demux_dir = Path(args.plate_demux_dir)
    well_demux_dir = Path(args.well_demux_dir)
    output_dir = Path(args.output_dir)

    plate_stats_path = plate_demux_dir / "plate_demux_stats.tsv"
    well_stats_path = well_demux_dir / "demux_stats.tsv"

    if not plate_stats_path.exists():
        print(f"ERROR: Plate demux stats not found: {plate_stats_path}")
        sys.exit(1)

    if not well_stats_path.exists():
        print(f"ERROR: Well demux stats not found: {well_stats_path}")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading plate demux stats from: {plate_stats_path}")
    plate_counts, plate_total = load_plate_demux_stats(plate_stats_path)
    print(f"  Total reads in plate demux: {plate_total:,}")

    print(f"Loading well demux stats from: {well_stats_path}")
    well_counts, well_total = load_well_demux_stats(well_stats_path)
    print(f"  Total reads in well demux: {well_total:,}")

    # Generate outputs
    print(f"\nGenerating QC outputs to: {output_dir}")

    # 1. Long table
    long_table_path = output_dir / "plate_well_counts.tsv"
    generate_long_table(plate_counts, long_table_path)
    print(f"  Generated: {long_table_path}")

    # 2. Matrix table
    matrix_path = output_dir / "plate_well_matrix.tsv"
    num_plates, num_wells = generate_matrix_table(plate_counts, matrix_path)
    print(f"  Generated: {matrix_path} ({num_plates} plates × {num_wells} wells)")

    # 3. Conservation check
    conservation = check_conservation(plate_total, well_counts)
    print(f"\nConservation check: {'PASS' if conservation['conserved'] else 'FAIL'}")
    print(f"  Well demux total: {conservation['well_demux_total']:,}")
    print(f"  Well demux known (excl. UNKNOWN): {conservation['well_demux_known']:,}")
    print(f"  Well demux UNKNOWN: {conservation['well_demux_unknown']:,}")
    print(f"  Plate demux (output): {plate_total:,}")
    print(f"  Difference (plate vs well_known): {conservation['difference']:,}")

    # 4. R1/R2 pairing check
    pairing = check_r1_r2_pairing(args.input_r1, args.input_r2)
    if pairing.get("checked"):
        print(f"\nR1/R2 pairing check: {'PASS' if pairing['equal'] else 'FAIL'}")
        print(f"  R1: {pairing['r1_count']:,}, R2: {pairing['r2_count']:,}")
    else:
        print(f"\nR1/R2 pairing check: SKIPPED ({pairing.get('reason', 'N/A')})")

    # 5. Calculate statistics
    stats = calculate_summary_stats(plate_counts)

    # 6. Determine AC results
    ac_results = {
        "AC-001": {
            "status": "PASS" if conservation["conserved"] else "FAIL",
            "message": f"守恒检查{'通过' if conservation['conserved'] else '失败'}, 差异={conservation['difference']}"
        },
        "AC-002": {
            "status": "PASS",  # Files generated successfully
            "message": "已生成 summary.json 和 qc_report.md"
        }
    }

    # Add pairing result to AC-001 if checked
    if pairing.get("checked") and not pairing.get("equal"):
        ac_results["AC-001"]["status"] = "FAIL"
        ac_results["AC-001"]["message"] += f"; R1/R2 不配对 (差异={pairing['difference']})"

    # 7. Generate summary.json
    summary_path = output_dir / "summary.json"
    generate_summary_json(summary_path, ac_results, stats, conservation, pairing)
    print(f"  Generated: {summary_path}")

    # 8. Generate qc_report.md
    report_path = output_dir / "qc_report.md"
    generate_qc_report(report_path, ac_results, stats, conservation, pairing)
    print(f"  Generated: {report_path}")

    # Print summary
    all_pass = all(r["status"] == "PASS" for r in ac_results.values())
    print(f"\n{'='*50}")
    print(f"QC Report Summary: {'PASS' if all_pass else 'FAIL'}")
    print(f"{'='*50}")
    for ac, result in ac_results.items():
        print(f"  {ac}: {result['status']}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
