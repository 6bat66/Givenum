import { NextResponse } from 'next/server'
import fs from 'fs'
import { getToolsUpdateLogFile } from '@/lib/tools'

export const dynamic = 'force-dynamic'

export async function GET() {
  const logFile = getToolsUpdateLogFile()
  try {
    const content = fs.existsSync(logFile) ? fs.readFileSync(logFile, 'utf-8') : ''
    const done = content.includes('[FND] all updates complete')
    return NextResponse.json({ content, done })
  } catch {
    return NextResponse.json({ content: '', done: false })
  }
}
