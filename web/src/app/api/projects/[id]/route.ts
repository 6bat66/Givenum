import { NextResponse } from 'next/server'
import { deleteProject, getProject } from '@/lib/app-data'

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const project = getProject(id)
  if (!project) return NextResponse.json({ error: 'Not found' }, { status: 404 })
  return NextResponse.json(project)
}

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  const project = getProject(id)
  if (!project) return NextResponse.json({ error: 'Project not found' }, { status: 404 })

  const ok = deleteProject(id)
  if (!ok) return NextResponse.json({ error: 'Falha ao apagar projeto' }, { status: 500 })
  return NextResponse.json({ ok: true })
}
