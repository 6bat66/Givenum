import { NextResponse } from 'next/server'
import { deleteJob, getJob } from '@/lib/app-data'

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const job = getJob(id)

  if (!job) {
    return NextResponse.json({ error: 'Job not found' }, { status: 404 })
  }

  return NextResponse.json(job, {
    headers: {
      'Cache-Control': 'no-store',
    },
  })
}

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const job = getJob(id)

  if (!job) {
    return NextResponse.json({ error: 'Job not found' }, { status: 404 })
  }

  if (job.status === 'running' || job.status === 'queued') {
    return NextResponse.json({ error: 'Cannot delete a running job. Stop it first.' }, { status: 409 })
  }

  deleteJob(id)
  return NextResponse.json({ ok: true })
}
