import Link from 'next/link'
import DashboardControls from '@/components/DashboardControls'
import { DeleteJobButton, DeleteProjectButton, DeleteScanButton, StopJobButton } from '@/components/ManageActions'
import { cleanupOrphanedJobs, listJobs, listProjects } from '@/lib/app-data'
import { listScans } from '@/lib/results'
import type { ProjectMeta, ScanJob, ScanMeta } from '@/lib/types'

export const dynamic = 'force-dynamic'

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtNum(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function fmtTs(ts: string): string {
  // "2025-04-15 14:23:05" → "Apr 15 14:23"
  const d = new Date(ts.replace(' ', 'T'))
  if (isNaN(d.getTime())) return ts.slice(0, 16)
  return d.toLocaleDateString('en', { month: 'short', day: 'numeric' })
    + ' ' + ts.slice(11, 16)
}

// ── scan row ──────────────────────────────────────────────────────────────────

function ScanRow({ scan }: { scan: ScanMeta }) {
  const hasVulns = scan.stats.vulns > 0

  return (
    <div className="row-link">
      <Link href={`/scan/${scan.id}`} className="flex items-center gap-0 px-4 py-2.5">
        {/* domain + mode */}
        <div className="flex items-center gap-2 min-w-0" style={{ flex: '0 0 260px' }}>
          <span
            style={{
              color: hasVulns ? 'var(--red)' : scan.mode === 'active' ? 'var(--orange)' : 'var(--text)',
              fontWeight: 600,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
            {scan.domain}
          </span>
          <span className={scan.mode === 'active' ? 'badge-active' : 'badge-passive'}>
            {scan.mode}
          </span>
        </div>

        {/* timestamp */}
        <div style={{ flex: '0 0 110px', color: 'var(--text-muted)', fontSize: '11px' }}>
          {fmtTs(scan.timestamp)}
        </div>

        {/* project */}
        <div style={{ flex: '0 0 120px', color: 'var(--text-subtle)', fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {scan.projectName}
        </div>

        {/* stats */}
        <div className="flex items-center gap-3 flex-1 min-w-0" style={{ fontSize: '11px' }}>
          {scan.stats.subdomains > 0 && (
            <span style={{ color: 'var(--cyan)' }}>
              <span style={{ color: 'var(--text-muted)' }}>subs </span>{fmtNum(scan.stats.subdomains)}
            </span>
          )}
          {scan.stats.alive > 0 && (
            <span style={{ color: 'var(--green)' }}>
              <span style={{ color: 'var(--text-muted)' }}>alive </span>{fmtNum(scan.stats.alive)}
            </span>
          )}
          {scan.stats.urls > 0 && (
            <span style={{ color: 'var(--purple)' }}>
              <span style={{ color: 'var(--text-muted)' }}>urls </span>{fmtNum(scan.stats.urls)}
            </span>
          )}
          {scan.stats.js > 0 && (
            <span style={{ color: 'var(--yellow)' }}>
              <span style={{ color: 'var(--text-muted)' }}>js </span>{scan.stats.js}
            </span>
          )}
          {scan.stats.ports > 0 && (
            <span style={{ color: 'var(--orange)' }}>
              <span style={{ color: 'var(--text-muted)' }}>ports </span>{scan.stats.ports}
            </span>
          )}
          {hasVulns && (
            <span style={{ color: 'var(--red)', fontWeight: 600 }}>
              <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>vulns </span>{scan.stats.vulns}
            </span>
          )}
        </div>

        {/* chevron */}
        <span style={{ color: 'var(--text-subtle)', fontSize: '14px' }}>›</span>
      </Link>

      {/* delete action — separated from the link */}
      <div className="flex justify-end px-4 pb-1.5" style={{ marginTop: '-2px' }}>
        <DeleteScanButton scanId={scan.id} domain={scan.domain} />
      </div>
    </div>
  )
}

// ── job row ───────────────────────────────────────────────────────────────────

function JobRow({ job }: { job: ScanJob }) {
  const ts = (job.endedAt || job.startedAt || job.createdAt).replace('T', ' ').slice(0, 16)
  const isActive = job.status === 'running' || job.status === 'queued' || job.status === 'paused'

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b"
      style={{ borderColor: 'var(--border-subtle)', fontSize: '12px' }}>

      <span
        className={`status-${job.status}`}
        style={{ padding: '1px 6px', borderRadius: 'var(--radius)', fontSize: '11px', flexShrink: 0 }}>
        {job.status}
      </span>

      <span style={{ color: 'var(--text)', fontWeight: 600, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: '0 0 200px' }}>
        {job.domain}
      </span>

      <span style={{ color: 'var(--text-muted)', flex: '0 0 80px', fontSize: '11px' }}>
        {job.mode}
      </span>

      <span style={{ color: 'var(--text-subtle)', flex: '0 0 120px', fontSize: '11px' }}>
        {ts}
      </span>

      <div className="flex items-center gap-2 ml-auto" style={{ flexShrink: 0 }}>
        <Link href={`/job/${job.id}`} style={{ color: 'var(--cyan)', fontSize: '11px' }}>log</Link>
        {job.scanId && (
          <Link href={`/scan/${job.scanId}`} style={{ color: 'var(--green)', fontSize: '11px' }}>scan</Link>
        )}
        {isActive ? (
          <StopJobButton jobId={job.id} status={job.status} />
        ) : (
          <DeleteJobButton jobId={job.id} domain={job.domain} status={job.status} />
        )}
      </div>
    </div>
  )
}

// ── section header ────────────────────────────────────────────────────────────

function SectionHeader({ title, count }: { title: string; count?: number }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b"
      style={{ borderColor: 'var(--border)', background: 'var(--surface-2)', fontSize: '11px' }}>
      <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{title}</span>
      {count !== undefined && (
        <span style={{ color: 'var(--text-subtle)' }}>{count}</span>
      )}
    </div>
  )
}

// ── page ──────────────────────────────────────────────────────────────────────

export default async function Home() {
  cleanupOrphanedJobs()

  let scans: ScanMeta[] = []
  let projects: ProjectMeta[] = []
  let jobs: ScanJob[] = []

  try {
    ;[scans, projects, jobs] = await Promise.all([
      Promise.resolve(listScans()),
      Promise.resolve(listProjects()),
      Promise.resolve(listJobs()),
    ])
  } catch {
    scans = []
    projects = [{
      id: 'default',
      name: 'Default',
      description: '',
      createdAt: new Date(0).toISOString(),
      resultsPath: '',
    }]
    jobs = []
  }

  const uniqueDomains = new Set(scans.map((s) => s.domain)).size
  const totalVulns    = scans.reduce((a, s) => a + s.stats.vulns, 0)
  const totalSubs     = scans.reduce((a, s) => a + s.stats.subdomains, 0)

  const groupedScans = projects.map((p) => ({
    project: p,
    scans: scans.filter((s) => s.projectId === p.id),
  }))

  const activeJobs  = jobs.filter((j) => ['queued','running','paused'].includes(j.status)).slice(0, 8)
  const recentJobs  = jobs.filter((j) => ['completed','failed','stopped'].includes(j.status)).slice(0, 12)

  return (
    <div className="max-w-screen-2xl mx-auto px-5 py-5">

      {/* ── summary line ──────────────────────────────────────────── */}
      <div className="flex items-center gap-3 mb-5" style={{ fontSize: '12px' }}>
        <span className="tag-fnd">[FND]</span>
        <span style={{ color: 'var(--text-muted)' }}>
          <span style={{ color: 'var(--text)' }}>{scans.length}</span> scans ·{' '}
          <span style={{ color: 'var(--text)' }}>{uniqueDomains}</span> domains ·{' '}
          <span style={{ color: 'var(--text)' }}>{fmtNum(totalSubs)}</span> subdomains
          {totalVulns > 0 && (
            <> · <span style={{ color: 'var(--red)', fontWeight: 600 }}>{totalVulns} vulns</span></>
          )}
        </span>
      </div>

      {/* ── controls: new project + new scan ──────────────────────── */}
      <DashboardControls projects={projects} />

      {/* ── main grid ─────────────────────────────────────────────── */}
      <div className="grid xl:grid-cols-3 gap-4">

        {/* scans (2/3 width) */}
        <div className="xl:col-span-2 space-y-4">
          {groupedScans.map(({ project, scans: ps }) => (
            ps.length > 0 && (
              <div key={project.id}
                style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
                <SectionHeader title={project.name} count={ps.length} />
                {ps.map((scan) => <ScanRow key={scan.id} scan={scan} />)}
              </div>
            )
          ))}

          {scans.length === 0 && (
            <div className="px-4 py-6 text-center"
              style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--text-muted)', fontSize: '12px' }}>
              <span className="tag-inf">[INF]</span>{' '}
              no scans yet — start one using the form above
            </div>
          )}
        </div>

        {/* jobs (1/3 width) */}
        <div className="space-y-4">
          {/* active jobs */}
          <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
            <SectionHeader title="active jobs" count={activeJobs.length} />
            {activeJobs.length === 0 ? (
              <div className="px-4 py-3 text-center" style={{ color: 'var(--text-subtle)', fontSize: '11px' }}>
                no active jobs
              </div>
            ) : (
              activeJobs.map((job) => <JobRow key={job.id} job={job} />)
            )}
          </div>

          {/* recent jobs */}
          <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
            <SectionHeader title="recent jobs" count={recentJobs.length} />
            {recentJobs.length === 0 ? (
              <div className="px-4 py-3 text-center" style={{ color: 'var(--text-subtle)', fontSize: '11px' }}>
                no completed jobs
              </div>
            ) : (
              recentJobs.map((job) => <JobRow key={job.id} job={job} />)
            )}
          </div>

          {/* projects summary */}
          <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
            <SectionHeader title="projects" count={projects.length} />
            {projects.map((p) => {
              const ps = scans.filter((s) => s.projectId === p.id)
              const pVulns = ps.reduce((a, s) => a + s.stats.vulns, 0)
              return (
                <div key={p.id} className="flex items-center gap-3 px-4 py-2 border-b"
                  style={{ borderColor: 'var(--border-subtle)', fontSize: '11px' }}>
                  <span style={{ color: 'var(--text)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {p.name}
                  </span>
                  <span style={{ color: 'var(--cyan)' }}>{ps.length}</span>
                  {pVulns > 0 && <span style={{ color: 'var(--red)' }}>{pVulns}v</span>}
                  <DeleteProjectButton projectId={p.id} name={p.name} />
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
