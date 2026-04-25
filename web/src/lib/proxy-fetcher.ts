/**
 * proxy-fetcher.ts
 *
 * Fetches free proxy lists from public sources, deduplicates them,
 * validates each one via a curl test, and writes results to proxy.json.
 *
 * Designed to run in a Node.js background process (spawned detached from
 * the Next.js API route) so it doesn't block the server.
 */

import fs from 'fs'
import path from 'path'
import { execSync, execFile } from 'child_process'
import type { ProxyEntry } from './types'

// ── Status file ────────────────────────────────────────────────────────────────

export interface FetchStatus {
  phase: 'idle' | 'fetching' | 'validating' | 'done' | 'error'
  fetched: number
  validating: number    // total being validated
  validated: number     // completed so far
  valid: number
  error: string | null
  startedAt: string | null
  completedAt: string | null
}

export function getProxyFetchStatusFile(configDir: string): string {
  return path.join(configDir, 'proxy_fetch_status.json')
}

export function readFetchStatus(configDir: string): FetchStatus {
  const file = getProxyFetchStatusFile(configDir)
  try {
    if (fs.existsSync(file)) return JSON.parse(fs.readFileSync(file, 'utf-8')) as FetchStatus
  } catch { /* ignore */ }
  return { phase: 'idle', fetched: 0, validating: 0, validated: 0, valid: 0, error: null, startedAt: null, completedAt: null }
}

function writeStatus(configDir: string, status: FetchStatus) {
  try { fs.writeFileSync(getProxyFetchStatusFile(configDir), JSON.stringify(status, null, 2)) } catch { /* ignore */ }
}

// ── Free proxy sources ─────────────────────────────────────────────────────────
// Each returns plain text, one proxy per line.
// Formats accepted: "IP:PORT" or "PROTO://IP:PORT"

const SOURCES = [
  // proxyscrape — http
  'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&proxy_format=ipport&format=text&timeout=5000',
  // proxyscrape — socks5
  'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&proxy_format=protocolipport&format=text&timeout=5000',
  // TheSpeedX HTTP list (GitHub raw)
  'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
  // TheSpeedX SOCKS5 list
  'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt',
  // roosterkid openproxylist
  'https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt',
  // jetkai proxy-list HTTP
  'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
]

async function fetchSource(url: string): Promise<string[]> {
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 15000)
    const res = await fetch(url, { signal: controller.signal })
    clearTimeout(timer)
    if (!res.ok) return []
    const text = await res.text()
    return text.split('\n').map((l) => l.trim()).filter(Boolean)
  } catch {
    return []
  }
}

export function normaliseProxy(raw: string): string | null {
  raw = raw.trim()
  if (!raw || raw.startsWith('#')) return null
  // Already has protocol
  if (/^(https?|socks[45]):\/\//i.test(raw)) {
    try { new URL(raw); return raw.toLowerCase() } catch { return null }
  }
  // IP:PORT — assume http
  const m = raw.match(/^(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})$/)
  if (m) {
    const port = parseInt(m[2], 10)
    if (port < 1 || port > 65535) return null
    return `http://${m[1]}:${m[2]}`
  }
  return null
}

// ── Validation ─────────────────────────────────────────────────────────────────

const VALIDATION_URL = 'https://api.ipify.org'
const VALIDATE_TIMEOUT_S = 8
const VALIDATE_CONCURRENCY = 40

function validateProxy(proxyUrl: string): Promise<{ ok: boolean; latency: number }> {
  return new Promise((resolve) => {
    const start = Date.now()
    // SECURITY: use execFile (no shell) so a malicious proxy URL like
    // `http://x:80$(touch /tmp/pwn)` cannot trigger command substitution.
    // Sources are public GitHub repos — supply-chain risk is real.
    const args = [
      '--proxy', proxyUrl,
      '--max-time', String(VALIDATE_TIMEOUT_S),
      '--connect-timeout', '6',
      '-s', '-o', '/dev/null',
      '-w', '%{http_code}',
      VALIDATION_URL,
    ]
    execFile('curl', args, { timeout: (VALIDATE_TIMEOUT_S + 2) * 1000 }, (err, stdout) => {
      const latency = Date.now() - start
      if (err) return resolve({ ok: false, latency })
      const code = parseInt(String(stdout).trim(), 10)
      resolve({ ok: code >= 200 && code < 400, latency })
    })
  })
}

