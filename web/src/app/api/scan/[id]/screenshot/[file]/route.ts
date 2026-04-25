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
  const ext = path.extname(safeName).toLowerCase()

  // Whitelist image extensions only — never let this route serve .env, .log,
  // or anything else that might land in the screenshots dir.
  const ALLOWED: Record<string, string> = {
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
    '.gif':  'image/gif',
  }
  const contentType = ALLOWED[ext]
  if (!contentType) {
    return NextResponse.json({ error: 'Unsupported file type' }, { status: 400 })
  }

  const filePath = path.join(scanDir, 'screenshots', safeName)

  // Defense-in-depth: confirm the resolved path stays inside the screenshots dir.
  const screenshotsDir = path.resolve(scanDir, 'screenshots')
  const resolved = path.resolve(filePath)
  if (!resolved.startsWith(screenshotsDir + path.sep)) {
    return NextResponse.json({ error: 'Invalid path' }, { status: 400 })
  }

  if (!fs.existsSync(resolved)) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  const buffer = fs.readFileSync(resolved)
  return new NextResponse(buffer, {
    headers: { 'Content-Type': contentType, 'Cache-Control': 'public, max-age=3600' },
  })
}
