'use client'

import Image from 'next/image'
import { useState, useMemo } from 'react'
import type { ScanData } from '@/lib/types'

// ── Utility components ──────────────────────────────────────

function Badge({ children, className = '', style = {} }: {
  children: React.ReactNode; className?: string; style?: React.CSSProperties
}) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`} style={style}>
      {children}
    </span>
  )
}

/**
 * Decode a gowitness screenshot filename back to its origin URL.
 * Always includes the port so callers can show it explicitly.
 */
function decodeScreenshotTarget(filename: string): { url: string; port: string } | null {
  const stem = filename.replace(/\.(png|jpg|jpeg|webp)$/i, '')
  const scheme = stem.startsWith('https---') ? 'https' : stem.startsWith('http---') ? 'http' : null
  if (!scheme) return null
  const rest = stem.slice(scheme.length + 3)
  const lastDash = rest.lastIndexOf('-')
  if (lastDash <= 0) return { url: `${scheme}://${rest}`, port: '' }
  const host = rest.slice(0, lastDash)
  const port = rest.slice(lastDash + 1)
  if (!host) return null
  return { url: `${scheme}://${host}:${port}`, port }
}

/** Return true if the URL's hostname belongs to the target scan domain. */
function isTargetHost(url: string, domain: string): boolean {
  try {
    const { hostname } = new URL(url)
    return hostname === domain || hostname.endsWith(`.${domain}`)
  } catch {
    return true // unparseable → keep
  }
}

function SevBadge({ sev }: { sev: string }) {
  return <Badge className={`sev-${sev}`}>{sev.toUpperCase()}</Badge>
}

function StatusBadge({ code }: { code: number }) {
  const cls = code >= 200 && code < 300 ? { bg: '#052e16', color: '#86efac' }
    : code >= 300 && code < 400 ? { bg: '#082f49', color: '#7dd3fc' }
    : code >= 400 && code < 500 ? { bg: '#422006', color: '#fcd34d' }
    : { bg: '#450a0a', color: '#fca5a5' }
  return <Badge style={{ background: cls.bg, color: cls.color }}>{code || '—'}</Badge>
}

function SearchInput({ placeholder, onChange }: { placeholder: string; onChange: (v: string) => void }) {
  return (
    <input
      type="text"
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="w-full sm:w-auto text-sm px-3 py-1.5 rounded-lg outline-none focus:ring-1"
      style={{
        background: 'var(--surface-2)',
        border: '1px solid var(--border)',
        color: 'var(--text)',
        minWidth: 0,
      }}
    />
  )
}

function EmptyState({ icon, text, hint }: { icon: string; text: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-4xl mb-3">{icon}</div>
      <p style={{ color: 'var(--text-muted)' }}>{text}</p>
      {hint && <p className="text-xs mt-1" style={{ color: 'var(--text-subtle)' }}>{hint}</p>}
    </div>
  )
}

function Card({ title, children, accent }: {
  title?: string; children: React.ReactNode; accent?: string
}) {
  return (
    <div className="rounded-xl overflow-hidden"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderLeft: accent ? `3px solid ${accent}` : undefined,
      }}>
      {title && (
        <div className="px-5 py-3 border-b text-sm font-medium" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
          {title}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  )
}

// ── Tab: Summary ─────────────────────────────────────────────

