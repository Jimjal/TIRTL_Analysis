#!/usr/bin/env python3
"""
run_pipeline.py - Unified CLI Entry Point for TIRTL-seq Demultiplex Pipeline

Reads a YAML configuration file and orchestrates the full pipeline:
  M-0002 (Well Demux) -> M-0003 (Plate Demux) -> M-0004 (QC Report)

Features:
- Single config file drives all stages
- Stage toggles for selective execution
- Synthetic data generation for testing
- Structured logging with JSON summary

P-0005 AC Requirements:
- AC-001: Config file parsing and validation
- AC-002: Pipeline orchestration (well -> plate -> QC)
- AC-003: Log and summary generation
- AC-004: Runbook documentation (see docs/runbook_cli.md)
- AC-005: verify.py --milestone M-0005 support

Usage:
    python scripts/run_pipeline.py --config config/tirtl_config.example.yaml
    python scripts/run_pipeline.py --config config/my_config.yaml --verbose

Environment:
    conda activate TIRTL_analyse
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# YAML import with fallback
try:
    import yaml
except ImportError:
    yaml = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Unified CLI for TIRTL-seq Demultiplex Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with example config (synthetic data)
    python scripts/run_pipeline.py --config config/tirtl_config.example.yaml

    # Run with custom config
    python scripts/run_pipeline.py --config config/my_config.yaml --verbose

    # Show parsed config without running
    python scripts/run_pipeline.py --config config/tirtl_config.example.yaml --dry-run

Environment:
    Requires TIRTL_analyse conda environment with demultiplex installed.
    Run: conda activate TIRTL_analyse
"""
    )
    parser.add_argument(
        "--config", "-c", required=True, type=str,
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and display config without running pipeline"
    )
    return parser.parse_args()


