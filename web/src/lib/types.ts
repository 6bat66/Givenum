export interface ProjectMeta {
  id: string
  name: string
  description: string
  createdAt: string
  resultsPath: string
}

export interface ScanMeta {
  id: string
  domain: string
  timestamp: string
  mode: 'passive' | 'active'
  projectId: string
  projectName: string
  stats: {
    subdomains: number
    alive: number
    urls: number
    vulns: number
    ports: number
    js: number
  }
}

export interface HttpHost {
  url: string
  status: number
  title: string
  tech: string[]
  ip: string
  contentLength: number
}

export interface NucleiFindings {
  critical: string[]
  high: string[]
  medium: string[]
  low: string[]
  info: string[]
}

export interface DiffData {
  new: string[]
  removed: string[]
}

export interface ToolLogEntry {
  status: 'ok' | 'partial' | 'fail' | 'timeout' | 'not_found' | 'error'
  rc: number
  elapsed: number
  msg?: string
  // Optional extra counters surfaced by batch tools
  found?: number
  hosts?: number
  timeouts?: number
  failures?: number
  skipped?: number
  urls?: number
  discovered?: number
  findings?: number
}

export interface ScanData extends ScanMeta {
  analysisAvailable?: boolean
  subdomains: string[]
  bruteforce: string[]
  resolved: string[]
  hosts: HttpHost[]
  topTech: [string, number][]
  urls: string[]
  paramUrls: string[]
  jsFiles: string[]
  parameters: string[]
  categorizedParameters: string[]
  openPorts: string[]
  nuclei: NucleiFindings
  dalfox: string[]
  subjack: string[]
  subzy: string[]
  securityHeaders: string[]
  emailSecurity: string[]
  corsFindings: string[]
  zoneTransfer: string[]
  gitExposed: string[]
  cloudAws: string[]
  cloudAzure: string[]
  cloudGcp: string[]
  screenshots: string[]
  diff: {
    previousScan: string | null
    files: Record<string, DiffData>
  }
  toolLogs: Record<string, ToolLogEntry>
}

export interface ScanJob {
  id: string
  projectId: string
  projectName: string
  domain: string
  mode: 'active' | 'passive'
  status: 'queued' | 'running' | 'completed' | 'failed' | 'stopped' | 'paused'
  createdAt: string
  startedAt: string | null
  endedAt: string | null
  outputBaseDir: string
  scanId: string | null
  scanDir: string | null
  logFile: string
  analysisFile?: string | null
  returnCode: number | null
  pid?: number | null
  options: {
    skipScreenshots: boolean
    skipPortscan: boolean
    skipVulnScan: boolean
  }
}
