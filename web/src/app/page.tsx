import Link from 'next/link'
import DashboardControls from '@/components/DashboardControls'
import { DeleteJobButton, DeleteProjectButton, DeleteScanButton, StopJobButton } from '@/components/ManageActions'
import { cleanupOrphanedJobs, listJobs, listProjects } from '@/lib/app-data'
import { listScans } from '@/lib/results'
import type { ProjectMeta, ScanJob, ScanMeta } from '@/lib/types'

export const dynamic = 'force-dynamic'

function StatPill({ value, label, color }: { value: number; label: string; color: string }) {
  if (value === 0) return null
  return (
    <span className="flex items-center gap-1 text-xs">
      <span className="font-semibold font-mono" style={{ color }}>{value}</span>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
    </span>
  )
}

function ScanCard({ scan }: { scan: ScanMeta }) {
  const hasVulns = scan.stats.vulns > 0
  const accentColor = hasVulns ? 'var(--red)' : scan.mode === 'active' ? 'var(--orange)' : 'var(--cyan)'

  return (
    <div className="rounded-xl p-5 transition-all duration-150 hover:translate-y-[-1px] relative group"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderLeft: `3px solid ${accentColor}`,
      }}>
      <Link href={`/scan/${scan.id}`} className="block">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0">
            <div className="font-semibold text-base truncate" style={{ color: 'var(--text)' }}>
              {scan.domain}
            </div>
            <div className="text-xs mt-0.5 font-mono" style={{ color: 'var(--text-muted)' }}>
              {scan.timestamp}
            </div>
          </div>
          <span className="shrink-0 text-xs px-2 py-0.5 rounded-full font-medium"
            style={scan.mode === 'active'
              ? { background: '#431407', color: '#fdba74' }
              : { background: '#082f49', color: '#7dd3fc' }}>
            {scan.mode}
          </span>
        </div>

        <div className="mb-3">
          <span className="text-xs px-2 py-0.5 rounded-full font-medium"
            style={{ background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
            {scan.projectName}
          </span>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <StatPill value={scan.stats.subdomains} label="subdomains" color="var(--cyan)" />
          <StatPill value={scan.stats.alive} label="alive" color="var(--green)" />
          <StatPill value={scan.stats.urls} label="URLs" color="var(--purple)" />
          <StatPill value={scan.stats.js} label="JS" color="var(--yellow)" />
          {scan.stats.ports > 0 && <StatPill value={scan.stats.ports} label="ports" color="var(--orange)" />}
          {scan.stats.vulns > 0 && <StatPill value={scan.stats.vulns} label="vulns" color="var(--red)" />}
        </div>
      </Link>

      <div className="flex justify-end mt-3 pt-3 border-t" style={{ borderColor: 'var(--border)' }}>
        <DeleteScanButton scanId={scan.id} domain={scan.domain} />
      </div>
    </div>
  )
}

function ProjectCard({ project, scans }: { project: ProjectMeta; scans: ScanMeta[] }) {
  const totalVulns = scans.reduce((sum, scan) => sum + scan.stats.vulns, 0)
  const latest = scans[0]

  return (
    <div className="rounded-xl p-4"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <div className="font-semibold" style={{ color: 'var(--text)' }}>{project.name}</div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            {project.description || 'Sem descrição'}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs px-2 py-0.5 rounded-full font-mono"
            style={{ background: 'var(--surface-2)', color: 'var(--text-subtle)', border: '1px solid var(--border)' }}>
            {project.id}
          </span>
          <DeleteProjectButton projectId={project.id} name={project.name} />
        </div>
      </div>
      <div className="flex flex-wrap gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
        <span><span className="font-semibold" style={{ color: 'var(--cyan)' }}>{scans.length}</span> scans</span>
        <span><span className="font-semibold" style={{ color: 'var(--red)' }}>{totalVulns}</span> vulns</span>
        {latest && <span>último: <span className="font-mono">{latest.timestamp}</span></span>}
      </div>
    </div>
  )
}

function jobStatusStyle(status: ScanJob['status']) {
  switch (status) {
    case 'completed': return { background: '#052e16', color: '#86efac' }
    case 'failed':    return { background: '#450a0a', color: '#fca5a5' }
    case 'stopped':   return { background: '#1c1917', color: '#a8a29e' }
    case 'paused':    return { background: '#422006', color: '#fde047' }
    default:          return { background: '#082f49', color: '#7dd3fc' }
  }
}

