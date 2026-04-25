# GivEnum

**Reconnaissance and active-scanning platform for web targets.**
Subdomain enumeration, URL collection, JavaScript analysis, port scanning, vulnerability detection — driven from a CLI or a web dashboard, all from one container.

[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-blue)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-green)]()
[![Go](https://img.shields.io/badge/go-1.19%2B-00ADD8)]()
[![Next.js](https://img.shields.io/badge/next.js-15-000)]()
[![Docker](https://img.shields.io/badge/docker-ready-2496ED)]()

---

## What it is

GivEnum orchestrates 30+ open-source security tools (ProjectDiscovery, Tomnomnom, Hahwul, OWASP, Assetnote, etc.) into a coherent enumeration pipeline. You point it at a domain, it runs everything in parallel, normalizes the output, deduplicates, diffs against the previous run, and saves it as browsable artifacts plus an HTML report.

Two ways to drive it:

1. **CLI** (`GivEnum.py`) — a single Python orchestrator. Good for automation, cron, CI.
2. **Web dashboard** (`web/`) — Next.js 15 + React 19 frontend that spawns the same Python orchestrator, tails its log live, manages jobs, and lets you configure proxies, API keys and tool installations from the browser.

---

## Quick start — Docker (recommended)

The container ships with every tool pre-installed and the dashboard pre-built.

```bash
git clone https://github.com/6bat66/Givenum
cd Givenum

cp .env.example .env
$EDITOR .env                    # set GIVENUM_PASSWORD

docker compose up -d app        # first build ~8-12 min
open http://localhost:3000      # log in with the password you set
```

CLI mode using the same image:

```bash
docker compose run --rm scanner -d example.com            # passive
docker compose run --rm scanner -d example.com --active   # passive + active
```

Results land under `./results/<project>/<domain>_<timestamp>/`.

---

## Quick start — local install

### Prerequisites

- **OS**: macOS or Debian/Ubuntu/Kali
- **Runtimes**: Python 3.8+, Go 1.19+, Node.js 20+, Git, curl

### Install

```bash
git clone https://github.com/6bat66/Givenum
cd Givenum

chmod +x install_tools.sh
./install_tools.sh              # installs all 30+ tools, ~10 min
source ~/.zshrc                 # or ~/.bashrc — picks up $GOPATH/bin

python3 GivEnum.py --check-tools                # confirm everything resolved
python3 GivEnum.py --configure-api              # one-time API key setup

# Run your first scan
python3 GivEnum.py -d example.com
```

### Run the dashboard

```bash
cd web
npm install
npm run build
npm start                       # http://localhost:3000
```

---

## CLI cheatsheet

```bash
# Passive recon (default — safe, low signal)
python3 GivEnum.py -d example.com

# Active mode — includes naabu port scan, nuclei, dalfox, arjun, ffuf, kr
python3 GivEnum.py -d example.com --active

# Skip slow phases
python3 GivEnum.py -d example.com --active \
    --skip-screenshots \
    --skip-portscan \
    --skip-vuln-scan

# Disable Slack/Discord/Telegram notifications for one run
python3 GivEnum.py -d example.com --no-notify

# Tool sanity check
python3 GivEnum.py --check-tools

# (Re)configure API keys
python3 GivEnum.py --configure-api
```

`--check-tools` separates **critical** (scan can't start without them — `subfinder`, `httpx`, `dnsx`, plus `naabu`/`nuclei` for active mode), **recommended** (scan loses capability without them) and **optional**.

---

## Dashboard tour

| Page | What it does |
|---|---|
| `/` | Project list, active scans, finished scans. Quick rescan from any past scan. |
| `/job/[id]` | Live log of a running scan with ANSI colors, pause/resume/stop, per-tool stderr tail. |
| `/scan/[id]` | Tabbed result browser — overview, hosts, subdomains (alive-only filter), URLs (extension filter), nuclei findings, dalfox, ports, screenshots (external domains filtered out), diff vs previous run, raw tool logs. |
| `/settings/apis` | Manage API keys (Shodan, Censys, VirusTotal, SecurityTrails, GitHub token, Discord webhook, Telegram). Masked display; empty value clears the key. |
| `/settings/proxy` | Single-mode (e.g. Burp) or rotate-mode (fetched from 10 public proxy lists, validated via `curl --proxy`). |
| `/settings/tools` | Per-tool install status with version. Select one or many and update from the browser; live tail of the install log. |
| `/settings/reports` | Generate an HTML report for any past scan, ready to share. |

---

## Architecture

```
.
├── GivEnum.py                  # main orchestrator (~5k lines, will be modularised)
├── analyze_results.py          # standalone post-scan analyser
├── scan_runner.py              # thin wrapper used by the web UI to spawn a scan
├── install_tools.sh            # cross-platform tool installer (macOS / Debian / Kali)
├── batch_enum.sh               # CLI multi-domain runner
├── docker-compose.yml          # `app` (web + tools) and `scanner` (CLI) services
├── Dockerfile                  # builds the all-in-one image
├── results/                    # per-project, per-domain scan output
└── web/                        # Next.js 15 dashboard
    ├── src/app/                # routes (App Router)
    │   ├── api/                # job spawning, log tailing, settings, reports
    │   ├── settings/           # configuration sub-pages (apis, proxy, tools, reports)
    │   ├── job/[id]/           # live job page
    │   └── scan/[id]/          # scan result page
    ├── src/components/         # ScanTabs, JobLogViewer, ProxySettingsForm, etc.
    └── src/lib/                # results parser, app data, proxy fetcher, ANSI renderer
```

The web app does **not** scan — it spawns `python3 scan_runner.py` as a detached child and writes job metadata to `~/.config/givenum/jobs/`. The Python process writes scan output to `./results/`. The dashboard reads both to render.

### Output layout per scan

```
results/<project>/<domain>_YYYYMMDD_HHMMSS/
├── subdomains/                 # all_subdomains.txt + per-tool files
├── dns/                        # dnsx, tlsx, puredns
├── http/                       # alive.txt, httpx JSON
├── ports/                      # naabu output
├── urls/                       # urls_clean.txt, gau/wayback/katana raw
├── js/                         # subjs, jsubfinder, trufflehog
├── screenshots/                # gowitness PNGs
├── vulnerabilities/            # nuclei_results.txt, dalfox
├── parameters/                 # arjun
├── git/                        # exposed_git.txt, dumps
├── api_data/                   # kiterunner, JWTs, S3 buckets
├── takeover/                   # subzy
├── cloud/                      # cloud provider attribution
├── diff/                       # vs previous scan
├── reports/                    # report.md, report.html
└── logs/                       # per-tool stderr + execution_summary.json
```

---

## Tools used

**Subdomain discovery:** subfinder · amass · assetfinder · findomain · knockpy · github-subdomains · uncover · puredns

**DNS / resolution:** dnsx · puredns · massdns · tlsx · shuffledns

**HTTP probing & screenshots:** httpx · gowitness

**URL collection:** gau · waybackurls · katana · hakrawler · xurlfind3r · meg

**JavaScript & secrets:** subjs · jsubfinder · getJS · trufflehog

**Port scanning:** naabu · sdlookup (Shodan InternetDB)

**Vulnerability scanning:** nuclei · dalfox · subzy · subjack · byp4xx · ffuf · arjun · kiterunner · jwt-tool · s3scanner · sqlmap

**Utility:** anew · gf · uro · unfurl · qsreplace · freq · notify · interactsh-client

**Wordlists:** SecLists (raft-medium-directories.txt, common.txt) · Gf-Patterns

---

## API keys

Configure once via the CLI (`python3 GivEnum.py --configure-api`) or in the dashboard at `/settings/apis`. Storage is `~/.config/givenum/api.json`, keys are masked when displayed.

| Service | Used by |
|---|---|
| Shodan | subfinder, uncover, ReconEnricher |
| Censys (id + secret) | subfinder, amass, uncover |
| Fofa (email + key) | uncover |
| VirusTotal | passive subdomain enrichment |
| SecurityTrails | passive subdomain enrichment |
| CertSpotter | certificate transparency |
| Hunter.io | uncover |
| Netlas | uncover |
| GitHub PAT | github-subdomains |
| Discord webhook / Telegram bot / Slack webhook | NotificationManager |

---

## Proxy support

Two modes, configurable from `/settings/proxy`:

- **Single mode** — point GivEnum at one proxy (typical use: Burp on `http://127.0.0.1:8080`). Set `http`, `https` and an optional `noProxy` bypass list.
- **Rotate mode** — fetch the latest free proxy list from 10 public sources (proxyscrape, jetkai/proxy-list, GitHub mirrors), validate each one in batches of 40 with `curl`, and use only the working ones. Refresh from the dashboard; status polls live.

Proxies are validated with `execFile` (no shell) so a malicious entry in a public list cannot inject commands.

---

## Diff between scans

Every scan compares its output to the most recent previous run for the same domain (in the same project). The dashboard's **Diff** tab shows what's `new`, `removed` and `persisted` for subdomains, alive hosts, URLs, open ports and nuclei findings. Useful for change-monitoring a target you scan weekly.

---

## Notifications

If a Discord/Telegram/Slack credential is set, GivEnum posts a one-line summary at the end of each scan: domain, mode, counts, link to the report. Disable per-run with `--no-notify`.

---

## Roadmap

- Modularise `GivEnum.py` into a proper package (`givenum/recon`, `givenum/scanning`, etc.).
- Add a minimal pytest suite covering `OutputManager`, domain validation, diff computation, proxy normalisation.
- Per-host rate limiting (`HostBucket` semaphore) to avoid getting blocked when running multiple tools against the same target in parallel.
- Centralised exponential-backoff retry wrapper around `subprocess` tool calls.
- NDJSON job log so the dashboard can render a per-tool timeline without parsing ANSI text.

---

## Project structure for contributors

| Path | Owner |
|---|---|
| `GivEnum.py` | scan orchestration, all classes |
| `web/src/app/api/**` | Next.js API routes (job lifecycle, settings, reports) |
| `web/src/components/**` | React UI components |
| `web/src/lib/results.ts` | parses scan output into `ScanData` for the UI |
| `web/src/lib/app-data.ts` | filesystem layer for jobs, projects, configs |
| `web/src/lib/tools.ts` | tool registry (used by `/settings/tools`) |
| `web/src/lib/proxy-fetcher.ts` | proxy fetch + validation runner |
| `Dockerfile` | image build (Go installs, SecLists, gf-patterns, nuclei templates) |
| `install_tools.sh` | cross-platform local installer with summary counters |

---

## Disclaimer

This software is for authorized security testing and educational purposes only. Use only against targets you own or have explicit written permission to test. The author and contributors take no responsibility for misuse.

---

## License

Released under the MIT License — see `LICENSE` for details.
