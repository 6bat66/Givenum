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
      className="text-sm px-3 py-1.5 rounded-lg outline-none focus:ring-1"
      style={{
        background: 'var(--surface-2)',
        border: '1px solid var(--border)',
        color: 'var(--text)',
        minWidth: 200,
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

        {!totalVulns && !data.gitExposed.length && !hasTakeover && !hasCloud && data.topTech.length === 0 && (
          <EmptyState icon="✅" text="No critical findings" hint="Run with --active for deeper analysis" />
        )}
      </div>
    </div>
  )
}

// ── Tab: Subdomains ───────────────────────────────────────────

function SubdomainsTab({ data }: { data: ScanData }) {
  const [query, setQuery] = useState('')
  const all = useMemo(() => [
    ...data.subdomains.map((s) => ({ sub: s, source: 'passive' as const })),
    ...data.bruteforce.map((s) => ({ sub: s, source: 'bruteforce' as const })),
  ], [data])

  const filtered = useMemo(() =>
    query ? all.filter((i) => i.sub.toLowerCase().includes(query.toLowerCase())) : all
  , [all, query])

  const alive = new Set(data.hosts.map((h) => {
    try { return new URL(h.url).hostname } catch { return h.url }
  }))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
          <span className="font-semibold" style={{ color: 'var(--cyan)' }}>{data.subdomains.length}</span> passive
          {data.bruteforce.length > 0 && (
            <> · <span className="font-semibold" style={{ color: 'var(--orange)' }}>{data.bruteforce.length}</span> brute-forced</>
          )}
        </div>
        <SearchInput placeholder="Filter subdomains…" onChange={setQuery} />
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon="🔍" text="No matches" />
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

function HostsTab({ data }: { data: ScanData }) {
  const [query, setQuery] = useState('')
  const filtered = useMemo(() =>
    query ? data.hosts.filter((h) =>
      h.url.toLowerCase().includes(query.toLowerCase()) ||
      h.title.toLowerCase().includes(query.toLowerCase()) ||
      h.tech.some((t) => t.toLowerCase().includes(query.toLowerCase()))
    ) : data.hosts
  , [data.hosts, query])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
          <span className="font-semibold" style={{ color: 'var(--green)' }}>{data.hosts.length}</span> hosts
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
              {filtered.map((host, i) => (
                <tr key={i} className="border-t transition-colors hover:bg-zinc-800/30" style={{ borderColor: 'var(--border-subtle)' }}>
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

function UrlsTab({ data }: { data: ScanData }) {
  const [query, setQuery] = useState('')
  const [showParamsOnly, setShowParamsOnly] = useState(false)
  const source = showParamsOnly ? data.paramUrls : data.urls
  const filtered = useMemo(() =>
    query ? source.filter((u) => u.toLowerCase().includes(query.toLowerCase())) : source
  , [source, query])
  const shown = filtered.slice(0, 500)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3 text-sm">
          <span style={{ color: 'var(--text-muted)' }}>
            <span className="font-semibold" style={{ color: 'var(--purple)' }}>{data.urls.length}</span> total ·{' '}
            <span className="font-semibold" style={{ color: 'var(--yellow)' }}>{data.paramUrls.length}</span> with params
          </span>
          <button
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

      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        <div className="overflow-y-auto" style={{ maxHeight: '60vh' }}>
          {shown.map((url, i) => (
            <div key={i} className="flex items-center px-4 py-1.5 border-b text-xs font-mono transition-colors hover:bg-zinc-800/30"
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

function VulnsTab({ data }: { data: ScanData }) {
  const sevs = ['critical', 'high', 'medium', 'low', 'info'] as const
  const total = sevs.reduce((acc, s) => acc + data.nuclei[s].length, 0)

  if (total === 0 && data.dalfox.length === 0) {
    return <EmptyState icon="✅" text="No vulnerability findings"
      hint="Run with --active to enable nuclei + dalfox scanning" />
  }

  return (
    <div className="space-y-4">
      {sevs.map((sev) =>
        data.nuclei[sev].length > 0 ? (
          <div key={sev} className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}>
              <SevBadge sev={sev} />
              <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>{data.nuclei[sev].length} findings</span>
            </div>
            <div className="overflow-y-auto" style={{ maxHeight: '40vh' }}>
              {data.nuclei[sev].map((item, i) => (
                <div key={i} className="px-4 py-2 border-b text-xs font-mono" style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-muted)' }}>
                  {item}
                </div>
              ))}
            </div>
          </div>
        ) : null
      )}

      {data.dalfox.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #7f1d1d' }}>
          <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: '#7f1d1d', background: '#450a0a' }}>
            <Badge style={{ background: '#7f1d1d', color: '#fca5a5' }}>XSS</Badge>
            <span className="text-sm font-medium" style={{ color: '#fca5a5' }}>Dalfox — {data.dalfox.length} findings</span>
          </div>
          <div className="overflow-y-auto" style={{ maxHeight: '40vh' }}>
            {data.dalfox.map((item, i) => (
              <div key={i} className="px-4 py-2 border-b text-xs font-mono" style={{ borderColor: '#7f1d1d', color: '#fca5a5' }}>
                {item}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tab: Diff ─────────────────────────────────────────────────

function DiffTab({ data }: { data: ScanData }) {
  const entries = Object.entries(data.diff.files)

  if (entries.length === 0) {
    return <EmptyState icon="📊" text="No diff data"
      hint={data.diff.previousScan ? 'No changes since last scan' : 'This may be the first scan for this domain'} />
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
            {diff.removed.length > 0 && <Badge style={{ background: '#450a0a', color: '#fca5a5' }}>-{diff.removed.length}</Badge>}
          </div>
          <div className="grid md:grid-cols-2 divide-x" style={{ borderColor: 'var(--border)' }}>
            {diff.new.length > 0 && (
              <div className="p-4">
                <div className="text-xs font-semibold mb-2" style={{ color: '#4ade80' }}>+ New ({diff.new.length})</div>
                <div className="overflow-y-auto" style={{ maxHeight: '30vh' }}>
                  {diff.new.map((item, i) => (
                    <div key={i} className="text-xs font-mono py-0.5 border-l-2 pl-2 mb-0.5"
                      style={{ borderColor: '#4ade80', color: '#86efac' }}>{item}</div>
                  ))}
                </div>
              </div>
            )}
            {diff.removed.length > 0 && (
              <div className="p-4">
                <div className="text-xs font-semibold mb-2" style={{ color: '#f87171' }}>- Removed ({diff.removed.length})</div>
                <div className="overflow-y-auto" style={{ maxHeight: '30vh' }}>
                  {diff.removed.map((item, i) => (
                    <div key={i} className="text-xs font-mono py-0.5 border-l-2 pl-2 mb-0.5"
                      style={{ borderColor: '#f87171', color: '#fca5a5' }}>{item}</div>
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
  if (data.screenshots.length === 0) {
    return <EmptyState icon="📸" text="No screenshots" hint="Screenshots are captured with gowitness during the scan" />
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {data.screenshots.map((img) => (
        <a key={img} href={`/api/scan/${data.id}/screenshot/${img}`} target="_blank" rel="noopener"
          className="group rounded-lg overflow-hidden transition-transform hover:scale-[1.02]"
          style={{ border: '1px solid var(--border)' }}>
          <Image
            src={`/api/scan/${data.id}/screenshot/${img}`}
            alt={img}
            width={640}
            height={360}
            unoptimized
            className="w-full h-36 object-cover"
            loading="lazy"
          />
          <div className="px-2 py-1.5 text-xs font-mono truncate group-hover:text-white transition-colors"
            style={{ background: 'var(--surface)', color: 'var(--text-muted)' }}>
            {img.replace(/\.(png|jpg|jpeg|webp)$/i, '')}
          </div>
        </a>
      ))}
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
] as const

type TabId = typeof TABS[number]['id']

export default function ScanTabs({ data }: { data: ScanData }) {
  const [active, setActive] = useState<TabId>('summary')

  const badges: Partial<Record<TabId, { value: number; color: string }>> = {
    subdomains: { value: data.subdomains.length + data.bruteforce.length, color: 'var(--cyan)' },
    hosts: { value: data.hosts.length, color: 'var(--green)' },
    urls: { value: data.urls.length, color: 'var(--purple)' },
    vulns: { value: Object.values(data.nuclei).flat().length + data.dalfox.length, color: 'var(--red)' },
    screenshots: { value: data.screenshots.length, color: 'var(--text-muted)' },
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
      </div>
    </div>
  )
}
