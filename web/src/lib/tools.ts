import { execSync } from 'child_process'
import fs from 'fs'

export interface ToolInfo {
  name: string
  description: string
  category: 'subdomain' | 'http' | 'vuln' | 'util'
  installCmd: string         // human-readable command (shown in the UI)
  installer: string[]        // argv used by execFile (no shell) — first item is the binary
  checkCmd: string           // command to run to verify tool exists
}

export interface ToolStatus extends ToolInfo {
  installed: boolean
  version: string | null
}

// Helpers so we don't repeat the installer pattern.
const goTool = (modulePath: string): string[] => ['go', 'install', '-v', modulePath]
const pipTool = (pkg: string): string[] => ['pip', 'install', '--break-system-packages', pkg]

export const TOOL_REGISTRY: ToolInfo[] = [
  // ── Subdomain enumeration ───────────────────────────────────
  { name: 'subfinder',    category: 'subdomain', description: 'Passive subdomain discovery',
    installCmd: 'go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest',
    installer: goTool('github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest'),
    checkCmd: 'subfinder -version' },
  { name: 'amass',        category: 'subdomain', description: 'In-depth subdomain enumeration',
    installCmd: 'go install -v github.com/owasp-amass/amass/v4/...@master',
    installer: goTool('github.com/owasp-amass/amass/v4/...@master'),
    checkCmd: 'amass -version' },
  { name: 'assetfinder',  category: 'subdomain', description: 'Find domains and subdomains related to a domain',
    installCmd: 'go install -v github.com/tomnomnom/assetfinder@latest',
    installer: goTool('github.com/tomnomnom/assetfinder@latest'),
    checkCmd: 'assetfinder --help' },

  // ── HTTP probing ────────────────────────────────────────────
  { name: 'httpx',        category: 'http', description: 'Fast multi-purpose HTTP toolkit',
    installCmd: 'go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest',
    installer: goTool('github.com/projectdiscovery/httpx/cmd/httpx@latest'),
    checkCmd: 'httpx -version' },
  { name: 'gowitness',    category: 'http', description: 'Web screenshot utility using Chrome',
    installCmd: 'go install -v github.com/sensepost/gowitness@latest',
    installer: goTool('github.com/sensepost/gowitness@latest'),
    checkCmd: 'gowitness version' },
  { name: 'waybackurls',  category: 'http', description: 'Fetch known URLs from Wayback Machine',
    installCmd: 'go install -v github.com/tomnomnom/waybackurls@latest',
    installer: goTool('github.com/tomnomnom/waybackurls@latest'),
    checkCmd: 'waybackurls --help' },
  { name: 'katana',       category: 'http', description: 'Next-gen web crawling framework',
    installCmd: 'go install -v github.com/projectdiscovery/katana/cmd/katana@latest',
    installer: goTool('github.com/projectdiscovery/katana/cmd/katana@latest'),
    checkCmd: 'katana -version' },
  { name: 'gau',          category: 'http', description: 'Fetch known URLs from AlienVault, Wayback, Common Crawl',
    installCmd: 'go install -v github.com/lc/gau/v2/cmd/gau@latest',
    installer: goTool('github.com/lc/gau/v2/cmd/gau@latest'),
    checkCmd: 'gau --help' },
  { name: 'hakrawler',    category: 'http', description: 'Simple fast web crawler for recon',
    installCmd: 'go install -v github.com/hakluke/hakrawler@latest',
    installer: goTool('github.com/hakluke/hakrawler@latest'),
    checkCmd: 'hakrawler --help' },

  // ── Vulnerability scanning ──────────────────────────────────
  { name: 'nuclei',       category: 'vuln', description: 'Fast and customizable vulnerability scanner',
    installCmd: 'go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest',
    installer: goTool('github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest'),
    checkCmd: 'nuclei -version' },
  { name: 'dalfox',       category: 'vuln', description: 'XSS scanner and parameter analysis tool',
    installCmd: 'go install -v github.com/hahwul/dalfox/v2@latest',
    installer: goTool('github.com/hahwul/dalfox/v2@latest'),
    checkCmd: 'dalfox version' },
  { name: 'subjack',      category: 'vuln', description: 'Subdomain takeover scanning tool',
    installCmd: 'go install -v github.com/haccer/subjack@latest',
    installer: goTool('github.com/haccer/subjack@latest'),
    checkCmd: 'subjack --help' },
  { name: 'subzy',        category: 'vuln', description: 'Subdomain takeover vulnerability checker',
    installCmd: 'go install -v github.com/LukaSikic/subzy@latest',
    installer: goTool('github.com/LukaSikic/subzy@latest'),
    checkCmd: 'subzy --help' },

  // ── Utilities ───────────────────────────────────────────────
  { name: 'dnsx',         category: 'util', description: 'Fast and multi-purpose DNS toolkit',
    installCmd: 'go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest',
    installer: goTool('github.com/projectdiscovery/dnsx/cmd/dnsx@latest'),
    checkCmd: 'dnsx -version' },
  { name: 'naabu',        category: 'util', description: 'Fast port scanner',
    installCmd: 'go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest',
    installer: goTool('github.com/projectdiscovery/naabu/v2/cmd/naabu@latest'),
    checkCmd: 'naabu -version' },
  { name: 'shuffledns',   category: 'util', description: 'MassDNS wrapper for subdomain enumeration',
    installCmd: 'go install -v github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest',
    installer: goTool('github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest'),
    checkCmd: 'shuffledns -version' },
  { name: 'massdns',      category: 'util', description: 'High-performance DNS resolver',
    installCmd: 'go install -v github.com/blechschmidt/massdns@latest',
    installer: goTool('github.com/blechschmidt/massdns@latest'),
    checkCmd: 'massdns --help' },
  { name: 'gf',           category: 'util', description: 'Grep patterns for bug bounty',
    installCmd: 'go install -v github.com/tomnomnom/gf@latest',
    installer: goTool('github.com/tomnomnom/gf@latest'),
    checkCmd: 'gf --help' },
  { name: 'anew',         category: 'util', description: 'Append lines to a file, deduplicated',
    installCmd: 'go install -v github.com/tomnomnom/anew@latest',
    installer: goTool('github.com/tomnomnom/anew@latest'),
    checkCmd: 'anew --help' },
  { name: 'ffuf',         category: 'util', description: 'Fast web fuzzer',
    installCmd: 'go install -v github.com/ffuf/ffuf/v2@latest',
    installer: goTool('github.com/ffuf/ffuf/v2@latest'),
    checkCmd: 'ffuf -V' },
  { name: 'notify',       category: 'util', description: 'Stream output to notification services',
    installCmd: 'go install -v github.com/projectdiscovery/notify/cmd/notify@latest',
    installer: goTool('github.com/projectdiscovery/notify/cmd/notify@latest'),
    checkCmd: 'notify -version' },
  { name: 'interactsh-client', category: 'util', description: 'OOB interaction gathering server client',
    installCmd: 'go install -v github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest',
    installer: goTool('github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest'),
    checkCmd: 'interactsh-client -version' },

  // ── Phase 2 — advanced active testing ──────────────────────
  { name: 'jwt_tool',    category: 'vuln', description: 'JWT vulnerability testing (none-alg, weak secret, RS/HS confusion)',
    installCmd: 'pip install jwt-tool',
    installer: pipTool('jwt-tool'),
    checkCmd: 'jwt_tool --help' },
  { name: 's3scanner',  category: 'vuln', description: 'Cloud bucket exposure scanner (S3, GCS, Azure)',
    installCmd: 'pip install s3scanner',
    installer: pipTool('s3scanner'),
    checkCmd: 's3scanner --help' },
  { name: 'byp4xx',     category: 'vuln', description: '403/401 bypass with header & path tricks',
    installCmd: 'go install -v github.com/lobuhi/byp4xx@latest',
    installer: goTool('github.com/lobuhi/byp4xx@latest'),
    checkCmd: 'byp4xx --help' },
  { name: 'kr',         category: 'http', description: 'Kiterunner — API endpoint discovery via route brute-force',
    installCmd: 'go install -v github.com/assetnote/kiterunner/cmd/kr@latest',
    installer: goTool('github.com/assetnote/kiterunner/cmd/kr@latest'),
    checkCmd: 'kr --help' },
]

/** Check if a tool binary is on PATH. Returns version string or null. */
export function checkTool(info: ToolInfo): { installed: boolean; version: string | null } {
  try {
    const out = execSync(info.checkCmd, {
      timeout: 5000,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env },
    })
    const text = out.toString().trim().split('\n')[0] ?? ''
    return { installed: true, version: text.slice(0, 80) || null }
  } catch (err) {
    // Tool may still be installed — only not_found if ENOENT
    const e = err as NodeJS.ErrnoException & { status?: number; stderr?: Buffer }
    if (e.code === 'ENOENT' || (e.message ?? '').includes('not found')) {
      return { installed: false, version: null }
    }
    // Non-zero exit (e.g. help text on stderr) still means installed
    const stderr = e.stderr?.toString().trim().split('\n')[0] ?? ''
    return { installed: true, version: stderr.slice(0, 80) || null }
  }
}

export function getToolsUpdateLogFile(): string {
  const home = process.env.HOME ?? '/tmp'
  const dir = process.env.GIVENUM_CONFIG_DIR ?? `${home}/.config/givenum`
  try { fs.mkdirSync(dir, { recursive: true }) } catch { /* ok */ }
  return `${dir}/tools_update.log`
}
