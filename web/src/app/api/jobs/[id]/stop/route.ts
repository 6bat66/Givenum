import { NextResponse } from 'next/server'
import { getJob, writeJob } from '@/lib/app-data'

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const job = getJob(id)

  if (!job) {
    return NextResponse.json({ error: 'Job not found' }, { status: 404 })
  }

  if (job.status !== 'running' && job.status !== 'paused') {
    return NextResponse.json({ error: 'Job is not running' }, { status: 409 })
  }

  if (!job.pid) {
    return NextResponse.json({ error: 'No PID found for job' }, { status: 500 })
  }

  try {
    if (job.status === 'paused') {
      process.kill(job.pid, 'SIGCONT')
    }
    process.kill(job.pid, 'SIGTERM')
  } catch {
    // Process may have already exited
  }

  writeJob({ ...job, status: 'stopped', endedAt: new Date().toISOString(), pid: null })
  return NextResponse.json({ ok: true })
}
