import { NextResponse } from 'next/server'
import { createProject, listProjects } from '@/lib/app-data'

export async function GET() {
  return NextResponse.json(listProjects())
}

export async function POST(req: Request) {
  const body = await req.json()
  const name = String(body?.name || '').trim()
  const description = String(body?.description || '').trim()

  if (!name) {
    return NextResponse.json({ error: 'Project name is required' }, { status: 400 })
  }

  const project = createProject({ name, description })
  return NextResponse.json(project, { status: 201 })
}
