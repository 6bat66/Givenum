import { NextResponse } from 'next/server'
import { listJobs } from '@/lib/app-data'

export async function GET() {
  return NextResponse.json(listJobs())
}
