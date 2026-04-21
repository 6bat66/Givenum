import fs from 'fs'
import path from 'path'
import crypto from 'crypto'
import type { ProjectMeta, ScanJob } from './types'

const DEFAULT_PROJECT_ID = 'default'

function ensureDir(dirPath: string): boolean {
  try {
    fs.mkdirSync(dirPath, { recursive: true })
    return true
  } catch {
    return false
  }
}

function resolveUsableDir(candidates: string[]): string {
  for (const candidate of candidates) {
    if (ensureDir(candidate)) {
      return candidate
    }
  }

  return candidates[candidates.length - 1]
}

function readJson<T>(filePath: string, fallback: T): T {
  try {
    if (!fs.existsSync(filePath)) return fallback
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T
  } catch {
    return fallback
  }
}

function isJobStatus(value: unknown): value is ScanJob['status'] {
  return value === 'queued' ||
    value === 'running' ||
    value === 'completed' ||
    value === 'failed' ||
    value === 'stopped' ||
    value === 'paused'
}

function isScanJobRecord(value: unknown): value is ScanJob {
  if (!value || typeof value !== 'object') return false

  const job = value as Partial<ScanJob>
  return typeof job.id === 'string' &&
    typeof job.projectId === 'string' &&
    typeof job.projectName === 'string' &&
    typeof job.domain === 'string' &&
    (job.mode === 'active' || job.mode === 'passive') &&
    isJobStatus(job.status) &&
    typeof job.createdAt === 'string' &&
    (job.startedAt === null || typeof job.startedAt === 'string') &&
    (job.endedAt === null || typeof job.endedAt === 'string') &&
    typeof job.outputBaseDir === 'string' &&
    (job.scanId === null || typeof job.scanId === 'string') &&
    (job.scanDir === null || typeof job.scanDir === 'string') &&
    typeof job.logFile === 'string' &&
    (job.analysisFile === undefined || job.analysisFile === null || typeof job.analysisFile === 'string') &&
    (job.returnCode === null || typeof job.returnCode === 'number') &&
    (job.pid === undefined || job.pid === null || typeof job.pid === 'number') &&
    Boolean(job.options) &&
    typeof job.options?.skipScreenshots === 'boolean' &&
    typeof job.options?.skipPortscan === 'boolean' &&
    typeof job.options?.skipVulnScan === 'boolean'
}

function writeJson(filePath: string, data: unknown): boolean {
  try {
    if (!ensureDir(path.dirname(filePath))) {
      return false
    }
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2))
    return true
  } catch {
    return false
  }
}

function slugify(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'project'
}

export function getWorkspaceRoot(): string {
  return process.env.GIVENUM_ROOT_DIR || path.resolve(process.cwd(), '..')
}

export function getConfigDir(): string {
  const workspaceRoot = getWorkspaceRoot()
  const preferred = process.env.GIVENUM_CONFIG_DIR || path.join(process.env.HOME || workspaceRoot, '.config', 'givenum')

  return resolveUsableDir([
    preferred,
    path.join(workspaceRoot, '.givenum-config'),
    path.join('/tmp', 'givenum-config'),
  ])
}

export function getResultsDir(): string {
  const workspaceRoot = getWorkspaceRoot()
  const preferred = process.env.RESULTS_DIR || path.join(workspaceRoot, 'results')

  return resolveUsableDir([
    preferred,
    path.join(getConfigDir(), 'runtime', 'results'),
    path.join(workspaceRoot, '.givenum-runtime', 'results'),
    path.join('/tmp', 'givenum-results'),
  ])
}

function getDefaultProjectResultsDir(): string {
  return path.join(getResultsDir(), DEFAULT_PROJECT_ID)
}

function getProjectsFile(): string {
  return process.env.GIVENUM_PROJECTS_FILE || path.join(getConfigDir(), 'projects.json')
}

function getJobsDir(): string {
  return path.join(getConfigDir(), 'jobs')
}

function getHiddenProjectsFile(): string {
  return path.join(getConfigDir(), 'hidden_projects.json')
}

function isProjectHidden(projectId: string): boolean {
  const hidden = readJson<string[]>(getHiddenProjectsFile(), [])
  return hidden.includes(projectId)
}

function hideProject(projectId: string): boolean {
  const hidden = readJson<string[]>(getHiddenProjectsFile(), [])
  if (hidden.includes(projectId)) return true
  return writeJson(getHiddenProjectsFile(), [...hidden, projectId])
}

export function getApiKeysFile(): string {
  return process.env.GIVENUM_API_KEYS_FILE || path.join(getConfigDir(), 'api_keys.json')
}

export function ensureAppLayout() {
  ensureDir(getResultsDir())
  ensureDir(getDefaultProjectResultsDir())
  ensureDir(getConfigDir())
  ensureDir(getJobsDir())

  const projectsFile = getProjectsFile()
  if (!fs.existsSync(projectsFile)) {
    writeJson(projectsFile, [])
  }
}

