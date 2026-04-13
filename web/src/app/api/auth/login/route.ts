import crypto from 'crypto'
import { NextResponse } from 'next/server'

const COOKIE_NAME = 'givenum_session'
const AUTH_PAYLOAD = 'givenum-auth-v1'
const COOKIE_MAX_AGE = 60 * 60 * 24 * 30 // 30 days

function signToken(secret: string): string {
  return crypto
    .createHmac('sha256', secret)
    .update(AUTH_PAYLOAD)
    .digest('base64url')
}

export async function POST(req: Request) {
  const password = process.env.GIVENUM_PASSWORD
  if (!password) {
    // Auth disabled — nothing to do
    return NextResponse.json({ ok: true })
  }

  let body: { password?: string } = {}
  try { body = await req.json() } catch { /* empty body */ }

  const input = String(body?.password ?? '')

  // Constant-time comparison
  const inputBuf = Buffer.from(input)
  const passwordBuf = Buffer.from(password)
  const safeLength = Math.max(inputBuf.length, passwordBuf.length)
  const paddedInput = Buffer.concat([inputBuf, Buffer.alloc(safeLength - inputBuf.length)])
  const paddedPassword = Buffer.concat([passwordBuf, Buffer.alloc(safeLength - passwordBuf.length)])

  const match = crypto.timingSafeEqual(paddedInput, paddedPassword) && inputBuf.length === passwordBuf.length

  if (!match) {
    return NextResponse.json({ error: 'Senha incorreta' }, { status: 401 })
  }

  const token = signToken(password)
  const forwardedProto = req.headers.get('x-forwarded-proto')?.split(',')[0]?.trim()
  const isSecureRequest = new URL(req.url).protocol === 'https:' || forwardedProto === 'https'

  const res = NextResponse.json({ ok: true })
  res.cookies.set(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: isSecureRequest,
    maxAge: COOKIE_MAX_AGE,
    path: '/',
  })
  return res
}
