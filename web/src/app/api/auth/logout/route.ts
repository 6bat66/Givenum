import { NextResponse } from 'next/server'

const COOKIE_NAME = 'givenum_session'

export async function POST() {
  const res = NextResponse.json({ ok: true })
  res.cookies.set(COOKIE_NAME, '', { maxAge: 0, path: '/' })
  return res
}
