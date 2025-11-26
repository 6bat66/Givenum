#!/bin/bash

# ============================================================================
# WebEnum Batch Processor
# Process multiple domains efficiently
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${BLUE}[*]${NC} $1"; }
success() { echo -e "${GREEN}[+]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[-]${NC} $1"; }
header() { echo -e "\n${CYAN}========================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}========================================${NC}\n"; }

# Default settings
WEBENUM_SCRIPT="./webenum.py"
LOG_DIR="./batch_logs"
RESULTS_SUMMARY="${LOG_DIR}/batch_summary.txt"
FAILED_DOMAINS="${LOG_DIR}/failed_domains.txt"

# Parse arguments
usage() {
    cat << EOF
Usage: $0 <domains_file> [options]

Arguments:
    domains_file        File with one domain per line

Options:
    --skip-screenshots  Skip screenshot capture
    --skip-portscan     Skip port scanning
    --skip-vuln-scan    Skip vulnerability scanning
    -o, --output DIR    Output directory (default: ./results)
    --parallel N        Process N domains in parallel (default: 1)
    --delay SECONDS     Delay between scans (default: 0)
    --continue-on-error Continue even if a scan fails
    -h, --help          Show this help

Examples:
    $0 domains.txt
    $0 domains.txt --skip-screenshots --parallel 3
    $0 targets.txt -o /data/results --delay 60

Domain File Format:
    # Lines starting with # are comments
    example.com
    target.com
    test.org
    
EOF
    exit 0
}

# Check arguments
if [ $# -lt 1 ]; then
    usage
fi

DOMAINS_FILE="$1"
shift

if [ ! -f "$DOMAINS_FILE" ]; then
    error "File not found: $DOMAINS_FILE"
    exit 1
fi

# Parse options
OUTPUT_DIR="./results"
EXTRA_ARGS=""
PARALLEL_JOBS=1
DELAY=0
CONTINUE_ON_ERROR=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-screenshots)
            EXTRA_ARGS="$EXTRA_ARGS --skip-screenshots"
            shift
            ;;
        --skip-portscan)
            EXTRA_ARGS="$EXTRA_ARGS --skip-portscan"
            shift
            ;;
        --skip-vuln-scan)
            EXTRA_ARGS="$EXTRA_ARGS --skip-vuln-scan"
            shift
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            EXTRA_ARGS="$EXTRA_ARGS -o $2"
            shift 2
            ;;
        --parallel)
            PARALLEL_JOBS="$2"
            shift 2
            ;;
        --delay)
            DELAY="$2"
            shift 2
            ;;
        --continue-on-error)
            CONTINUE_ON_ERROR=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            warning "Unknown option: $1"
            shift
            ;;
    esac
done

# Verify webenum script
if [ ! -f "$WEBENUM_SCRIPT" ]; then
    error "WebEnum script not found: $WEBENUM_SCRIPT"
    exit 1
fi

# Create log directory
mkdir -p "$LOG_DIR"

# Count domains
TOTAL=$(grep -v '^#' "$DOMAINS_FILE" | grep -v '^[[:space:]]*$' | wc -l)

if [ $TOTAL -eq 0 ]; then
    error "No domains found in $DOMAINS_FILE"
    exit 1
fi

# Display configuration
header "BATCH ENUMERATION"
info "Domains file: $DOMAINS_FILE"
info "Total domains: $TOTAL"
info "Parallel jobs: $PARALLEL_JOBS"
info "Delay: ${DELAY}s"
info "Output: $OUTPUT_DIR"
info "Extra args: ${EXTRA_ARGS:-none}"
info "Continue on error: $CONTINUE_ON_ERROR"
echo ""

# Confirm
read -p "$(echo -e ${YELLOW}Start processing? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    warning "Cancelled"
    exit 0
fi

# Initialize counters
COUNTER=0
SUCCESS=0
FAILED=0
SKIPPED=0
START_TIME=$(date +%s)

# Clear failed domains list
> "$FAILED_DOMAINS"

# Process function
process_domain() {
    local domain="$1"
    local job_num="$2"
    local log_file="${LOG_DIR}/${domain}.log"
    
    echo ""
    header "[$job_num/$TOTAL] $domain"
    
    # Check if already processed
    if [ -d "${OUTPUT_DIR}/${domain}_"* ] 2>/dev/null; then
        local existing=$(ls -dt "${OUTPUT_DIR}/${domain}_"* 2>/dev/null | head -1)
        warning "Previous scan: $existing"
        read -p "$(echo -e ${YELLOW}Skip? [Y/n]: ${NC})" -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            info "Skipping $domain"
            return 2
        fi
    fi
    
    # Run scan
    info "Scanning $domain..."
    info "Log: $log_file"
    
    if python3 "$WEBENUM_SCRIPT" -d "$domain" $EXTRA_ARGS > "$log_file" 2>&1; then
        success "✓ $domain complete"
        return 0
    else
        error "✗ $domain failed"
        echo "$domain" >> "$FAILED_DOMAINS"
        
        # Show last 5 lines
        warning "Last 5 lines:"
        tail -5 "$log_file" | sed 's/^/    /'
        
        return 1
    fi
}

# Export for parallel execution
export -f process_domain
export -f info
export -f success
export -f error
export -f warning
export WEBENUM_SCRIPT EXTRA_ARGS OUTPUT_DIR LOG_DIR BLUE GREEN RED YELLOW NC

# Read domains
mapfile -t DOMAINS < <(grep -v '^#' "$DOMAINS_FILE" | grep -v '^[[:space:]]*$')

