# GivEnum

**Reconnaissance framework with web dashboard — subdomain discovery, URL collection, vulnerability scanning and asset analysis.**

[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-blue)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-green)]()
[![Go](https://img.shields.io/badge/go-1.19%2B-00ADD8)]()
[![Docker](https://img.shields.io/badge/docker-ready-2496ED)]()

---

## Overview

GivEnum orchestrates 30+ security tools for comprehensive web reconnaissance. Run it from the CLI or use the built-in **Next.js web dashboard** to start scans, monitor live output, manage projects and browse results from any browser.

### Key Features

- **Web Dashboard** — Start scans, watch live logs, manage jobs/scans/projects from the browser
- **Docker-first** — Single `docker compose up` runs the full stack (tools + dashboard)
- **Password Protected** — Dashboard requires a password; set `GIVENUM_PASSWORD` in `.env`
- **Job Management** — Stop, pause and resume running scans; delete old jobs and results
- **Passive/Active Mode** — Default is silent passive recon; `--active` unlocks brute-force, nuclei, dalfox, arjun, subjack
- **Multi-Source Subdomain Enum** — Combines 8+ tools and APIs for maximum coverage
- **URL Collection** — xurlfind3r, gau, waybackurls, hakrawler
- **JavaScript Analysis** — jsubfinder, subjs, getJS
- **Port Scanning** — sdlookup (Shodan InternetDB, no noise)
- **Vulnerability Scanning** — Nuclei with 3000+ templates (active mode)
- **XSS Detection** — Dalfox (active mode)
- **Git Exposure** — goop + git-dumper automatic detection and dump
- **Diff Tracking** — Change monitoring between scans
- **API Integration** — VirusTotal, SecurityTrails, CertSpotter, AlienVault OTX
- **Tool Execution Logs** — Every tool's stderr saved to `logs/`, summary printed at end of scan

---

## Quick Start — Docker (recommended)

```bash
git clone https://github.com/6bat66/Givenum
cd Givenum

# Set your dashboard password
cp .env.example .env
nano .env   # set GIVENUM_PASSWORD

# Build and start (first run ~10 min — installs all tools)
docker compose up -d app

# Open dashboard
open http://localhost:3000
```

From the dashboard you can start scans, watch real-time output, stop/pause jobs, and browse results.

### CLI scan using the same Docker image

```bash
docker compose run --rm scanner -d example.com --active
```

---

## Quick Start — Local (no Docker)

### Requirements

- macOS or Debian/Kali Linux
- Python 3.8+, Go 1.19+, Git

```bash
git clone https://github.com/6bat66/Givenum
cd Givenum
chmod +x install_tools.sh GivEnum.py

# Install all tools (~10-15 min)
./install_tools.sh
source ~/.zshrc   # or ~/.bashrc

# Configure API keys
python3 GivEnum.py --configure-api

# Verify
python3 GivEnum.py --check-tools
```

---

## CLI Usage

```bash
# Passive scan — subdomain discovery, HTTP, URLs, JS, git, takeover
python3 GivEnum.py -d example.com

# Active scan — adds brute-force, ports, nuclei, dalfox, subjack, arjun
python3 GivEnum.py -d example.com --active

# Skip heavy steps
python3 GivEnum.py -d example.com --active --skip-screenshots --skip-portscan
python3 GivEnum.py -d example.com --active --skip-vuln-scan

# Custom output directory
python3 GivEnum.py -d example.com -o /path/to/output

# Check installed tools
python3 GivEnum.py --check-tools
```

### All flags

| Flag | Description |
|------|-------------|
| `-d DOMAIN` | Target domain |
| `-o OUTPUT` | Output directory (default: `./results`) |
| `--active` | Enable active scanning |
| `--skip-screenshots` | Skip gowitness |
| `--skip-portscan` | Skip sdlookup port scan |
| `--skip-vuln-scan` | Skip nuclei + dalfox |
| `--check-tools` | Print tool status and exit |
| `--configure-api` | Configure API keys interactively |

---

## Web Dashboard

The dashboard is a Next.js app bundled inside the Docker image.

### Features

| Feature | Description |
|---------|-------------|
| **Projects** | Organize scans into projects |
| **Start Scan** | Launch passive or active scans from the browser |
| **Live Logs** | Real-time ANSI-colored terminal output |
| **Job Control** | Stop, pause, resume running jobs |
| **Management** | Delete jobs, scans and projects |
| **Progress Bar** | Shows current scan phase |
| **Scan Browser** | Subdomains, HTTP hosts, URLs, vulns, ports, JS files, screenshots |
| **Diff View** | Changes detected since previous scan |
| **API Keys** | Configure tool API keys from the settings page |

### Authentication

Set `GIVENUM_PASSWORD` in `.env` — any unauthenticated request redirects to `/login`. Leave it empty to disable auth for local development.

```env
GIVENUM_PASSWORD=your-strong-password
APP_PORT=3000
```

### VPS Deploy

```bash
ssh root@your-vps

curl -fsSL https://get.docker.com | sh

git clone -b organize-web-enum-tools https://github.com/6bat66/Givenum
cd Givenum
cp .env.example .env
nano .env   # set GIVENUM_PASSWORD

docker compose up -d app
docker compose logs -f app
```

For HTTPS and access control on a public VPS, put Cloudflare Access or a reverse proxy (Caddy/nginx) in front of port 3000.

---

## Passive vs Active Mode

| Feature | Passive (default) | Active (`--active`) |
|---|:---:|:---:|
| Subdomain discovery (passive APIs) | ✓ | ✓ |
| DNS resolution + HTTP probing | ✓ | ✓ |
| Screenshots (gowitness) | ✓ | ✓ |
| URL collection | ✓ | ✓ |
| JS analysis + git exposure | ✓ | ✓ |
| Takeover check (subzy) | ✓ | ✓ |
| DNS brute-force (puredns) | — | ✓ |
| Port scan (sdlookup/Shodan) | — | ✓ |
| Vulnerability scan (nuclei) | — | ✓ |
| XSS scan (dalfox) | — | ✓ |
| Parameter discovery (arjun) | — | ✓ |
| Takeover check (subjack) | — | ✓ |

---

## Output Structure

```
results/example.com_20250122_123456/
├── subdomains/       all_subdomains.txt, bruteforce.txt (--active), per-tool files
├── api_data/         virustotal, alienvault, securitytrails
├── dns/              resolved.txt, a_records.txt, cname_records.txt
├── http/             alive.txt, httpx_full.json
├── urls/             urls_clean.txt, per-tool files
├── js/               all_js_files.txt, jsubfinder_results.txt
├── git/              exposed_git.txt, dumped repos
├── ports/            open_ports.txt, sdlookup_results.json  (--active)
├── vulnerabilities/  nuclei_results.txt, dalfox_results.txt (--active)
├── parameters/       interesting_parameters.txt, arjun_params.txt (--active)
├── cloud/            aws_services.txt, azure_services.txt, gcp_services.txt
├── takeover/         subzy_results.json, subjack_results.txt (--active)
├── screenshots/      gowitness output
├── diff/             *.diff files vs previous scan
├── reports/          report.md, report.json, analysis.md
└── logs/             per-tool stderr logs + execution_summary.json
```

---

## Tool Stack

### Passive

| Tool | Purpose |
|------|---------|
| subfinder | Passive subdomain discovery |
| assetfinder | Subdomain enumeration |
| findomain | Fast subdomain finder |
| amass | In-depth subdomain enum |
| github-subdomains | GitHub code search for subdomains (needs token) |
| uncover | Multi-engine OSINT — Shodan, Censys, Fofa, Hunter, Netlas |
| tlsx | TLS cert SAN extraction for new subdomains |
| dnsx | Fast DNS resolver |
| httpx | HTTP probe & analyzer |
| gowitness | Screenshot capture |
| xurlfind3r | Unified URL finder |
| gau | Get All URLs (archive, root domain) |
| waybackurls | Wayback Machine URLs (root domain) |
| katana | Modern active web crawler |
| hakrawler | Web crawler |
| subjs / getJS | JS file collection |
| jsubfinder | JS endpoint finder |
| trufflehog | Secret scanning in JS and git dumps |
| subzy | Subdomain takeover check |
| goop / git-dumper | Git repo dumper |

### Active (`--active`)

| Tool | Purpose |
|------|---------|
| puredns | DNS brute-force |
| massdns | High-performance DNS resolution |
| sdlookup | Port scan via Shodan InternetDB |
| nuclei | Vulnerability scanning (3000+ templates) |
| dalfox | Automated XSS detection |
| arjun | HTTP parameter discovery |
| subjack | Subdomain takeover |

---

## API Configuration

```bash
# Interactive
python3 GivEnum.py --configure-api

# Manual
mkdir -p ~/.config/givenum
cat > ~/.config/givenum/api_keys.json << 'EOF'
{
  "virustotal": "YOUR_KEY",
  "securitytrails": "YOUR_KEY",
  "certspotter": "YOUR_KEY",
  "shodan": "YOUR_KEY"
}
EOF
```

API keys can also be configured from the dashboard Settings page.

With keys configured expect **50–200% more subdomains** discovered.

---

## Batch Processing

```bash
./batch_enum.sh domains.txt
./batch_enum.sh domains.txt --active
./batch_enum.sh domains.txt --parallel 3
./batch_enum.sh domains.txt --delay 60
```

---

## Troubleshooting

**Tool not found**
```bash
python3 GivEnum.py --check-tools
./install_tools.sh
```

**puredns returns 0 subdomains**

Expected for targets behind Cloudflare/Akamai CDN — anycast IPs cause trusted-resolver validation to drop results. httpx resolves independently and will still find active hosts.

**View tool logs**
```bash
cat results/*/logs/execution_summary.json
tail -f results/*/logs/subfinder.log
```

---

## Security & Legal

Use only on systems you have explicit permission to test: your own infrastructure, bug bounty programs (within scope), or authorized engagements.

---

## Changelog

### v4.0 — In Development

> **Not stable yet.** The web dashboard and Docker support are actively being developed. Use v3 for production work.

**Web Dashboard (WIP)**
- Next.js dashboard: start scans, browse results, manage jobs
- Real-time log streaming with ANSI color rendering
- Stop, pause and resume running jobs
- Delete jobs, scans and projects from the UI
- Password-based auth (`GIVENUM_PASSWORD`)

**Docker (WIP)**
- Single `docker compose up app` runs the full stack
- `docker compose run --rm scanner` for CLI scans using the same image

**Tool Logging**
- All tool stderr saved to `logs/<tool>.log`
- `logs/execution_summary.json` with status, exit code and timing per tool
- Summary table printed at end of every scan

---

### v3.0 (stable — recommended for CLI use)

> The CLI is fully stable and works standalone — no Docker or web required.
>
> ```bash
> # Install
> ./install_tools.sh
>
> # Run
> python3 GivEnum.py -d example.com
> python3 GivEnum.py -d example.com --active
> ```

- `--active` flag gates all intrusive tools behind a single flag
- Default run is fully passive
- Dalfox XSS scanning (active mode)
- Subjack takeover check (active mode)
- Arjun parameter discovery (active mode)
- Fixed xurlfind3r, gau v2 and waybackurls input handling

### v2.0

- Modern URL collection (xurlfind3r)
- JavaScript analysis (jsubfinder)
- Port scanning via sdlookup/Shodan
- Git repository dumping
- Cross-platform support (macOS + Linux)
- Diff tracking between scans

---

## Acknowledgments

- [ProjectDiscovery](https://github.com/projectdiscovery) — subfinder, httpx, nuclei, dnsx, dalfox
- [TomNomNom](https://github.com/tomnomnom) — waybackurls, anew, unfurl, assetfinder
- [OWASP Amass](https://github.com/owasp-amass/amass)
- [Findomain](https://github.com/Findomain/Findomain)
- [xurlfind3r](https://github.com/hueristiq/xurlfind3r)
- [jsubfinder](https://github.com/ThreatUnknown/jsubfinder)
- [sdlookup](https://github.com/j3ssie/sdlookup)
- [goop](https://github.com/nyancrimew/goop)
- [arjun](https://github.com/s0md3v/Arjun)
- [subjack](https://github.com/haccer/subjack)