function JobCard({ job }: { job: ScanJob }) {
  const finishedAt = job.endedAt || job.startedAt || job.createdAt
  const isActive = job.status === 'running' || job.status === 'queued' || job.status === 'paused'

  return (
    <div className="rounded-xl p-4"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <div className="font-semibold" style={{ color: 'var(--text)' }}>{job.domain}</div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            {job.projectName} · {job.mode}
          </div>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={jobStatusStyle(job.status)}>
          {job.status}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
        <span className="font-mono">{finishedAt.replace('T', ' ').slice(0, 19)}</span>
        <Link href={`/job/${job.id}`} className="hover:underline" style={{ color: 'var(--cyan)' }}>
          ver job
        </Link>
        <Link href={`/api/jobs/${job.id}/log`} target="_blank" className="hover:underline" style={{ color: 'var(--text-muted)' }}>
          log
        </Link>
        {job.scanId && (
          <Link href={`/scan/${job.scanId}`} className="hover:underline" style={{ color: 'var(--green)' }}>
            scan
          </Link>
        )}
        {isActive && <StopJobButton jobId={job.id} status={job.status} />}
        {!isActive && <DeleteJobButton jobId={job.id} domain={job.domain} status={job.status} />}
      </div>
    </div>
  )
}

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
      description: 'Scans not assigned to a custom project',
      createdAt: new Date(0).toISOString(),
      resultsPath: '',
    }]
    jobs = []
  }

  const uniqueDomains = new Set(scans.map((scan) => scan.domain)).size
  const totalVulns = scans.reduce((acc, scan) => acc + scan.stats.vulns, 0)
  const totalSubs = scans.reduce((acc, scan) => acc + scan.stats.subdomains, 0)
  const groupedScans = projects.map((project) => ({
    project,
    scans: scans.filter((scan) => scan.projectId === project.id),
  }))
  const activeJobs = jobs.filter((job) => job.status === 'queued' || job.status === 'running' || job.status === 'paused').slice(0, 6)
  const recentJobs = jobs.filter((job) => job.status === 'completed' || job.status === 'failed' || job.status === 'stopped').slice(0, 10)

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
            GivEnum Control Center
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Gerencie projetos, inicie scans, acompanhe jobs e analise resultados pela UI
          </p>
        </div>
        <Link href="/settings"
          className="text-sm px-3 py-2 rounded-lg"
          style={{ background: 'var(--surface)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
          Settings
        </Link>
      </div>

      <DashboardControls projects={projects} />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        {[
          { label: 'Total Scans', value: scans.length, color: 'var(--cyan)' },
          { label: 'Unique Domains', value: uniqueDomains, color: 'var(--green)' },
          { label: 'Total Subdomains', value: totalSubs, color: 'var(--purple)' },
          { label: 'Total Vulnerabilities', value: totalVulns, color: 'var(--red)' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl p-4"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="text-2xl font-bold font-mono" style={{ color }}>
              {value.toLocaleString()}
            </div>
            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{label}</div>
          </div>
        ))}
      </div>

      <div className="grid xl:grid-cols-2 gap-4 mb-8">
        <div>
          <div className="text-sm font-semibold mb-3" style={{ color: 'var(--text)' }}>Projetos</div>
          <div className="grid gap-3">
            {groupedScans.map(({ project, scans: projectScans }) => (
              <ProjectCard key={project.id} project={project} scans={projectScans} />
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <div className="text-sm font-semibold mb-3" style={{ color: 'var(--text)' }}>Jobs Ativos</div>
            {activeJobs.length === 0 ? (
              <div className="rounded-xl p-4 text-sm" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                Nenhum job em execução.
              </div>
            ) : (
              <div className="grid gap-3">
                {activeJobs.map((job) => <JobCard key={job.id} job={job} />)}
              </div>
            )}
          </div>

          <div>
            <div className="text-sm font-semibold mb-3" style={{ color: 'var(--text)' }}>Últimos Jobs</div>
            {recentJobs.length === 0 ? (
              <div className="rounded-xl p-4 text-sm" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                Ainda não há jobs concluídos.
              </div>
            ) : (
              <div className="grid gap-3">
                {recentJobs.map((job) => <JobCard key={job.id} job={job} />)}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-8">
        {groupedScans.map(({ project, scans: projectScans }) => (
          <section key={project.id}>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>{project.name}</h2>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {projectScans.length} scans
                </p>
              </div>
            </div>
            {projectScans.length === 0 ? (
              <div className="rounded-xl p-4 text-sm" style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                Sem scans neste projeto.
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {projectScans.map((scan) => (
                  <ScanCard key={scan.id} scan={scan} />
                ))}
              </div>
            )}
          </section>
        ))}
      </div>
    </div>
  )
}