async function validateBatch(proxies: string[], onProgress: (done: number, valid: number) => void): Promise<ProxyEntry[]> {
  const results: ProxyEntry[] = []
  let done = 0
  let valid = 0

  for (let i = 0; i < proxies.length; i += VALIDATE_CONCURRENCY) {
    const batch = proxies.slice(i, i + VALIDATE_CONCURRENCY)
    const batchResults = await Promise.all(
      batch.map(async (url) => {
        const { ok, latency } = await validateProxy(url)
        return { url, ok, latency }
      })
    )

    for (const r of batchResults) {
      done++
      const proto = r.url.split('://')[0] ?? 'http'
      if (r.ok) {
        valid++
        results.push({
          url: r.url,
          protocol: proto,
          latency: r.latency,
          valid: true,
          lastChecked: new Date().toISOString(),
        })
      }
    }

    onProgress(done, valid)
  }

  return results
}

// ── Main entry (called from spawned script) ────────────────────────────────────

export async function runProxyFetch(configDir: string) {
  const proxyFile = path.join(configDir, 'proxy.json')
  const status: FetchStatus = {
    phase: 'fetching',
    fetched: 0,
    validating: 0,
    validated: 0,
    valid: 0,
    error: null,
    startedAt: new Date().toISOString(),
    completedAt: null,
  }
  writeStatus(configDir, status)

  // ── 1. Fetch all sources ───────────────────────────────────────────────────
  const rawLines = (await Promise.all(SOURCES.map(fetchSource))).flat()
  const unique = new Set<string>()
  for (const line of rawLines) {
    const norm = normaliseProxy(line)
    if (norm) unique.add(norm)
  }
  const proxies = [...unique]
  status.fetched = proxies.length
  status.validating = proxies.length
  status.phase = 'validating'
  writeStatus(configDir, status)

  // ── 2. Validate in parallel batches ───────────────────────────────────────
  const valid = await validateBatch(proxies, (done, validCount) => {
    status.validated = done
    status.valid = validCount
    writeStatus(configDir, status)
  })

  // Sort by latency ascending
  valid.sort((a, b) => (a.latency ?? 9999) - (b.latency ?? 9999))

  // ── 3. Merge into proxy.json ───────────────────────────────────────────────
  let existing: Record<string, unknown> = {}
  try {
    if (fs.existsSync(proxyFile)) existing = JSON.parse(fs.readFileSync(proxyFile, 'utf-8'))
  } catch { /* start fresh */ }

  existing.proxies = valid
  existing.lastFetched = new Date().toISOString()
  fs.writeFileSync(proxyFile, JSON.stringify(existing, null, 2))

  // ── 4. Write done status ───────────────────────────────────────────────────
  status.phase = 'done'
  status.completedAt = new Date().toISOString()
  writeStatus(configDir, status)
}

// ── CLI entry — called when this file is executed directly via ts-node/node ────
// Usage: node proxy-fetcher-runner.js <configDir>
if (require.main === module) {
  const configDir = process.argv[2] ?? path.join(process.env.HOME ?? '/tmp', '.config', 'givenum')
  runProxyFetch(configDir).catch((err) => {
    const configDirArg = process.argv[2] ?? path.join(process.env.HOME ?? '/tmp', '.config', 'givenum')
    const statusFile = getProxyFetchStatusFile(configDirArg)
    try {
      fs.writeFileSync(statusFile, JSON.stringify({
        phase: 'error', error: String(err), fetched: 0, validating: 0, validated: 0, valid: 0,
        startedAt: null, completedAt: new Date().toISOString(),
      }))
    } catch { /* ignore */ }
    process.exit(1)
  })
}

// ── Helper used in API route: pick a working proxy from list ──────────────────

export function pickProxy(proxies: ProxyEntry[]): ProxyEntry | null {
  const valid = proxies.filter((p) => p.valid)
  if (valid.length === 0) return null
  // Weighted random: prefer lower latency entries (top 20% get 5× weight)
  const top = Math.max(1, Math.floor(valid.length * 0.2))
  const r = Math.random()
  if (r < 0.7 && valid.length > 1) {
    return valid[Math.floor(Math.random() * top)]
  }
  return valid[Math.floor(Math.random() * valid.length)]
}

/** Verify curl is available on PATH */
export function curlAvailable(): boolean {
  try { execSync('curl --version', { stdio: 'ignore', timeout: 3000 }); return true } catch { return false }
}
