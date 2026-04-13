'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'

export default function LogoutButton() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  async function handleLogout() {
    setLoading(true)
    try {
      await fetch('/api/auth/logout', { method: 'POST' })
    } finally {
      setLoading(false)
    }
    router.replace('/login')
  }

  return (
    <button
      type="button"
      disabled={loading}
      onClick={() => void handleLogout()}
      className="text-sm transition-colors hover:text-white"
      style={{ color: 'var(--text-muted)' }}>
      {loading ? '...' : 'Sair'}
    </button>
  )
}
