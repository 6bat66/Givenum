import fs from 'fs'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import JobLogViewer from '@/components/JobLogViewer'
import { getJob } from '@/lib/app-data'

export const dynamic = 'force-dynamic'

function readInitialLog(logFile: string) {
  if (!logFile || !fs.existsSync(logFile)) {
    return ''
  }

  const content = fs.readFileSync(logFile, 'utf-8')
  return content.length > 400000 ? content.slice(-400000) : content
}

export default async function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const job = getJob(id)

  if (!job) {
    notFound()
  }

  return (
    <div className="max-w-screen-2xl mx-auto px-6 py-6">
      <div className="flex items-center gap-2 text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
        <Link href="/" className="hover:text-white transition-colors">Dashboard</Link>
        <span>/</span>
        <span style={{ color: 'var(--text)' }}>Job {job.id.slice(0, 8)}</span>
      </div>

      <JobLogViewer initialJob={job} initialLog={readInitialLog(job.logFile)} />
    </div>
  )
}
