'use client'

import { useState } from 'react'
import type { ProjectMeta } from '@/lib/types'

type Props = {
  projects: ProjectMeta[]
}

export default function DashboardControls({ projects }: Props) {
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [scanDomain, setScanDomain] = useState('')
  const [scanProjectId, setScanProjectId] = useState(projects[0]?.id ?? 'default')
  const [mode, setMode] = useState<'passive' | 'active'>('passive')
  const [skipScreenshots, setSkipScreenshots] = useState(false)
  const [skipPortscan, setSkipPortscan] = useState(false)
  const [skipVulnScan, setSkipVulnScan] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [busy, setBusy] = useState<'project' | 'scan' | null>(null)

  async function createProject() {
    setBusy('project')
    setStatus(null)

    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: projectName, description: projectDescription }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.error || 'Falha ao criar projeto')
      }
      setStatus(`Projeto criado: ${payload.name}`)
      window.location.reload()
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Falha ao criar projeto')
    } finally {
      setBusy(null)
    }
  }

  async function startScan() {
    setBusy('scan')
    setStatus(null)

    try {
      const response = await fetch('/api/scans/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId: scanProjectId,
          domain: scanDomain,
          mode,
          options: { skipScreenshots, skipPortscan, skipVulnScan },
        }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.error || 'Falha ao iniciar scan')
      }
      setStatus(`Scan iniciado para ${payload.domain}`)
      setScanDomain('')
      window.location.reload()
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Falha ao iniciar scan')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="grid xl:grid-cols-2 gap-4 mb-8">
      <div className="rounded-xl p-5" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <div className="text-sm font-semibold mb-4" style={{ color: 'var(--text)' }}>Novo Projeto</div>
        <div className="space-y-3">
          <input
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="Nome do projeto"
            className="w-full rounded-lg px-3 py-2 text-sm outline-none"
            style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)' }}
          />
          <textarea
            value={projectDescription}
            onChange={(e) => setProjectDescription(e.target.value)}
            placeholder="Descrição curta"
            rows={3}
            className="w-full rounded-lg px-3 py-2 text-sm outline-none resize-none"
            style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)' }}
          />
          <button
            type="button"
            disabled={busy !== null || projectName.trim().length === 0}
            onClick={createProject}
            className="px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
            style={{ background: 'var(--cyan)', color: '#082f49' }}>
            {busy === 'project' ? 'Criando...' : 'Criar Projeto'}
          </button>
        </div>
      </div>

      <div className="rounded-xl p-5" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <div className="text-sm font-semibold mb-4" style={{ color: 'var(--text)' }}>Iniciar Scan</div>
        <div className="space-y-3">
          <div className="grid sm:grid-cols-2 gap-3">
            <input
              value={scanDomain}
              onChange={(e) => setScanDomain(e.target.value)}
              placeholder="example.com"
              className="w-full rounded-lg px-3 py-2 text-sm outline-none"
              style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)' }}
            />
            <select
              value={scanProjectId}
              onChange={(e) => setScanProjectId(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm outline-none"
              style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)' }}>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
          </div>

          <div className="flex gap-2">
            {(['passive', 'active'] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setMode(option)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium"
                style={mode === option
                  ? { background: option === 'active' ? '#431407' : '#082f49', color: option === 'active' ? '#fdba74' : '#7dd3fc' }
                  : { background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                {option}
              </button>
            ))}
          </div>

          <div className="grid sm:grid-cols-3 gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={skipScreenshots} onChange={(e) => setSkipScreenshots(e.target.checked)} />
              pular screenshots
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={skipPortscan} onChange={(e) => setSkipPortscan(e.target.checked)} />
              pular portscan
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={skipVulnScan} onChange={(e) => setSkipVulnScan(e.target.checked)} />
              pular vuln scan
            </label>
          </div>

          <button
            type="button"
            disabled={busy !== null || scanDomain.trim().length === 0}
            onClick={startScan}
            className="px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
            style={{ background: 'var(--green)', color: '#052e16' }}>
            {busy === 'scan' ? 'Iniciando...' : 'Iniciar Scan'}
          </button>
        </div>
      </div>

      {status && (
        <div className="xl:col-span-2 rounded-xl px-4 py-3 text-sm"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
          {status}
        </div>
      )}
    </div>
  )
}
