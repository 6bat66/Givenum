import { NextResponse } from 'next/server'
import { getJob, writeJob } from '@/lib/app-data'

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const job = getJob(id)

  if (!job) {
    return NextResponse.json({ error: 'Job not found' }, { status: 404 })
  }

  if (job.status !== 'paused') {
    return NextResponse.json({ error: 'Job is not paused' }, { status: 409 })
  }

  if (!job.pid) {
    return NextResponse.json({ error: 'No PID found for job' }, { status: 500 })
  }

  try {
    process.kill(job.pid, 'SIGCONT')
  } catch {
    return NextResponse.json({ error: 'Failed to resume process' }, { status: 500 })
  }

  writeJob({ ...job, status: 'running' })
  return NextResponse.json({ ok: true })
}
