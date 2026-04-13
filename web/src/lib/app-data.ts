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
  const defaultProject: ProjectMeta = {
    id: DEFAULT_PROJECT_ID,
    name: 'Default',
    description: 'Scans not assigned to a custom project',
    createdAt: new Date(0).toISOString(),
    resultsPath: getDefaultProjectResultsDir(),
  }

  const deduped = new Map<string, ProjectMeta>()
  deduped.set(defaultProject.id, defaultProject)

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
  return readJson<ScanJob | null>(filePath, null)
}

export function listJobs(): ScanJob[] {
  ensureAppLayout()
  try {
    return fs
      .readdirSync(getJobsDir())
      .filter((entry) => entry.endsWith('.json'))
      .map((entry) => readJson<ScanJob | null>(path.join(getJobsDir(), entry), null))
      .filter((job): job is ScanJob => Boolean(job))
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
  if (projectId === DEFAULT_PROJECT_ID) return false
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
