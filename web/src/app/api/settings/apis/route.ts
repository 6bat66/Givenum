import { NextResponse } from 'next/server'
import { maskApiKeys, readApiKeys, writeApiKeys } from '@/lib/app-data'

export async function GET() {
  return NextResponse.json({
    keys: maskApiKeys(readApiKeys()),
  })
}

export async function PUT(req: Request) {
  const body = await req.json()
  const incoming = typeof body?.keys === 'object' && body.keys !== null
    ? body.keys as Record<string, string>
    : {}

  // Read the current (unmasked) keys so we can preserve any that came back
  // as masked values (••••) — those should not overwrite the real key.
  const current = readApiKeys()
  const merged: Record<string, string> = { ...current }

  for (const [k, v] of Object.entries(incoming)) {
    const val = String(v ?? '').trim()
    // Skip if this is a masked sentinel (contains ••) — user didn't change it
    if (val.includes('••')) continue
    if (val.length > 0) {
      merged[k] = val
    } else {
      delete merged[k]   // empty string = clear the key
    }
  }

  writeApiKeys(merged)
  return NextResponse.json({
    ok: true,
    keys: maskApiKeys(readApiKeys()),
  })
}
