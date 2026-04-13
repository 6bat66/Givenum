'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'

type ConfirmState = { type: 'job' | 'scan' | 'project'; id: string; label: string } | null

function useDeleteWithConfirm() {
  const router = useRouter()
  const [pending, setPending] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<ConfirmState>(null)
  const [error, setError] = useState<string | null>(null)

  function requestDelete(type: 'job' | 'scan' | 'project', id: string, label: string) {
    setConfirm({ type, id, label })
    setError(null)
  }

  async function confirmDelete() {
    if (!confirm) return
    const { type, id } = confirm
    const url = type === 'job' ? `/api/jobs/${id}` : type === 'scan' ? `/api/scan/${id}` : `/api/projects/${id}`
    setPending(id)
    setConfirm(null)
    try {
      const res = await fetch(url, { method: 'DELETE' })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'Falha ao apagar')
      } else {
        router.refresh()
      }
    } catch {
      setError('Erro de rede')
    } finally {
      setPending(null)
    }
  }

  return { pending, confirm, error, requestDelete, confirmDelete, cancelConfirm: () => setConfirm(null) }
}

// ---- Delete button for a single job ----

export function DeleteJobButton({ jobId, domain, status }: { jobId: string; domain: string; status: string }) {
  const { pending, confirm, error, requestDelete, confirmDelete, cancelConfirm } = useDeleteWithConfirm()
  const isRunning = status === 'running' || status === 'queued'

  return (
    <>
      <button
        type="button"
        title={isRunning ? 'Pare o job antes de apagar' : 'Apagar job'}
        disabled={isRunning || pending === jobId}
        onClick={() => requestDelete('job', jobId, domain)}
        className="text-xs px-2 py-1 rounded"
        style={{
          background: isRunning ? 'transparent' : '#450a0a',
          color: isRunning ? 'var(--text-subtle)' : '#fca5a5',
          border: `1px solid ${isRunning ? 'var(--border)' : '#7f1d1d'}`,
          opacity: isRunning ? 0.4 : 1,
          cursor: isRunning ? 'not-allowed' : 'pointer',
        }}>
        {pending === jobId ? '...' : 'Apagar'}
      </button>
      {error && <span className="text-xs" style={{ color: '#f87171' }}>{error}</span>}
      {confirm && confirm.id === jobId && (
        <ConfirmDialog label={confirm.label} onConfirm={confirmDelete} onCancel={cancelConfirm} />
      )}
    </>
  )
}

// ---- Delete button for a scan ----

export function DeleteScanButton({ scanId, domain }: { scanId: string; domain: string }) {
  const { pending, confirm, error, requestDelete, confirmDelete, cancelConfirm } = useDeleteWithConfirm()

  return (
    <>
      <button
        type="button"
        title="Apagar scan (arquivos serão removidos)"
        disabled={pending === scanId}
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); requestDelete('scan', scanId, domain) }}
        className="text-xs px-2 py-1 rounded"
        style={{ background: '#450a0a', color: '#fca5a5', border: '1px solid #7f1d1d' }}>
        {pending === scanId ? '...' : 'Apagar'}
      </button>
      {error && <span className="text-xs" style={{ color: '#f87171' }}>{error}</span>}
      {confirm && confirm.id === scanId && (
        <ConfirmDialog label={`scan de ${confirm.label}`} onConfirm={confirmDelete} onCancel={cancelConfirm} />
      )}
    </>
  )
}

// ---- Delete button for a project ----

export function DeleteProjectButton({ projectId, name }: { projectId: string; name: string }) {
  const { pending, confirm, error, requestDelete, confirmDelete, cancelConfirm } = useDeleteWithConfirm()
  const isDefault = projectId === 'default'

  return (
    <>
      <button
        type="button"
        title={isDefault ? 'Não é possível apagar o projeto padrão' : 'Apagar projeto'}
        disabled={isDefault || pending === projectId}
        onClick={() => requestDelete('project', projectId, name)}
        className="text-xs px-2 py-1 rounded"
        style={{
          background: isDefault ? 'transparent' : '#450a0a',
          color: isDefault ? 'var(--text-subtle)' : '#fca5a5',
          border: `1px solid ${isDefault ? 'var(--border)' : '#7f1d1d'}`,
          opacity: isDefault ? 0.4 : 1,
          cursor: isDefault ? 'not-allowed' : 'pointer',
        }}>
        {pending === projectId ? '...' : 'Apagar'}
      </button>
      {error && <span className="text-xs" style={{ color: '#f87171' }}>{error}</span>}
      {confirm && confirm.id === projectId && (
        <ConfirmDialog label={`projeto "${confirm.label}"`} onConfirm={confirmDelete} onCancel={cancelConfirm} />
      )}
    </>
  )
}

// ---- Quick-stop button for active jobs ----

export function StopJobButton({ jobId, status }: { jobId: string; status: string }) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isActive = status === 'running' || status === 'paused'

  if (!isActive) return null

  async function handleStop() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/jobs/${jobId}/stop`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) setError(data.error || 'Falha ao parar')
      else router.refresh()
    } catch {
      setError('Erro de rede')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        type="button"
        disabled={loading}
        onClick={() => void handleStop()}
        className="text-xs px-2 py-1 rounded"
        style={{ background: '#450a0a', color: '#fca5a5', border: '1px solid #7f1d1d', opacity: loading ? 0.6 : 1 }}>
        {loading ? 'Parando...' : 'Parar'}
      </button>
      {error && <span className="text-xs" style={{ color: '#f87171' }}>{error}</span>}
    </>
  )
}

// ---- Shared confirm dialog (inline, not a modal) ----

function ConfirmDialog({ label, onConfirm, onCancel }: { label: string; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      onClick={onCancel}>
      <div
        className="rounded-xl p-6 max-w-sm w-full mx-4 space-y-4"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        onClick={(e) => e.stopPropagation()}>
        <div className="font-semibold" style={{ color: 'var(--text)' }}>Confirmar ação</div>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Tem certeza que deseja apagar <strong style={{ color: 'var(--text)' }}>{label}</strong>? Esta ação não pode ser desfeita.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm"
            style={{ background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)' }}>
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="px-4 py-2 rounded-lg text-sm"
            style={{ background: '#450a0a', color: '#fca5a5', border: '1px solid #7f1d1d' }}>
            Apagar
          </button>
        </div>
      </div>
    </div>
  )
}
