#!/usr/bin/env python3
"""
Background job runner for GivEnum scans started by the web UI.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Set


def load_job(job_file: Path) -> Optional[dict]:
    """Read a job JSON file. Returns None for missing/corrupt files.

    NB: previously used a bare `except Exception: pass` which silently swallowed
    JSON corruption, OS errors, AND KeyboardInterrupt-derived bugs. Now we
    classify and log so a corrupt job file shows up in stderr instead of
    behaving as a missing file (TASK #29).
    """
    if not job_file.exists():
        return None
    try:
        with open(job_file, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError as e:
        print(f"[!] scan_runner: corrupt job file {job_file}: {e}", file=sys.stderr)
        return None
    except OSError as e:
        print(f"[!] scan_runner: cannot read job file {job_file}: {e}", file=sys.stderr)
        return None


def save_job(job_file: Path, data: dict):
    job_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = job_file.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    tmp.replace(job_file)  # atomic rename


def update_job(job_file: Path, **fields) -> bool:
    job = load_job(job_file)
    if not job:
        return False
    job.update(fields)
    save_job(job_file, job)
    return True


def find_scan_dir(base_output_dir: Path, domain: str, before: Set[str]) -> Optional[Path]:
    candidates = [
        entry for entry in base_output_dir.iterdir()
        if entry.is_dir() and entry.name.startswith(f"{domain}_") and entry.name not in before
    ]
    if not candidates:
        candidates = [
            entry for entry in base_output_dir.iterdir()
            if entry.is_dir() and entry.name.startswith(f"{domain}_")
        ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]


def encode_scan_id(scan_dir: Path, results_dir: Path) -> str:
    relative = scan_dir.relative_to(results_dir).as_posix().encode('utf-8')
    return base64.urlsafe_b64encode(relative).decode('utf-8').rstrip('=')


def main():
    parser = argparse.ArgumentParser(description='Run a GivEnum scan job')
    parser.add_argument('--job-file', required=True)
    parser.add_argument('--scanner-script', required=True)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--config-dir', required=True)
    parser.add_argument('--log-file', required=True)
    parser.add_argument('--active', action='store_true')
    parser.add_argument('--skip-screenshots', action='store_true')
    parser.add_argument('--skip-portscan', action='store_true')
    parser.add_argument('--skip-vuln-scan', action='store_true')
    args = parser.parse_args()

    job_file = Path(args.job_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(args.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    before = {entry.name for entry in output_dir.iterdir() if entry.is_dir()} if output_dir.exists() else set()
    if not update_job(
        job_file,
        status='running',
        startedAt=datetime.utcnow().isoformat() + 'Z',
        endedAt=None,
        returnCode=None,
        logFile=str(log_file),
    ):
        print(f"Job file missing or invalid, aborting: {job_file}", file=sys.stderr)
        return

    cmd = [
        sys.executable,
        '-u',
        args.scanner_script,
        '-d', args.domain,
        '-o', str(output_dir),
        '--no-notify',
    ]
    if args.active:
        cmd.append('--active')
    if args.skip_screenshots:
        cmd.append('--skip-screenshots')
    if args.skip_portscan:
        cmd.append('--skip-portscan')
    if args.skip_vuln_scan:
        cmd.append('--skip-vuln-scan')

    env = os.environ.copy()
    env['GIVENUM_CONFIG_DIR'] = args.config_dir
    results_dir = Path(env.get('RESULTS_DIR', output_dir.parent))

    with open(log_file, 'a') as log:
        log.write(f"[{datetime.utcnow().isoformat()}Z] Starting job\n")
        log.write(f"Command: {' '.join(cmd)}\n\n")
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
        update_job(job_file, pid=proc.pid)
        proc.wait()
        log.write(f"\n[{datetime.utcnow().isoformat()}Z] Job finished with rc={proc.returncode}\n")

    scan_dir = find_scan_dir(output_dir, args.domain, before)
    # analyze_results.py was removed (TASK #20). The analysis_file slot in the
    # job metadata is kept for backward compat but always None now.
    analysis_file = None

    current_job = load_job(job_file)
    if current_job and current_job.get('status') == 'stopped':
        final_status = 'stopped'
    else:
        final_status = 'completed' if proc.returncode == 0 else 'failed'

    update_job(
        job_file,
        status=final_status,
        endedAt=datetime.utcnow().isoformat() + 'Z',
        returnCode=proc.returncode,
        pid=None,
        scanId=encode_scan_id(scan_dir, results_dir) if scan_dir else None,
        scanDir=str(scan_dir) if scan_dir else None,
        analysisFile=str(analysis_file) if analysis_file else None,
    )


if __name__ == '__main__':
    main()
