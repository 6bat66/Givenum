'use client'

import { useEffect, useRef, useState } from 'react'
import { parseAnsi } from '@/lib/ansi'
import type { ToolStatus } from '@/lib/tools'

type Props = {
  tools: ToolStatus[]
}

export default function ToolUpdateConsole({ tools }: Props) {
  const [selected, setSelected] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [done, setDone] = useState(false)
  const [log, setLog] = useState('')
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Toggle all pre-selection
  function toggleAll() {
    setSelected((s) => s.length === tools.length ? [] : tools.map((t) => t.name))
  }

  function toggleTool(name: string) {
    setSelected((s) => s.includes(name) ? s.filter((n) => n !== name) : [...s, name])
  }

  async function startUpdate() {
    if (selected.length === 0) return
    setRunning(true)
    setDone(false)
    setLog('')
    setError(null)

    try {
      const res = await fetch('/api/tools/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tools: selected }),
      })
      if (!res.ok) throw new Error((await res.json()).error ?? 'Failed to start')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
      setRunning(false)
      return
    }

    // Poll log
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch('/api/tools/update/log')
        const { content, done: isDone } = await res.json() as { content: string; done: boolean }
        setLog(content)
        if (isDone) {
          setDone(true)
          setRunning(false)
          clearInterval(pollRef.current!)
          pollRef.current = null
        }
      } catch { /* ignore */ }
    }, 1200)
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [log])

  const lines = parseAnsi(log)

  const categoryOrder = ['subdomain', 'http', 'vuln', 'util'] as const
  const grouped = categoryOrder.map((cat) => ({
    cat,
    items: tools.filter((t) => t.category === cat),
  })).filter((g) => g.items.length > 0)

  return (
    <div className="space-y-4">
      {/* Tool selection */}
      <div className="panel rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b"
          style={{ borderColor: 'var(--border)', background: 'var(--surface-2)' }}>
          <span className="text-xs" style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            select tools to update
          </span>
          <button
            type="button"
            onClick={toggleAll}
            className="text-xs px-3 py-1 rounded-lg"
            style={{ background: 'var(--surface-3)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
            {selected.length === tools.length ? 'deselect all' : 'select all'}
          </button>
        </div>

        {grouped.map(({ cat, items }) => (
          <div key={cat}>
            <div className="px-4 py-2 text-xs font-semibold"
              style={{ background: 'var(--surface)', color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: '1px solid var(--border-subtle)' }}>
              {cat}
            </div>
            {items.map((tool) => (
              <label
                key={tool.name}
                className="flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors border-b"
                style={{ borderColor: 'var(--border-subtle)', background: selected.includes(tool.name) ? 'rgba(135,88,216,0.06)' : 'transparent' }}>
                <input
                  type="checkbox"
                  checked={selected.includes(tool.name)}
                  onChange={() => toggleTool(tool.name)}
                  className="rounded"
                  style={{ accentColor: 'var(--purple)' }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm" style={{ color: 'var(--text)' }}>{tool.name}</span>
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{
                        background: tool.installed ? 'rgba(74,222,128,0.1)' : 'rgba(248,113,113,0.1)',
                        color: tool.installed ? 'var(--green)' : 'var(--red)',
                        border: `1px solid ${tool.installed ? 'rgba(74,222,128,0.2)' : 'rgba(248,113,113,0.2)'}`,
                      }}>
                      {tool.installed ? 'installed' : 'missing'}
                    </span>
                  </div>
                  <div className="text-xs truncate mt-0.5" style={{ color: 'var(--text-subtle)' }}>
                    {tool.description}
                    {tool.version && <span className="ml-2" style={{ color: 'var(--text-subtle)', opacity: 0.7 }}>{tool.version}</span>}
                  </div>
                </div>
              </label>
            ))}
          </div>
        ))}
      </div>

      {/* Run button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={running || selected.length === 0}
          onClick={() => void startUpdate()}
          className="neon-button px-5 py-2.5 text-sm font-semibold"
          style={{
            opacity: running || selected.length === 0 ? 0.5 : 1,
            cursor: running || selected.length === 0 ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit',
          }}>
          {running ? 'updating...' : `update ${selected.length > 0 ? `(${selected.length})` : ''}`}
        </button>
        {selected.length > 0 && !running && (
          <span className="text-xs" style={{ color: 'var(--text-subtle)' }}>
            {selected.length} tool{selected.length !== 1 ? 's' : ''} selected
          </span>
        )}
        {done && (
          <span className="text-xs" style={{ color: 'var(--green)' }}>[FND] updates complete</span>
        )}
        {error && (
          <span className="text-xs" style={{ color: 'var(--red)' }}>[ERR] {error}</span>
        )}
      </div>

      {/* Console output */}
      {(running || log) && (
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: '1px solid var(--border)', background: '#080810', boxShadow: 'var(--glow-purple)' }}>
          {/* Title bar */}
          <div className="flex items-center gap-2 px-4 py-2.5 border-b"
            style={{ borderColor: 'var(--border)', background: 'rgba(135,88,216,0.08)' }}>
            <span style={{ color: 'var(--purple)', fontWeight: 700, fontSize: '13px' }}>❯</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>tool updater</span>
            <span className="ml-auto text-xs" style={{ color: running ? 'var(--purple-bright)' : done ? 'var(--green)' : 'var(--text-subtle)' }}>
              {running ? '● running' : done ? '■ done' : ''}
            </span>
          </div>

          {/* Log content */}
          <div className="overflow-auto p-4" style={{ maxHeight: '50vh', fontFamily: 'monospace', fontSize: '12px', lineHeight: 1.65 }}>
            {lines.map((spans, li) => (
              <div key={li} style={{ minHeight: '1.65em' }}>
                {spans.map((span, si) => (
                  <span key={si} style={span.style}>{span.text}</span>
                ))}
              </div>
            ))}
            {running && (
              <div style={{ color: 'var(--purple-bright)', animation: 'pulse 1s infinite' }}>▌</div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>
      )}
    </div>
  )
}
