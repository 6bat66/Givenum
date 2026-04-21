import Link from 'next/link'
import ApiSettingsForm from '@/components/ApiSettingsForm'
import { readApiKeys } from '@/lib/app-data'

export const dynamic = 'force-dynamic'

export default function SettingsPage() {
  const apiKeys = readApiKeys()

  return (
    <div className="max-w-screen-lg mx-auto px-6 py-8">
      <div className="flex items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
            API Settings
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Configure as chaves usadas pelo scanner e pelas notificações.
          </p>
        </div>
        <Link href="/"
          className="text-sm px-3 py-2 rounded-lg"
          style={{ background: 'var(--surface)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
          Voltar
        </Link>
      </div>

      <div className="rounded-xl p-5" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <ApiSettingsForm initialKeys={apiKeys} />
      </div>
    </div>
  )
}
