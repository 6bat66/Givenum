import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getScan } from '@/lib/results'
import ScanTabs from '@/components/ScanTabs'

export const dynamic = 'force-dynamic'

function StatCard({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="rounded-xl p-4 text-center"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="text-2xl font-bold font-mono" style={{ color }}>
        {value.toLocaleString()}
      </div>
      <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{label}</div>
    </div>
  )
}

export default async function ScanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = getScan(id)
  if (!data) notFound()

  const totalVulns = Object.values(data.nuclei).flat().length

  return (
    <div className="max-w-screen-2xl mx-auto px-6 py-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
        <Link href="/" className="hover:text-white transition-colors">Scans</Link>
        <span>/</span>
        <span>{data.projectName}</span>
        <span>/</span>
        <span style={{ color: 'var(--text)' }}>{data.domain}</span>
        <span className="text-xs px-2 py-0.5 rounded font-mono"
          style={{ background: 'var(--surface)', color: 'var(--text-subtle)' }}>
          {data.timestamp}
        </span>
        <span className="text-xs px-2 py-0.5 rounded"
          style={data.mode === 'active'
            ? { background: '#431407', color: '#fdba74' }
            : { background: '#082f49', color: '#7dd3fc' }}>
          {data.mode}
        </span>
        {data.analysisAvailable && (
          <Link
            href={`/api/scan/${data.id}/analysis`}
            target="_blank"
            className="text-xs px-2 py-0.5 rounded hover:text-white transition-colors"
            style={{ background: 'var(--surface)', color: 'var(--cyan)' }}>
            analysis.md
          </Link>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-8">
        <StatCard value={data.stats.subdomains} label="Subdomains" color="var(--cyan)" />
        <StatCard value={data.stats.alive} label="Alive" color="var(--green)" />
        <StatCard value={data.stats.urls} label="URLs" color="var(--purple)" />
        <StatCard value={data.stats.js} label="JS Files" color="var(--yellow)" />
        <StatCard value={data.stats.ports} label="Open Ports" color="var(--orange)" />
        <StatCard value={totalVulns} label="Vulnerabilities" color={totalVulns > 0 ? 'var(--red)' : 'var(--text-muted)'} />
      </div>

      {/* Tabs */}
      <ScanTabs data={data} />
    </div>
  )
}
