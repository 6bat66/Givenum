import fs from 'fs'
import path from 'path'
import { spawn } from 'child_process'
import { NextResponse } from 'next/server'
import { createJob, getConfigDir, getJobFile, getProject, getProjectOutputDir, getResultsDir, getWorkspaceRoot } from '@/lib/app-data'

const DOMAIN_PATTERN = /^(?:\*\.)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$/

export async function POST(req: Request) {
  const body = await req.json()
  const domain = String(body?.domain || '').trim().toLowerCase()
  const projectId = String(body?.projectId || 'default').trim()
  const mode = body?.mode === 'active' ? 'active' : 'passive'
  const options = {
    skipScreenshots: Boolean(body?.options?.skipScreenshots),
    skipPortscan: Boolean(body?.options?.skipPortscan),
    skipVulnScan: Boolean(body?.options?.skipVulnScan),
  }

  if (!DOMAIN_PATTERN.test(domain)) {
    return NextResponse.json({ error: 'Invalid domain' }, { status: 400 })
  }

  const project = getProject(projectId)
  if (!project) {
    return NextResponse.json({ error: 'Unknown project' }, { status: 404 })
  }

  const outputBaseDir = getProjectOutputDir(project.id)
  const logDir = path.join(getConfigDir(), 'job-logs')
  fs.mkdirSync(logDir, { recursive: true })

  const job = createJob({
    projectId: project.id,
    projectName: project.name,
    domain,
    mode,
    status: 'queued',
    startedAt: null,
    endedAt: null,
    outputBaseDir,
    scanId: null,
    scanDir: null,
    logFile: path.join(logDir, `${Date.now()}-${domain.replace(/[^a-z0-9.-]/g, '_')}.log`),
    analysisFile: null,
    returnCode: null,
    options,
  })

  const workspaceRoot = getWorkspaceRoot()
  const runnerScript = path.join(workspaceRoot, 'scan_runner.py')
  const scannerScript = path.join(workspaceRoot, 'GivEnum.py')
  const analyzerScript = path.join(workspaceRoot, 'analyze_results.py')

  const child = spawn('python3', [
    runnerScript,
    '--job-file', getJobFile(job.id),
    '--scanner-script', scannerScript,
    '--analyzer-script', analyzerScript,
    '--domain', domain,
    '--output-dir', outputBaseDir,
    '--config-dir', getConfigDir(),
    '--log-file', job.logFile,
    ...(mode === 'active' ? ['--active'] : []),
    ...(options.skipScreenshots ? ['--skip-screenshots'] : []),
    ...(options.skipPortscan ? ['--skip-portscan'] : []),
    ...(options.skipVulnScan ? ['--skip-vuln-scan'] : []),
  ], {
    cwd: workspaceRoot,
    detached: true,
    stdio: 'ignore',
    env: {
      ...process.env,
      RESULTS_DIR: getResultsDir(),
      GIVENUM_CONFIG_DIR: getConfigDir(),
      GIVENUM_ROOT_DIR: workspaceRoot,
    },
  })

  child.unref()

  return NextResponse.json(job, { status: 202 })
}
