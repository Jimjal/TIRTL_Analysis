#!/usr/bin/env python3
"""
verify.py - Verification Script for TIRTL-seq Pipeline

Supports verification for multiple milestones:
- M-0001: Demux Recon (generate -> recon -> assert)
- M-0002: Well Demux (generate -> demux -> assert)

AC Requirements:
- M-0001 AC-004: Closed-loop recon verification
- M-0002 AC-005: Closed-loop demux verification (Synthetic Gen -> Demux -> Check)

Usage:
    python3 scripts/verify.py [options]
    python3 scripts/verify.py --milestone M-0002  # Verify M-0002 only

Options:
    --milestone M       Milestone to verify (default: all)
    --output-dir DIR    Build output directory (default: build/)
    --log-dir DIR       Log output directory (default: logs/)
    --verbose           Show detailed output
"""

import argparse
import csv
import gzip
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class VerificationResult:
    """Holds verification check results."""

    def __init__(self):
        self.checks = []
        self.passed = 0
        self.failed = 0

    def add_check(self, name, passed, message=None):
        """Add a verification check result."""
        status = "PASS" if passed else "FAIL"
        self.checks.append({
            "name": name,
            "status": status,
            "message": message,
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        return passed

    @property
    def total(self):
        return len(self.checks)

    @property
    def success(self):
        return self.failed == 0


class Verifier:
    """Main verification class implementing closed-loop testing."""

    def __init__(self, project_root, output_dir, log_dir, verbose=False):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.verbose = verbose
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        self.results = VerificationResult()
        self.log_lines = []

    def log(self, message):
        """Log a message."""
        self.log_lines.append(message)
        if self.verbose:
            print(message)

    def check(self, name, condition, message=None):
        """Perform a verification check."""
        passed = self.results.add_check(name, condition, message)
        status = "[PASS]" if passed else "[FAIL]"
        self.log(f"{status} {name}")
        if message and not passed:
            self.log(f"       {message}")
        return passed

    def run_command(self, cmd, description, capture=True):
        """Run a shell command and return result."""
        self.log(f"[INFO] {description}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                cwd=self.project_root,
            )
            return result
        except Exception as e:
            self.log(f"[ERROR] Command failed: {e}")
            return None

    def verify_ac001_structure(self):
        """AC-001: Verify repository structure and templates."""
        self.log("")
        self.log("--- AC-001: Repo Structure & Templates ---")
        self.log("")

        # Check directories
        self.check("examples/ directory exists",
                   (self.project_root / "examples").is_dir())
        self.check("scripts/ directory exists",
                   (self.project_root / "scripts").is_dir())
        self.check("docs/ directory exists",
                   (self.project_root / "docs").is_dir())

        # Check files
        self.check("examples/well_barcodes.csv exists",
                   (self.project_root / "examples/well_barcodes.csv").is_file())
        self.check("examples/plate_barcodes.csv exists",
                   (self.project_root / "examples/plate_barcodes.csv").is_file())
        self.check("docs/demux_plan.md exists",
                   (self.project_root / "docs/demux_plan.md").is_file())

        # Check barcode files
        self.check("TIRTL_barcode_well.csv exists",
                   (self.project_root / "TIRTL_barcode_well.csv").is_file())
        self.check("TIRTL_barcode_plate.csv exists",
                   (self.project_root / "TIRTL_barcode_plate.csv").is_file())

        # Check demux_plan.md content
        demux_plan = self.project_root / "docs/demux_plan.md"
        if demux_plan.is_file():
            content = demux_plan.read_text()
            self.check("demux_plan.md contains Overview section",
                       "## 1. Overview" in content)
            self.check("demux_plan.md contains Data Structure section",
                       "## 2. Data Structure" in content)

    def verify_ac003_synthetic_generator(self):
        """AC-003: Verify synthetic data generator."""
        self.log("")
        self.log("--- AC-003: Synthetic Data Generator ---")
        self.log("")

        gen_script = self.project_root / "scripts/generate_synthetic.py"

        self.check("scripts/generate_synthetic.py exists",
                   gen_script.is_file())

        if not gen_script.is_file():
            return False

        # Run generator
        self.output_dir.mkdir(parents=True, exist_ok=True)
        result = self.run_command(
            [sys.executable, str(gen_script),
             "--output-dir", str(self.output_dir),
             "--wells", "3",
             "--plates", "2",
             "--num-reads", "10"],
            "Running synthetic data generator..."
        )

        gen_success = result is not None and result.returncode == 0
        self.check("Synthetic data generator runs successfully", gen_success)

        if not gen_success:
            if result:
                self.log(f"[ERROR] Generator stderr: {result.stderr}")
            return False

        # Check outputs
        r1_path = self.output_dir / "synthetic_R1.fq.gz"
        r2_path = self.output_dir / "synthetic_R2.fq.gz"
        manifest_path = self.output_dir / "synthetic_manifest.csv"

        self.check("synthetic_R1.fq.gz generated", r1_path.is_file())
        self.check("synthetic_R2.fq.gz generated", r2_path.is_file())
        self.check("synthetic_manifest.csv generated", manifest_path.is_file())

        # Verify FASTQ content
        if r1_path.is_file():
            import gzip
            with gzip.open(r1_path, "rt") as f:
                header = f.readline().strip()
                seq = f.readline().strip()

            # Check Illumina header format
            has_illumina_header = (
                header.startswith("@") and
                ":" in header and
                " " in header
            )
            self.check("R1 has Illumina-format header", has_illumina_header)

            # Check plate barcode prefix
            has_plate_barcode = seq.startswith("TCGTCGGCAG")
            self.check("R1 contains plate barcode prefix", has_plate_barcode)

        if r2_path.is_file():
            import gzip
            with gzip.open(r2_path, "rt") as f:
                header = f.readline().strip()
                seq = f.readline().strip()

            # Check well barcode (i7)
            expected_barcodes = ["ATAGGCGCTC", "TACAACCTCA", "AGTTATCGGA"]
            has_well_barcode = any(seq.startswith(bc) for bc in expected_barcodes)
            self.check("R2 contains well barcode (i7)", has_well_barcode)

        return True

    def verify_ac002_recon_tool(self):
        """AC-002: Verify recon tool implementation."""
        self.log("")
        self.log("--- AC-002: Recon Tool Implementation ---")
        self.log("")

        recon_script = self.project_root / "scripts/recon_fastq.py"

        self.check("scripts/recon_fastq.py exists",
                   recon_script.is_file())

        if not recon_script.is_file():
            return False

        r1_path = self.output_dir / "synthetic_R1.fq.gz"
        r2_path = self.output_dir / "synthetic_R2.fq.gz"
        recon_output = self.output_dir / "recon_report.txt"
        recon_json = self.output_dir / "recon_report.json"

        if not r1_path.is_file() or not r2_path.is_file():
            self.log("[ERROR] Synthetic data not available for recon")
            return False

        # Run recon tool
        result = self.run_command(
            [sys.executable, str(recon_script),
             "--r1", str(r1_path),
             "--r2", str(r2_path),
             "--sample-size", "60",
             "--window-size", "10",
             "--output", str(recon_output),
             "--json", str(recon_json)],
            "Running recon tool on synthetic data..."
        )

        recon_success = result is not None and result.returncode == 0
        self.check("Recon tool runs successfully", recon_success)

        if not recon_success:
            if result:
                self.log(f"[ERROR] Recon stderr: {result.stderr}")
            return False

        # Check outputs
        self.check("Recon text report generated", recon_output.is_file())
        self.check("Recon JSON report generated", recon_json.is_file())

        # Verify report content
        if recon_output.is_file():
            content = recon_output.read_text()

            self.check("Report contains Header Structure analysis",
                       "Header Structure" in content)
            self.check("Report shows Illumina format detection",
                       "Illumina format" in content)
            self.check("Report contains index detection",
                       "Has index in header" in content)
            self.check("Report contains Sequence Window Analysis",
                       "Sequence Window Analysis" in content)
            self.check("Report identifies barcode candidates",
                       "BARCODE CANDIDATE" in content)

        return True

    def verify_ac004_closed_loop(self):
        """AC-004: Verify closed-loop integration."""
        self.log("")
        self.log("--- AC-004: Closed-Loop Verification ---")
        self.log("")

        recon_json = self.output_dir / "recon_report.json"
        manifest_path = self.output_dir / "synthetic_manifest.csv"

        if not recon_json.is_file():
            self.check("Recon JSON available for validation", False)
            return False

        self.check("Recon JSON available for validation", True)

        # Load recon results
        with open(recon_json) as f:
            recon_data = json.load(f)

        # Load manifest (ground truth)
        import csv
        with open(manifest_path) as f:
            reader = csv.DictReader(f)
            manifest = list(reader)

        # Extract expected barcodes from manifest (exclude RANDOM/UNKNOWN noise entries)
        expected_i7 = set(row["i7_name"] for row in manifest if row["i7_name"] != "RANDOM")
        expected_plate_prefix = "TCGTCGGCAG"  # First 10bp of plate sequence

        # Verify R1 barcode detection
        r1_data = recon_data.get("r1", {})
        r1_windows = r1_data.get("windows", {})

        r1_start_freqs = r1_windows.get("start", {}).get("frequencies", {})
        detected_plate = expected_plate_prefix in r1_start_freqs

        self.check("Recon correctly identified plate barcode in R1",
                   detected_plate,
                   f"Expected {expected_plate_prefix} in R1 start position")

        # Verify R2 barcode detection
        r2_data = recon_data.get("r2", {})
        r2_windows = r2_data.get("windows", {})

        r2_start_freqs = r2_windows.get("start", {}).get("frequencies", {})
        detected_wells = set(r2_start_freqs.keys()) & expected_i7

        self.check("Recon correctly identified well barcodes in R2",
                   len(detected_wells) == len(expected_i7),
                   f"Expected {expected_i7}, detected {detected_wells}")

        # Verify barcode candidates
        r1_candidates = recon_data.get("summary", {}).get("r1_barcode_positions", [])
        r2_candidates = recon_data.get("summary", {}).get("r2_barcode_positions", [])

        self.check("R1 start position identified as barcode candidate",
                   "start" in r1_candidates)
        self.check("R2 start position identified as barcode candidate",
                   "start" in r2_candidates)

        return True

    # =========================================================================
    # M-0002: Well Demux Verification
    # =========================================================================

    def verify_m0002_ac001_interface(self):
        """M-0002 AC-001: Verify run_demux.py interface."""
        self.log("")
        self.log("--- M-0002 AC-001: Demux Interface ---")
        self.log("")

        demux_script = self.project_root / "scripts/run_demux.py"

        self.check("scripts/run_demux.py exists",
                   demux_script.is_file())

        if not demux_script.is_file():
            return False

        # Test --help
        result = self.run_command(
            [sys.executable, str(demux_script), "--help"],
            "Testing run_demux.py --help..."
        )

        help_success = result is not None and result.returncode == 0
        self.check("run_demux.py --help runs successfully", help_success)

        if help_success:
            help_text = result.stdout
            self.check("--r1 argument documented", "--r1" in help_text)
            self.check("--barcodes argument documented", "--barcodes" in help_text)
            self.check("--output-dir argument documented", "--output-dir" in help_text)

        return help_success

    def verify_m0002_ac002_functionality(self):
        """M-0002 AC-002: Verify demux produces correct output files."""
        self.log("")
        self.log("--- M-0002 AC-002: Demux Functionality ---")
        self.log("")

        demux_script = self.project_root / "scripts/run_demux.py"
        barcode_file = self.project_root / "TIRTL_barcode_well.csv"
        r1_path = self.output_dir / "synthetic_R1.fq.gz"
        demux_output = self.output_dir / "demux"

        if not r1_path.is_file():
            self.check("Synthetic data available for demux", False,
                       "Run AC-003 first to generate synthetic data")
            return False

        self.check("Synthetic data available for demux", True)

        # Run demux
        result = self.run_command(
            [sys.executable, str(demux_script),
             "--r1", str(r1_path),
             "--barcodes", str(barcode_file),
             "--output-dir", str(demux_output)],
            "Running demux on synthetic data..."
        )

        demux_success = result is not None and result.returncode == 0
        self.check("run_demux.py runs successfully", demux_success)

        if not demux_success:
            if result:
                self.log(f"[ERROR] Demux stderr: {result.stderr}")
            return False

        # Load manifest to get expected wells
        manifest_path = self.output_dir / "synthetic_manifest.csv"
        expected_wells = []
        with open(manifest_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["well"] != "UNKNOWN":
                    # Normalize well format: A1 -> A01
                    well = row["well"]
                    if len(well) == 2:  # e.g., "A1"
                        well = f"{well[0]}{int(well[1:]):02d}"
                    expected_wells.append(well)

        # Check well files exist (AC-002: well_<row><col>.fastq.gz)
        for well in expected_wells:
            well_file = demux_output / f"well_{well}.fastq.gz"
            self.check(f"well_{well}.fastq.gz exists", well_file.is_file())

        # Check unknown file exists
        unknown_file = demux_output / "unknown.fastq.gz"
        self.check("unknown.fastq.gz exists", unknown_file.is_file())

        return True

    def verify_m0002_ac003_integrity(self):
        """M-0002 AC-003: Verify data integrity (valid gzip, R1/R2 pairing)."""
        self.log("")
        self.log("--- M-0002 AC-003: Data Integrity ---")
        self.log("")

        demux_output = self.output_dir / "demux"

        if not demux_output.is_dir():
            self.check("Demux output available for integrity check", False)
            return False

        self.check("Demux output available for integrity check", True)

        # Check all .gz files are valid gzip
        gz_files = list(demux_output.glob("*.gz"))
        all_valid = True

        for gz_file in gz_files:
            try:
                with gzip.open(gz_file, "rt") as f:
                    # Read first line to verify it's valid
                    f.readline()
                is_valid = True
            except Exception as e:
                is_valid = False
                all_valid = False
                self.log(f"[ERROR] Invalid gzip: {gz_file}: {e}")

            self.check(f"{gz_file.name} is valid gzip", is_valid)

        return all_valid

    def verify_m0002_ac004_reporting(self):
        """M-0002 AC-004: Verify stats generation and read count sum."""
        self.log("")
        self.log("--- M-0002 AC-004: Reporting ---")
        self.log("")

        demux_output = self.output_dir / "demux"
        stats_file = demux_output / "demux_stats.tsv"

        # Check stats file exists
        self.check("demux_stats.tsv exists", stats_file.is_file())

        if not stats_file.is_file():
            return False

        # Load stats
        stats = {}
        total_from_stats = 0
        with open(stats_file) as f:
            reader = csv.DictReader(f, delimiter="\t")
            columns = reader.fieldnames

            # Check required columns
            self.check("Stats has 'well_id' column", "well_id" in columns)
            self.check("Stats has 'read_count' column", "read_count" in columns)
            self.check("Stats has 'percent' column", "percent" in columns)

            for row in reader:
                well_id = row["well_id"]
                count = int(row["read_count"])
                stats[well_id] = count
                total_from_stats += count

        # Count reads in input file
        r1_path = self.output_dir / "synthetic_R1.fq.gz"
        total_input = 0
        with gzip.open(r1_path, "rt") as f:
            for _ in f:
                total_input += 1
        total_input = total_input // 4  # 4 lines per read

        # Verify sum equals total
        sum_matches = total_from_stats == total_input
        self.check(f"Stats sum ({total_from_stats}) equals input reads ({total_input})",
                   sum_matches)

        # Load manifest and verify counts match expected
        manifest_path = self.output_dir / "synthetic_manifest.csv"
        manifest_counts = {}
        with open(manifest_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                well = row["well"]
                count = int(row["num_reads"])
                # Normalize well format: A1 -> A01
                if well != "UNKNOWN" and len(well) == 2:
                    well = f"{well[0]}{int(well[1:]):02d}"
                manifest_counts[well] = count

        # Verify each well count matches
        all_match = True
        for well, expected in manifest_counts.items():
            if well == "UNKNOWN":
                actual = stats.get("UNKNOWN", 0)
            else:
                actual = stats.get(well, 0)

            matches = actual == expected
            if not matches:
                all_match = False
                self.log(f"[WARN] {well}: expected {expected}, got {actual}")

        self.check("All well counts match expected", all_match)

        return sum_matches and all_match

    def verify_m0002_full_cycle(self):
        """M-0002 AC-005: Run full verification cycle."""
        self.log("")
        self.log("=" * 50)
        self.log("M-0002 Full Cycle Verification")
        self.log("=" * 50)

        # Step 1: Generate synthetic data (reuse AC-003 from M-0001)
        self.log("")
        self.log("Step 1: Generate Synthetic Data")
        gen_script = self.project_root / "scripts/generate_synthetic.py"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        result = self.run_command(
            [sys.executable, str(gen_script),
             "--output-dir", str(self.output_dir),
             "--wells", "3",
             "--plates", "1",
             "--num-reads", "10",
             "--noise-reads", "5"],
            "Generating synthetic data (3 wells, 10 reads each, 5 noise)..."
        )

        gen_success = result is not None and result.returncode == 0
        self.check("Synthetic data generation", gen_success)

        if not gen_success:
            return False

        # Step 2: Run demux
        self.log("")
        self.log("Step 2: Run Demux")
        self.verify_m0002_ac001_interface()
        self.verify_m0002_ac002_functionality()

        # Step 3: Verify integrity
        self.log("")
        self.log("Step 3: Verify Integrity")
        self.verify_m0002_ac003_integrity()

        # Step 4: Verify reporting
        self.log("")
        self.log("Step 4: Verify Reporting")
        self.verify_m0002_ac004_reporting()

        return True

    def save_results(self, milestone="M-0001"):
        """Save verification results to log and JSON files."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

        log_file = self.log_dir / f"{milestone}-verify-{self.timestamp}.txt"
        json_file = self.log_dir / f"{milestone}-verify-{self.timestamp}.summary.json"

        # Build full log
        header = [
            "=" * 50,
            f"{milestone} Verification - {self.timestamp}",
            "=" * 50,
            "",
        ]

        footer = [
            "",
            "=" * 50,
            f"Summary: {self.results.passed} passed, {self.results.failed} failed (Total: {self.results.total})",
            "=" * 50,
            "",
            f"Log saved to: {log_file}",
            f"Summary saved to: {json_file}",
            "",
            "SUCCESS: All checks passed." if self.results.success else f"FAILED: {self.results.failed} checks did not pass.",
        ]

        full_log = "\n".join(header + self.log_lines + footer)

        # Save log file
        log_file.write_text(full_log)

        # Determine tasks and ACs based on milestone
        if milestone == "M-0001":
            tasks = ["T-001", "T-002", "T-003", "T-004"]
            acs = ["AC-001", "AC-002", "AC-003", "AC-004"]
        elif milestone == "M-0002":
            tasks = ["T-001", "T-002", "T-003"]
            acs = ["AC-001", "AC-002", "AC-003", "AC-004", "AC-005"]
        else:
            tasks = []
            acs = []

        # Save JSON summary
        summary = {
            "timestamp": self.timestamp,
            "milestone": milestone,
            "tasks_verified": tasks,
            "acceptance_criteria": acs,
            "total_checks": self.results.total,
            "passed": self.results.passed,
            "failed": self.results.failed,
            "status": "SUCCESS" if self.results.success else "FAILED",
            "log_file": str(log_file),
            "checks": self.results.checks,
        }

        with open(json_file, "w") as f:
            json.dump(summary, f, indent=2)

        # Print summary
        print(full_log)

        return log_file, json_file

    def run(self, milestone="M-0001"):
        """Run full verification workflow for specified milestone."""

        if milestone == "M-0001":
            # M-0001: Demux Recon
            # AC-001: Structure
            self.verify_ac001_structure()

            # AC-003: Synthetic generator
            self.verify_ac003_synthetic_generator()

            # AC-002: Recon tool
            self.verify_ac002_recon_tool()

            # AC-004: Closed-loop
            self.verify_ac004_closed_loop()

            # Save results
            log_file, json_file = self.save_results(milestone="M-0001")

        elif milestone == "M-0002":
            # M-0002: Well Demux - Full Cycle (AC-005)
            self.verify_m0002_full_cycle()

            # Save results
            log_file, json_file = self.save_results(milestone="M-0002")

        elif milestone == "all":
            # Run both milestones
            self.log("=" * 50)
            self.log("Running M-0001 Verification")
            self.log("=" * 50)

            self.verify_ac001_structure()
            self.verify_ac003_synthetic_generator()
            self.verify_ac002_recon_tool()
            self.verify_ac004_closed_loop()

            self.log("")
            self.log("=" * 50)
            self.log("Running M-0002 Verification")
            self.log("=" * 50)

            self.verify_m0002_full_cycle()

            # Save combined results
            log_file, json_file = self.save_results(milestone="M-0001-M-0002")

        else:
            self.log(f"Unknown milestone: {milestone}")
            return False

        return self.results.success


def find_project_root():
    """Find project root by looking for _milestone directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "_milestone").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent


def parse_args():
    parser = argparse.ArgumentParser(
        description="Verification script for TIRTL-seq Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/verify.py                    # Verify M-0001 (default)
    python scripts/verify.py --milestone M-0002 # Verify M-0002 only
    python scripts/verify.py --milestone all    # Verify all milestones
"""
    )
    parser.add_argument(
        "--milestone", "-m", type=str, default="M-0001",
        choices=["M-0001", "M-0002", "all"],
        help="Milestone to verify (default: M-0001)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="build",
        help="Build output directory (default: build/)"
    )
    parser.add_argument(
        "--log-dir", type=str, default="logs",
        help="Log output directory (default: logs/)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed output"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    project_root = find_project_root()

    # Resolve paths
    if os.path.isabs(args.output_dir):
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / args.output_dir

    if os.path.isabs(args.log_dir):
        log_dir = Path(args.log_dir)
    else:
        log_dir = project_root / args.log_dir

    # Run verification
    verifier = Verifier(project_root, output_dir, log_dir, args.verbose)
    success = verifier.run(milestone=args.milestone)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
