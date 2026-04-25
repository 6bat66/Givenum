import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getScan } from '@/lib/results'
import ScanTabs from '@/components/ScanTabs'

export const dynamic = 'force-dynamic'

function fmtNum(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function StatChip({
  value, label, color, dimIfZero = true,
}: {
  value: number; label: string; color: string; dimIfZero?: boolean
}) {
  const dim = dimIfZero && value === 0
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        fontSize: '12px',
        opacity: dim ? 0.35 : 1,
      }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ color: dim ? 'var(--text-subtle)' : color, fontWeight: dim ? 400 : 600 }}>
        {fmtNum(value)}
      </span>
    </span>
  )
}

export default async function ScanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = getScan(id)
  if (!data) notFound()

  const totalVulns = Object.values(data.nuclei).flat().length

  return (
    <div className="max-w-screen-2xl mx-auto px-4 py-4 md:px-5">

      {/* ── breadcrumb + meta bar ──────────────────────────────────── */}
      <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-2" style={{ fontSize: '12px' }}>
        <Link href="/" style={{ color: 'var(--text-muted)' }} className="hover:text-white transition-colors">
          ~/givenum
        </Link>
        <span style={{ color: 'var(--text-subtle)' }}>/</span>
        <span style={{ color: 'var(--text-muted)' }}>{data.projectName}</span>
        <span style={{ color: 'var(--text-subtle)' }}>/</span>
        <span style={{ color: 'var(--green)', fontWeight: 600 }}>{data.domain}</span>

        <span className={data.mode === 'active' ? 'badge-active' : 'badge-passive'}>
          {data.mode}
        </span>

        <span style={{ color: 'var(--text-subtle)', fontSize: '11px' }}>{data.timestamp}</span>

        {data.diff.previousScan && (
          <span className="text-[11px]" style={{ color: 'var(--text-subtle)' }}>
            diff ← {data.diff.previousScan}
          </span>
        )}

        {data.analysisAvailable && (
          <Link
            href={`/api/scan/${data.id}/analysis`}
            target="_blank"
            style={{ color: 'var(--cyan)', fontSize: '11px' }}
            className="hover:underline">
            analysis.md
          </Link>
        )}
      </div>

      {/* ── compact stats bar ─────────────────────────────────────── */}
      <div
        className="mb-5 flex flex-wrap items-center gap-3 px-4 py-3"
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--glow-purple)',
        }}>
        <span className="tag-fnd">[FND]</span>
        <StatChip value={data.stats.subdomains} label="subdomains" color="var(--cyan)" />
        <StatChip value={data.stats.alive}      label="alive"      color="var(--green)" />
        <StatChip value={data.stats.urls}       label="urls"       color="var(--purple)" />
        <StatChip value={data.stats.js}         label="js"         color="var(--yellow)" />
        <StatChip value={data.stats.ports}      label="ports"      color="var(--orange)" />
        <StatChip
          value={totalVulns}
          label="vulns"
          color="var(--red)"
          dimIfZero={false}
        />
      </div>

      {/* ── tabs ──────────────────────────────────────────────────── */}
      <ScanTabs data={data} />
    </div>
  )
}
