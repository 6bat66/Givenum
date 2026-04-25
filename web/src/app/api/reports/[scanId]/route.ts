import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'
import { resolveScanDir, getScan } from '@/lib/results'
import { generateHtmlReport } from '@/lib/report'

export const dynamic = 'force-dynamic'

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ scanId: string }> }
) {
  const { scanId } = await params
  const data = getScan(scanId)
  if (!data) return NextResponse.json({ error: 'Scan not found' }, { status: 404 })

  const html = generateHtmlReport(data)
  const scanDir = resolveScanDir(scanId)!
  const reportFile = path.join(scanDir, 'report.html')
  fs.writeFileSync(reportFile, html, 'utf-8')

  return NextResponse.json({ ok: true, filename: 'report.html' })
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ scanId: string }> }
) {
  const { scanId } = await params
  const scanDir = resolveScanDir(scanId)
  if (!scanDir) return NextResponse.json({ error: 'Scan not found' }, { status: 404 })

  const reportFile = path.join(scanDir, 'report.html')
  if (!fs.existsSync(reportFile)) {
    return NextResponse.json({ error: 'Report not generated yet' }, { status: 404 })
  }

  const html = fs.readFileSync(reportFile, 'utf-8')
  return new NextResponse(html, {
    status: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
  })
}
