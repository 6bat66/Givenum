'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useRef, useState } from 'react'

function LoginForm() {
  const router = useRouter()
  const params = useSearchParams()
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const password = inputRef.current?.value ?? ''
    if (!password) return

    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })

      if (res.ok) {
        const next = params.get('next') || '/'
        router.replace(next)
      } else {
        const data = await res.json()
        setError(data.error || 'Senha incorreta')
        if (inputRef.current) {
          inputRef.current.value = ''
          inputRef.current.focus()
        }
      }
    } catch {
      setError('Erro de conexão')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--bg)' }}>
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl mb-4"
            style={{ background: 'linear-gradient(135deg, #0891b2, #4f46e5)' }}>
            <span className="text-xl font-bold text-white">G</span>
          </div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text)' }}>GivEnum</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Insira a senha para acessar o dashboard</p>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div>
            <input
              ref={inputRef}
              type="password"
              placeholder="Senha"
              autoFocus
              required
              className="w-full px-4 py-3 rounded-xl text-sm outline-none"
              style={{
                background: 'var(--surface)',
                border: `1px solid ${error ? '#7f1d1d' : 'var(--border)'}`,
                color: 'var(--text)',
              }}
            />
          </div>

          {error && (
            <div className="text-sm px-3 py-2 rounded-lg" style={{ background: '#450a0a', color: '#fca5a5', border: '1px solid #7f1d1d' }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl text-sm font-semibold transition-opacity"
            style={{
              background: 'linear-gradient(135deg, #0891b2, #4f46e5)',
              color: '#fff',
              opacity: loading ? 0.7 : 1,
            }}>
            {loading ? 'Autenticando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}
