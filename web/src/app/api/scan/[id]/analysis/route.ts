import fs from 'fs'
import path from 'path'
import { NextResponse } from 'next/server'
import { resolveScanDir } from '@/lib/results'

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const scanDir = resolveScanDir(id)
  if (!scanDir) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  const analysisFile = path.join(scanDir, 'reports', 'analysis.md')
  if (!fs.existsSync(analysisFile)) {
    return NextResponse.json({ error: 'Analysis not found' }, { status: 404 })
  }

  return new NextResponse(fs.readFileSync(analysisFile, 'utf-8'), {
    headers: {
      'Content-Type': 'text/markdown; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  })
}
