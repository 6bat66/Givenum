'use client'

import { useState } from 'react'
import type { ProjectMeta } from '@/lib/types'

type Props = {
  projects: ProjectMeta[]
}

export default function DashboardControls({ projects }: Props) {
  const [projectName, setProjectName]           = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [scanDomain, setScanDomain]             = useState('')
  const [scanProjectId, setScanProjectId]       = useState(projects[0]?.id ?? 'default')
  const [mode, setMode]                         = useState<'passive' | 'active'>('passive')
  const [skipScreenshots, setSkipScreenshots]   = useState(false)
  const [skipPortscan, setSkipPortscan]         = useState(false)
  const [skipVulnScan, setSkipVulnScan]         = useState(false)
  const [status, setStatus]                     = useState<string | null>(null)
  const [statusOk, setStatusOk]                 = useState(true)
  const [busy, setBusy]                         = useState<'project' | 'scan' | null>(null)
  const [showNewProject, setShowNewProject]     = useState(false)

  async function createProject() {
    setBusy('project')
    setStatus(null)
    try {
      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: projectName, description: projectDescription }),
      })
      const payload = await res.json()
      if (!res.ok) throw new Error(payload.error || 'Failed to create project')
      setStatus(`[FND] project created: ${payload.name}`)
      setStatusOk(true)
      setProjectName('')
      setProjectDescription('')
      setShowNewProject(false)
      window.location.reload()
    } catch (err) {
      setStatus(`[ERR] ${err instanceof Error ? err.message : 'Failed'}`)
      setStatusOk(false)
    } finally {
      setBusy(null)
    }
  }

  async function startScan() {
    setBusy('scan')
    setStatus(null)
    try {
      const res = await fetch('/api/scans/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId: scanProjectId,
          domain: scanDomain,
          mode,
          options: { skipScreenshots, skipPortscan, skipVulnScan },
        }),
      })
      const payload = await res.json()
      if (!res.ok) throw new Error(payload.error || 'Failed to start scan')
      setStatus(`[FND] scan started → ${payload.domain}`)
      setStatusOk(true)
      setScanDomain('')
      window.location.reload()
    } catch (err) {
      setStatus(`[ERR] ${err instanceof Error ? err.message : 'Failed'}`)
      setStatusOk(false)
    } finally {
      setBusy(null)
    }
  }

  const inputStyle = {
    background: 'var(--surface-2)',
    border: '1px solid var(--border)',
    color: 'var(--text)',
    borderRadius: 'var(--radius)',
    padding: '5px 8px',
    fontSize: '12px',
    outline: 'none',
    fontFamily: 'inherit',
  } as const

  const btnStyle = (active: boolean, activeColor: string, activeBg: string) => ({
    background: active ? activeBg : 'var(--surface-2)',
    color: active ? activeColor : 'var(--text-muted)',
    border: `1px solid ${active ? activeColor + '44' : 'var(--border)'}`,
    borderRadius: 'var(--radius)',
    padding: '4px 10px',
    fontSize: '11px',
    cursor: 'pointer',
    fontFamily: 'inherit',
  })

  return (
    <div className="mb-5 space-y-2">

      {/* ── scan launch bar ──────────────────────────────────────── */}
      <div
        className="flex flex-wrap items-center gap-2 px-4 py-2.5"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>

        <span className="tag-inf" style={{ flexShrink: 0 }}>[RUN]</span>

        <input
          value={scanDomain}
          onChange={(e) => setScanDomain(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && scanDomain.trim() && void startScan()}
          placeholder="target.com"
          style={{ ...inputStyle, width: '180px', flexShrink: 0 }}
        />

        <select
          value={scanProjectId}
          onChange={(e) => setScanProjectId(e.target.value)}
          style={{ ...inputStyle, flexShrink: 0 }}>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>

        {/* mode toggle */}
        <div className="flex gap-1">
          {(['passive', 'active'] as const).map((opt) => (
            <button key={opt} type="button" onClick={() => setMode(opt)}
              style={btnStyle(mode === opt, opt === 'active' ? 'var(--orange)' : 'var(--cyan)', opt === 'active' ? '#43140733' : '#082f4933')}>
              {opt}
            </button>
          ))}
        </div>

        {/* skip flags */}
        <div className="flex gap-3" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={skipScreenshots} onChange={(e) => setSkipScreenshots(e.target.checked)} />
            no-screens
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={skipPortscan} onChange={(e) => setSkipPortscan(e.target.checked)} />
            no-ports
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={skipVulnScan} onChange={(e) => setSkipVulnScan(e.target.checked)} />
            no-vulns
          </label>
        </div>

        <button
          type="button"
          disabled={busy !== null || scanDomain.trim().length === 0}
          onClick={() => void startScan()}
          style={{
            background: 'var(--green)',
            color: '#052e16',
            border: 'none',
            borderRadius: 'var(--radius)',
            padding: '5px 14px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: busy !== null || !scanDomain.trim() ? 'not-allowed' : 'pointer',
            opacity: busy !== null || !scanDomain.trim() ? 0.5 : 1,
            fontFamily: 'inherit',
            marginLeft: 'auto',
          }}>
          {busy === 'scan' ? 'starting...' : '❯ scan'}
        </button>
      </div>

      {/* ── new project (collapsed by default) ───────────────────── */}
      <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
        <button
          type="button"
          onClick={() => setShowNewProject((v) => !v)}
          className="w-full flex items-center gap-2 px-4 py-2"
          style={{ background: 'var(--surface)', fontSize: '11px', color: 'var(--text-muted)', cursor: 'pointer', fontFamily: 'inherit', border: 'none', textAlign: 'left' }}>
          <span style={{ color: showNewProject ? 'var(--green)' : 'var(--text-subtle)' }}>
            {showNewProject ? '▾' : '▸'}
          </span>
          new project
        </button>

        {showNewProject && (
          <div className="flex flex-wrap items-end gap-2 px-4 py-3"
            style={{ background: 'var(--surface-2)', borderTop: '1px solid var(--border)' }}>
            <div className="flex flex-col gap-1">
              <label style={{ fontSize: '10px', color: 'var(--text-subtle)' }}>name</label>
              <input value={projectName} onChange={(e) => setProjectName(e.target.value)}
                placeholder="my-project" style={{ ...inputStyle, width: '160px' }} />
            </div>
            <div className="flex flex-col gap-1">
              <label style={{ fontSize: '10px', color: 'var(--text-subtle)' }}>description</label>
              <input value={projectDescription} onChange={(e) => setProjectDescription(e.target.value)}
                placeholder="optional" style={{ ...inputStyle, width: '220px' }} />
            </div>
            <button
              type="button"
              disabled={busy !== null || projectName.trim().length === 0}
              onClick={() => void createProject()}
              style={{
                background: 'var(--cyan)', color: '#082f49',
                border: 'none', borderRadius: 'var(--radius)',
                padding: '5px 14px', fontSize: '12px', fontWeight: 600,
                cursor: busy !== null || !projectName.trim() ? 'not-allowed' : 'pointer',
                opacity: busy !== null || !projectName.trim() ? 0.5 : 1,
                fontFamily: 'inherit',
              }}>
              {busy === 'project' ? 'creating...' : 'create'}
            </button>
          </div>
        )}
      </div>

      {/* ── status feedback ───────────────────────────────────────── */}
      {status && (
        <div className="px-4 py-2" style={{
          fontSize: '12px',
          color: statusOk ? 'var(--green)' : 'var(--red)',
          background: statusOk ? '#052e1620' : '#450a0a20',
          border: `1px solid ${statusOk ? '#14532d44' : '#7f1d1d44'}`,
          borderRadius: 'var(--radius)',
        }}>
          {status}
        </div>
      )}
    </div>
  )
}
