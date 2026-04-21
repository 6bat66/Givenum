import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'
import { resolveScanDir } from '@/lib/results'

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string; tool: string }> }
) {
  const { id, tool } = await params

  // Sanitize tool name — only allow word chars and hyphens
  if (!/^[\w-]+$/.test(tool)) {
    return NextResponse.json({ error: 'Invalid tool name' }, { status: 400 })
  }

  const scanDir = resolveScanDir(id)
  if (!scanDir) return NextResponse.json({ error: 'Scan not found' }, { status: 404 })

  const logFile = path.join(scanDir, 'logs', `${tool}.log`)

  if (!fs.existsSync(logFile)) {
    return new NextResponse('', { status: 200, headers: { 'Content-Type': 'text/plain' } })
  }

  const content = fs.readFileSync(logFile, 'utf-8')
  return new NextResponse(content, { status: 200, headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
}