function SummaryTab({ data }: { data: ScanData }) {
  const totalVulns = Object.values(data.nuclei).flat().length
  const hasTakeover = data.subjack.length + data.subzy.length > 0
  const hasCloud = data.cloudAws.length + data.cloudAzure.length + data.cloudGcp.length > 0
  const hasHeaderIssues = data.securityHeaders.length > 0 || data.emailSecurity.length > 0 || data.corsFindings.length > 0

  return (
    <div className="grid md:grid-cols-2 gap-4">
      {/* Technologies */}
      {data.topTech.length > 0 && (
        <Card title="Technologies Detected">
          <div className="space-y-2">
            {data.topTech.map(([tech, count]) => (
              <div key={tech} className="flex items-center justify-between text-sm">
                <span style={{ color: 'var(--text)' }}>{tech}</span>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 rounded-full" style={{
                    width: `${Math.min((count / data.topTech[0][1]) * 80, 80)}px`,
                    background: 'var(--cyan)',
                    opacity: 0.5,
                  }} />
                  <span className="font-mono text-xs w-4 text-right" style={{ color: 'var(--text-muted)' }}>{count}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="space-y-4">
        {/* Findings summary */}
        {totalVulns > 0 && (
          <Card title="Vulnerability Summary" accent="var(--red)">
            <div className="flex flex-wrap gap-2">
              {(['critical', 'high', 'medium', 'low', 'info'] as const).map((sev) =>
                data.nuclei[sev].length > 0 ? (
                  <div key={sev} className="flex items-center gap-2 text-sm">
                    <SevBadge sev={sev} />
                    <span className="font-mono" style={{ color: 'var(--text)' }}>{data.nuclei[sev].length}</span>
                  </div>
                ) : null
              )}
            </div>
          </Card>
        )}

        {/* Exposed Git */}
        {data.gitExposed.length > 0 && (
          <Card title={`Exposed Git (${data.gitExposed.length})`} accent="var(--red)">
            <div className="space-y-1">
              {data.gitExposed.slice(0, 8).map((item) => (
                <div key={item} className="text-xs font-mono truncate" style={{ color: '#fca5a5' }}>{item}</div>
              ))}
              {data.gitExposed.length > 8 && (
                <div className="text-xs" style={{ color: 'var(--text-subtle)' }}>+{data.gitExposed.length - 8} more</div>
              )}
            </div>
          </Card>
        )}

        {/* Takeover */}
        {hasTakeover && (
          <Card title="Takeover Candidates" accent="var(--orange)">
            <div className="space-y-1">
              {[...data.subjack, ...data.subzy].slice(0, 8).map((item) => (
                <div key={item} className="text-xs font-mono truncate" style={{ color: '#fdba74' }}>{item}</div>
              ))}
            </div>
          </Card>
        )}

        {/* Cloud */}
        {hasCloud && (
          <Card title="Cloud Services">
            {data.cloudAws.length > 0 && (
              <div className="mb-2">
                <div className="text-xs font-semibold mb-1" style={{ color: '#fb923c' }}>AWS ({data.cloudAws.length})</div>
                {data.cloudAws.slice(0, 3).map((i) => (
                  <div key={i} className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{i}</div>
                ))}
              </div>
            )}
            {data.cloudAzure.length > 0 && (
              <div className="mb-2">
                <div className="text-xs font-semibold mb-1" style={{ color: '#7dd3fc' }}>Azure ({data.cloudAzure.length})</div>
                {data.cloudAzure.slice(0, 3).map((i) => (
                  <div key={i} className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{i}</div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* Security header / email quick summary */}
        {hasHeaderIssues && (
          <Card title="Passive Security Checks" accent="var(--cyan)">
            <div className="space-y-1 text-sm">
              {data.emailSecurity.length > 0 && (
                <div className="flex justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>📧 Email (SPF/DMARC)</span>
                  <span className="font-mono font-bold" style={{ color: '#f87171' }}>{data.emailSecurity.length}</span>
                </div>
              )}
              {data.securityHeaders.length > 0 && (
                <div className="flex justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>🔒 Security Headers</span>
                  <span className="font-mono font-bold" style={{ color: '#fb923c' }}>{data.securityHeaders.length}</span>
                </div>
              )}
              {data.corsFindings.length > 0 && (
                <div className="flex justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>🌐 CORS</span>
                  <span className="font-mono font-bold" style={{ color: '#fb923c' }}>{data.corsFindings.length}</span>
                </div>
              )}
            </div>
          </Card>
        )}

        {!totalVulns && !data.gitExposed.length && !hasTakeover && !hasCloud && !hasHeaderIssues && data.topTech.length === 0 && (
          <EmptyState icon="✅" text="No critical findings" hint="Run with --active for deeper analysis" />
        )}
      </div>
    </div>
  )
}

// ── Tab: Subdomains ───────────────────────────────────────────

function SubdomainsTab({ data }: { data: ScanData }) {
  const [query, setQuery]       = useState('')
  const [aliveOnly, setAliveOnly] = useState(false)

  const alive = useMemo(() => new Set(data.hosts.map((h) => {
    try { return new URL(h.url).hostname } catch { return h.url }
  })), [data.hosts])

  const all = useMemo(() => [
    ...data.subdomains.map((s) => ({ sub: s, source: 'passive' as const })),
    ...data.bruteforce.map((s) => ({ sub: s, source: 'bruteforce' as const })),
  ], [data])

  const filtered = useMemo(() => {
    let list = aliveOnly ? all.filter((i) => alive.has(i.sub)) : all
    if (query) list = list.filter((i) => i.sub.toLowerCase().includes(query.toLowerCase()))
    return list
  }, [all, alive, aliveOnly, query])

  const aliveCount = useMemo(() => all.filter(i => alive.has(i.sub)).length, [all, alive])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
          <span className="font-semibold" style={{ color: 'var(--cyan)' }}>{data.subdomains.length}</span> passive
          {data.bruteforce.length > 0 && (
            <> · <span className="font-semibold" style={{ color: 'var(--orange)' }}>{data.bruteforce.length}</span> brute-forced</>
          )}
          {aliveOnly && (
            <> · <span className="font-semibold" style={{ color: 'var(--green)' }}>{filtered.length}</span> showing</>
          )}
        </div>

        {/* alive-only toggle */}
        <button
          type="button"
          onClick={() => setAliveOnly((v) => !v)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors"
          style={{
            background: aliveOnly ? 'rgba(74,222,128,0.12)' : 'var(--surface-2)',
            color: aliveOnly ? 'var(--green)' : 'var(--text-muted)',
            border: `1px solid ${aliveOnly ? 'rgba(74,222,128,0.3)' : 'var(--border)'}`,
            cursor: 'pointer', fontFamily: 'inherit',
          }}>
          <span style={{ fontSize: '10px' }}>●</span>
          alive only
          <span className="font-mono" style={{ opacity: 0.7 }}>({aliveCount})</span>
        </button>

        <div className="ml-auto">
          <SearchInput placeholder="Filter subdomains…" onChange={setQuery} />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon="🔍" text="No matches" hint={aliveOnly ? 'No alive subdomains found' : undefined} />
      ) : (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
          <div className="overflow-y-auto" style={{ maxHeight: '60vh' }}>
            {filtered.map(({ sub, source }) => (
              <div key={sub + source} className="flex items-center justify-between px-4 py-2 text-sm border-b"
                style={{ borderColor: 'var(--border-subtle)' }}>
                <span className="font-mono" style={{ color: source === 'bruteforce' ? 'var(--orange)' : 'var(--text)' }}>
                  {sub}
                </span>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  {alive.has(sub) && (
                    <Badge style={{ background: '#052e16', color: '#86efac' }}>alive</Badge>
                  )}
                  {source === 'bruteforce' && (
                    <Badge style={{ background: '#431407', color: '#fdba74' }}>bf</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tab: HTTP Hosts ───────────────────────────────────────────

type StatusFilter = 'all' | '2xx' | '3xx' | '4xx' | '5xx'

function HostsTab({ data }: { data: ScanData }) {
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  const statusMatch = (code: number, f: StatusFilter) => {
    if (f === 'all') return true
    if (f === '2xx') return code >= 200 && code < 300
    if (f === '3xx') return code >= 300 && code < 400
    if (f === '4xx') return code >= 400 && code < 500
    if (f === '5xx') return code >= 500 && code < 600
    return true
  }

  const filtered = useMemo(() =>
    data.hosts.filter((h) => {
      if (!statusMatch(h.status, statusFilter)) return false
      if (!query) return true
      const q = query.toLowerCase()
      return h.url.toLowerCase().includes(q) ||
        h.title.toLowerCase().includes(q) ||
        h.tech.some((t) => t.toLowerCase().includes(q))
    })
  , [data.hosts, query, statusFilter])

  const STATUS_PILLS: { id: StatusFilter; label: string; bg: string; color: string }[] = [
    { id: 'all', label: 'all',  bg: 'var(--surface-2)', color: 'var(--text-muted)' },
    { id: '2xx', label: '2xx',  bg: '#052e16',          color: '#86efac' },
    { id: '3xx', label: '3xx',  bg: '#082f49',          color: '#7dd3fc' },
    { id: '4xx', label: '4xx',  bg: '#422006',          color: '#fcd34d' },
    { id: '5xx', label: '5xx',  bg: '#450a0a',          color: '#fca5a5' },
  ]

  const countFor = (f: StatusFilter) =>
    f === 'all' ? data.hosts.length : data.hosts.filter((h) => statusMatch(h.status, f)).length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            <span className="font-semibold" style={{ color: 'var(--green)' }}>{data.hosts.length}</span> hosts
          </span>
          <div className="flex gap-1 flex-wrap">
            {STATUS_PILLS.map((p) => {
              const cnt = countFor(p.id)
              if (p.id !== 'all' && cnt === 0) return null
              return (
                <button key={p.id} type="button"
                  onClick={() => setStatusFilter(p.id === statusFilter ? 'all' : p.id)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-semibold transition-colors"
                  style={{
                    background: statusFilter === p.id ? p.bg : 'var(--surface-2)',
                    color: statusFilter === p.id ? p.color : 'var(--text-muted)',
                    border: `1px solid ${statusFilter === p.id ? p.color + '55' : 'var(--border)'}`,
                    cursor: 'pointer', fontFamily: 'inherit',
                  }}>
                  {p.label}
                  <span className="font-mono opacity-75">{cnt}</span>
                </button>
              )
            })}
          </div>
        </div>
        <SearchInput placeholder="Filter hosts…" onChange={setQuery} />
      </div>

      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        <div className="overflow-auto" style={{ maxHeight: '60vh' }}>
          <table className="w-full text-sm">
            <thead style={{ background: 'var(--surface)' }}>
              <tr className="text-left text-xs" style={{ color: 'var(--text-muted)' }}>
                {['URL', 'Status', 'Title', 'Tech'].map((h) => (
                  <th key={h} className="px-4 py-3 font-medium sticky top-0" style={{ background: 'var(--surface)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((host) => (
                <tr key={host.url} className="border-t transition-colors hover:bg-zinc-800/30" style={{ borderColor: 'var(--border-subtle)' }}>
                  <td className="px-4 py-2.5">
                    <a href={host.url} target="_blank" rel="noopener"
                      className="font-mono text-xs truncate block max-w-xs hover:underline"
                      style={{ color: 'var(--cyan)' }}>
                      {host.url}
                    </a>
                  </td>
                  <td className="px-4 py-2.5"><StatusBadge code={host.status} /></td>
                  <td className="px-4 py-2.5 text-xs max-w-xs truncate" style={{ color: 'var(--text-muted)' }}>
                    {host.title || '—'}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {host.tech.slice(0, 3).map((t) => (
                        <Badge key={t} style={{ background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                          {t}
                        </Badge>
                      ))}
                      {host.tech.length > 3 && (
                        <Badge style={{ background: 'var(--surface-2)', color: 'var(--text-subtle)' }}>
                          +{host.tech.length - 3}
                        </Badge>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && <EmptyState icon="🔍" text="No matches" />}
        </div>
      </div>
    </div>
  )
}

// ── Tab: URLs ─────────────────────────────────────────────────

type ProtoFilter = 'all' | 'http' | 'https'
type ExtFilter   = 'all' | '.js' | '.php' | '.json' | '.html' | '.xml' | '.txt' | '.asp' | '.aspx'

const EXT_LIST: ExtFilter[] = ['all', '.js', '.php', '.json', '.html', '.xml', '.txt', '.asp', '.aspx']

function UrlsTab({ data }: { data: ScanData }) {
  const [query, setQuery] = useState('')
  const [showParamsOnly, setShowParamsOnly] = useState(false)
  const [proto, setProto] = useState<ProtoFilter>('all')
  const [ext, setExt] = useState<ExtFilter>('all')

  const source = showParamsOnly ? data.paramUrls : data.urls

  const filtered = useMemo(() => {
    return source.filter((u) => {
      if (proto !== 'all' && !u.startsWith(`${proto}://`)) return false
      if (ext !== 'all') {
        try {
          const pathname = new URL(u).pathname.toLowerCase()
          if (!pathname.endsWith(ext)) return false
        } catch { return false }
      }
      if (query && !u.toLowerCase().includes(query.toLowerCase())) return false
      return true
    })
  }, [source, query, proto, ext])

  const shown = filtered.slice(0, 500)

  // Only show ext pills that have at least 1 match in current source
  const extCounts = useMemo(() => {
    const counts: Partial<Record<ExtFilter, number>> = { all: source.length }
    for (const e of EXT_LIST.slice(1)) {
      counts[e] = source.filter((u) => {
        try { return new URL(u).pathname.toLowerCase().endsWith(e) } catch { return false }
      }).length
    }
    return counts
  }, [source])

  const httpCount  = source.filter((u) => u.startsWith('http://')).length
  const httpsCount = source.filter((u) => u.startsWith('https://')).length

  return (
    <div className="space-y-3">
      {/* ── row 1: stats + params toggle ─────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3 text-sm">
          <span style={{ color: 'var(--text-muted)' }}>
            <span className="font-semibold" style={{ color: 'var(--purple)' }}>{data.urls.length}</span> total ·{' '}
            <span className="font-semibold" style={{ color: 'var(--yellow)' }}>{data.paramUrls.length}</span> with params
          </span>
          <button
            type="button"
            onClick={() => setShowParamsOnly((v) => !v)}
            className="px-2 py-1 rounded text-xs transition-colors"
            style={showParamsOnly
              ? { background: '#1e3a4c', color: 'var(--cyan)', border: '1px solid #0891b2' }
              : { background: 'var(--surface)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
            Params only
          </button>
        </div>
        <SearchInput placeholder="Filter URLs…" onChange={setQuery} />
      </div>

      {/* ── row 2: protocol + extension pills ────────────────────────── */}
      <div className="flex flex-wrap gap-1.5 items-center">
        {/* protocol */}
        {([
          { id: 'all'   as ProtoFilter, label: 'all',   cnt: source.length },
          { id: 'https' as ProtoFilter, label: 'https', cnt: httpsCount },
          { id: 'http'  as ProtoFilter, label: 'http',  cnt: httpCount  },
        ]).filter(p => p.id === 'all' || p.cnt > 0).map((p) => (
          <button key={p.id} type="button"
            onClick={() => setProto(p.id === proto ? 'all' : p.id)}
            className="flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-semibold transition-colors"
            style={{
              background: proto === p.id ? '#0c2a1a' : 'var(--surface-2)',
              color:      proto === p.id ? '#86efac'  : 'var(--text-muted)',
              border:    `1px solid ${proto === p.id ? '#86efac55' : 'var(--border)'}`,
              cursor: 'pointer', fontFamily: 'inherit',
            }}>
            {p.label}
            <span className="font-mono opacity-75">{p.cnt}</span>
          </button>
        ))}

        <span style={{ color: 'var(--border)', fontSize: 10 }}>│</span>

        {/* extensions */}
        {EXT_LIST.filter((e) => e === 'all' || (extCounts[e] ?? 0) > 0).map((e) => (
          <button key={e} type="button"
            onClick={() => setExt(e === ext ? 'all' : e)}
            className="flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-semibold transition-colors"
            style={{
              background: ext === e ? '#1e1a4c' : 'var(--surface-2)',
              color:      ext === e ? '#c084fc'  : 'var(--text-muted)',
              border:    `1px solid ${ext === e ? '#c084fc55' : 'var(--border)'}`,
              cursor: 'pointer', fontFamily: 'inherit',
            }}>
            {e === 'all' ? 'all ext' : e}
            {e !== 'all' && <span className="font-mono opacity-75">{extCounts[e]}</span>}
          </button>
        ))}
      </div>

      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        <div className="overflow-y-auto" style={{ maxHeight: '60vh' }}>
          {shown.map((url) => (
            <div key={url} className="flex items-center px-4 py-1.5 border-b text-xs font-mono transition-colors hover:bg-zinc-800/30"
              style={{ borderColor: 'var(--border-subtle)' }}>
              <a href={url} target="_blank" rel="noopener"
                className="truncate hover:underline" style={{ color: url.includes('?') ? 'var(--yellow)' : 'var(--text-muted)' }}>
                {url}
              </a>
            </div>
          ))}
          {filtered.length > 500 && (
            <div className="px-4 py-3 text-xs text-center" style={{ color: 'var(--text-subtle)' }}>
              Showing 500 of {filtered.length} URLs
            </div>
          )}
          {filtered.length === 0 && <EmptyState icon="🔍" text="No matches" />}
        </div>
      </div>
    </div>
  )
}

// ── Tab: Vulnerabilities ──────────────────────────────────────

function FindingList({ items, borderColor, textColor, maxH = '40vh' }: {
  items: string[]
  borderColor: string
  textColor: string
  maxH?: string
}) {
  return (
    <div className="overflow-y-auto" style={{ maxHeight: maxH }}>
      {items.map((item, i) => (
        <div key={i} className="px-4 py-2 border-b text-xs font-mono break-all"
          style={{ borderColor, color: textColor }}>
          {item}
        </div>
      ))}
    </div>
  )
}

type VulnFilter = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'info' | 'xss' | 'cors' | 'headers' | 'email' | 'zone'

function VulnsTab({ data }: { data: ScanData }) {
  const [filter, setFilter] = useState<VulnFilter>('all')
  const sevs = ['critical', 'high', 'medium', 'low', 'info'] as const
  const nucleiTotal = sevs.reduce((acc, s) => acc + data.nuclei[s].length, 0)

  const hasAny =
    nucleiTotal > 0 || data.dalfox.length > 0 || data.securityHeaders.length > 0 ||
    data.emailSecurity.length > 0 || data.corsFindings.length > 0 || data.zoneTransfer.length > 0

  if (!hasAny) {
    return (
      <EmptyState icon="✅" text="No vulnerability findings"
        hint="Passive scans check headers, email security, CORS. Run with --active for nuclei + dalfox." />
    )
  }

  function sevColor(line: string): string {
    if (line.startsWith('[high]') || line.startsWith('[critical]')) return '#f87171'
    if (line.startsWith('[medium]')) return '#fb923c'
    if (line.startsWith('[low]')) return '#facc15'
    return 'var(--text-muted)'
  }

  // Filter pill config
  const ALL_PILLS: { id: VulnFilter; label: string; count: number; color: string; bg: string }[] = [
    { id: 'all',     label: 'all',      count: nucleiTotal + data.dalfox.length + data.securityHeaders.length + data.emailSecurity.length + data.corsFindings.length + data.zoneTransfer.length, color: 'var(--text-muted)', bg: 'var(--surface-2)' },
    { id: 'critical',label: 'critical', count: data.nuclei.critical.length, color: '#fca5a5', bg: '#450a0a' },
    { id: 'high',    label: 'high',     count: data.nuclei.high.length,     color: '#fdba74', bg: '#431407' },
    { id: 'medium',  label: 'medium',   count: data.nuclei.medium.length,   color: '#fcd34d', bg: '#422006' },
    { id: 'low',     label: 'low',      count: data.nuclei.low.length,      color: '#86efac', bg: '#052e16' },
    { id: 'info',    label: 'info',     count: data.nuclei.info.length,     color: '#c084fc', bg: '#0d0b1e' },
    { id: 'xss',     label: 'xss',      count: data.dalfox.length,          color: '#fca5a5', bg: '#450a0a' },
    { id: 'cors',    label: 'cors',     count: data.corsFindings.length,    color: '#fdba74', bg: '#431407' },
    { id: 'headers', label: 'headers',  count: data.securityHeaders.length, color: '#7dd3fc', bg: '#0c1f35' },
    { id: 'email',   label: 'email',    count: data.emailSecurity.length,   color: '#c4b5fd', bg: '#1e0a4a' },
    { id: 'zone',    label: 'zone',     count: data.zoneTransfer.length,    color: '#fca5a5', bg: '#450a0a' },
  ]
  const pills = ALL_PILLS.filter(p => p.count > 0)

  const show = (id: VulnFilter) => filter === 'all' || filter === id

  return (
    <div className="space-y-4">
      {/* ── Filter bar ─────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-1.5">
        {pills.map((p) => (
          <button key={p.id} type="button"
            onClick={() => setFilter(p.id === filter ? 'all' : p.id)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors"
            style={{
              background: filter === p.id ? p.bg : 'var(--surface-2)',
              color: filter === p.id ? p.color : 'var(--text-muted)',
              border: `1px solid ${filter === p.id ? p.color + '55' : 'var(--border)'}`,
              cursor: 'pointer', fontFamily: 'inherit',
            }}>
            {p.label}
            <span className="font-mono opacity-75">{p.count}</span>
          </button>
        ))}
      </div>

      {/* ── Email Security ─────────────────────────────────────────────────── */}
      {show('email') && data.emailSecurity.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #3b1278' }}>
          <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: '#3b1278', background: '#1e0a4a' }}>
            <Badge style={{ background: '#3b1278', color: '#c4b5fd' }}>📧</Badge>
            <span className="text-sm font-medium" style={{ color: '#c4b5fd' }}>
              Email Security (SPF/DMARC/DKIM) — {data.emailSecurity.length} issue(s)
            </span>
          </div>
          <div className="overflow-y-auto" style={{ maxHeight: '30vh' }}>
            {data.emailSecurity.map((item, i) => (
              <div key={i} className="px-4 py-2 border-b text-xs font-mono break-all"
                style={{ borderColor: '#3b1278', color: sevColor(item) }}>{item}</div>
            ))}
          </div>
        </div>
      )}

      {/* ── Security Headers ───────────────────────────────────────────────── */}
      {show('headers') && data.securityHeaders.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #1e3a5f' }}>
          <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: '#1e3a5f', background: '#0c1f35' }}>
            <Badge style={{ background: '#1e3a5f', color: '#7dd3fc' }}>🔒</Badge>
            <span className="text-sm font-medium" style={{ color: '#7dd3fc' }}>
              Security Headers — {data.securityHeaders.length} issue(s)
            </span>
          </div>
          <div className="overflow-y-auto" style={{ maxHeight: '40vh' }}>
            {data.securityHeaders.map((item, i) => (
              <div key={i} className="px-4 py-2 border-b text-xs font-mono break-all"
                style={{ borderColor: '#1e3a5f', color: sevColor(item) }}>{item}</div>
            ))}
          </div>
        </div>
      )}

      {/* ── CORS ───────────────────────────────────────────────────────────── */}
      {show('cors') && data.corsFindings.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #7c2d12' }}>
          <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: '#7c2d12', background: '#431407' }}>
            <Badge style={{ background: '#7c2d12', color: '#fdba74' }}>🌐</Badge>
            <span className="text-sm font-medium" style={{ color: '#fdba74' }}>
              CORS Misconfigurations — {data.corsFindings.length}
            </span>
          </div>
          <FindingList items={data.corsFindings} borderColor="#7c2d12" textColor="#fdba74" />
        </div>
      )}

      {/* ── Zone Transfer ──────────────────────────────────────────────────── */}
      {show('zone') && data.zoneTransfer.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #7f1d1d' }}>
          <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: '#7f1d1d', background: '#450a0a' }}>
            <Badge style={{ background: '#7f1d1d', color: '#fca5a5' }}>🔓</Badge>
            <span className="text-sm font-medium" style={{ color: '#fca5a5' }}>
              Zone Transfer Exposed — {data.zoneTransfer.length} records
            </span>
          </div>
          <FindingList items={data.zoneTransfer} borderColor="#7f1d1d" textColor="#fca5a5" />
        </div>
      )}

      {/* ── Nuclei by severity ─────────────────────────────────────────────── */}
      {sevs.map((sev) =>
        show(sev) && data.nuclei[sev].length > 0 ? (
          <div key={sev} className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-3 px-4 py-3 border-b"
              style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}>
              <SevBadge sev={sev} />
              <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                {data.nuclei[sev].length} findings
              </span>
            </div>
            <FindingList items={data.nuclei[sev]} borderColor="var(--border-subtle)" textColor="var(--text-muted)" />
          </div>
        ) : null
      )}

      {/* ── Dalfox XSS ─────────────────────────────────────────────────────── */}
      {show('xss') && data.dalfox.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #7f1d1d' }}>
          <div className="flex items-center gap-3 px-4 py-3 border-b"
            style={{ borderColor: '#7f1d1d', background: '#450a0a' }}>
            <Badge style={{ background: '#7f1d1d', color: '#fca5a5' }}>XSS</Badge>
            <span className="text-sm font-medium" style={{ color: '#fca5a5' }}>
              Dalfox — {data.dalfox.length} findings
            </span>
          </div>
          <FindingList items={data.dalfox} borderColor="#7f1d1d" textColor="#fca5a5" />
        </div>
      )}
    </div>
  )
}

// ── Tab: Diff ─────────────────────────────────────────────────

function DiffTab({ data }: { data: ScanData }) {
  const entries = Object.entries(data.diff.files).filter(([, diff]) => diff.new.length > 0)

  if (entries.length === 0) {
    return <EmptyState icon="📊" text="No new changes"
      hint={data.diff.previousScan ? 'No new items since last scan' : 'This may be the first scan for this domain'} />
  }

  const labels: Record<string, string> = {
    'all_subdomains.txt.diff': 'Subdomains',
    'alive.txt.diff': 'Alive Hosts',
    'urls_clean.txt.diff': 'URLs',
    'open_ports.txt.diff': 'Open Ports',
    'nuclei_results.txt.diff': 'Vulnerabilities',
  }

  return (
    <div className="space-y-4">
      {data.diff.previousScan && (
        <div className="text-xs px-3 py-2 rounded-lg" style={{ background: 'var(--surface)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
          Compared with: <span className="font-mono" style={{ color: 'var(--cyan)' }}>{data.diff.previousScan}</span>
        </div>
      )}

      {entries.map(([fname, diff]) => (
        <div key={fname} className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
          <div className="px-4 py-3 border-b text-sm font-medium flex items-center gap-2" style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}>
            {labels[fname] || fname}
            {diff.new.length > 0 && <Badge style={{ background: '#052e16', color: '#86efac' }}>+{diff.new.length}</Badge>}
          </div>
          <div className="grid" style={{ borderColor: 'var(--border)' }}>
            {diff.new.length > 0 && (
              <div className="p-4" style={{ borderColor: 'var(--border-subtle)' }}>
                <div className="text-xs font-semibold mb-2" style={{ color: '#4ade80' }}>+ New ({diff.new.length})</div>
                <div className="overflow-y-auto" style={{ maxHeight: '30vh' }}>
                  {diff.new.map((item, i) => (
                    <div key={i} className="text-xs font-mono py-0.5 border-l-2 pl-2 mb-0.5"
                      style={{ borderColor: '#4ade80', color: '#86efac' }}>{item}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Tab: Screenshots ──────────────────────────────────────────

function ScreenshotsTab({ data }: { data: ScanData }) {
  // Filter out screenshots that don't belong to the target domain
  // (gowitness sometimes follows links to external sites like google.com)
  const screenshots = data.screenshots.filter((img) => {
    const decoded = decodeScreenshotTarget(img)
    if (!decoded) return true // keep undecodable filenames
    return isTargetHost(decoded.url, data.domain)
  })

  if (screenshots.length === 0) {
    return <EmptyState icon="📸" text="No screenshots" hint="Screenshots are captured with gowitness during the scan" />
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {screenshots.map((img) => {
        const decoded = decodeScreenshotTarget(img)
        return (
          <div key={img}
            className="group rounded-xl overflow-hidden transition-transform hover:scale-[1.02]"
            style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}>
            {/* image — clicking opens full-size in new tab */}
            <a href={`/api/scan/${data.id}/screenshot/${img}`} target="_blank" rel="noopener">
              <Image
                src={`/api/scan/${data.id}/screenshot/${img}`}
                alt={img}
                width={640}
                height={360}
                unoptimized
                className="w-full h-36 object-cover"
                loading="lazy"
              />
            </a>
            {/* caption — URL with port, plain text, no link */}
            <div className="px-2 py-2 text-xs font-mono"
              style={{ background: 'var(--surface)', color: 'var(--text-muted)' }}>
              <div className="truncate" title={decoded?.url ?? img}>
                {decoded?.url ?? img.replace(/\.(png|jpg|jpeg|webp)$/i, '')}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Tab: Tools ────────────────────────────────────────────────

function ToolsTab({ data }: { data: ScanData }) {
  const [selectedTool, setSelectedTool] = useState<string | null>(null)
  const [logContent, setLogContent] = useState<string | null>(null)
  const [logLoading, setLogLoading] = useState(false)

  const entries = Object.entries(data.toolLogs).sort((a, b) => a[0].localeCompare(b[0]))
  const selectedIndex = selectedTool ? entries.findIndex(([tool]) => tool === selectedTool) : -1

  if (entries.length === 0) {
    return <EmptyState icon="🔧" text="No tool log data" hint="execution_summary.json is written at scan end — older scans won't have this" />
  }

  const ok = entries.filter(([, v]) => v.status === 'ok').length
  const partial = entries.filter(([, v]) => v.status === 'partial').length
  const fail = entries.filter(([, v]) => v.status === 'fail').length
  const missing = entries.filter(([, v]) => v.status === 'not_found').length
  const other = entries.length - ok - partial - fail - missing

  async function openLog(tool: string) {
    setSelectedTool(tool)
    setLogContent(null)
    setLogLoading(true)
    try {
      const res = await fetch(`/api/scan/${data.id}/logs/${tool}`)
      const text = await res.text()
      setLogContent(text || '(no output captured for this tool)')
    } catch {
      setLogContent('(failed to load log)')
    } finally {
      setLogLoading(false)
    }
  }

  async function openLogByIndex(index: number) {
    if (index < 0 || index >= entries.length) return
    await openLog(entries[index][0])
  }

  function statusColor(status: string): string {
    if (status === 'ok') return '#4ade80'
    if (status === 'partial') return '#facc15'
    if (status === 'fail') return '#f87171'
    if (status === 'timeout') return '#fb923c'
    if (status === 'not_found') return 'var(--text-subtle)'
    return '#f97316'
  }

  function statusIcon(status: string): string {
    if (status === 'ok') return '✓'
    if (status === 'partial') return '⚠'
    if (status === 'fail') return '✗'
    if (status === 'timeout') return '⏱'
    if (status === 'not_found') return '—'
    return '!'
  }

  function toolCounters(info: import('@/lib/types').ToolLogEntry): string {
    const parts: string[] = []
    if (info.found !== undefined)      parts.push(`${info.found} found`)
    if (info.urls !== undefined)       parts.push(`${info.urls} urls`)
    if (info.discovered !== undefined) parts.push(`${info.discovered} discovered`)
    if (info.findings !== undefined)   parts.push(`${info.findings} findings`)
    if (info.hosts !== undefined)      parts.push(`${info.hosts} hosts`)
    if (info.timeouts !== undefined && info.timeouts > 0)  parts.push(`${info.timeouts} timeouts`)
    if (info.failures !== undefined && info.failures > 0)  parts.push(`${info.failures} failures`)
    if (info.skipped  !== undefined && info.skipped  > 0)  parts.push(`${info.skipped} skipped (budget)`)
    return parts.join(' · ')
  }

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      <div className="flex flex-wrap gap-3 text-sm">
        <span style={{ color: '#4ade80' }}><span className="font-mono font-bold">{ok}</span> ok</span>
        {partial > 0 && <span style={{ color: '#facc15' }}><span className="font-mono font-bold">{partial}</span> partial</span>}
        {fail > 0 && <span style={{ color: '#f87171' }}><span className="font-mono font-bold">{fail}</span> failed</span>}
        {other > 0 && <span style={{ color: '#fb923c' }}><span className="font-mono font-bold">{other}</span> timeout/error</span>}
        {missing > 0 && <span style={{ color: 'var(--text-subtle)' }}><span className="font-mono font-bold">{missing}</span> not installed</span>}
      </div>

      {/* Tool table */}
      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        <div className="overflow-auto" style={{ maxHeight: '60vh' }}>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs" style={{ color: 'var(--text-muted)', background: 'var(--surface)' }}>
                <th className="px-4 py-3 font-medium sticky top-0" style={{ background: 'var(--surface)' }}>Tool</th>
                <th className="px-4 py-3 font-medium sticky top-0" style={{ background: 'var(--surface)' }}>Status</th>
                <th className="px-4 py-3 font-medium sticky top-0" style={{ background: 'var(--surface)' }}>Exit code</th>
                <th className="px-4 py-3 font-medium sticky top-0" style={{ background: 'var(--surface)' }}>Elapsed</th>
                <th className="px-4 py-3 font-medium sticky top-0" style={{ background: 'var(--surface)' }}>Log</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([tool, info]) => (
                <tr
                  key={tool}
                  className="border-t transition-colors hover:bg-zinc-800/30 cursor-pointer"
                  style={{ borderColor: 'var(--border-subtle)' }}
                  onClick={() => openLog(tool)}
                >
                  <td className="px-4 py-2.5 font-mono text-xs" style={{ color: 'var(--text)' }}>{tool}</td>
                  <td className="px-4 py-2.5">
                    <span className="font-mono text-xs font-semibold" style={{ color: statusColor(info.status) }}>
                      {statusIcon(info.status)} {info.status}
                    </span>
                    {info.msg && (
                      <span className="text-xs ml-2" style={{ color: 'var(--text-subtle)' }}>{info.msg}</span>
                    )}
                    {toolCounters(info) && (
                      <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>{toolCounters(info)}</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs" style={{ color: info.rc === 0 ? 'var(--text-muted)' : '#f87171' }}>
                    {info.rc === -1 ? '—' : info.rc}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs" style={{ color: 'var(--text-muted)' }}>{info.elapsed}s</td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--surface-2)', color: 'var(--cyan)', border: '1px solid var(--border)', cursor: 'pointer' }}>
                      ver
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Log modal */}
      {selectedTool && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.75)' }}
          onClick={() => setSelectedTool(null)}
        >
          <div
            className="rounded-xl flex flex-col w-full max-w-3xl"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', maxHeight: '80vh', boxShadow: 'var(--glow-purple)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={selectedIndex <= 0}
                  onClick={() => void openLogByIndex(selectedIndex - 1)}
                  className="px-2 py-1 rounded text-xs"
                  style={{ background: 'var(--surface-2)', color: selectedIndex <= 0 ? 'var(--text-subtle)' : 'var(--purple-bright)', border: '1px solid var(--border)' }}
                >
                  ←
                </button>
                <div>
                  <span className="font-mono font-semibold text-sm" style={{ color: 'var(--cyan)' }}>{selectedTool}</span>
                  <span className="text-xs ml-3" style={{ color: 'var(--text-muted)' }}>output log {selectedIndex >= 0 ? `${selectedIndex + 1}/${entries.length}` : ''}</span>
                </div>
                <button
                  type="button"
                  disabled={selectedIndex < 0 || selectedIndex >= entries.length - 1}
                  onClick={() => void openLogByIndex(selectedIndex + 1)}
                  className="px-2 py-1 rounded text-xs"
                  style={{ background: 'var(--surface-2)', color: selectedIndex < 0 || selectedIndex >= entries.length - 1 ? 'var(--text-subtle)' : 'var(--purple-bright)', border: '1px solid var(--border)' }}
                >
                  →
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => void openLogByIndex(selectedIndex - 1)}
                  disabled={selectedIndex <= 0}
                  className="text-xs px-3 py-1 rounded"
                  style={{ background: 'var(--surface-2)', color: selectedIndex <= 0 ? 'var(--text-subtle)' : 'var(--text)', border: '1px solid var(--border)' }}
                >
                  prev
                </button>
                <button
                  type="button"
                  onClick={() => void openLogByIndex(selectedIndex + 1)}
                  disabled={selectedIndex < 0 || selectedIndex >= entries.length - 1}
                  className="text-xs px-3 py-1 rounded"
                  style={{ background: 'var(--surface-2)', color: selectedIndex < 0 || selectedIndex >= entries.length - 1 ? 'var(--text-subtle)' : 'var(--text)', border: '1px solid var(--border)' }}
                >
                  next
                </button>
                <button
                  onClick={() => setSelectedTool(null)}
                  className="text-sm px-3 py-1 rounded"
                  style={{ background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}
                >
                  Fechar
                </button>
              </div>
            </div>
            <div className="overflow-auto p-4 flex-1" style={{ fontFamily: 'monospace' }}>
              {logLoading ? (
                <div className="text-sm" style={{ color: 'var(--text-subtle)' }}>Carregando...</div>
              ) : (
                <pre className="text-xs whitespace-pre-wrap break-all" style={{ color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  {logContent}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main tabs component ───────────────────────────────────────

const TABS = [
  { id: 'summary', label: 'Summary' },
  { id: 'subdomains', label: 'Subdomains' },
  { id: 'hosts', label: 'HTTP Hosts' },
  { id: 'urls', label: 'URLs' },
  { id: 'vulns', label: 'Vulnerabilities' },
  { id: 'diff', label: 'Diff' },
  { id: 'screenshots', label: 'Screenshots' },
  { id: 'tools', label: 'Tools' },
] as const

type TabId = typeof TABS[number]['id']

export default function ScanTabs({ data }: { data: ScanData }) {
  const [active, setActive] = useState<TabId>('summary')

  const toolFails = Object.values(data.toolLogs).filter((v) => v.status !== 'ok' && v.status !== 'not_found').length
  const badges: Partial<Record<TabId, { value: number; color: string }>> = {
    subdomains: { value: data.subdomains.length + data.bruteforce.length, color: 'var(--cyan)' },
    hosts: { value: data.hosts.length, color: 'var(--green)' },
    urls: { value: data.urls.length, color: 'var(--purple)' },
    vulns: {
      value: Object.values(data.nuclei).flat().length + data.dalfox.length +
             data.securityHeaders.length + data.emailSecurity.length + data.corsFindings.length,
      color: 'var(--red)',
    },
    screenshots: { value: data.screenshots.length, color: 'var(--text-muted)' },
    tools: { value: toolFails, color: '#f87171' },
  }

  return (
    <div>
      {/* Tab bar */}
      <div className="flex gap-1 border-b mb-6 overflow-x-auto" style={{ borderColor: 'var(--border)' }}>
        {TABS.map((tab) => {
          const badge = badges[tab.id]
          return (
            <button
              key={tab.id}
              onClick={() => setActive(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-all ${
                active === tab.id ? 'tab-active' : 'tab-inactive'
              }`}>
              {tab.label}
              {badge && badge.value > 0 && (
                <span className="text-xs font-mono px-1.5 py-0.5 rounded"
                  style={{ background: 'var(--surface-2)', color: badge.color }}>
                  {badge.value}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      <div className="animate-fade-in">
        {active === 'summary'     && <SummaryTab data={data} />}
        {active === 'subdomains'  && <SubdomainsTab data={data} />}
        {active === 'hosts'       && <HostsTab data={data} />}
        {active === 'urls'        && <UrlsTab data={data} />}
        {active === 'vulns'       && <VulnsTab data={data} />}
        {active === 'diff'        && <DiffTab data={data} />}
        {active === 'screenshots' && <ScreenshotsTab data={data} />}
        {active === 'tools'       && <ToolsTab data={data} />}
      </div>
    </div>
  )
}
