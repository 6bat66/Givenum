import type { ScanData } from './types'

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function sev(label: string, items: string[], bg: string, fg: string): string {
  if (items.length === 0) return ''
  return `
    <section>
      <h3 style="color:${fg};margin-bottom:8px">${esc(label)} <span style="font-size:13px;opacity:0.7">(${items.length})</span></h3>
      <ul style="list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:4px">
        ${items.map((i) => `<li style="background:${bg};border:1px solid ${fg}33;border-radius:6px;padding:4px 10px;font-family:monospace;font-size:12px;word-break:break-all">${esc(i)}</li>`).join('')}
      </ul>
    </section>`
}

export function generateHtmlReport(data: ScanData): string {
  const ts = new Date().toLocaleString()
  const totalVulns = Object.values(data.nuclei).flat().length
  const hasTakeover = data.subjack.length + data.subzy.length > 0

  const statItems = [
    { label: 'Subdomains', value: data.subdomains.length, color: '#22d3ee' },
    { label: 'Alive Hosts', value: data.hosts.length, color: '#4ade80' },
    { label: 'URLs', value: data.urls.length, color: '#c084fc' },
    { label: 'JS Files', value: data.jsFiles.length, color: '#facc15' },
    { label: 'Open Ports', value: data.openPorts.length, color: '#fb923c' },
    { label: 'Vulnerabilities', value: totalVulns, color: '#f87171' },
  ]

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>GivEnum Report — ${esc(data.domain)}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#050507;color:#f2f2f7;font-family:'JetBrains Mono',monospace,sans-serif;font-size:13px;line-height:1.65;padding:32px 24px;max-width:960px;margin:0 auto}
h1{font-size:22px;font-weight:700;color:#b28cff;margin-bottom:4px}
h2{font-size:15px;font-weight:700;color:#a19ab8;text-transform:uppercase;letter-spacing:0.12em;margin:28px 0 14px;padding-bottom:6px;border-bottom:1px solid #2e2b42}
h3{font-size:13px;font-weight:600;margin-bottom:8px}
section{margin-bottom:20px}
.meta{color:#656079;font-size:12px;margin-bottom:24px}
.stats{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:8px}
.stat{background:#0d0d11;border:1px solid #2e2b42;border-radius:12px;padding:12px 18px;min-width:130px}
.stat-val{font-size:22px;font-weight:700;line-height:1}
.stat-lbl{font-size:11px;color:#656079;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em}
.tag{display:inline-block;padding:1px 8px;border-radius:6px;font-size:11px;font-weight:600}
.list-block{background:#0d0d11;border:1px solid #1f1d2b;border-radius:10px;padding:14px;margin-top:6px}
.list-item{font-family:monospace;font-size:12px;padding:3px 0;border-bottom:1px solid #1f1d2b;word-break:break-all}
.list-item:last-child{border-bottom:none}
</style>
</head>
<body>
<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
  <span style="color:#8758d8;font-weight:700;font-size:18px">❯</span>
  <h1>${esc(data.domain)}</h1>
  <span class="tag" style="background:#14141a;color:${data.mode === 'active' ? '#fb923c' : '#22d3ee'};border:1px solid ${data.mode === 'active' ? '#fb923c44' : '#22d3ee44'}">${data.mode}</span>
</div>
<div class="meta">
  generated ${esc(ts)} · project: ${esc(data.projectName)} · scan id: ${esc(data.id)}
</div>

<h2>Overview</h2>
<div class="stats">
${statItems.map((s) => `  <div class="stat">
    <div class="stat-val" style="color:${s.color}">${s.value}</div>
    <div class="stat-lbl">${esc(s.label)}</div>
  </div>`).join('\n')}
</div>

${data.subdomains.length > 0 ? `
<h2>Subdomains (${data.subdomains.length})</h2>
<div class="list-block">
${data.subdomains.map((s) => `<div class="list-item" style="color:#22d3ee">${esc(s)}</div>`).join('\n')}
</div>` : ''}

${data.hosts.length > 0 ? `
<h2>Alive HTTP Hosts (${data.hosts.length})</h2>
<div class="list-block">
${data.hosts.map((h) => `<div class="list-item"><span style="color:#4ade80">${esc(h.url)}</span> <span style="color:#656079">${h.status} ${esc(h.title.slice(0, 60))} ${h.tech.slice(0, 3).join(', ')}</span></div>`).join('\n')}
</div>` : ''}

${totalVulns > 0 ? `
<h2>Vulnerabilities (${totalVulns})</h2>
${sev('Critical', data.nuclei.critical, '#450a0a', '#fca5a5')}
${sev('High', data.nuclei.high, '#431407', '#fdba74')}
${sev('Medium', data.nuclei.medium, '#422006', '#fcd34d')}
${sev('Low', data.nuclei.low, '#052e16', '#86efac')}
${sev('Info', data.nuclei.info, '#0d0b1e', '#c084fc')}` : ''}

${data.dalfox.length > 0 ? `
<h2>XSS Findings (${data.dalfox.length})</h2>
<div class="list-block">
${data.dalfox.map((s) => `<div class="list-item" style="color:#fca5a5">${esc(s)}</div>`).join('\n')}
</div>` : ''}

${hasTakeover ? `
<h2>Takeover Candidates</h2>
<div class="list-block">
${[...data.subjack, ...data.subzy].map((s) => `<div class="list-item" style="color:#fdba74">${esc(s)}</div>`).join('\n')}
</div>` : ''}

${data.openPorts.length > 0 ? `
<h2>Open Ports (${data.openPorts.length})</h2>
<div class="list-block">
${data.openPorts.map((s) => `<div class="list-item" style="color:#fb923c">${esc(s)}</div>`).join('\n')}
</div>` : ''}

${data.securityHeaders.length > 0 ? `
<h2>Security Header Issues (${data.securityHeaders.length})</h2>
<div class="list-block">
${data.securityHeaders.map((s) => `<div class="list-item" style="color:#fcd34d">${esc(s)}</div>`).join('\n')}
</div>` : ''}

${data.emailSecurity.length > 0 ? `
<h2>Email Security Issues (${data.emailSecurity.length})</h2>
<div class="list-block">
${data.emailSecurity.map((s) => `<div class="list-item" style="color:#fcd34d">${esc(s)}</div>`).join('\n')}
</div>` : ''}

${data.corsFindings.length > 0 ? `
<h2>CORS Findings (${data.corsFindings.length})</h2>
<div class="list-block">
${data.corsFindings.map((s) => `<div class="list-item" style="color:#fdba74">${esc(s)}</div>`).join('\n')}
</div>` : ''}

${data.gitExposed.length > 0 ? `
<h2>Exposed Git (${data.gitExposed.length})</h2>
<div class="list-block">
${data.gitExposed.map((s) => `<div class="list-item" style="color:#fca5a5">${esc(s)}</div>`).join('\n')}
</div>` : ''}

${data.urls.length > 0 ? `
<h2>URLs (${data.urls.length})</h2>
<div class="list-block" style="max-height:300px;overflow:auto">
${data.urls.map((s) => `<div class="list-item" style="color:#a19ab8">${esc(s)}</div>`).join('\n')}
</div>` : ''}

</body>
</html>`
}
