'use client'

import { useState } from 'react'
import type { ScanMeta } from '@/lib/types'

type Props = {
  scans: ScanMeta[]
}

export default function ReportsForm({ scans }: Props) {
  const [selected, setSelected] = useState<string>(scans[0]?.id ?? '')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null)

  const scan = scans.find((s) => s.id === selected)

  async function generate() {
    if (!selected) return
    setBusy(true)
    setStatus(null)
    try {
      const res = await fetch(`/api/reports/${selected}`, { method: 'POST' })
      if (!res.ok) throw new Error((await res.json()).error ?? 'Failed')
      setStatus({ ok: true, msg: '[FND] report generated' })
    } catch (err) {
      setStatus({ ok: false, msg: `[ERR] ${err instanceof Error ? err.message : 'Failed'}` })
    } finally {
      setBusy(false)
    }
  }

  if (scans.length === 0) {
    return (
      <div className="text-center py-8" style={{ color: 'var(--text-subtle)', fontSize: '13px' }}>
        no scans available — run a scan first
      </div>
    )
  }

  const selectStyle = {
    background: 'var(--surface-2)',
    border: '1px solid var(--border)',
    color: 'var(--text)',
    borderRadius: '12px',
    padding: '8px 12px',
    fontSize: '13px',
    outline: 'none',
    fontFamily: 'inherit',
    width: '100%',
  } as const

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <div>
          <label className="block text-xs mb-1.5"
            style={{ color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            select scan
          </label>
          <select value={selected} onChange={(e) => setSelected(e.target.value)} style={selectStyle}>
            {scans.map((s) => (
              <option key={s.id} value={s.id}>
                {s.domain} — {s.mode} — {s.timestamp.slice(0, 10)}
              </option>
            ))}
          </select>
        </div>

        {scan && (
          <div className="rounded-xl p-3 text-xs space-y-1"
            style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ color: 'var(--text-muted)' }}>
              <span style={{ color: 'var(--text-subtle)' }}>domain </span>
              <span style={{ color: 'var(--cyan)' }}>{scan.domain}</span>
            </div>
            <div style={{ color: 'var(--text-muted)' }}>
              <span style={{ color: 'var(--text-subtle)' }}>project </span>{scan.projectName}
            </div>
            <div className="flex flex-wrap gap-3 mt-1">
              {scan.stats.subdomains > 0 && <span style={{ color: 'var(--cyan)' }}>subs {scan.stats.subdomains}</span>}
              {scan.stats.alive > 0 && <span style={{ color: 'var(--green)' }}>alive {scan.stats.alive}</span>}
              {scan.stats.urls > 0 && <span style={{ color: 'var(--purple-bright)' }}>urls {scan.stats.urls}</span>}
              {scan.stats.vulns > 0 && <span style={{ color: 'var(--red)' }}>vulns {scan.stats.vulns}</span>}
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={busy || !selected}
          onClick={() => void generate()}
          className="neon-button px-4 py-2 text-sm font-semibold"
          style={{
            opacity: busy || !selected ? 0.5 : 1,
            cursor: busy || !selected ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit',
          }}>
          {busy ? 'generating...' : 'generate report'}
        </button>

        {status?.ok && selected && (
          <a
            href={`/api/reports/${selected}`}
            target="_blank"
            rel="noopener"
            className="text-sm px-3 py-2 rounded-xl"
            style={{
              background: 'rgba(74,222,128,0.1)',
              color: 'var(--green)',
              border: '1px solid rgba(74,222,128,0.2)',
              textDecoration: 'none',
            }}>
            open report ↗
          </a>
        )}

        {status && (
          <span className="text-sm" style={{ color: status.ok ? 'var(--green)' : 'var(--red)' }}>
            {status.msg}
          </span>
        )}
      </div>

      <div className="text-xs" style={{ color: 'var(--text-subtle)' }}>
        Report is saved as <code>report.html</code> inside the scan directory and served via <code>/api/reports/{'{scanId}'}</code>.
      </div>
    </div>
  )
}
