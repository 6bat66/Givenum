import { NextResponse } from 'next/server'
import { listScans } from '@/lib/results'
import { listJobs, listProjects } from '@/lib/app-data'

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const projectId = searchParams.get('project') || undefined

  return NextResponse.json({
    projects: listProjects(),
    scans: listScans(projectId),
    jobs: listJobs(),
  })
}