# Process domains
if [ "$PARALLEL_JOBS" -gt 1 ]; then
    info "Processing $PARALLEL_JOBS domains in parallel..."
    
    for domain in "${DOMAINS[@]}"; do
        COUNTER=$((COUNTER + 1))
        
        # Wait if max parallel jobs reached
        while [ $(jobs -r | wc -l) -ge "$PARALLEL_JOBS" ]; do
            sleep 1
        done
        
        # Process in background
        (
            if process_domain "$domain" "$COUNTER"; then
                echo "SUCCESS:$domain" >> "${LOG_DIR}/status.tmp"
            elif [ $? -eq 2 ]; then
                echo "SKIPPED:$domain" >> "${LOG_DIR}/status.tmp"
            else
                echo "FAILED:$domain" >> "${LOG_DIR}/status.tmp"
            fi
        ) &
        
        # Delay
        [ "$DELAY" -gt 0 ] && sleep "$DELAY"
    done
    
    # Wait for all jobs
    wait
    
    # Count results
    if [ -f "${LOG_DIR}/status.tmp" ]; then
        SUCCESS=$(grep -c "^SUCCESS:" "${LOG_DIR}/status.tmp" || true)
        FAILED=$(grep -c "^FAILED:" "${LOG_DIR}/status.tmp" || true)
        SKIPPED=$(grep -c "^SKIPPED:" "${LOG_DIR}/status.tmp" || true)
        rm "${LOG_DIR}/status.tmp"
    fi
    
else
    # Sequential processing
    for domain in "${DOMAINS[@]}"; do
        COUNTER=$((COUNTER + 1))
        
        if process_domain "$domain" "$COUNTER"; then
            SUCCESS=$((SUCCESS + 1))
        elif [ $? -eq 2 ]; then
            SKIPPED=$((SKIPPED + 1))
        else
            FAILED=$((FAILED + 1))
            
            if [ "$CONTINUE_ON_ERROR" = false ]; then
                read -p "$(echo -e ${YELLOW}Continue? [Y/n]: ${NC})" -n 1 -r
                echo
                if [[ $REPLY =~ ^[Nn]$ ]]; then
                    warning "Stopped by user"
                    break
                fi
            fi
        fi
        
        # Delay
        if [ "$DELAY" -gt 0 ] && [ "$COUNTER" -lt "$TOTAL" ]; then
            info "Waiting ${DELAY}s..."
            sleep "$DELAY"
        fi
    done
fi

# Calculate time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
HOURS=$((ELAPSED / 3600))
MINUTES=$(((ELAPSED % 3600) / 60))
SECONDS=$((ELAPSED % 60))

# Generate summary
header "SUMMARY"

cat > "$RESULTS_SUMMARY" << EOF
Batch Enumeration Summary
Generated: $(date)
================================================================================

Configuration:
- Domains file: $DOMAINS_FILE
- Total domains: $TOTAL
- Parallel jobs: $PARALLEL_JOBS
- Output: $OUTPUT_DIR

Results:
- Successful: $SUCCESS
- Failed: $FAILED
- Skipped: $SKIPPED
- Processed: $COUNTER

Time:
- Total: ${HOURS}h ${MINUTES}m ${SECONDS}s
- Average: $((ELAPSED / COUNTER))s per domain

Failed Domains:
EOF

if [ $FAILED -gt 0 ]; then
    cat "$FAILED_DOMAINS" >> "$RESULTS_SUMMARY"
else
    echo "None" >> "$RESULTS_SUMMARY"
fi

# Display summary
cat "$RESULTS_SUMMARY"

echo ""
success "Successful: $SUCCESS"
if [ $FAILED -gt 0 ]; then
    error "Failed: $FAILED (see $FAILED_DOMAINS)"
fi
if [ $SKIPPED -gt 0 ]; then
    warning "Skipped: $SKIPPED"
fi
info "Processed: $COUNTER"
info "Time: ${HOURS}h ${MINUTES}m ${SECONDS}s"

echo ""
info "Results: $OUTPUT_DIR"
info "Summary: $RESULTS_SUMMARY"
info "Logs: $LOG_DIR"

# Generate combined report
if [ $SUCCESS -gt 0 ]; then
    echo ""
    read -p "$(echo -e ${YELLOW}Generate combined report? [y/N]: ${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Generating combined report..."
        
        COMBINED_REPORT="${LOG_DIR}/combined_report.md"
        
        cat > "$COMBINED_REPORT" << EOF
# Batch Enumeration Report

**Date**: $(date)
**Domains**: $SUCCESS successful

---

## Summary

| Metric | Count |
|--------|-------|
| Total | $TOTAL |
| Successful | $SUCCESS |
| Failed | $FAILED |
| Skipped | $SKIPPED |

---

## Domain Results

EOF
        
        # Add results from each domain
        for result_dir in "${OUTPUT_DIR}/"*_*; do
            if [ -d "$result_dir" ]; then
                domain=$(basename "$result_dir" | sed 's/_[0-9]*$//')
                report="${result_dir}/reports/report.md"
                
                if [ -f "$report" ]; then
                    echo "### $domain" >> "$COMBINED_REPORT"
                    echo "" >> "$COMBINED_REPORT"
                    tail -n +2 "$report" >> "$COMBINED_REPORT"
                    echo "" >> "$COMBINED_REPORT"
                    echo "---" >> "$COMBINED_REPORT"
                    echo "" >> "$COMBINED_REPORT"
                fi
            fi
        done
        
        success "Combined report: $COMBINED_REPORT"
    fi
fi

echo ""
if [ $SUCCESS -gt 0 ]; then
    success "✓ Batch processing complete"
else
    error "✗ No successful scans"
    exit 1
fi

exit 0