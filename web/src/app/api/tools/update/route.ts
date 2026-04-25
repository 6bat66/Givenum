import { NextResponse } from 'next/server'
import { spawn } from 'child_process'
import fs from 'fs'
import path from 'path'
import os from 'os'
import { TOOL_REGISTRY, getToolsUpdateLogFile } from '@/lib/tools'

export const dynamic = 'force-dynamic'

/**
 * POST /api/tools/update
 *
 * Body: { tools?: string[] }   // names to install; empty / missing = all
 *
 * Spawns a detached Node orchestrator that runs each tool's installer with
 * `execFile`-style argv (no shell). Output is appended live to the log file
 * polled by the front-end.
 *
 * Why a Node orchestrator (not a shell script)?
 * The previous implementation generated a shell script on disk and ran it via
 * `sh -c`. Even though tool data comes from a hard-coded registry, the pattern
 * was fragile — anyone adding a registry entry from external input would have
 * created a command-injection sink. Spawning each installer with argv array
 * removes the shell from the loop entirely.
 */
export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as { tools?: string[] }
  const names = Array.isArray(body.tools) && body.tools.length > 0
    ? body.tools
    : TOOL_REGISTRY.map((t) => t.name)

  const tools = TOOL_REGISTRY.filter((t) => names.includes(t.name))
  if (tools.length === 0) {
    return NextResponse.json({ error: 'No matching tools' }, { status: 400 })
  }

  const logFile = getToolsUpdateLogFile()
  // Truncate the log so the UI starts from a clean slate.
  fs.writeFileSync(logFile, '')

  // Plan the runs as plain data — no shell, no string interpolation.
  const plan = tools.map((t) => ({ name: t.name, installer: t.installer }))

  // Generate a tiny self-contained Node script. The plan is embedded as JSON,
  // which is a safe JS literal for any string content.
  const orchestrator = `
const fs = require('fs')
const { spawn } = require('child_process')

const PLAN = ${JSON.stringify(plan)}
const LOG  = ${JSON.stringify(logFile)}

function append(line) {
  try { fs.appendFileSync(LOG, line) } catch (_) { /* best-effort */ }
}

function runOne({ name, installer }) {
  return new Promise((resolve) => {
    const [cmd, ...args] = installer
    append('\\n[INF] updating ' + name + '... (' + cmd + ' ' + args.join(' ') + ')\\n')
    const child = spawn(cmd, args, { env: process.env })
    child.stdout.on('data', (chunk) => append(chunk.toString()))
    child.stderr.on('data', (chunk) => append(chunk.toString()))
    child.on('error', (err) => {
      append('[ERR] ' + name + ': ' + err.message + '\\n')
      resolve(1)
    })
    child.on('exit', (code) => {
      append('[FND] ' + name + ' done (rc=' + (code ?? 'null') + ')\\n')
      resolve(code ?? 1)
    })
  })
}

;(async () => {
  append('[RUN] starting update of ' + PLAN.length + ' tool(s)...\\n')
  let failed = 0
  for (const item of PLAN) {
    const code = await runOne(item)
    if (code !== 0) failed++
  }
  append('\\n[FND] all updates complete (' + (PLAN.length - failed) + ' ok, ' + failed + ' failed)\\n')
})()
`.trim()

  // Drop the orchestrator in the OS temp dir; mode 600.
  const scriptPath = path.join(os.tmpdir(), `givenum-tools-${process.pid}-${Date.now()}.js`)
  fs.writeFileSync(scriptPath, orchestrator, { mode: 0o600 })

  const child = spawn('node', [scriptPath], {
    detached: true,
    stdio: 'ignore',
    env: {
      ...process.env,
      PATH: process.env.PATH ?? '/usr/local/go/bin:/root/go/bin:/usr/local/bin:/usr/bin:/bin',
    },
  })
  child.unref()

  return NextResponse.json({ ok: true, logFile, tools: tools.map((t) => t.name) })
}
