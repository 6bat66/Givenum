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

  const statusStyle = job.status === 'completed'
    ? { background: '#052e16', color: '#86efac' }
    : job.status === 'failed'
      ? { background: '#450a0a', color: '#fca5a5' }
      : job.status === 'stopped'
        ? { background: '#1c1917', color: '#a8a29e' }
        : job.status === 'paused'
          ? { background: '#1c1917', color: '#fde047' }
          : { background: '#082f49', color: '#7dd3fc' }

  const cursor = !isFinished && !isPaused ? '<span style="color:#86efac">▌</span>' : ''

  const showProgressBar = (isActive || isPaused) && job.status !== 'queued'

  return (
    <div className="space-y-4">
      <div className="rounded-xl p-5" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
          <div>
            <div className="text-lg font-semibold" style={{ color: 'var(--text)' }}>{job.domain}</div>
            <div className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              {job.projectName} · {job.mode}
            </div>
          </div>
          <span className="text-xs px-2 py-1 rounded-full font-medium" style={statusStyle}>
            {job.status}
          </span>
        </div>

        {showProgressBar && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>
              <span>{progressPhase}</span>
              <span className="font-mono">{progressPct}%</span>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--surface-2)' }}>
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${progressPct}%`,
                  background: isPaused ? '#ca8a04' : 'linear-gradient(90deg, #0ea5e9, #22d3ee)',
                }}
              />
            </div>
          </div>
        )}

        <div className="grid sm:grid-cols-2 xl:grid-cols-5 gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
          <div>criado: <span className="font-mono">{formatTimestamp(job.createdAt)}</span></div>
          <div>iniciado: <span className="font-mono">{formatTimestamp(job.startedAt)}</span></div>
          <div>finalizado: <span className="font-mono">{formatTimestamp(job.endedAt)}</span></div>
          <div>atualizado: <span className="font-mono">{formatTimestamp(updatedAt)}</span></div>
          <div>rc: <span className="font-mono">{job.returnCode ?? 'running'}</span></div>
        </div>

        <div className="flex flex-wrap gap-3 mt-4 text-sm">
          <button
            type="button"
            onClick={() => void refresh()}
            className="px-3 py-2 rounded-lg"
            style={{ background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)' }}>
            {loading ? 'Atualizando...' : 'Atualizar'}
          </button>
          <button
            type="button"
            onClick={() => {
              setFollow(true)
              if (terminalRef.current) {
                terminalRef.current.scrollTop = terminalRef.current.scrollHeight
              }
            }}
            className="px-3 py-2 rounded-lg"
            style={{ background: follow ? '#0f766e' : 'var(--surface-2)', color: follow ? '#ecfeff' : 'var(--text)', border: '1px solid var(--border)' }}>
            {follow ? 'Seguindo saída' : 'Seguir saída'}
          </button>

          {isActive && (
            <>
              <button
                type="button"
                disabled={actionLoading !== null}
                onClick={() => void handleAction('pause')}
                className="px-3 py-2 rounded-lg"
                style={{ background: '#422006', color: '#fde047', border: '1px solid #713f12', opacity: actionLoading ? 0.6 : 1 }}>
                {actionLoading === 'pause' ? 'Pausando...' : 'Pausar'}
              </button>
              <button
                type="button"
                disabled={actionLoading !== null}
                onClick={() => void handleAction('stop')}
                className="px-3 py-2 rounded-lg"
                style={{ background: '#450a0a', color: '#fca5a5', border: '1px solid #7f1d1d', opacity: actionLoading ? 0.6 : 1 }}>
                {actionLoading === 'stop' ? 'Parando...' : 'Parar'}
              </button>
            </>
          )}

          {isPaused && (
            <>
              <button
                type="button"
                disabled={actionLoading !== null}
                onClick={() => void handleAction('resume')}
                className="px-3 py-2 rounded-lg"
                style={{ background: '#052e16', color: '#86efac', border: '1px solid #14532d', opacity: actionLoading ? 0.6 : 1 }}>
                {actionLoading === 'resume' ? 'Retomando...' : 'Retomar'}
              </button>
              <button
                type="button"
                disabled={actionLoading !== null}
                onClick={() => void handleAction('stop')}
                className="px-3 py-2 rounded-lg"
                style={{ background: '#450a0a', color: '#fca5a5', border: '1px solid #7f1d1d', opacity: actionLoading ? 0.6 : 1 }}>
                {actionLoading === 'stop' ? 'Parando...' : 'Parar'}
              </button>
            </>
          )}

          <Link
            href={`/api/jobs/${job.id}/log`}
            target="_blank"
            className="px-3 py-2 rounded-lg"
            style={{ background: 'var(--surface-2)', color: 'var(--cyan)', border: '1px solid var(--border)' }}>
            Log bruto
          </Link>
          {job.scanId && (
            <Link
              href={`/scan/${job.scanId}`}
              className="px-3 py-2 rounded-lg"
              style={{ background: 'var(--surface-2)', color: 'var(--green)', border: '1px solid var(--border)' }}>
              Abrir scan
            </Link>
          )}
        </div>
      </div>

      {truncated && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
          Exibindo só a parte final do log para manter a UI fluida.
        </div>
      )}

      {error && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ background: '#450a0a', border: '1px solid #7f1d1d', color: '#fecaca' }}>
          {error}
        </div>
      )}

      <div className="rounded-xl overflow-hidden" style={{ background: '#06080d', border: '1px solid #1f2937', boxShadow: '0 24px 60px rgba(0, 0, 0, 0.35)' }}>
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b" style={{ borderColor: '#111827', background: '#0b1220' }}>
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex items-center gap-2">
              <span className="block h-3 w-3 rounded-full" style={{ background: '#f87171' }} />
              <span className="block h-3 w-3 rounded-full" style={{ background: '#facc15' }} />
              <span className="block h-3 w-3 rounded-full" style={{ background: '#4ade80' }} />
            </div>
            <div className="text-xs font-mono truncate" style={{ color: '#cbd5e1' }}>
              job/{job.id.slice(0, 8)}.log
            </div>
          </div>
          <div className="text-xs font-mono" style={{ color: isFinished ? '#94a3b8' : isPaused ? '#fde047' : '#86efac' }}>
            {isFinished ? 'finalizado' : isPaused ? 'pausado' : 'streaming'}
          </div>
        </div>

        <div
          ref={terminalRef}
          onScroll={handleTerminalScroll}
          className="overflow-auto min-h-[420px] max-h-[72vh] p-4"
          style={{ background: 'linear-gradient(180deg, #050816 0%, #04060b 100%)' }}
        >
          <div
            className="font-mono text-xs leading-6 whitespace-pre-wrap break-words"
            style={{ color: '#e5e7eb', fontVariantLigatures: 'none' }}
            dangerouslySetInnerHTML={{ __html: renderedLog || escapeHtml('Aguardando saída do scanner...') + cursor }}
          />
          {renderedLog && !isFinished && !isPaused && (
            <div
              className="font-mono text-xs leading-6 whitespace-pre-wrap"
              style={{ color: '#86efac' }}
              dangerouslySetInnerHTML={{ __html: cursor }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