export function listProjects(): ProjectMeta[] {
  ensureAppLayout()
  const projects = readJson<ProjectMeta[]>(getProjectsFile(), [])

  const deduped = new Map<string, ProjectMeta>()

  if (!isProjectHidden(DEFAULT_PROJECT_ID)) {
    const defaultProject: ProjectMeta = {
      id: DEFAULT_PROJECT_ID,
      name: 'Default',
      description: 'Scans not assigned to a custom project',
      createdAt: new Date(0).toISOString(),
      resultsPath: getDefaultProjectResultsDir(),
    }
    deduped.set(defaultProject.id, defaultProject)
  }

  for (const project of projects) {
    deduped.set(project.id, {
      ...project,
      resultsPath: path.join(getResultsDir(), project.id),
    })
  }

  return [...deduped.values()].sort((a, b) => a.name.localeCompare(b.name))
}

export function getProject(projectId: string): ProjectMeta | null {
  return listProjects().find((project) => project.id === projectId) ?? null
}

export function createProject(input: { name: string; description?: string }): ProjectMeta {
  ensureAppLayout()
  const existing = readJson<ProjectMeta[]>(getProjectsFile(), [])
  const baseId = slugify(input.name)
  let candidateId = baseId
  let suffix = 2

  while (candidateId === DEFAULT_PROJECT_ID || existing.some((project) => project.id === candidateId)) {
    candidateId = `${baseId}-${suffix}`
    suffix += 1
  }

  const project: ProjectMeta = {
    id: candidateId,
    name: input.name.trim(),
    description: input.description?.trim() || '',
    createdAt: new Date().toISOString(),
    resultsPath: path.join(getResultsDir(), candidateId),
  }

  existing.push({
    ...project,
    resultsPath: '',
  })
  if (!writeJson(getProjectsFile(), existing)) {
    throw new Error('Falha ao salvar projeto')
  }
  ensureDir(project.resultsPath)
  return project
}

export function readApiKeys(): Record<string, string> {
  ensureAppLayout()
  return readJson<Record<string, string>>(getApiKeysFile(), {})
}

export function writeApiKeys(keys: Record<string, string>) {
  ensureAppLayout()
  const cleaned = Object.fromEntries(
    Object.entries(keys)
      .map(([key, value]) => [key, value.trim()])
      .filter(([, value]) => value.length > 0)
  )
  if (!writeJson(getApiKeysFile(), cleaned)) {
    throw new Error('Falha ao salvar API keys')
  }
}

export function maskApiKeys(keys: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(keys).map(([key, value]) => {
      if (value.length <= 8) return [key, '********']
      return [key, `${value.slice(0, 4)}••••${value.slice(-4)}`]
    })
  )
}

export function createJob(input: Omit<ScanJob, 'id' | 'createdAt'>): ScanJob {
  ensureAppLayout()
  const id = crypto.randomUUID()
  const job: ScanJob = {
    ...input,
    id,
    createdAt: new Date().toISOString(),
  }
  writeJob(job)
  return job
}

export function getJob(jobId: string): ScanJob | null {
  ensureAppLayout()
  const filePath = path.join(getJobsDir(), `${jobId}.json`)
  const job = readJson<unknown>(filePath, null)
  return isScanJobRecord(job) ? job : null
}

export function listJobs(): ScanJob[] {
  ensureAppLayout()
  try {
    return fs
      .readdirSync(getJobsDir())
      .filter((entry) => entry.endsWith('.json'))
      .map((entry) => readJson<unknown>(path.join(getJobsDir(), entry), null))
      .filter(isScanJobRecord)
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  } catch {
    return []
  }
}

export function writeJob(job: ScanJob) {
  ensureAppLayout()
  if (!writeJson(path.join(getJobsDir(), `${job.id}.json`), job)) {
    throw new Error('Falha ao salvar job')
  }
}

export function getJobFile(jobId: string): string {
  ensureAppLayout()
  return path.join(getJobsDir(), `${jobId}.json`)
}

export function cleanupOrphanedJobs(): number {
  ensureAppLayout()
  let fixed = 0
  try {
    for (const entry of fs.readdirSync(getJobsDir()).filter((e) => e.endsWith('.json'))) {
      const filePath = path.join(getJobsDir(), entry)
      const job = readJson<Record<string, unknown>>(filePath, {})
      if (!job.status || job.status !== 'running') continue
      const pid = job.pid as number | undefined
      if (pid) {
        try { process.kill(pid, 0) ; continue } catch { /* process gone */ }
      }
      // Job says running but process is dead — mark as failed
      job.status = 'failed'
      job.endedAt = new Date().toISOString()
      job.returnCode = -9
      job.pid = null
      writeJson(filePath, job)
      fixed++
    }
  } catch { /* ignore */ }
  return fixed
}

export function deleteJob(jobId: string): boolean {
  const filePath = path.join(getJobsDir(), `${jobId}.json`)
  try {
    if (!fs.existsSync(filePath)) return false
    fs.unlinkSync(filePath)
    return true
  } catch {
    return false
  }
}

export function deleteProject(projectId: string): boolean {
  if (projectId === DEFAULT_PROJECT_ID) {
    return hideProject(DEFAULT_PROJECT_ID)
  }
  const projects = readJson<ProjectMeta[]>(getProjectsFile(), [])
  const filtered = projects.filter((project) => project.id !== projectId)
  if (filtered.length === projects.length) return false
  return writeJson(getProjectsFile(), filtered)
}

export function getProjectOutputDir(projectId: string): string {
  const project = getProject(projectId)
  if (!project) {
    throw new Error(`Unknown project: ${projectId}`)
  }

  ensureDir(project.resultsPath)
  return project.resultsPath
}
