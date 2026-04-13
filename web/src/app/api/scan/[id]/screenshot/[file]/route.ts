import { NextResponse } from 'next/server'
import { resolveScanDir } from '@/lib/results'
import path from 'path'
import fs from 'fs'

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string; file: string }> }
) {
  const { id, file } = await params

  const scanDir = resolveScanDir(id)
  if (!scanDir) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  // Prevent path traversal
  const safeName = path.basename(file)
  const filePath = path.join(scanDir, 'screenshots', safeName)

  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  const ext = path.extname(safeName).toLowerCase()
  const contentType = ext === '.png' ? 'image/png'
    : ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg'
    : ext === '.webp' ? 'image/webp'
    : 'application/octet-stream'

  const buffer = fs.readFileSync(filePath)
  return new NextResponse(buffer, {
    headers: { 'Content-Type': contentType, 'Cache-Control': 'public, max-age=3600' },
  })
}
