import fs from 'fs'
import { NextResponse } from 'next/server'
import { getJob } from '@/lib/app-data'

function getTailContent(content: string, tail: number) {
  if (tail <= 0 || content.length <= tail) {
    return { content, truncated: false }
  }

  return {
    content: content.slice(-tail),
    truncated: true,
  }
}

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const job = getJob(id)
  if (!job) {
    return NextResponse.json({ error: 'Job not found' }, { status: 404 })
  }

  if (!job.logFile || !fs.existsSync(job.logFile)) {
    return NextResponse.json({ error: 'Log not found' }, { status: 404 })
  }

  const url = new URL(req.url)
  const format = url.searchParams.get('format')
  const tail = Number(url.searchParams.get('tail') || '0')
  const offset = Number(url.searchParams.get('offset') || '0')
  const stat = fs.statSync(job.logFile)
  const fileSize = stat.size

  // Incremental fetch: only read bytes after offset
  let rawContent: string
  if (offset > 0 && offset < fileSize) {
    const buf = Buffer.alloc(fileSize - offset)
    const fd = fs.openSync(job.logFile, 'r')
    fs.readSync(fd, buf, 0, buf.length, offset)
    fs.closeSync(fd)
    rawContent = buf.toString('utf-8')
  } else if (offset >= fileSize) {
    rawContent = ''
  } else {
    rawContent = fs.readFileSync(job.logFile, 'utf-8')
  }
  const { content, truncated } = getTailContent(rawContent, Number.isFinite(tail) ? tail : 0)

  if (format === 'json') {
    return NextResponse.json({
      content,
      truncated,
      size: fileSize,
      status: job.status,
      updatedAt: stat.mtime.toISOString(),
    }, {
      headers: {
        'Cache-Control': 'no-store',
      },
    })
  }

  return new NextResponse(content, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  })
}
