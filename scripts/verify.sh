#!/bin/bash
# verify.sh - Verification script for M-0001 TIRTL-seq demux recon
# This script validates acceptance criteria for the milestone tasks.
#
# Usage: ./scripts/verify.sh
# Output: logs/M-0001-verify-YYYYMMDD-HHMM.txt

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +"%Y%m%d-%H%M")
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/M-0001-verify-$TIMESTAMP.txt"
SUMMARY_FILE="$LOG_DIR/M-0001-verify-$TIMESTAMP.summary.json"

mkdir -p "$LOG_DIR"

# Initialize counters
PASS=0
FAIL=0
TOTAL=0

log() {
    echo "$1" | tee -a "$LOG_FILE"
}

check() {
    local desc="$1"
    local condition="$2"
    TOTAL=$((TOTAL + 1))

    if eval "$condition"; then
        log "[PASS] $desc"
        PASS=$((PASS + 1))
        return 0
    else
        log "[FAIL] $desc"
        FAIL=$((FAIL + 1))
        return 1
    fi
}

log "=========================================="
log "M-0001 Verification - $TIMESTAMP"
log "=========================================="
log ""

# AC-001: Repo Structure & Templates
log "--- AC-001: Repo Structure & Templates ---"
log ""

check "examples/ directory exists" "[ -d '$PROJECT_ROOT/examples' ]"
check "examples/well_barcodes.csv exists" "[ -f '$PROJECT_ROOT/examples/well_barcodes.csv' ]"
check "examples/plate_barcodes.csv exists" "[ -f '$PROJECT_ROOT/examples/plate_barcodes.csv' ]"
check "scripts/ directory exists" "[ -d '$PROJECT_ROOT/scripts' ]"
check "docs/demux_plan.md exists" "[ -f '$PROJECT_ROOT/docs/demux_plan.md' ]"

# Check CSV format (has header and data rows)
check "well_barcodes.csv has valid format (header + data)" \
    "grep -q '^Row,Column' '$PROJECT_ROOT/examples/well_barcodes.csv' && grep -q '^[A-H],[0-9]' '$PROJECT_ROOT/examples/well_barcodes.csv'"

check "plate_barcodes.csv has valid format (header + data)" \
    "grep -q '^name,sequence' '$PROJECT_ROOT/examples/plate_barcodes.csv' && grep -q '^MP_' '$PROJECT_ROOT/examples/plate_barcodes.csv'"

# Check demux_plan.md has required sections
check "demux_plan.md contains Overview section" \
    "grep -q '## 1. Overview' '$PROJECT_ROOT/docs/demux_plan.md'"

check "demux_plan.md contains Data Structure section" \
    "grep -q '## 2. Data Structure' '$PROJECT_ROOT/docs/demux_plan.md'"

check "demux_plan.md contains Demultiplex Strategy section" \
    "grep -q '## 4. Demultiplex Strategy' '$PROJECT_ROOT/docs/demux_plan.md'"

log ""

# AC-003: Synthetic Data Generator
log "--- AC-003: Synthetic Data Generator ---"
log ""

check "scripts/generate_synthetic.py exists" \
    "[ -f '$PROJECT_ROOT/scripts/generate_synthetic.py' ]"

check "scripts/generate_synthetic.py is executable or runnable" \
    "python3 -c \"import ast; ast.parse(open('$PROJECT_ROOT/scripts/generate_synthetic.py').read())\""

# Run the generator to create test data
log "[INFO] Running synthetic data generator..."
if python3 "$PROJECT_ROOT/scripts/generate_synthetic.py" --output-dir "$PROJECT_ROOT/build" >> "$LOG_FILE" 2>&1; then
    log "[INFO] Generator completed successfully"
else
    log "[FAIL] Generator failed to run"
    FAIL=$((FAIL + 1))
    TOTAL=$((TOTAL + 1))
fi

check "build/synthetic_R1.fq.gz exists" \
    "[ -f '$PROJECT_ROOT/build/synthetic_R1.fq.gz' ]"

check "build/synthetic_R2.fq.gz exists" \
    "[ -f '$PROJECT_ROOT/build/synthetic_R2.fq.gz' ]"

check "build/synthetic_manifest.csv exists" \
    "[ -f '$PROJECT_ROOT/build/synthetic_manifest.csv' ]"

# Verify Illumina header format: @<instrument>:<run>:<flowcell>:<lane>:<tile>:<x>:<y> <read>:<filtered>:<control>:<index>
check "R1 has valid Illumina header format" \
    "gunzip -c '$PROJECT_ROOT/build/synthetic_R1.fq.gz' | head -1 | grep -qE '^@[A-Z0-9]+:[0-9]+:[0-9A-Z-]+:[0-9]+:[0-9]+:[0-9]+:[0-9]+ [12]:[YN]:[0-9]+:[ACGTN+]+$'"

check "R2 has valid Illumina header format" \
    "gunzip -c '$PROJECT_ROOT/build/synthetic_R2.fq.gz' | head -1 | grep -qE '^@[A-Z0-9]+:[0-9]+:[0-9A-Z-]+:[0-9]+:[0-9]+:[0-9]+:[0-9]+ [12]:[YN]:[0-9]+:[ACGTN+]+$'"

# Verify barcodes are embedded in reads
check "R1 contains expected plate barcode prefix (TCGTCGGCAGCGTCAGATGT)" \
    "gunzip -c '$PROJECT_ROOT/build/synthetic_R1.fq.gz' | grep -q 'TCGTCGGCAGCGTCAGATGT'"

check "R2 contains expected well barcode (i7)" \
    "gunzip -c '$PROJECT_ROOT/build/synthetic_R2.fq.gz' | grep -qE '^(ATAGGCGCTC|TACAACCTCA|AGTTATCGGA)'"

# Verify manifest has correct columns
check "Manifest has correct header columns" \
    "head -1 '$PROJECT_ROOT/build/synthetic_manifest.csv' | grep -q 'well,plate,i5_name,i7_name'"

log ""
log "=========================================="
log "Summary: $PASS passed, $FAIL failed (Total: $TOTAL)"
log "=========================================="

# Generate JSON summary
cat > "$SUMMARY_FILE" << EOF
{
  "timestamp": "$TIMESTAMP",
  "milestone": "M-0001",
  "tasks_verified": ["T-001", "T-002"],
  "acceptance_criteria": ["AC-001", "AC-003"],
  "total_checks": $TOTAL,
  "passed": $PASS,
  "failed": $FAIL,
  "status": "$([ $FAIL -eq 0 ] && echo 'SUCCESS' || echo 'FAILED')",
  "log_file": "$LOG_FILE"
}
EOF

log ""
log "Log saved to: $LOG_FILE"
log "Summary saved to: $SUMMARY_FILE"

if [ $FAIL -eq 0 ]; then
    log ""
    log "SUCCESS: All checks passed (AC-001, AC-003)."
    exit 0
else
    log ""
    log "FAILED: $FAIL checks did not pass."
    exit 1
fi
