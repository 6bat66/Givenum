import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const COOKIE_NAME = 'givenum_session'
const AUTH_PAYLOAD = 'givenum-auth-v1'

// Runs in Edge runtime — uses Web Crypto API (no Node crypto here)
async function signToken(secret: string): Promise<string> {
  const enc = new TextEncoder()
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(AUTH_PAYLOAD))
  return btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
}

async function isValidToken(token: string, secret: string): Promise<boolean> {
  const expected = await signToken(secret)
  if (token.length !== expected.length) return false
  // Constant-time comparison via subtle
  const enc = new TextEncoder()
  const a = enc.encode(token)
  const b = enc.encode(expected)
  if (a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i]
  return diff === 0
}

export async function middleware(req: NextRequest) {
  const password = process.env.GIVENUM_PASSWORD
  // Auth disabled when no password is configured (local dev)
  if (!password) return NextResponse.next()

  const { pathname } = req.nextUrl

  // Always allow login page and auth API
  if (pathname === '/login' || pathname.startsWith('/api/auth/')) {
    return NextResponse.next()
  }

  const token = req.cookies.get(COOKIE_NAME)?.value
  if (token && await isValidToken(token, password)) {
    return NextResponse.next()
  }

  // Redirect API calls to 401 instead of login page
  if (pathname.startsWith('/api/')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const loginUrl = req.nextUrl.clone()
  loginUrl.pathname = '/login'
  loginUrl.searchParams.set('next', pathname)
  return NextResponse.redirect(loginUrl)
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
