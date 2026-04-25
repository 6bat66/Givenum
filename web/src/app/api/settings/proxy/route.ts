import { NextResponse } from 'next/server'
import { readProxyConfig, writeProxyConfig } from '@/lib/app-data'
import type { ProxyConfig } from '@/lib/types'

export async function GET() {
  return NextResponse.json(readProxyConfig())
}

export async function PUT(req: Request) {
  const body = await req.json() as Partial<ProxyConfig>
  const current = readProxyConfig()
  const cfg: ProxyConfig = {
    ...current,
    enabled:  Boolean(body.enabled),
    mode:     (body.mode === 'rotate' ? 'rotate' : 'single'),
    http:     String(body.http    ?? '').trim(),
    https:    String(body.https   ?? '').trim(),
    noProxy:  String(body.noProxy ?? '').trim(),
    // proxies list is managed by the fetch endpoint, not this one
    proxies:  current.proxies,
    lastFetched: current.lastFetched,
  }
  writeProxyConfig(cfg)
  return NextResponse.json({ ok: true, config: cfg })
}
