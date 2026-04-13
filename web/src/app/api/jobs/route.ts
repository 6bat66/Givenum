import { NextResponse } from 'next/server'
import { listJobs } from '@/lib/app-data'

export async function GET() {
  try {
    return NextResponse.json(listJobs())
  } catch {
    return NextResponse.json([])
  }
}
