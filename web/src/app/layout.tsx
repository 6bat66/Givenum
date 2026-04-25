import type { Metadata } from 'next'
import Link from 'next/link'
import LogoutButton from '@/components/LogoutButton'
import './globals.css'

export const metadata: Metadata = {
  title: 'GivEnum',
  description: 'Web Enumeration Results Dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen" style={{ background: 'var(--bg)' }}>
        <header
          className="sticky top-0 z-50"
          style={{
            background: 'rgba(8,8,11,0.86)',
            borderBottom: '1px solid var(--border)',
            backdropFilter: 'blur(12px)',
            boxShadow: '0 10px 35px rgba(0,0,0,0.35)',
          }}>
          <div className="max-w-screen-2xl mx-auto px-5 h-12 md:h-14 flex items-center justify-between">
            {/* ❯ givenum — neon purple prompt */}
            <Link href="/" className="flex items-center gap-1.5 group">
              <span style={{
                color: 'var(--purple)',
                fontWeight: 700,
                fontSize: '17px',
                textShadow: '0 0 6px rgba(135,88,216,0.28)',
              }}>❯</span>
              <span style={{
                color: 'var(--text)',
                fontWeight: 700,
                letterSpacing: '-0.3px',
                fontSize: '15px',
              }}>givenum</span>
            </Link>

            {/* nav */}
            <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
              <Link href="/" className="ghost-button px-3 py-1.5 text-sm transition-colors" style={{ textDecoration: 'none' }}>dashboard</Link>
              <Link href="/#active-jobs" className="ghost-button px-3 py-1.5 text-sm transition-colors" style={{ textDecoration: 'none' }}>active</Link>
              <Link href="/settings" className="ghost-button px-3 py-1.5 text-sm transition-colors" style={{ textDecoration: 'none' }}>settings</Link>
              <a
                href="https://github.com/6bat66/Givenum"
                target="_blank"
                rel="noopener"
                className="ghost-button px-3 py-1.5 text-sm transition-colors flex items-center gap-1"
                style={{ textDecoration: 'none' }}>
                <svg width="13" height="13" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
                </svg>
                github
              </a>
              {process.env.GIVENUM_PASSWORD && <LogoutButton />}
            </div>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  )
}
