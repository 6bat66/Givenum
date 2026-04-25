import ApiSettingsForm from '@/components/ApiSettingsForm'
import { readApiKeys } from '@/lib/app-data'

export const dynamic = 'force-dynamic'

export default function ApisSettingsPage() {
  const apiKeys = readApiKeys()

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text)' }}>API Keys</h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Keys used by the scanner and notification integrations.
        </p>
      </div>

      <div className="panel rounded-xl p-5">
        <ApiSettingsForm initialKeys={apiKeys} />
      </div>
    </div>
  )
}
