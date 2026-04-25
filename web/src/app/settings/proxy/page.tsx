import ProxySettingsForm from '@/components/ProxySettingsForm'
import { readProxyConfig } from '@/lib/app-data'

export const dynamic = 'force-dynamic'

export default function ProxySettingsPage() {
  const cfg = readProxyConfig()

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text)' }}>Proxy</h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Route scanner traffic through an HTTP/S proxy (e.g. Burp Suite, MITM Proxy).
        </p>
      </div>

      <div className="panel rounded-xl p-5">
        <ProxySettingsForm initial={cfg} />
      </div>

    </div>
  )
}
