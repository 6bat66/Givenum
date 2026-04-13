import { NextResponse } from 'next/server'
import { maskApiKeys, readApiKeys, writeApiKeys } from '@/lib/app-data'

export async function GET() {
  return NextResponse.json({
    keys: maskApiKeys(readApiKeys()),
  })
}

export async function PUT(req: Request) {
  const body = await req.json()
  const keys = typeof body?.keys === 'object' && body.keys !== null ? body.keys : {}
  writeApiKeys(keys as Record<string, string>)
  return NextResponse.json({
    ok: true,
    keys: maskApiKeys(readApiKeys()),
  })
}