def load_config(config_path):
    """Load and validate YAML configuration file."""
    if yaml is None:
        raise ImportError(
            "PyYAML not installed. Run: pip install pyyaml"
        )

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Validate required sections
    required_sections = ["input", "barcodes", "output", "stages"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")

    return config


def resolve_paths(config, project_root):
    """Resolve relative paths in config to absolute paths."""
    resolved = {}

    # Input paths
    r1 = config["input"].get("r1", "")
    r2 = config["input"].get("r2")

    if r1 and not os.path.isabs(r1):
        r1 = str(project_root / r1)
    if r2 and not os.path.isabs(r2):
        r2 = str(project_root / r2)

    resolved["r1"] = r1
    resolved["r2"] = r2

    # Barcode paths
    well_bc = config["barcodes"].get("well", "")
    plate_bc = config["barcodes"].get("plate", "")

    if well_bc and not os.path.isabs(well_bc):
        well_bc = str(project_root / well_bc)
    if plate_bc and not os.path.isabs(plate_bc):
        plate_bc = str(project_root / plate_bc)

    resolved["well_barcodes"] = well_bc
    resolved["plate_barcodes"] = plate_bc

    # Output paths
    output_root = config["output"].get("root_dir", "build")
    if not os.path.isabs(output_root):
        output_root = str(project_root / output_root)

    resolved["output_root"] = output_root
    resolved["well_demux_dir"] = os.path.join(
        output_root, config["output"].get("well_demux_dir", "demux")
    )
    resolved["plate_demux_dir"] = os.path.join(
        output_root, config["output"].get("plate_demux_dir", "plate_demux")
    )
    resolved["qc_dir"] = os.path.join(
        output_root, config["output"].get("qc_dir", "qc")
    )

    # Log paths
    log_dir = config.get("logging", {}).get("log_dir", "logs")
    if not os.path.isabs(log_dir):
        log_dir = str(project_root / log_dir)

    resolved["log_dir"] = log_dir
    resolved["log_prefix"] = config.get("logging", {}).get("log_prefix", "pipeline")

    return resolved


class PipelineRunner:
    """Orchestrates the TIRTL-seq demultiplex pipeline."""

    def __init__(self, config, paths, project_root, verbose=False):
        self.config = config
        self.paths = paths
        self.project_root = project_root
        self.verbose = verbose
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        self.log_lines = []
        self.stage_results = {}
        self.ac_results = {}

    def log(self, message, level="INFO"):
        """Log a message."""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {message}"
        self.log_lines.append(line)
        if self.verbose or level in ("ERROR", "WARN"):
            print(line)

    def run_command(self, cmd, description, capture=True):
        """Run a shell command and return result."""
        self.log(f"Running: {description}")
        self.log(f"  Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                cwd=self.project_root,
            )
            if result.returncode == 0:
                self.log(f"  Status: SUCCESS")
            else:
                self.log(f"  Status: FAILED (code={result.returncode})", "ERROR")
                if result.stderr:
                    self.log(f"  Stderr: {result.stderr[:500]}", "ERROR")
            return result
        except Exception as e:
            self.log(f"  Exception: {e}", "ERROR")
            return None

    def stage_generate_synthetic(self):
        """Stage 0: Generate synthetic test data."""
        self.log("=" * 50)
        self.log("Stage 0: Generate Synthetic Data")
        self.log("=" * 50)

        stages = self.config.get("stages", {})
        if not stages.get("generate_synthetic", False):
            self.log("Skipped (generate_synthetic=false)")
            self.stage_results["synthetic"] = "SKIPPED"
            return True

        params = stages.get("synthetic_params", {})
        wells = params.get("wells", 2)
        plates = params.get("plates", 2)
        num_reads = params.get("num_reads", 10)
        noise_reads = params.get("noise_reads", 5)

        gen_script = self.project_root / "scripts/generate_synthetic.py"
        output_dir = self.paths["output_root"]

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        result = self.run_command(
            [
                sys.executable, str(gen_script),
                "--output-dir", output_dir,
                "--wells", str(wells),
                "--plates", str(plates),
                "--num-reads", str(num_reads),
                "--noise-reads", str(noise_reads),
            ],
            f"Generate synthetic data ({wells} wells, {plates} plates, {num_reads} reads)"
        )

        success = result is not None and result.returncode == 0
        self.stage_results["synthetic"] = "PASS" if success else "FAIL"

        # Update R1/R2 paths if synthetic generation was used
        if success:
            self.paths["r1"] = os.path.join(output_dir, "synthetic_R1.fq.gz")
            self.paths["r2"] = os.path.join(output_dir, "synthetic_R2.fq.gz")

        return success

    def stage_well_demux(self):
        """Stage 1: Well Demultiplexing (M-0002)."""
        self.log("")
        self.log("=" * 50)
        self.log("Stage 1: Well Demux (M-0002)")
        self.log("=" * 50)

        stages = self.config.get("stages", {})
        if not stages.get("well_demux", True):
            self.log("Skipped (well_demux=false)")
            self.stage_results["well_demux"] = "SKIPPED"
            return True

        demux_script = self.project_root / "scripts/run_demux.py"

        # Build command
        cmd = [
            sys.executable, str(demux_script),
            "--r1", self.paths["r1"],
            "--barcodes", self.paths["well_barcodes"],
            "--output-dir", self.paths["well_demux_dir"],
        ]

        # Add R2 if provided
        r2 = self.paths.get("r2")
        if r2 and os.path.exists(r2):
            cmd.extend(["--r2", r2])

        # Add mismatch setting
        mismatch = self.config.get("advanced", {}).get("mismatch", 1)
        cmd.extend(["--mismatch", str(mismatch)])

        result = self.run_command(cmd, "Well demultiplexing")

        success = result is not None and result.returncode == 0
        self.stage_results["well_demux"] = "PASS" if success else "FAIL"
        return success

    def stage_plate_demux(self):
        """Stage 2: Plate Demultiplexing (M-0003)."""
        self.log("")
        self.log("=" * 50)
        self.log("Stage 2: Plate Demux (M-0003)")
        self.log("=" * 50)

        stages = self.config.get("stages", {})
        if not stages.get("plate_demux", True):
            self.log("Skipped (plate_demux=false)")
            self.stage_results["plate_demux"] = "SKIPPED"
            return True

        plate_demux_script = self.project_root / "scripts/run_plate_demux.py"

        cmd = [
            sys.executable, str(plate_demux_script),
            "--input-dir", self.paths["well_demux_dir"],
            "--barcodes", self.paths["plate_barcodes"],
            "--output-dir", self.paths["plate_demux_dir"],
        ]

        # Add mismatch setting
        mismatch = self.config.get("advanced", {}).get("mismatch", 1)
        cmd.extend(["--mismatch", str(mismatch)])

        result = self.run_command(cmd, "Plate demultiplexing")

        success = result is not None and result.returncode == 0
        self.stage_results["plate_demux"] = "PASS" if success else "FAIL"
        return success

    def stage_qc_report(self):
        """Stage 3: QC & Reporting (M-0004)."""
        self.log("")
        self.log("=" * 50)
        self.log("Stage 3: QC & Reporting (M-0004)")
        self.log("=" * 50)

        stages = self.config.get("stages", {})
        if not stages.get("qc_report", True):
            self.log("Skipped (qc_report=false)")
            self.stage_results["qc_report"] = "SKIPPED"
            return True

        qc_script = self.project_root / "scripts/run_qc.py"

        cmd = [
            sys.executable, str(qc_script),
            "--plate-demux-dir", self.paths["plate_demux_dir"],
            "--well-demux-dir", self.paths["well_demux_dir"],
            "--output-dir", self.paths["qc_dir"],
        ]

        # Add optional R1/R2 for pairing check
        r1 = self.paths.get("r1")
        r2 = self.paths.get("r2")
        if r1 and os.path.exists(r1):
            cmd.extend(["--input-r1", r1])
        if r2 and os.path.exists(r2):
            cmd.extend(["--input-r2", r2])

        result = self.run_command(cmd, "QC & Reporting")

        success = result is not None and result.returncode == 0
        self.stage_results["qc_report"] = "PASS" if success else "FAIL"
        return success

    def evaluate_ac(self):
        """Evaluate Acceptance Criteria based on stage results."""
        # AC-001: Config parsing (already passed if we got here)
        self.ac_results["AC-001"] = {
            "status": "PASS",
            "message": "Config parsed and paths resolved"
        }

        # AC-002: Pipeline execution
        failed_stages = [s for s, r in self.stage_results.items() if r == "FAIL"]
        if failed_stages:
            self.ac_results["AC-002"] = {
                "status": "FAIL",
                "message": f"Failed stages: {failed_stages}"
            }
        else:
            self.ac_results["AC-002"] = {
                "status": "PASS",
                "message": "All enabled stages completed"
            }

        # AC-003: Logs generated (will be set after save_results)
        self.ac_results["AC-003"] = {
            "status": "PENDING",
            "message": "Logs pending"
        }

        # AC-004: Runbook exists
        runbook_path = self.project_root / "docs/runbook_cli.md"
        if runbook_path.exists():
            self.ac_results["AC-004"] = {
                "status": "PASS",
                "message": "Runbook exists at docs/runbook_cli.md"
            }
        else:
            self.ac_results["AC-004"] = {
                "status": "FAIL",
                "message": "Runbook not found at docs/runbook_cli.md"
            }

        # AC-005: Will be checked by verify.py

    def save_results(self):
        """Save log and summary files."""
        log_dir = Path(self.paths["log_dir"])
        log_dir.mkdir(parents=True, exist_ok=True)

        log_prefix = self.paths["log_prefix"]
        log_file = log_dir / f"{log_prefix}-{self.timestamp}.txt"
        summary_file = log_dir / f"{log_prefix}-{self.timestamp}.summary.json"

        # Update AC-003
        self.ac_results["AC-003"] = {
            "status": "PASS",
            "message": f"Logs: {log_file.name}, {summary_file.name}"
        }

        # Build summary
        all_pass = all(
            r["status"] == "PASS"
            for r in self.ac_results.values()
            if r["status"] != "PENDING"
        )

        summary = {
            "timestamp": self.timestamp,
            "config_file": str(self.config.get("_source_file", "unknown")),
            "stage_results": self.stage_results,
            "acceptance_criteria": self.ac_results,
            "overall_status": "PASS" if all_pass else "FAIL",
            "paths": {
                "output_root": self.paths["output_root"],
                "well_demux_dir": self.paths["well_demux_dir"],
                "plate_demux_dir": self.paths["plate_demux_dir"],
                "qc_dir": self.paths["qc_dir"],
            }
        }

        # Write log file
        header = [
            "=" * 60,
            f"TIRTL-seq Pipeline Log - {self.timestamp}",
            "=" * 60,
            "",
        ]
        footer = [
            "",
            "=" * 60,
            f"Overall Status: {summary['overall_status']}",
            "=" * 60,
            "",
            "Stage Results:",
        ]
        for stage, result in self.stage_results.items():
            footer.append(f"  {stage}: {result}")

        footer.append("")
        footer.append("Acceptance Criteria:")
        for ac, result in self.ac_results.items():
            footer.append(f"  {ac}: {result['status']} - {result['message']}")

        full_log = "\n".join(header + self.log_lines + footer)
        log_file.write_text(full_log, encoding="utf-8")

        # Write summary JSON
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.log("")
        self.log(f"Log saved to: {log_file}")
        self.log(f"Summary saved to: {summary_file}")

        return log_file, summary_file, summary

    def run(self):
        """Run the full pipeline."""
        self.log("TIRTL-seq Demultiplex Pipeline Started")
        self.log(f"Timestamp: {self.timestamp}")
        self.log(f"Project Root: {self.project_root}")
        self.log("")

        # Log key paths
        self.log("Configuration:")
        self.log(f"  R1: {self.paths['r1']}")
        self.log(f"  R2: {self.paths.get('r2', 'N/A')}")
        self.log(f"  Well Barcodes: {self.paths['well_barcodes']}")
        self.log(f"  Plate Barcodes: {self.paths['plate_barcodes']}")
        self.log(f"  Output Root: {self.paths['output_root']}")

        # Run stages
        stages_ok = True

        # Stage 0: Synthetic data (optional)
        if not self.stage_generate_synthetic():
            stages_ok = False

        # Stage 1: Well Demux
        if stages_ok and not self.stage_well_demux():
            stages_ok = False

        # Stage 2: Plate Demux
        if stages_ok and not self.stage_plate_demux():
            stages_ok = False

        # Stage 3: QC Report
        if stages_ok and not self.stage_qc_report():
            stages_ok = False

        # Evaluate AC
        self.evaluate_ac()

        # Save results
        log_file, summary_file, summary = self.save_results()

        # Print final summary
        print("")
        print("=" * 60)
        print(f"Pipeline Complete: {summary['overall_status']}")
        print("=" * 60)
        print("")
        print("Stage Results:")
        for stage, result in self.stage_results.items():
            status_icon = "OK" if result == "PASS" else ("--" if result == "SKIPPED" else "XX")
            print(f"  [{status_icon}] {stage}: {result}")
        print("")
        print(f"Log: {log_file}")
        print(f"Summary: {summary_file}")

        return summary["overall_status"] == "PASS"


def find_project_root():
    """Find project root by looking for _milestone directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "_milestone").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent


def main():
    args = parse_args()

    # Find project root
    project_root = find_project_root()

    # Load config
    try:
        config = load_config(args.config)
        config["_source_file"] = args.config
    except ImportError as e:
        print(f"ERROR: {e}")
        print("Install PyYAML: pip install pyyaml")
        return 1
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    except ValueError as e:
        print(f"ERROR: Config validation failed: {e}")
        return 1

    # Resolve paths
    paths = resolve_paths(config, project_root)

    # Dry run mode
    if args.dry_run:
        print("=" * 60)
        print("Dry Run - Configuration Summary")
        print("=" * 60)
        print("")
        print("Input:")
        print(f"  R1: {paths['r1']}")
        print(f"  R2: {paths.get('r2', 'N/A')}")
        print("")
        print("Barcodes:")
        print(f"  Well: {paths['well_barcodes']}")
        print(f"  Plate: {paths['plate_barcodes']}")
        print("")
        print("Output:")
        print(f"  Root: {paths['output_root']}")
        print(f"  Well Demux: {paths['well_demux_dir']}")
        print(f"  Plate Demux: {paths['plate_demux_dir']}")
        print(f"  QC: {paths['qc_dir']}")
        print("")
        print("Stages:")
        stages = config.get("stages", {})
        print(f"  Generate Synthetic: {stages.get('generate_synthetic', False)}")
        print(f"  Well Demux: {stages.get('well_demux', True)}")
        print(f"  Plate Demux: {stages.get('plate_demux', True)}")
        print(f"  QC Report: {stages.get('qc_report', True)}")
        print("")
        print("Use --verbose to run the pipeline")
        return 0

    # Run pipeline
    runner = PipelineRunner(config, paths, project_root, args.verbose)
    success = runner.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
