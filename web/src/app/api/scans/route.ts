import { NextResponse } from 'next/server'
import { listScans } from '@/lib/results'
import { listJobs, listProjects } from '@/lib/app-data'

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const projectId = searchParams.get('project') || undefined

  try {
    return NextResponse.json({
      projects: listProjects(),
      scans: listScans(projectId),
      jobs: listJobs(),
    })
  } catch {
    return NextResponse.json({
      projects: [],
      scans: [],
      jobs: [],
    })
  }
}
