import { NextResponse } from 'next/server'
import { spawn, execSync } from 'child_process'
import fs from 'fs'
import path from 'path'
import { getConfigDir } from '@/lib/app-data'
import { readFetchStatus, curlAvailable } from '@/lib/proxy-fetcher'

export const dynamic = 'force-dynamic'

// ── GET — return current fetch status ─────────────────────────────────────────

export async function GET() {
  const configDir = getConfigDir()
  const status = readFetchStatus(configDir)

  const proxyFile = path.join(configDir, 'proxy.json')
  let validCount = 0
  let lastFetched: string | null = null
  try {
    if (fs.existsSync(proxyFile)) {
      const cfg = JSON.parse(fs.readFileSync(proxyFile, 'utf-8'))
      validCount = Array.isArray(cfg.proxies) ? cfg.proxies.filter((p: { valid: boolean }) => p.valid).length : 0
      lastFetched = cfg.lastFetched ?? null
    }
  } catch { /* ignore */ }

  return NextResponse.json({ status, validCount, lastFetched })
}

// ── POST — spawn background Python fetch+validate job ─────────────────────────

export async function POST() {
  if (!curlAvailable()) {
    return NextResponse.json({ error: 'curl is not installed — required for proxy validation' }, { status: 400 })
  }

  // Check Python is available
  let pythonBin = 'python3'
  try { execSync('python3 --version', { stdio: 'ignore', timeout: 3000 }) }
  catch {
    try { execSync('python --version', { stdio: 'ignore', timeout: 3000 }); pythonBin = 'python' }
    catch { return NextResponse.json({ error: 'python3 not found — required for proxy fetching' }, { status: 400 }) }
  }

  const configDir = getConfigDir()

  // Reset status
  const statusFile = path.join(configDir, 'proxy_fetch_status.json')
  fs.writeFileSync(statusFile, JSON.stringify({
    phase: 'fetching', fetched: 0, validating: 0, validated: 0, valid: 0,
    error: null, startedAt: new Date().toISOString(), completedAt: null,
  }))

  // Write the Python fetcher script
  const scriptPath = path.join(configDir, 'proxy_fetcher.py')
  fs.writeFileSync(scriptPath, PYTHON_FETCHER)

  // Spawn detached — pass configDir as argument so paths are always correct
  const child = spawn(pythonBin, [scriptPath, configDir], {
    detached: true,
    stdio: 'ignore',
    env: { ...process.env },
  })
  child.unref()

  return NextResponse.json({ ok: true, message: 'Proxy fetch started' })
}

// ── Python fetcher script ──────────────────────────────────────────────────────
// Written to configDir/proxy_fetcher.py and run with configDir as argv[1].
// Uses only stdlib: urllib, subprocess, json, os.

const PYTHON_FETCHER = `#!/usr/bin/env python3
"""
GivEnum proxy fetcher — fetches free proxy lists, validates via curl,
saves results to proxy.json in the config dir.
Usage: python3 proxy_fetcher.py <config_dir>
"""
import sys, os, json, subprocess, time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from concurrent.futures import ThreadPoolExecutor, as_completed

CONFIG_DIR   = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / '.config' / 'givenum'
PROXY_FILE   = CONFIG_DIR / 'proxy.json'
STATUS_FILE  = CONFIG_DIR / 'proxy_fetch_status.json'
VALIDATE_URL = 'https://api.ipify.org'
TIMEOUT_S    = 8
CONCURRENCY  = 40

SOURCES = [
    'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&proxy_format=ipport&format=text&timeout=5000',
    'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&proxy_format=protocolipport&format=text&timeout=5000',
    'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
    'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt',
    'https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt',
    'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
]

def ws(data):
    try:
        STATUS_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass

def fetch_source(url):
    try:
        req = Request(url, headers={'User-Agent': 'GivEnum/1.0'})
        with urlopen(req, timeout=15) as r:
            return r.read().decode('utf-8', errors='replace').splitlines()
    except Exception:
        return []

def normalise(raw):
    raw = raw.strip()
    if not raw or raw.startswith('#'):
        return None
    import re
    if re.match(r'^(https?|socks[45])://', raw, re.I):
        return raw.lower()
    m = re.match(r'^(\\d{1,3}(?:\\.\\d{1,3}){3}):(\\d{2,5})$', raw)
    if m:
        port = int(m.group(2))
        if 1 <= port <= 65535:
            return f'http://{m.group(1)}:{m.group(2)}'
    return None

def validate_proxy(url):
    start = time.time()
    try:
        result = subprocess.run(
            ['curl', '--proxy', url, '--max-time', str(TIMEOUT_S),
             '--connect-timeout', '6', '-s', '-o', '/dev/null', '-w', '%{http_code}',
             VALIDATE_URL],
            capture_output=True, text=True,
            timeout=TIMEOUT_S + 3
        )
        latency = int((time.time() - start) * 1000)
        ok = result.returncode == 0 and result.stdout.strip().startswith('2')
        return url, ok, latency
    except Exception:
        return url, False, int((time.time() - start) * 1000)

def main():
    status = {
        'phase': 'fetching', 'fetched': 0, 'validating': 0,
        'validated': 0, 'valid': 0, 'error': None,
        'startedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'completedAt': None,
    }
    ws(status)

    # 1. Fetch sources in parallel
    all_lines = []
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as ex:
        for lines in ex.map(fetch_source, SOURCES):
            all_lines.extend(lines)

    unique = list(dict.fromkeys(filter(None, (normalise(l) for l in all_lines))))
    status['fetched'] = len(unique)
    status['validating'] = len(unique)
    status['phase'] = 'validating'
    ws(status)

    # 2. Validate in parallel batches
    valid_proxies = []
    completed = 0

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {ex.submit(validate_proxy, url): url for url in unique}
        for future in as_completed(futures):
            url, ok, latency = future.result()
            completed += 1
            status['validated'] = completed
            if ok:
                proto = url.split('://')[0] if '://' in url else 'http'
                valid_proxies.append({
                    'url': url, 'protocol': proto, 'latency': latency,
                    'valid': True, 'lastChecked': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                })
                status['valid'] = len(valid_proxies)
            # Write progress every 20 completions
            if completed % 20 == 0 or completed == len(unique):
                ws(status)

    # Sort by latency
    valid_proxies.sort(key=lambda p: p['latency'] or 9999)

    # 3. Merge into proxy.json
    existing = {}
    if PROXY_FILE.exists():
        try:
            existing = json.loads(PROXY_FILE.read_text())
        except Exception:
            pass
    existing['proxies'] = valid_proxies
    existing['lastFetched'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    PROXY_FILE.write_text(json.dumps(existing, indent=2))

    # 4. Final status
    status['phase'] = 'done'
    status['completedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    ws(status)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        ws({
            'phase': 'error', 'error': str(e), 'fetched': 0,
            'validating': 0, 'validated': 0, 'valid': 0,
            'startedAt': None, 'completedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        })
        sys.exit(1)
`
