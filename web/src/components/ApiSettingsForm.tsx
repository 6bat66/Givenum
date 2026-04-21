'use client'

import { useState } from 'react'

type Props = {
  initialKeys: Record<string, string>
}

const FIELD_LABELS: Record<string, string> = {
  virustotal: 'VirusTotal',
  securitytrails: 'SecurityTrails',
  certspotter: 'CertSpotter',
  shodan: 'Shodan',
  censys_id: 'Censys API ID',
  censys_secret: 'Censys API Secret',
  fofa_email: 'Fofa Email',
  fofa_key: 'Fofa API Key',
  hunter: 'Hunter.io API Key',
  netlas: 'Netlas API Key',
  github_token: 'GitHub Token (github-subdomains)',
  discord_webhook: 'Discord Webhook',
  telegram_token: 'Telegram Bot Token',
  telegram_chat_id: 'Telegram Chat ID',
}

export default function ApiSettingsForm({ initialKeys }: Props) {
  const [keys, setKeys] = useState<Record<string, string>>(initialKeys)
  const [status, setStatus] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    setStatus(null)

    try {
      const response = await fetch('/api/settings/apis', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys }),
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.error || 'Falha ao salvar configuração')
      }
      setStatus(payload.ok ? 'Configuração salva' : 'Falha ao salvar configuração')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Falha ao salvar configuração')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      {Object.entries(FIELD_LABELS).map(([key, label]) => (
        <div key={key}>
          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text)' }}>
            {label}
          </label>
          <input
            value={keys[key] || ''}
            onChange={(e) => setKeys((current) => ({ ...current, [key]: e.target.value }))}
            placeholder={`Configurar ${label}`}
            className="w-full rounded-lg px-3 py-2 text-sm outline-none"
            style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)' }}
          />
        </div>
      ))}

      <button
        type="button"
        onClick={save}
        disabled={saving}
        className="px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
        style={{ background: 'var(--cyan)', color: '#082f49' }}>
        {saving ? 'Salvando...' : 'Salvar Configuração'}
      </button>

      {status && (
        <div className="rounded-lg px-3 py-2 text-sm"
          style={{
            background: status === 'Configuração salva' ? '#052e16' : '#450a0a',
            border: `1px solid ${status === 'Configuração salva' ? '#14532d' : '#7f1d1d'}`,
            color: status === 'Configuração salva' ? '#86efac' : '#fca5a5',
          }}>
          {status}
        </div>
      )}
    </div>
  )
}
