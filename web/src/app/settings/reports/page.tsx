import ReportsForm from '@/components/ReportsForm'
import { listScans } from '@/lib/results'

export const dynamic = 'force-dynamic'

export default function ReportsSettingsPage() {
  const scans = listScans()

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text)' }}>Reports</h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Generate a self-contained HTML report from any completed scan.
        </p>
      </div>

      <div className="panel rounded-xl p-5">
        <ReportsForm scans={scans} />
      </div>
    </div>
  )
}
