import fs from 'fs'
import path from 'path'
import type { ScanData, ScanMeta, HttpHost, NucleiFindings, DiffData } from './types'
import { getResultsDir, getProject, listProjects } from './app-data'

type ReportMeta = {
  scan_mode?: 'active' | 'passive'
}

function readLines(filePath: string): string[] {
  try {
    if (!fs.existsSync(filePath)) return []
    return fs
      .readFileSync(filePath, 'utf-8')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
  } catch {
    return []
  }
}

function readJsonl(filePath: string): Record<string, unknown>[] {
  try {
    if (!fs.existsSync(filePath)) return []
    const rows: Record<string, unknown>[] = []
    for (const line of readLines(filePath)) {
      try { rows.push(JSON.parse(line)) } catch { /* skip bad row */ }
    }
    return rows
  } catch {
    return []
  }
}

function readJson<T>(filePath: string): T | null {
  try { return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T }
  catch { return null }
}

function readDirectories(dirPath: string): string[] {
  try {
    return fs
      .readdirSync(dirPath, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
  } catch {
    return []
  }
}

function encodeScanId(relativePath: string): string {
  return Buffer.from(relativePath, 'utf-8').toString('base64url')
}

function decodeScanId(scanId: string): string | null {
  try {
    return Buffer.from(scanId, 'base64url').toString('utf-8')
  } catch {
    return null
  }
}

function detectScanMode(scanDir: string, reportMeta: ReportMeta | null): 'active' | 'passive' {
  if (reportMeta?.scan_mode === 'active' || reportMeta?.scan_mode === 'passive') {
    return reportMeta.scan_mode
  }

  const activeArtifacts = [
    path.join(scanDir, 'subdomains', 'bruteforce.txt'),
    path.join(scanDir, 'ports', 'sdlookup_results.json'),
    path.join(scanDir, 'vulnerabilities', 'nuclei_results.txt'),
    path.join(scanDir, 'vulnerabilities', 'dalfox_results.txt'),
    path.join(scanDir, 'takeover', 'subjack_results.txt'),
    path.join(scanDir, 'parameters', 'arjun_params.txt'),
  ]

  return activeArtifacts.some((filePath) => fs.existsSync(filePath)) ? 'active' : 'passive'
}

export function buildDiffData(currentFile: string, previousFile: string): DiffData {
  const current = readLines(currentFile)
  const previous = readLines(previousFile)
  const currentSet = new Set(current)
  const previousSet = new Set(previous)

  return {
    current,
    previous,
    new: current.filter((item) => !previousSet.has(item)),
    persisted: current.filter((item) => previousSet.has(item)),
    removed: previous.filter((item) => !currentSet.has(item)),
  }
}

function findScanDirectories(baseDir: string): string[] {
  if (!fs.existsSync(baseDir)) return []

  const scanDirs: string[] = []
  const stack = [baseDir]
  const visited = new Set<string>()

  while (stack.length > 0) {
    const currentDir = stack.pop() as string
    if (visited.has(currentDir)) continue
    visited.add(currentDir)

    for (const entry of readDirectories(currentDir)) {
      const fullPath = path.join(currentDir, entry)

      if (/^.+_\d{8}_\d{6}$/.test(entry)) {
        scanDirs.push(fullPath)
      } else {
        stack.push(fullPath)
      }
    }
  }

  return scanDirs
}

function getProjectForScan(relativePath: string) {
  const pathParts = relativePath.split(path.sep).filter(Boolean)
  const projectId = pathParts.length > 1 ? pathParts[0] : 'default'

  const project = getProject(projectId)
  return {
    id: project?.id ?? projectId,
    name: project?.name ?? (projectId === 'default' ? 'Default' : projectId),
  }
}

function buildTimestamp(datePart: string, timePart: string): string {
  return `${datePart.slice(0, 4)}-${datePart.slice(4, 6)}-${datePart.slice(6, 8)} ${timePart.slice(0, 2)}:${timePart.slice(2, 4)}:${timePart.slice(4, 6)}`
}

export function resolveScanDir(scanId: string): string | null {
  const decoded = decodeScanId(scanId)
  if (!decoded) return null

  const baseDir = getResultsDir()
  const scanDir = path.resolve(baseDir, decoded)
  const expectedBase = path.resolve(baseDir) + path.sep

  if (!scanDir.startsWith(expectedBase)) {
    return null
  }

  try {
    if (!fs.existsSync(scanDir) || !fs.statSync(scanDir).isDirectory()) {
      return null
    }
  } catch {
    return null
  }

  if (!/^.+_\d{8}_\d{6}$/.test(path.basename(scanDir))) {
    return null
  }

  return scanDir
}

export function deleteScan(scanId: string): boolean {
  const scanDir = resolveScanDir(scanId)
  if (!scanDir) return false
  try {
    fs.rmSync(scanDir, { recursive: true, force: true })
    return true
  } catch {
    return false
  }
}

export function listScans(projectId?: string): ScanMeta[] {
  const baseDir = getResultsDir()
  if (!fs.existsSync(baseDir)) return []

  const searchRoots = new Set<string>([baseDir])
  for (const project of listProjects()) {
    searchRoots.add(project.resultsPath)
  }

  const scanDirs = [...searchRoots].flatMap((root) => findScanDirectories(root))
  const uniqueScanDirs = [...new Set(scanDirs)]

  return uniqueScanDirs
    .map((fullPath) => {
      const relativePath = path.relative(baseDir, fullPath)
      const scanName = path.basename(fullPath)
      const match = scanName.match(/^(.+)_(\d{8})_(\d{6})$/)
      if (!match) return null

      const project = getProjectForScan(relativePath)
      if (projectId && project.id !== projectId) return null

      const [, domain, datePart, timePart] = match
      const reportMeta = readJson<ReportMeta>(path.join(fullPath, 'reports', 'report.json'))

      return {
        id: encodeScanId(relativePath),
        domain,
        timestamp: buildTimestamp(datePart, timePart),
        mode: detectScanMode(fullPath, reportMeta),
        projectId: project.id,
        projectName: project.name,
        stats: {
          subdomains: readLines(path.join(fullPath, 'subdomains', 'all_subdomains.txt')).length,
          alive: readLines(path.join(fullPath, 'http', 'alive.txt')).length,
          urls: readLines(path.join(fullPath, 'urls', 'urls_clean.txt')).length,
          vulns: readLines(path.join(fullPath, 'vulnerabilities', 'nuclei_results.txt')).length,
          ports: readLines(path.join(fullPath, 'ports', 'open_ports.txt')).length,
          js: readLines(path.join(fullPath, 'js', 'all_js_files.txt')).length,
        },
      } satisfies ScanMeta
    })
    .filter((scan): scan is ScanMeta => Boolean(scan))
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
}

export function getScan(scanId: string): ScanData | null {
  const scanDir = resolveScanDir(scanId)
  if (!scanDir) return null

  const relativePath = path.relative(getResultsDir(), scanDir)
  const scanName = path.basename(scanDir)
  const match = scanName.match(/^(.+)_(\d{8})_(\d{6})$/)
  if (!match) return null

  const [, domain, datePart, timePart] = match
  const reportMeta = readJson<ReportMeta>(path.join(scanDir, 'reports', 'report.json'))
  const project = getProjectForScan(relativePath)

  const rawHosts = readJsonl(path.join(scanDir, 'http', 'httpx_full.json'))
  const hosts: HttpHost[] = rawHosts.map((row) => ({
    url: (row.url as string) || (row.input as string) || '',
    status: (row.status_code as number) || 0,
    title: (row.title as string) || '',
    tech: (row.tech as string[]) || [],
    ip: (row.host_ip as string) || ((row.a as string[] | undefined)?.[0] ?? '') || '',
    contentLength: (row.content_length as number) || 0,
  }))

  const techCount: Record<string, number> = {}
  for (const host of hosts) {
    for (const tech of host.tech) {
      techCount[tech] = (techCount[tech] || 0) + 1
    }
  }
  const topTech = Object.entries(techCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15) as [string, number][]

  const allUrls = readLines(path.join(scanDir, 'urls', 'urls_clean.txt'))
  const paramUrls = allUrls.filter((url) => url.includes('?'))

  const nucleiRaw = readLines(path.join(scanDir, 'vulnerabilities', 'nuclei_results.txt'))
  const nuclei: NucleiFindings = { critical: [], high: [], medium: [], low: [], info: [] }
  const severityRe = /\[(critical|high|medium|low|info)\]/i
  for (const line of nucleiRaw) {
    const match = line.match(severityRe)
    if (match) {
      const sev = match[1].toLowerCase() as keyof NucleiFindings
      nuclei[sev].push(line)
    } else {
      nuclei.info.push(line)
    }
  }

  const diffSummary = readJson<{ previous_scan?: string }>(path.join(scanDir, 'diff', 'diff_summary.json'))
  const previousScanDir = diffSummary?.previous_scan
    ? path.join(path.dirname(scanDir), diffSummary.previous_scan)
    : null

  // Map each diff filename to the category subdirectory and the source filename.
  // Single source of truth — adding a new diffable artifact only requires one entry here.
  const DIFF_SOURCES: Record<string, { dir: string; file: string }> = {
    'all_subdomains.txt.diff': { dir: 'subdomains',     file: 'all_subdomains.txt' },
    'alive.txt.diff':          { dir: 'http',           file: 'alive.txt' },
    'urls_clean.txt.diff':     { dir: 'urls',           file: 'urls_clean.txt' },
    'open_ports.txt.diff':     { dir: 'ports',          file: 'open_ports.txt' },
    'nuclei_results.txt.diff': { dir: 'vulnerabilities', file: 'nuclei_results.txt' },
  }

  const diffFiles: Record<string, DiffData> = {}
  if (previousScanDir && fs.existsSync(previousScanDir)) {
    for (const [diffName, { dir, file }] of Object.entries(DIFF_SOURCES)) {
      const currentFile = path.join(scanDir, dir, file)
      const previousFile = path.join(previousScanDir, dir, file)
      if (!fs.existsSync(currentFile) || !fs.existsSync(previousFile)) continue
      const diffData = buildDiffData(currentFile, previousFile)
      if (diffData.new.length || diffData.removed.length || diffData.persisted.length) {
        diffFiles[diffName] = diffData
      }
    }
  }

  const screenshotsDir = path.join(scanDir, 'screenshots')
  let screenshots: string[] = []
  try {
    screenshots = fs.existsSync(screenshotsDir)
      ? fs.readdirSync(screenshotsDir).filter((file) => /\.(png|jpg|jpeg|webp)$/i.test(file))
      : []
  } catch {
    screenshots = []
  }

  const subdomains = readLines(path.join(scanDir, 'subdomains', 'all_subdomains.txt'))

  return {
    id: scanId,
    domain,
    timestamp: buildTimestamp(datePart, timePart),
    mode: detectScanMode(scanDir, reportMeta),
    projectId: project.id,
    projectName: project.name,
    analysisAvailable: fs.existsSync(path.join(scanDir, 'reports', 'analysis.md')),
    stats: {
      subdomains: subdomains.length,
      alive: readLines(path.join(scanDir, 'http', 'alive.txt')).length,
      urls: allUrls.length,
      vulns: nucleiRaw.length,
      ports: readLines(path.join(scanDir, 'ports', 'open_ports.txt')).length,
      js: readLines(path.join(scanDir, 'js', 'all_js_files.txt')).length,
    },
    subdomains,
    bruteforce: readLines(path.join(scanDir, 'subdomains', 'bruteforce.txt')),
    resolved: readLines(path.join(scanDir, 'dns', 'resolved.txt')),
    hosts,
    topTech,
    urls: allUrls,
    paramUrls,
    jsFiles: readLines(path.join(scanDir, 'js', 'all_js_files.txt')),
    parameters: readLines(path.join(scanDir, 'parameters', 'interesting_parameters.txt')),
    categorizedParameters: readLines(path.join(scanDir, 'parameters', 'categorized_parameters.txt')),
    openPorts: readLines(path.join(scanDir, 'ports', 'open_ports.txt')),
    nuclei,
    dalfox: readLines(path.join(scanDir, 'vulnerabilities', 'dalfox_results.txt')),
    subjack: readLines(path.join(scanDir, 'takeover', 'subjack_results.txt')),
    subzy: readLines(path.join(scanDir, 'takeover', 'subzy_results.txt')),
    securityHeaders: readLines(path.join(scanDir, 'vulnerabilities', 'security_headers.txt')),
    emailSecurity: readLines(path.join(scanDir, 'vulnerabilities', 'email_security.txt')).filter(l => l.startsWith('[')),
    corsFindings: readLines(path.join(scanDir, 'vulnerabilities', 'cors_misconfig.txt')),
    zoneTransfer: readLines(path.join(scanDir, 'dns', 'zone_transfer.txt')),
    gitExposed: readLines(path.join(scanDir, 'git', 'exposed_git.txt')),
    cloudAws: readLines(path.join(scanDir, 'cloud', 'aws_services.txt')),
    cloudAzure: readLines(path.join(scanDir, 'cloud', 'azure_services.txt')),
    cloudGcp: readLines(path.join(scanDir, 'cloud', 'gcp_services.txt')),
    screenshots,
    diff: {
      previousScan: diffSummary?.previous_scan ?? null,
      files: diffFiles,
    },
    toolLogs: (readJson<Record<string, { status: string; rc: number; elapsed: number; msg?: string }>>(
      path.join(scanDir, 'logs', 'execution_summary.json')
    ) ?? {}) as ScanData['toolLogs'],
  }
}
