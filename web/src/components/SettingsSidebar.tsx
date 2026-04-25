'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV = [
  { href: '/settings/apis',    label: 'API Keys',    icon: '🔑' },
  { href: '/settings/proxy',   label: 'Proxy',       icon: '🌐' },
  { href: '/settings/tools',   label: 'Tools',       icon: '🔧' },
  { href: '/settings/reports', label: 'Reports',     icon: '📄' },
]

export default function SettingsSidebar() {
  const pathname = usePathname()

  return (
    <nav className="flex flex-col gap-0.5 py-2">
      {NAV.map(({ href, label, icon }) => {
        const active = pathname === href || pathname.startsWith(href + '/')
        return (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm transition-colors"
            style={{
              background: active ? 'rgba(135,88,216,0.14)' : 'transparent',
              color: active ? 'var(--purple-bright)' : 'var(--text-muted)',
              border: active ? '1px solid rgba(135,88,216,0.22)' : '1px solid transparent',
              textDecoration: 'none',
              fontWeight: active ? 600 : 400,
            }}
          >
            <span style={{ fontSize: '14px' }}>{icon}</span>
            <span>{label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
