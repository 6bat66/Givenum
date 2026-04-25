import Link from 'next/link'
import SettingsSidebar from '@/components/SettingsSidebar'

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-screen-xl mx-auto px-4 py-6 md:px-6 md:py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="text-xs px-2 py-1 rounded"
          style={{ background: 'var(--surface-2)', color: 'var(--text-subtle)', border: '1px solid var(--border)', textDecoration: 'none' }}>
          ← back
        </Link>
        <span style={{ color: 'var(--text-subtle)', fontSize: '12px' }}>settings</span>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <aside
          className="shrink-0 rounded-xl"
          style={{
            width: '180px',
            background: 'var(--surface)',
            border: '1px solid var(--border-subtle)',
            padding: '8px',
            alignSelf: 'start',
            position: 'sticky',
            top: '80px',
          }}>
          <div className="px-3 pb-2 pt-1"
            style={{ fontSize: '11px', color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            settings
          </div>
          <SettingsSidebar />
        </aside>

        {/* Content */}
        <main className="min-w-0 flex-1">
          {children}
        </main>
      </div>
    </div>
  )
}
