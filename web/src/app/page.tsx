import Link from 'next/link'
import DashboardControls from '@/components/DashboardControls'
import { DeleteJobButton, DeleteProjectButton, DeleteScanButton, RescanButton, StopJobButton } from '@/components/ManageActions'
import { cleanupOrphanedJobs, listJobs, listProjects } from '@/lib/app-data'
import { listScans } from '@/lib/results'
import type { ProjectMeta, ScanJob, ScanMeta } from '@/lib/types'

export const dynamic = 'force-dynamic'

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtNum(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function pluralize(value: number, singular: string, plural: string): string {
  return `${value} ${value === 1 ? singular : plural}`
}

function fmtTs(ts: string): string {
  // "2025-04-15 14:23:05" → "Apr 15 14:23"
  const d = new Date(ts.replace(' ', 'T'))
  if (isNaN(d.getTime())) return ts.slice(0, 16)
  return d.toLocaleDateString('en', { month: 'short', day: 'numeric' })
    + ' ' + ts.slice(11, 16)
}

function fmtJobTs(ts: string): string {
  const d = new Date(ts.replace(' ', 'T'))
  if (isNaN(d.getTime())) return ts.slice(5, 16)
  return d.toLocaleDateString('en', { month: 'short', day: 'numeric' })
    + ' ' + ts.slice(11, 16)
}

// ── scan row ──────────────────────────────────────────────────────────────────

function ScanRow({ scan }: { scan: ScanMeta }) {
  const hasVulns = scan.stats.vulns > 0

  return (
    <div className="row-link">
      <Link href={`/scan/${scan.id}`} className="flex flex-col gap-2 px-5 py-4 md:flex-row md:items-center">
        <div className="flex min-w-0 flex-wrap items-center gap-2 md:w-[270px] md:flex-none">
          <span
            style={{
              color: hasVulns ? 'var(--red)' : scan.mode === 'active' ? 'var(--orange)' : 'var(--text)',
              fontWeight: 700,
              fontSize: '14px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: '100%',
            }}>
            {scan.domain}
          </span>
          <span className={scan.mode === 'active' ? 'badge-active' : 'badge-passive'}>
            {scan.mode}
          </span>
          <span className="text-[12px]" style={{ color: 'var(--text-subtle)' }}>
            {scan.projectName}
          </span>
        </div>

        <div className="text-[12px] md:w-[120px] md:flex-none" style={{ color: 'var(--text-muted)' }}>
          {fmtTs(scan.timestamp)}
        </div>

        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-4 gap-y-1 text-[12px]">
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

        <span className="hidden md:block" style={{ color: 'var(--text-subtle)', fontSize: '14px' }}>›</span>
      </Link>

      <div className="flex justify-end gap-2 px-4 pb-1.5" style={{ marginTop: '-2px' }}>
        <RescanButton domain={scan.domain} projectId={scan.projectId} mode={scan.mode} />
        <DeleteScanButton scanId={scan.id} domain={scan.domain} />
      </div>
    </div>
  )
}

// ── job row ───────────────────────────────────────────────────────────────────

function JobRow({ job }: { job: ScanJob }) {
  const ts = fmtJobTs((job.endedAt || job.startedAt || job.createdAt).replace('T', ' ').slice(0, 16))
  const isActive = job.status === 'running' || job.status === 'queued' || job.status === 'paused'
  const actionBtn = {
    textDecoration: 'none',
    padding: '6px 10px',
    borderRadius: '999px',
    border: '1px solid var(--border)',
    background: 'var(--surface-2)',
    fontSize: '12px',
    lineHeight: 1,
  } as const

  return (
    <div
      className="grid gap-3 px-5 py-4 border-b"
      style={{ borderColor: 'var(--border-subtle)', fontSize: '13px' }}>

      <div className="flex min-w-0 items-center gap-3">
        <span
          className={`status-${job.status}`}
          style={{ padding: '4px 10px', borderRadius: '999px', fontSize: '12px', width: 'fit-content', flexShrink: 0 }}>
          {job.status}
        </span>

        <span
          style={{ color: 'var(--text)', fontWeight: 700, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          className="flex-1">
          {job.domain}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px]">
        <span style={{ color: 'var(--text-muted)' }}>{job.mode}</span>
        <span style={{ color: 'var(--text-subtle)' }}>{ts}</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Link href={`/job/${job.id}`} style={{ ...actionBtn, color: 'var(--cyan)' }}>live</Link>
        <RescanButton domain={job.domain} projectId={job.projectId} mode={job.mode} />
        {job.scanId && (
          <Link href={`/scan/${job.scanId}`} style={{ ...actionBtn, color: 'var(--green)' }}>scan</Link>
        )}
        {isActive ? (
          <StopJobButton jobId={job.id} status={job.status} />
        ) : (
          <>
            {job.scanId && (
              <DeleteScanButton scanId={job.scanId} domain={job.domain} label="del scan" />
            )}
            <DeleteJobButton jobId={job.id} domain={job.domain} status={job.status} label="del job" />
          </>
        )}
      </div>
    </div>
  )
}

// ── section header ────────────────────────────────────────────────────────────

function SectionHeader({ title, count }: { title: string; count?: number }) {
  return (
    <div className="flex items-center gap-2 px-5 py-3 border-b"
      style={{ borderColor: 'var(--border)', background: 'var(--surface-2)', fontSize: '12px' }}>
      <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>{title}</span>
      {count !== undefined && (
        <span style={{ color: 'var(--text-subtle)', fontSize: '12px' }}>{count}</span>
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
  const activeCount   = jobs.filter((j) => ['queued', 'running', 'paused'].includes(j.status)).length

  const groupedScans = projects.map((p) => ({
    project: p,
    scans: scans.filter((s) => s.projectId === p.id),
  }))

  const activeJobs  = jobs.filter((j) => ['queued','running','paused'].includes(j.status)).slice(0, 8)
  const recentJobs  = jobs.filter((j) => ['completed','failed','stopped'].includes(j.status)).slice(0, 12)

  return (
    <div className="max-w-screen-2xl mx-auto px-4 py-4 md:px-5 md:py-5">

      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-3 text-[13px]">
          <span className="tag-fnd">[FND]</span>
          <span style={{ color: 'var(--text-muted)' }}>
            <span style={{ color: 'var(--text)' }}>{pluralize(scans.length, 'scan', 'scans')}</span> ·{' '}
            <span style={{ color: 'var(--text)' }}>{pluralize(uniqueDomains, 'root domain', 'root domains')}</span> ·{' '}
            <span style={{ color: 'var(--text)' }}>{pluralize(projects.length, 'project', 'projects')}</span>
            {totalVulns > 0 && (
              <> · <span style={{ color: 'var(--red)', fontWeight: 700 }}>{totalVulns} findings</span></>
            )}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a href="#active-jobs" className="ghost-button px-3 py-2 text-sm" style={{ textDecoration: 'none' }}>
            active jobs {activeCount > 0 ? `(${activeCount})` : ''}
          </a>
          {activeJobs[0] && (
            <Link href={`/job/${activeJobs[0].id}`} className="ghost-button px-3 py-2 text-sm" style={{ textDecoration: 'none', color: 'var(--cyan)' }}>
              live
            </Link>
          )}
        </div>
      </div>

      <DashboardControls projects={projects} />

      <div className="grid gap-4 xl:grid-cols-3">

        <div className="xl:col-span-2 space-y-4">
          {groupedScans.map(({ project, scans: ps }) => (
            ps.length > 0 && (
              <div key={project.id}
                className="panel"
                style={{ overflow: 'hidden' }}>
                <SectionHeader title={project.name} count={ps.length} />
                {ps.map((scan) => <ScanRow key={scan.id} scan={scan} />)}
              </div>
            )
          ))}

          {scans.length === 0 && (
            <div className="px-4 py-6 text-center"
              style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', color: 'var(--text-muted)', fontSize: '12px' }}>
              <span className="tag-inf">[INF]</span>{' '}
              no scans yet — start one using the form above
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div id="active-jobs" className="panel" style={{ overflow: 'hidden' }}>
            <SectionHeader title="active jobs" count={activeJobs.length} />
            {activeJobs.length === 0 ? (
              <div className="px-5 py-4 text-center" style={{ color: 'var(--text-subtle)', fontSize: '12px' }}>
                no active jobs
              </div>
            ) : (
              activeJobs.map((job) => <JobRow key={job.id} job={job} />)
            )}
          </div>

          <div className="panel-soft" style={{ overflow: 'hidden' }}>
            <SectionHeader title="recent jobs" count={recentJobs.length} />
            {recentJobs.length === 0 ? (
              <div className="px-5 py-4 text-center" style={{ color: 'var(--text-subtle)', fontSize: '12px' }}>
                no completed jobs
              </div>
            ) : (
              recentJobs.map((job) => <JobRow key={job.id} job={job} />)
            )}
          </div>

          <div className="panel-soft" style={{ overflow: 'hidden' }}>
            <SectionHeader title="projects" count={projects.length} />
            {projects.map((p) => {
              const ps = scans.filter((s) => s.projectId === p.id)
              const pVulns = ps.reduce((a, s) => a + s.stats.vulns, 0)
              return (
                <div key={p.id} className="flex items-center gap-3 px-5 py-3 border-b"
                  style={{ borderColor: 'var(--border-subtle)', fontSize: '12px' }}>
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
