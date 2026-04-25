'use client'

import { useEffect, useRef, useState } from 'react'
import type { ProxyConfig, ProxyEntry } from '@/lib/types'

type FetchStatus = {
  phase: 'idle' | 'fetching' | 'validating' | 'done' | 'error'
  fetched: number
  validating: number
  validated: number
  valid: number
  error: string | null
  startedAt: string | null
  completedAt: string | null
}

type RemoteState = {
  status: FetchStatus
  validCount: number
  lastFetched: string | null
}

export default function ProxySettingsForm({ initial }: { initial: ProxyConfig }) {
  const [cfg, setCfg] = useState<ProxyConfig>(initial)
  const [busy, setBusy] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; msg: string } | null>(null)

  // rotation state
  const [remote, setRemote] = useState<RemoteState>({ status: { phase: 'idle', fetched: 0, validating: 0, validated: 0, valid: 0, error: null, startedAt: null, completedAt: null }, validCount: initial.proxies?.filter(p => p.valid).length ?? 0, lastFetched: initial.lastFetched ?? null })
  const [fetching, setFetching] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Load initial remote status ──────────────────────────────────────────────
  useEffect(() => {
    fetch('/api/settings/proxy/fetch').then(r => r.json()).then((d: RemoteState) => setRemote(d)).catch(() => {})
  }, [])

  // ── Poll while fetch is running ─────────────────────────────────────────────
  function startPolling() {
    if (pollRef.current) return
    pollRef.current = setInterval(async () => {
      try {
        const d: RemoteState = await fetch('/api/settings/proxy/fetch').then(r => r.json())
        setRemote(d)
        if (d.status.phase === 'done' || d.status.phase === 'error') {
          setFetching(false)
          clearInterval(pollRef.current!)
          pollRef.current = null
          // Reload proxy config to get updated proxies list
          const cfg2: ProxyConfig = await fetch('/api/settings/proxy').then(r => r.json())
          setCfg(cfg2)
        }
      } catch { /* ignore */ }
    }, 2000)
  }

  useEffect(() => {
    // If a fetch was already running when we loaded the page, resume polling
    if (remote.status.phase === 'fetching' || remote.status.phase === 'validating') {
      setFetching(true)
      startPolling()
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Save config ─────────────────────────────────────────────────────────────
  async function save() {
    setBusy(true)
    setSaveMsg(null)
    try {
      const res = await fetch('/api/settings/proxy', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg),
      })
      if (!res.ok) throw new Error((await res.json()).error ?? 'Failed')
      setSaveMsg({ ok: true, msg: '[FND] saved' })
    } catch (err) {
      setSaveMsg({ ok: false, msg: `[ERR] ${err instanceof Error ? err.message : 'Failed'}` })
    } finally {
      setBusy(false)
    }
  }

  // ── Start free proxy fetch ──────────────────────────────────────────────────
  async function startFetch() {
    setFetching(true)
    setSaveMsg(null)
    try {
      const res = await fetch('/api/settings/proxy/fetch', { method: 'POST' })
      const body = await res.json()
      if (!res.ok) throw new Error(body.error ?? 'Failed to start')
      startPolling()
    } catch (err) {
      setFetching(false)
      setSaveMsg({ ok: false, msg: `[ERR] ${err instanceof Error ? err.message : 'Failed'}` })
    }
  }

  // ── Styles ──────────────────────────────────────────────────────────────────
  const inputSt = {
    background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)',
    borderRadius: '12px', padding: '8px 12px', fontSize: '13px', outline: 'none',
    fontFamily: 'inherit', width: '100%',
  } as const

  const labelSt = {
    fontSize: '11px', color: 'var(--text-subtle)', marginBottom: '4px',
    display: 'block', textTransform: 'uppercase' as const, letterSpacing: '0.08em',
  }

  const phase = remote.status.phase
  const pct = remote.status.validating > 0
    ? Math.round((remote.status.validated / remote.status.validating) * 100)
    : 0

  return (
    <div className="space-y-5">

      {/* ── Enable toggle ──────────────────────────────────────────────────── */}
      <label className="flex items-center gap-3 cursor-pointer">
        <Toggle on={cfg.enabled} onChange={(v) => setCfg(c => ({ ...c, enabled: v }))} />
        <span className="text-sm" style={{ color: cfg.enabled ? 'var(--text)' : 'var(--text-muted)' }}>
          Enable proxy routing
        </span>
        {cfg.enabled && (
          <span className="text-xs px-2 py-0.5 rounded"
            style={{ background: 'rgba(135,88,216,0.15)', color: 'var(--purple-bright)', border: '1px solid rgba(135,88,216,0.2)' }}>
            active
          </span>
        )}
      </label>

      {/* ── Mode selector ──────────────────────────────────────────────────── */}
      <div className="flex gap-2">
        {(['single', 'rotate'] as const).map((m) => (
          <button key={m} type="button"
            onClick={() => setCfg(c => ({ ...c, mode: m }))}
            className="px-4 py-2 rounded-xl text-sm font-semibold transition-colors"
            style={{
              background: cfg.mode === m ? 'rgba(135,88,216,0.18)' : 'var(--surface-2)',
              color: cfg.mode === m ? 'var(--purple-bright)' : 'var(--text-muted)',
              border: `1px solid ${cfg.mode === m ? 'rgba(135,88,216,0.35)' : 'var(--border)'}`,
              fontFamily: 'inherit', cursor: 'pointer',
            }}>
            {m === 'single' ? '🎯 Single proxy' : '🔄 Rotate (free list)'}
          </button>
        ))}
      </div>

      {/* ── SINGLE mode ────────────────────────────────────────────────────── */}
      {cfg.mode === 'single' && (
        <div className="space-y-3 rounded-xl p-4"
          style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>

          <div className="text-xs mb-3" style={{ color: 'var(--text-subtle)' }}>
            Route all scan traffic through a fixed proxy — ideal for <span style={{ color: 'var(--orange)' }}>Burp Suite</span>, MITM Proxy, or a corporate proxy.
          </div>

          <div>
            <label style={labelSt}>HTTP Proxy URL</label>
            <input style={inputSt} value={cfg.http}
              onChange={e => setCfg(c => ({ ...c, http: e.target.value }))}
              placeholder="http://127.0.0.1:8080" />
          </div>
          <div>
            <label style={labelSt}>HTTPS Proxy URL</label>
            <input style={inputSt} value={cfg.https}
              onChange={e => setCfg(c => ({ ...c, https: e.target.value }))}
              placeholder="http://127.0.0.1:8080" />
          </div>
          <div>
            <label style={labelSt}>No Proxy (bypass)</label>
            <input style={inputSt} value={cfg.noProxy}
              onChange={e => setCfg(c => ({ ...c, noProxy: e.target.value }))}
              placeholder="localhost,127.0.0.1,.internal" />
            <p className="mt-1 text-xs" style={{ color: 'var(--text-subtle)' }}>
              Comma-separated hosts/domains that bypass the proxy.
            </p>
          </div>

          {/* Burp quick-fill */}
          <div className="flex flex-wrap gap-2 pt-1">
            <span className="text-xs" style={{ color: 'var(--text-subtle)' }}>quick fill:</span>
            {[
              { label: 'Burp :8080', http: 'http://127.0.0.1:8080', https: 'http://127.0.0.1:8080' },
              { label: 'MITM :8080', http: 'http://127.0.0.1:8080', https: 'http://127.0.0.1:8080' },
              { label: 'Burp :8081', http: 'http://127.0.0.1:8081', https: 'http://127.0.0.1:8081' },
            ].map(q => (
              <button key={q.label} type="button"
                onClick={() => setCfg(c => ({ ...c, http: q.http, https: q.https }))}
                className="text-xs px-2.5 py-1 rounded-lg"
                style={{ background: 'var(--surface-3)', color: 'var(--cyan)', border: '1px solid var(--border)', fontFamily: 'inherit', cursor: 'pointer' }}>
                {q.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── ROTATE mode ────────────────────────────────────────────────────── */}
      {cfg.mode === 'rotate' && (
        <div className="space-y-4">
          <div className="rounded-xl p-4 space-y-3"
            style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>

            <div className="text-xs" style={{ color: 'var(--text-subtle)' }}>
              Fetches free HTTP/SOCKS5 proxies from public lists, validates them via <code style={{ color: 'var(--cyan)' }}>curl</code>, and rotates through working ones during scans.
            </div>

            {/* Stats row */}
            <div className="flex flex-wrap gap-4">
              <div className="text-sm">
                <span className="font-mono font-bold" style={{ color: 'var(--green)' }}>
                  {remote.validCount}
                </span>
                <span className="ml-1.5" style={{ color: 'var(--text-muted)' }}>valid proxies</span>
              </div>
              {remote.lastFetched && (
                <div className="text-xs" style={{ color: 'var(--text-subtle)' }}>
                  last fetch: {new Date(remote.lastFetched).toLocaleString()}
                </div>
              )}
            </div>

            {/* Progress bar while fetching/validating */}
            {(phase === 'fetching' || phase === 'validating') && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs" style={{ color: 'var(--text-muted)' }}>
                  <span>
                    {phase === 'fetching'
                      ? '[INF] fetching proxy lists…'
                      : `[INF] validating ${remote.status.validated}/${remote.status.validating} — ${remote.status.valid} valid so far`}
                  </span>
                  <span>{phase === 'validating' ? `${pct}%` : ''}</span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--surface-3)' }}>
                  <div className="h-full rounded-full transition-all"
                    style={{ width: phase === 'fetching' ? '8%' : `${pct}%`, background: 'var(--purple)' }} />
                </div>
              </div>
            )}

            {phase === 'done' && (
              <div className="text-xs" style={{ color: 'var(--green)' }}>
                [FND] done — {remote.validCount} working proxies found
              </div>
            )}
            {phase === 'error' && (
              <div className="text-xs" style={{ color: 'var(--red)' }}>
                [ERR] {remote.status.error ?? 'fetch failed'}
              </div>
            )}

            <button type="button"
              disabled={fetching}
              onClick={() => void startFetch()}
              className="neon-button px-4 py-2 text-sm font-semibold"
              style={{ opacity: fetching ? 0.5 : 1, cursor: fetching ? 'not-allowed' : 'pointer', fontFamily: 'inherit' }}>
              {fetching ? '⟳ fetching…' : remote.validCount > 0 ? '↻ refresh list' : '⬇ fetch free proxies'}
            </button>
          </div>

          {/* Proxy list preview */}
          {cfg.proxies && cfg.proxies.length > 0 && (
            <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between px-4 py-2.5 border-b"
                style={{ borderColor: 'var(--border)', background: 'var(--surface-2)', fontSize: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>
                  proxy list — {cfg.proxies.filter(p => p.valid).length} valid / {cfg.proxies.length} total
                </span>
              </div>
              <div className="overflow-auto" style={{ maxHeight: '240px' }}>
                {cfg.proxies.filter(p => p.valid).slice(0, 100).map((p, i) => (
                  <ProxyRow key={p.url + i} proxy={p} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Save button ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 pt-1">
        <button type="button" disabled={busy}
          onClick={() => void save()}
          className="neon-button px-4 py-2 text-sm font-semibold"
          style={{ opacity: busy ? 0.5 : 1, cursor: busy ? 'not-allowed' : 'pointer', fontFamily: 'inherit' }}>
          {busy ? 'saving…' : 'save'}
        </button>
        {saveMsg && (
          <span className="text-sm" style={{ color: saveMsg.ok ? 'var(--green)' : 'var(--red)' }}>
            {saveMsg.msg}
          </span>
        )}
      </div>

      {/* ── Info box ────────────────────────────────────────────────────────── */}
      <div className="rounded-xl p-4 text-xs space-y-1"
        style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)', color: 'var(--text-subtle)' }}>
        <div className="font-semibold mb-1.5" style={{ color: 'var(--text-muted)' }}>[INF] how proxies are applied</div>
        <div>• <code>HTTP_PROXY</code> / <code>HTTPS_PROXY</code> env vars → all sub-processes inherit them</div>
        <div>• Explicit <code>-proxy</code> flag passed to: httpx, nuclei, subfinder, katana, dalfox, gowitness</div>
        <div>• Python <code>requests</code> calls pick up env vars automatically</div>
        <div>• Rotate mode picks a random valid proxy from the list at scan start</div>
      </div>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Toggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="relative cursor-pointer" style={{ width: '38px', height: '20px' }}
      onClick={() => onChange(!on)}>
      <div style={{
        position: 'absolute', inset: 0,
        background: on ? 'rgba(135,88,216,0.6)' : 'var(--surface-3)',
        border: `1px solid ${on ? 'rgba(135,88,216,0.5)' : 'var(--border)'}`,
        borderRadius: '999px', transition: 'background 0.15s',
      }} />
      <div style={{
        position: 'absolute', top: '3px', left: on ? '20px' : '3px',
        width: '12px', height: '12px',
        background: on ? 'var(--purple-bright)' : 'var(--text-subtle)',
        borderRadius: '50%', transition: 'left 0.15s',
      }} />
    </div>
  )
}

function ProxyRow({ proxy }: { proxy: ProxyEntry }) {
  const latColor = proxy.latency === null ? 'var(--text-subtle)'
    : proxy.latency < 1000 ? 'var(--green)'
    : proxy.latency < 3000 ? 'var(--yellow)'
    : 'var(--red)'

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b text-xs font-mono"
      style={{ borderColor: 'var(--border-subtle)' }}>
      <span className="flex-1 truncate" style={{ color: 'var(--text)' }}>{proxy.url}</span>
      <span className="px-1.5 py-0.5 rounded text-xs"
        style={{ background: 'var(--surface-2)', color: 'var(--cyan)', border: '1px solid var(--border)' }}>
        {proxy.protocol}
      </span>
      {proxy.latency !== null && (
        <span style={{ color: latColor, minWidth: '50px', textAlign: 'right' }}>
          {proxy.latency}ms
        </span>
      )}
    </div>
  )
}
