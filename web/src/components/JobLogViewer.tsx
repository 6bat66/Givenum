'use client'

import Link from 'next/link'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { ScanJob } from '@/lib/types'

type Props = {
  initialJob: ScanJob
  initialLog: string
}

type FetchState = {
  job: ScanJob
  log: string
  truncated: boolean
  updatedAt: string | null
}

type AnsiState = {
  fg: string | null
  bg: string | null
  bold: boolean
  dim: boolean
}

const ANSI_PATTERN = /\u001b\[([0-9;]*)m/g
const ANSI_CONTROL_PATTERN = /\u001b\[[0-9;?]*[A-Za-z]/g
const ANSI_OSC_PATTERN = /\u001b\][^\u0007]*(\u0007|\u001b\\)/g

const ANSI_FG: Record<number, string> = {
  30: '#111827',
  31: '#f87171',
  32: '#86efac',
  33: '#fde047',
  34: '#93c5fd',
  35: '#e879f9',
  36: '#67e8f9',
  37: '#e5e7eb',
  90: '#6b7280',
  91: '#fca5a5',
  92: '#bbf7d0',
  93: '#fef08a',
  94: '#bfdbfe',
  95: '#f5d0fe',
  96: '#a5f3fc',
  97: '#ffffff',
}

const ANSI_BG: Record<number, string> = {
  40: '#111827',
  41: '#7f1d1d',
  42: '#14532d',
  43: '#713f12',
  44: '#1e3a8a',
  45: '#701a75',
  46: '#164e63',
  47: '#e5e7eb',
  100: '#374151',
  101: '#991b1b',
  102: '#166534',
  103: '#854d0e',
  104: '#1d4ed8',
  105: '#86198f',
  106: '#155e75',
  107: '#f9fafb',
}

// Known scan phases in approximate order. Each phase adds ~1 step.
const SCAN_PHASES = [
  { pattern: /subdomain enum/i, label: 'Subdomain Enum', step: 1 },
  { pattern: /dns resolv/i, label: 'DNS Resolution', step: 2 },
  { pattern: /http prob/i, label: 'HTTP Probing', step: 3 },
  { pattern: /url collect/i, label: 'URL Collection', step: 4 },
  { pattern: /javascript/i, label: 'JS Analysis', step: 5 },
  { pattern: /port scan/i, label: 'Port Scan', step: 6 },
  { pattern: /vuln scan|nuclei/i, label: 'Vuln Scan', step: 7 },
  { pattern: /screenshot/i, label: 'Screenshots', step: 8 },
  { pattern: /diff|report/i, label: 'Report', step: 9 },
]
const TOTAL_STEPS = SCAN_PHASES.length + 1

function estimateProgress(log: string, isFinished: boolean): { pct: number; phase: string } {
  if (isFinished) return { pct: 100, phase: 'Done' }
  if (!log) return { pct: 0, phase: 'Starting…' }

  let maxStep = 0
  let currentPhase = 'Starting…'

  for (const { pattern, label, step } of SCAN_PHASES) {
    if (pattern.test(log)) {
      if (step > maxStep) {
        maxStep = step
        currentPhase = label
      }
    }
  }

  const pct = Math.min(Math.round((maxStep / TOTAL_STEPS) * 100), 95)
  return { pct, phase: currentPhase }
}

function formatTimestamp(value: string | null) {
  if (!value) return 'n/a'
  return value.replace('T', ' ').replace('Z', '').slice(0, 19)
}

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function normalizeLog(value: string) {
  return value.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
}

function getDefaultAnsiState(): AnsiState {
  return {
    fg: null,
    bg: null,
    bold: false,
    dim: false,
  }
}

function applyAnsiCode(state: AnsiState, code: number) {
  if (code === 0) {
    state.fg = null
    state.bg = null
    state.bold = false
    state.dim = false
    return
  }

  if (code === 1) {
    state.bold = true
    state.dim = false
    return
  }

  if (code === 2) {
    state.dim = true
    return
  }

  if (code === 22) {
    state.bold = false
    state.dim = false
    return
  }

  if (code === 39) {
    state.fg = null
    return
  }

  if (code === 49) {
    state.bg = null
    return
  }

  if (ANSI_FG[code]) {
    state.fg = ANSI_FG[code]
    return
  }

  if (ANSI_BG[code]) {
    state.bg = ANSI_BG[code]
  }
}

function inlineStyleForAnsi(state: AnsiState) {
  const rules: string[] = []

  if (state.fg) rules.push(`color:${state.fg}`)
  if (state.bg) rules.push(`background:${state.bg}`)
  if (state.bold) rules.push('font-weight:700')
  if (state.dim) rules.push('opacity:0.8')

  return rules.join(';')
}

function renderAnsiToHtml(content: string) {
  const sanitized = normalizeLog(content).replace(ANSI_OSC_PATTERN, '')
  const state = getDefaultAnsiState()
  let html = ''
  let lastIndex = 0

  const appendChunk = (chunk: string) => {
    const cleanedChunk = chunk.replace(ANSI_CONTROL_PATTERN, '')
    if (!cleanedChunk) return

    const escaped = escapeHtml(cleanedChunk)
    const style = inlineStyleForAnsi(state)
    html += style ? `<span style="${style}">${escaped}</span>` : escaped
  }

  for (const match of sanitized.matchAll(ANSI_PATTERN)) {
    const index = match.index ?? 0
    appendChunk(sanitized.slice(lastIndex, index))

    const codes = (match[1] || '0')
      .split(';')
      .map((part) => Number(part || '0'))
      .filter((value) => Number.isFinite(value))

    if (codes.length === 0) {
      applyAnsiCode(state, 0)
    } else {
      for (const code of codes) {
        applyAnsiCode(state, code)
      }
    }

    lastIndex = index + match[0].length
  }

  appendChunk(sanitized.slice(lastIndex))
  return html
}

async function fetchJobState(jobId: string, offset?: number): Promise<FetchState & { size: number }> {
  const logParams = new URLSearchParams({ format: 'json' })
  if (offset !== undefined && offset > 0) {
    logParams.set('offset', String(offset))
  } else {
    logParams.set('tail', '400000')
  }

  const [jobResponse, logResponse] = await Promise.all([
    fetch(`/api/jobs/${jobId}`, { cache: 'no-store' }),
    fetch(`/api/jobs/${jobId}/log?${logParams}`, { cache: 'no-store' }),
  ])

  const nextJob = await jobResponse.json()
  if (!jobResponse.ok) {
    throw new Error(nextJob.error || 'Falha ao carregar job')
  }

  const nextLog = await logResponse.json()
  if (!logResponse.ok) {
    throw new Error(nextLog.error || 'Falha ao carregar log')
  }

  return {
    job: nextJob as ScanJob,
    log: String(nextLog.content || ''),
    truncated: Boolean(nextLog.truncated),
    updatedAt: typeof nextLog.updatedAt === 'string' ? nextLog.updatedAt : null,
    size: typeof nextLog.size === 'number' ? nextLog.size : 0,
  }
}

async function sendJobAction(jobId: string, action: 'stop' | 'pause' | 'resume'): Promise<{ ok?: boolean; error?: string }> {
  const res = await fetch(`/api/jobs/${jobId}/${action}`, { method: 'POST' })
  return res.json()
}

export default function JobLogViewer({ initialJob, initialLog }: Props) {
  const terminalRef = useRef<HTMLDivElement | null>(null)
  const [job, setJob] = useState(initialJob)
  const [log, setLog] = useState(initialLog)
  const [truncated, setTruncated] = useState(initialLog.length >= 400000)
  const [loading, setLoading] = useState(false)
  const [follow, setFollow] = useState(true)
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const logSizeRef = useRef(0)
  const pollInFlightRef = useRef(false)

  const renderedLog = useMemo(() => renderAnsiToHtml(log), [log])
  const isFinished = job.status === 'completed' || job.status === 'failed' || job.status === 'stopped'
  const isActive = job.status === 'running' || job.status === 'queued'
  const isPaused = job.status === 'paused'

  const { pct: progressPct, phase: progressPhase } = useMemo(
    () => estimateProgress(log, job.status === 'completed'),
    [log, job.status]
  )

  async function refresh() {
    setLoading(true)
    setError(null)

    try {
      const next = await fetchJobState(job.id)
      setJob(next.job)
      setLog(next.log)
      logSizeRef.current = next.size
      setTruncated(next.truncated)
      setUpdatedAt(next.updatedAt)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao atualizar log')
    } finally {
      setLoading(false)
    }
  }

  async function handleAction(action: 'stop' | 'pause' | 'resume') {
    setActionLoading(action)
    setError(null)
    try {
      const result = await sendJobAction(job.id, action)
      if (result.error) {
        setError(result.error)
      } else {
        await refresh()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha na ação')
    } finally {
      setActionLoading(null)
    }
  }

  useEffect(() => {
    if (isFinished) {
      return
    }

    let cancelled = false

    const poll = async () => {
      // Prevent overlapping polls: if a previous poll hasn't finished yet,
      // skip this tick.  Without this guard, multiple in-flight polls all
      // read the same logSizeRef offset and each append the same chunk,
      // producing N-times duplication of lines written near that boundary.
      if (pollInFlightRef.current) return
      pollInFlightRef.current = true
      try {
        const currentOffset = logSizeRef.current
        const next = await fetchJobState(job.id, currentOffset)
        if (cancelled) return
        setJob(next.job)
        if (currentOffset > 0 && next.log) {
          setLog((prev) => prev + next.log)
        } else if (next.log) {
          setLog(next.log)
        }
        logSizeRef.current = next.size
        setTruncated(next.truncated)
        setUpdatedAt(next.updatedAt)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Falha ao atualizar log')
      } finally {
        pollInFlightRef.current = false
      }
    }

    void poll()
    const interval = window.setInterval(() => {
      void poll()
    }, isPaused ? 5000 : 1000)

    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [job.id, isFinished, isPaused])

  useEffect(() => {
    if (!follow || !terminalRef.current) {
      return
    }
    terminalRef.current.scrollTop = terminalRef.current.scrollHeight
  }, [follow, log])

  function handleTerminalScroll() {
    const terminal = terminalRef.current
    if (!terminal) return

    const distanceFromBottom = terminal.scrollHeight - terminal.scrollTop - terminal.clientHeight
    const shouldFollow = distanceFromBottom < 32
    if (shouldFollow !== follow) {
      setFollow(shouldFollow)
    }
  }

  const cursor = !isFinished && !isPaused ? '<span style="color:#86efac">▌</span>' : ''

  const showProgressBar = (isActive || isPaused) && job.status !== 'queued'

  const btnBase = {
    fontFamily: 'inherit',
    fontSize: '11px',
    padding: '4px 10px',
    borderRadius: 'var(--radius)',
    cursor: 'pointer',
    border: '1px solid var(--border)',
  } as const

  return (
    <div className="space-y-3">
      {/* ── job meta bar ───────────────────────────────────────────── */}
      <div
        style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>

        {/* header row */}
        <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 border-b"
          style={{ borderColor: 'var(--border)', fontSize: '12px' }}>
          <span style={{ color: 'var(--green)', fontWeight: 600 }}>{job.domain}</span>
          <span style={{ color: 'var(--text-muted)' }}>{job.projectName} · {job.mode}</span>
          <span
            className={`status-${job.status}`}
            style={{ padding: '1px 6px', borderRadius: 'var(--radius)', fontSize: '11px', marginLeft: 'auto' }}>
            {job.status}
          </span>
        </div>

        {/* progress bar */}
        {showProgressBar && (
          <div className="px-4 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center justify-between mb-1" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              <span>{progressPhase}</span>
              <span>{progressPct}%</span>
            </div>
            <div style={{ height: '2px', background: 'var(--surface-2)', borderRadius: '1px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${progressPct}%`,
                background: isPaused ? '#ca8a04' : 'var(--green)',
                transition: 'width 500ms ease',
              }} />
            </div>
          </div>
        )}

        {/* timestamps */}
        <div className="flex flex-wrap gap-4 px-4 py-2 border-b" style={{ borderColor: 'var(--border)', fontSize: '11px', color: 'var(--text-muted)' }}>
          <span>created <span style={{ color: 'var(--text)' }}>{formatTimestamp(job.createdAt)}</span></span>
          <span>started  <span style={{ color: 'var(--text)' }}>{formatTimestamp(job.startedAt)}</span></span>
          <span>ended    <span style={{ color: 'var(--text)' }}>{formatTimestamp(job.endedAt)}</span></span>
          <span>updated  <span style={{ color: 'var(--text)' }}>{formatTimestamp(updatedAt)}</span></span>
          <span>rc <span style={{ color: job.returnCode === 0 ? 'var(--green)' : job.returnCode != null ? 'var(--red)' : 'var(--text)' }}>
            {job.returnCode ?? '—'}
          </span></span>
        </div>

        {/* actions */}
        <div className="flex flex-wrap gap-2 px-4 py-2.5" style={{ fontSize: '11px' }}>
          <button type="button" onClick={() => void refresh()}
            style={{ ...btnBase, background: 'var(--surface-2)', color: 'var(--text)' }}>
            {loading ? '...' : 'refresh'}
          </button>
          <button type="button"
            onClick={() => { setFollow(true); if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight }}
            style={{ ...btnBase, background: follow ? '#134e4a' : 'var(--surface-2)', color: follow ? '#99f6e4' : 'var(--text-muted)' }}>
            {follow ? '↓ following' : '↓ follow'}
          </button>

          {isActive && (
            <>
              <button type="button" disabled={actionLoading !== null}
                onClick={() => void handleAction('pause')}
                style={{ ...btnBase, background: '#42200633', color: 'var(--yellow)', borderColor: '#71331244', opacity: actionLoading ? 0.6 : 1 }}>
                {actionLoading === 'pause' ? '...' : 'pause'}
              </button>
              <button type="button" disabled={actionLoading !== null}
                onClick={() => void handleAction('stop')}
                style={{ ...btnBase, background: '#450a0a33', color: 'var(--red)', borderColor: '#7f1d1d44', opacity: actionLoading ? 0.6 : 1 }}>
                {actionLoading === 'stop' ? '...' : 'stop'}
              </button>
            </>
          )}

          {isPaused && (
            <>
              <button type="button" disabled={actionLoading !== null}
                onClick={() => void handleAction('resume')}
                style={{ ...btnBase, background: '#052e1633', color: 'var(--green)', borderColor: '#14532d44', opacity: actionLoading ? 0.6 : 1 }}>
                {actionLoading === 'resume' ? '...' : 'resume'}
              </button>
              <button type="button" disabled={actionLoading !== null}
                onClick={() => void handleAction('stop')}
                style={{ ...btnBase, background: '#450a0a33', color: 'var(--red)', borderColor: '#7f1d1d44', opacity: actionLoading ? 0.6 : 1 }}>
                {actionLoading === 'stop' ? '...' : 'stop'}
              </button>
            </>
          )}

          <Link href={`/api/jobs/${job.id}/log`} target="_blank"
            style={{ ...btnBase, background: 'var(--surface-2)', color: 'var(--cyan)', display: 'inline-flex', alignItems: 'center' }}>
            raw log
          </Link>
          {job.scanId && (
            <Link href={`/scan/${job.scanId}`}
              style={{ ...btnBase, background: 'var(--surface-2)', color: 'var(--green)', display: 'inline-flex', alignItems: 'center' }}>
              open scan ›
            </Link>
          )}
        </div>
      </div>

      {truncated && (
        <div className="px-4 py-2" style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>
          [INF] showing tail of log only — file is large
        </div>
      )}

      {error && (
        <div className="px-4 py-2" style={{ fontSize: '12px', color: 'var(--red)', background: '#450a0a33', border: '1px solid #7f1d1d44', borderRadius: 'var(--radius)' }}>
          [ERR] {error}
        </div>
      )}

      <div style={{ border: '1px solid #1a1f2e', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
        {/* terminal title bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b"
          style={{ borderColor: '#1a1f2e', background: '#0d1117', fontSize: '11px' }}>
          <span style={{ color: '#4b5563' }}>❯ givenum scan</span>
          <div className="flex items-center gap-3">
            <span style={{ color: '#4b5563' }}>job/{job.id.slice(0, 8)}</span>
            <span style={{
              color: isFinished ? '#6b7280' : isPaused ? 'var(--yellow)' : 'var(--green)',
              fontWeight: 600,
            }}>
              {isFinished ? '■ done' : isPaused ? '⏸ paused' : '● streaming'}
            </span>
          </div>
        </div>

        {/* log output */}
        <div
          ref={terminalRef}
          onScroll={handleTerminalScroll}
          style={{ overflowY: 'auto', minHeight: '420px', maxHeight: '72vh', padding: '12px 16px', background: '#060810' }}
        >
          <div
            style={{ fontFamily: 'inherit', fontSize: '12px', lineHeight: '1.65', whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: '#d1d5db', fontVariantLigatures: 'none' }}
            dangerouslySetInnerHTML={{ __html: renderedLog || escapeHtml('waiting for scanner output...') + cursor }}
          />
          {renderedLog && !isFinished && !isPaused && (
            <div
              style={{ fontFamily: 'inherit', fontSize: '12px', lineHeight: '1.65', whiteSpace: 'pre-wrap', color: '#4ade80' }}
              dangerouslySetInnerHTML={{ __html: cursor }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
