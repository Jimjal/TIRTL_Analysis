#!/usr/bin/env python3
"""
verify.py - Verification Script for M-0001 TIRTL-seq Demux Recon

This script implements the closed-loop verification workflow:
1. Generate synthetic FASTQ data with known barcodes
2. Run recon tool to analyze the synthetic data
3. Assert that recon correctly identified the barcode characteristics
4. Output verification logs and JSON summary

AC-004 Requirements:
- scripts/verify.py runs successfully (Exit Code 0)
- Closed-loop: generate -> recon -> assert
- Output logs/M-0001-verify-*.txt and .json

Usage:
    python3 scripts/verify.py [options]

Options:
    --output-dir DIR    Build output directory (default: build/)
    --log-dir DIR       Log output directory (default: logs/)
    --verbose           Show detailed output
"""

import argparse
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

        # Extract expected barcodes from manifest
        expected_i7 = set(row["i7_name"] for row in manifest)
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

    def save_results(self):
        """Save verification results to log and JSON files."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

        log_file = self.log_dir / f"M-0001-verify-{self.timestamp}.txt"
        json_file = self.log_dir / f"M-0001-verify-{self.timestamp}.summary.json"

        # Build full log
        header = [
            "=" * 50,
            f"M-0001 Verification - {self.timestamp}",
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

        # Save JSON summary
        summary = {
            "timestamp": self.timestamp,
            "milestone": "M-0001",
            "tasks_verified": ["T-001", "T-002", "T-003", "T-004"],
            "acceptance_criteria": ["AC-001", "AC-002", "AC-003", "AC-004"],
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

    def run(self):
        """Run full verification workflow."""
        # AC-001: Structure
        self.verify_ac001_structure()

        # AC-003: Synthetic generator
        self.verify_ac003_synthetic_generator()

        # AC-002: Recon tool
        self.verify_ac002_recon_tool()

        # AC-004: Closed-loop
        self.verify_ac004_closed_loop()

        # Save results
        log_file, json_file = self.save_results()

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
        description="Verification script for M-0001 TIRTL-seq Demux Recon"
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
    success = verifier.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
