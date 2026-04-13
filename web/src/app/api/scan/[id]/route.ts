import { NextResponse } from 'next/server'
import { deleteScan, getScan } from '@/lib/results'

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = getScan(id)
  if (!data) return NextResponse.json({ error: 'Not found' }, { status: 404 })
  return NextResponse.json(data)
}

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const ok = deleteScan(id)
  if (!ok) return NextResponse.json({ error: 'Scan not found' }, { status: 404 })
  return NextResponse.json({ ok: true })
}
