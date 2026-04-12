# GivEnum - Modern Web Enumeration Framework

**Advanced reconnaissance framework for comprehensive subdomain discovery, URL collection, vulnerability scanning, and asset analysis.**

[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-blue)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-green)]()
[![Go](https://img.shields.io/badge/go-1.19%2B-00ADD8)]()

---

## Overview

GivEnum is a modern, comprehensive web enumeration framework designed for security professionals conducting reconnaissance during bug bounty hunting, penetration testing, and security assessments. It orchestrates 30+ security tools to provide complete attack surface visibility.

### Key Features

- **Multi-Source Subdomain Enumeration** - Combines 8+ tools and APIs for maximum coverage
- **Passive/Active Mode** - Default runs silent passive recon; `--active` unlocks brute-force, port scan, nuclei, dalfox, arjun, subjack
- **Advanced URL Collection** - Modern tools (xurlfind3r, gau, waybackurls, hakrawler) for comprehensive URL discovery
- **JavaScript Analysis** - Dedicated JS file collection and analysis (jsubfinder, subjs)
- **Fast Port Scanning** - Uses sdlookup (Shodan InternetDB) instead of slow nmap
- **Git Repository Dumping** - Automatic detection and dumping with goop/git-dumper
- **Vulnerability Scanning** - Nuclei integration with 3000+ templates (active mode)
- **XSS Detection** - Dalfox automated XSS scanning (active mode)
- **Cloud Service Detection** - Identifies AWS, Azure, GCP resources
- **Diff Tracking** - Monitors changes between scans
- **Professional Reports** - Markdown and JSON output formats
- **API Integration** - VirusTotal, SecurityTrails, CertSpotter, AlienVault OTX
- **Certificate Transparency** - Queries crt.sh and CertSpotter logs

---

## Quick Start

### Prerequisites

- **Operating System**: macOS or Debian/Kali Linux
- **Go**: 1.19 or higher
- **Python**: 3.8 or higher
- **Git**: For cloning repositories

### Installation

```bash
# Clone the repository
git clone https://github.com/6bat66/GivEnum
cd GivEnum

# Make scripts executable
chmod +x install_tools.sh GivEnum.py

# Install all tools (takes 10-15 minutes)
./install_tools.sh

# Reload shell environment
source ~/.zshrc  # or ~/.bashrc

# Configure API keys (recommended for better results)
python3 GivEnum.py --configure-api

# Verify installation
python3 GivEnum.py --check-tools
```

### Basic Usage

```bash
# Passive scan (default) — subdomain discovery, HTTP, URLs, JS, git, takeover
python3 GivEnum.py -d example.com

# Active scan — adds brute-force, port scan, nuclei, dalfox, subjack, arjun
python3 GivEnum.py -d example.com --active

# Active but skip heavy steps
python3 GivEnum.py -d example.com --active --skip-screenshots --skip-portscan

# Active but skip vuln scan (nuclei + dalfox)
python3 GivEnum.py -d example.com --active --skip-vuln-scan

# Custom output directory
python3 GivEnum.py -d example.com -o /path/to/output
```

---

## Documentation

### Command Line Options

```
usage: GivEnum.py [-h] [-d DOMAIN] [-o OUTPUT] [--active]
                  [--skip-screenshots] [--skip-portscan] [--skip-vuln-scan]
                  [--check-tools] [--configure-api]

Arguments:
  -d, --domain          Target domain (e.g., example.com)
  -o, --output          Output directory (default: ./results)
  --active              Enable active scanning (brute-force, port scan,
                        nuclei, dalfox, subjack, arjun)
  --skip-screenshots    Skip screenshot capture with gowitness
  --skip-portscan       Skip port scanning with sdlookup (active mode)
  --skip-vuln-scan      Skip vulnerability scanning with nuclei + dalfox (active mode)
  --check-tools         Check installed tools and exit
  --configure-api       Configure API keys interactively
  -h, --help            Show help message
```

### Passive vs Active Mode

| Feature | Passive (default) | Active (`--active`) |
|---|:---:|:---:|
| Subdomain discovery (passive APIs) | ✓ | ✓ |
| DNS resolution + HTTP probing | ✓ | ✓ |
| Screenshots (gowitness) | ✓ | ✓ |
| URL collection (gau, waybackurls, hakrawler) | ✓ | ✓ |
| JS analysis + git exposure | ✓ | ✓ |
| Takeover check (subzy) | ✓ | ✓ |
| **DNS brute-force (puredns + wordlist)** | — | ✓ |
| **Port scan (sdlookup/Shodan)** | — | ✓ |
| **Vulnerability scan (nuclei)** | — | ✓ |
| **XSS scan (dalfox)** | — | ✓ |
| **Parameter discovery (arjun)** | — | ✓ |
| **Takeover check (subjack)** | — | ✓ |

### Output Structure

```
results/example.com_20250122_123456/
├── subdomains/           # Subdomain enumeration results
│   ├── all_subdomains.txt       # All unique subdomains (passive)
│   ├── bruteforce.txt           # Brute-forced subdomains (--active)
│   ├── subfinder.txt
│   ├── assetfinder.txt
│   ├── findomain.txt
│   ├── amass.txt
│   ├── crtsh.txt               # Certificate Transparency
│   └── certspotter.txt
│
├── api_data/            # API query results
│   ├── virustotal.txt
│   ├── virustotal.json
│   ├── alienvault.txt
│   └── securitytrails.txt
│
├── dns/                 # DNS resolution
│   ├── resolved.txt            # Live subdomains
│   ├── a_records.txt
│   └── cname_records.txt
│
├── ports/               # Port scanning results (--active)
│   ├── sdlookup_results.json
│   └── open_ports.txt
│
├── http/                # HTTP probing
│   ├── alive.txt               # Active web services
│   ├── httpx_full.json         # Detailed HTTP info
│   └── url_status.txt
│
├── urls/                # URL collection
│   ├── urls_raw.txt
│   ├── urls_clean.txt          # Cleaned/deduped URLs
│   ├── xurlfind3r.txt
│   ├── gau.txt
│   └── waybackurls.txt
│
├── js/                  # JavaScript analysis
│   ├── all_js_files.txt
│   ├── subjs.txt
│   ├── getjs.txt
│   └── jsubfinder_results.txt  # Endpoints from JS
│
├── git/                 # Git repository findings
│   ├── exposed_git.txt
│   └── [domain]/               # Dumped repositories
│
├── vulnerabilities/     # Security findings
│   ├── nuclei_results.txt      # Nuclei findings (--active)
│   ├── nuclei_results.json
│   ├── dalfox_targets.txt      # XSS targets tested (--active)
│   └── dalfox_results.txt      # XSS findings (--active)
│
├── parameters/          # Parameter analysis
│   ├── all_parameters.txt
│   ├── interesting_parameters.txt
│   └── arjun_params.txt        # Discovered params (--active)
│
├── cloud/               # Cloud service detection
│   ├── aws_services.txt
│   ├── azure_services.txt
│   └── gcp_services.txt
│
├── takeover/            # Subdomain takeover
│   ├── subzy_results.json      # Passive check
│   └── subjack_results.txt     # Active check (--active)
│
├── screenshots/         # Visual reconnaissance
│   └── [gowitness output]
│
├── diff/                # Change tracking
│   ├── all_subdomains.txt.diff
│   └── alive.txt.diff
│
├── reports/             # Final reports
│   ├── report.md               # Human-readable
│   └── report.json             # Machine-parseable
│
└── logs/                # Execution logs
```

---

## Tool Stack

### Passive Recon (runs by default)

| Tool | Purpose |
|------|---------|
| **subfinder** | Passive subdomain discovery |
| **assetfinder** | Subdomain enumeration |
| **findomain** | Fast subdomain finder |
| **amass** | In-depth subdomain enum |
| **dnsx** | Fast DNS resolver |
| **httpx** | HTTP probe & analyzer |
| **gowitness** | Screenshot capture |
| **xurlfind3r** | Unified URL finder |
| **gau** | Get All URLs (archive) |
| **waybackurls** | Wayback Machine URLs |
| **hakrawler** | Web crawler |
| **subjs / getJS** | JS file collection |
| **jsubfinder** | JS endpoint finder |
| **subzy** | Subdomain takeover check |
| **goop / git-dumper** | Git repo dumper |

### Active Recon (`--active` only)

| Tool | Purpose |
|------|---------|
| **puredns** | DNS brute-force with wordlist |
| **massdns** | High-performance DNS resolution |
| **sdlookup** | Port scanning via Shodan InternetDB |
| **nuclei** | Vulnerability scanning (3000+ templates) |
| **dalfox** | Automated XSS detection |
| **arjun** | HTTP parameter discovery |
| **subjack** | Subdomain takeover (active) |

### Utilities

| Tool | Purpose |
|------|---------|
| **anew** | Append unique lines |
| **uro** | URL deduplication |
| **unfurl** | URL extraction |
| **qsreplace** | Query string replacement |

---

## API Configuration

### Supported Services

1. **VirusTotal** (Free/Paid) — Subdomain enumeration, domain reputation
2. **SecurityTrails** (Free/Paid) — Historical DNS data, subdomain intelligence
3. **CertSpotter** (Free/Paid) — Certificate monitoring
4. **AlienVault OTX** (Free) — Threat intelligence, passive DNS
5. **Shodan** (Optional) — Used by sdlookup for port data

### Configuration

```bash
# Interactive configuration
python3 GivEnum.py --configure-api

# Manual configuration
mkdir -p ~/.config/givenum
cat > ~/.config/givenum/api_keys.json << 'EOF'
{
  "virustotal": "YOUR_VT_API_KEY",
  "securitytrails": "YOUR_ST_API_KEY",
  "certspotter": "YOUR_CS_API_KEY",
  "shodan": "YOUR_SHODAN_API_KEY"
}
EOF
```

With API keys configured you can expect **50-200% more subdomains** discovered.

---

## Usage Examples

### Bug Bounty Hunting

```bash
# Step 1: Passive recon (fast, no noise)
python3 GivEnum.py -d target.com

# Step 2: Review findings
cat results/target.com_*/reports/report.md
python3 analyze_results.py results/target.com_*/

# Step 3: Active scan on interesting targets
python3 GivEnum.py -d api.target.com --active
python3 GivEnum.py -d admin.target.com --active --skip-portscan

# Step 4: Review active findings
cat results/target.com_*/vulnerabilities/nuclei_results.txt
cat results/target.com_*/vulnerabilities/dalfox_results.txt
cat results/target.com_*/takeover/subjack_results.txt
```

### Red Team Assessment

```bash
# Stealthy passive reconnaissance (no noise)
python3 GivEnum.py -d corp.com

# Check quick wins
cat results/corp.com_*/git/exposed_git.txt
cat results/corp.com_*/takeover/subzy_results.json

# Full active assessment (authorized)
python3 GivEnum.py -d corp.com --active

# Review all active findings
grep "high\|critical" results/corp.com_*/vulnerabilities/nuclei_results.txt
cat results/corp.com_*/vulnerabilities/dalfox_results.txt
cat results/corp.com_*/ports/open_ports.txt
```

### Continuous Monitoring

```bash
# Daily cron job
0 2 * * * cd /opt/givenum && python3 GivEnum.py -d target.com --skip-screenshots

# Check changes
cat results/target.com_*/diff/*.diff

# Alert on new findings
NEW=$(wc -l < results/target.com_*/diff/all_subdomains.txt.diff)
[ "$NEW" -gt 0 ] && echo "New subdomains: $NEW"
```

### Penetration Testing

```bash
# Comprehensive assessment
python3 GivEnum.py -d client.com --active

# Analyze results
python3 analyze_results.py results/client.com_*/
grep -E "(id=|file=|redirect=)" results/client.com_*/urls/urls_clean.txt
cat results/client.com_*/parameters/interesting_parameters.txt
cat results/client.com_*/cloud/aws_services.txt
```

---

## Analysis

### Analyze Results

```bash
# Full analysis
python3 analyze_results.py results/example.com_20250122_123456/

# Summary only
python3 analyze_results.py results/example.com_*/ --summary-only

# Export markdown report
python3 analyze_results.py results/example.com_*/ --export report.md
```

### Useful One-Liners

```bash
# Admin panels
grep -i "admin\|dashboard\|panel" results/*/http/httpx_full.json

# API endpoints
grep -i "api" results/*/urls/urls_clean.txt

# Development environments
grep -E "(dev|staging|test|uat)" results/*/subdomains/all_subdomains.txt

# Exposed Git repos
cat results/*/git/exposed_git.txt

# URLs with parameters
grep '?' results/*/urls/urls_clean.txt

# JavaScript files
cat results/*/js/all_js_files.txt

# Open ports (--active)
cat results/*/ports/open_ports.txt

# Vulnerabilities (--active)
cat results/*/vulnerabilities/nuclei_results.txt

# XSS findings (--active)
cat results/*/vulnerabilities/dalfox_results.txt

# Status codes
jq '.status_code' results/*/http/httpx_full.json | sort | uniq -c

# Technologies detected
jq '.tech[]' results/*/http/httpx_full.json | sort -u
```

### Vulnerability Patterns

```bash
# LFI/Path Traversal
grep -E "(file=|path=|page=|include=)" results/*/urls/urls_clean.txt

# SQL Injection
grep -E "(id=|user=|product=|category=)" results/*/urls/urls_clean.txt

# Open Redirect
grep -E "(redirect=|url=|return=|next=)" results/*/urls/urls_clean.txt

# SSRF
grep -E "(url=|uri=|target=|dest=)" results/*/urls/urls_clean.txt

# XSS
grep -E "(search=|query=|q=|keyword=)" results/*/urls/urls_clean.txt
```

---

## Workflow Integration

### Burp Suite

```bash
cat results/*/urls/urls_clean.txt > burp_targets.txt
```

### SQLMap

```bash
cat results/*/parameters/interesting_parameters.txt | while read url; do
    sqlmap -u "$url" --batch --risk=2 --level=3
done
```

### Dalfox (manual XSS)

```bash
cat results/*/urls/urls_clean.txt | grep '?' | dalfox pipe
```

---

## Performance Tips

```bash
# Fast passive scan (skip screenshots)
python3 GivEnum.py -d target.com --skip-screenshots

# Active scan without port scan
python3 GivEnum.py -d target.com --active --skip-portscan

# Active scan without vuln scan
python3 GivEnum.py -d target.com --active --skip-vuln-scan

# Fastest possible active
python3 GivEnum.py -d target.com --active --skip-screenshots --skip-portscan --skip-vuln-scan
```

The tool automatically uses:
- Thread pools for subdomain enumeration (3 workers)
- Parallel DNS resolution (puredns)
- Concurrent HTTP probing (httpx)

---

## Troubleshooting

**`Tool not found`**
```bash
python3 GivEnum.py --check-tools
./install_tools.sh
```

**`Permission denied`**
```bash
chmod +x GivEnum.py install_tools.sh
```

**`API rate limiting`**
```bash
python3 GivEnum.py --configure-api
```

**`puredns returns 0 subdomains`**

This is expected for targets behind Akamai or Cloudflare CDN. These CDNs use anycast IPs — different resolvers return different IPs, causing puredns trusted-resolver validation to discard results as false wildcards. httpx resolves independently and will still find active hosts.

**`Scans taking too long`**
```bash
python3 GivEnum.py -d target.com --skip-portscan --skip-vuln-scan --skip-screenshots
```

**View logs**
```bash
tail -f results/*/logs/*.log
grep -i error results/*/logs/*.log
```

---

## File Locations

```
~/.config/givenum/api_keys.json    # API keys
~/.config/givenum/wordlists/       # Brute-force wordlists
./results/                          # Scan results
./batch_logs/                       # Batch processing logs
```

**Important output files:**
```
results/*/reports/report.md                     # Main report
results/*/subdomains/all_subdomains.txt          # All subdomains (passive)
results/*/subdomains/bruteforce.txt              # Brute-forced subdomains (--active)
results/*/http/alive.txt                         # Active HTTP hosts
results/*/urls/urls_clean.txt                    # Deduplicated URLs
results/*/ports/open_ports.txt                   # Open ports (--active)
results/*/vulnerabilities/nuclei_results.txt     # Nuclei findings (--active)
results/*/vulnerabilities/dalfox_results.txt     # XSS findings (--active)
results/*/takeover/subzy_results.json            # Takeover check (passive)
results/*/takeover/subjack_results.txt           # Takeover check (--active)
results/*/git/exposed_git.txt                    # Exposed .git dirs
results/*/parameters/interesting_parameters.txt  # Interesting URL params
results/*/diff/*.diff                            # Changes from last scan
```

---

## Batch Processing

```bash
# Process multiple domains
./batch_enum.sh domains.txt

# Parallel processing
./batch_enum.sh domains.txt --parallel 3

# With delay between scans
./batch_enum.sh domains.txt --delay 60

# Skip optional steps
./batch_enum.sh domains.txt --skip-screenshots --skip-portscan
```

---

## Security & Legal

**ONLY** use this tool on systems you have explicit permission to test:

- Your own systems
- Bug bounty programs (within scope)
- Authorized penetration tests
- Security research with permission

This tool is provided for educational and authorized security testing purposes only. Users are responsible for complying with all applicable laws and regulations. The authors assume no liability for misuse or damage caused by this tool.

---

## Changelog

### v3.0 (Current)

**New Features:**
- `--active` flag — gates all intrusive tools behind a single flag (brute-force, port scan, nuclei, dalfox, arjun, subjack)
- Default run is now fully passive — no DNS brute-force, no vuln scan, no noise
- Dalfox XSS scanning integrated (active mode)
- Subjack takeover check integrated (active mode)
- Arjun parameter discovery gated to active mode

**Bug Fixes:**
- Fixed `xurlfind3r` flag (`-silent` → `--silent`)
- Fixed `gau` v2 input — now reads domains from stdin instead of positional args
- Fixed `waybackurls` input — now extracts bare hostnames instead of passing full URLs
- Added informational tip for puredns 0 results on Akamai/Cloudflare CDN targets

### v2.0

**New Features:**
- Modern URL collection with xurlfind3r
- JavaScript analysis with jsubfinder
- Fast port scanning with sdlookup (replaces nmap)
- Git repository dumping with goop
- Enhanced Certificate Transparency queries
- Cross-platform support (macOS + Linux)
- Professional markdown reports
- Diff tracking between scans

---

## Acknowledgments

This framework orchestrates the following open-source tools:

- [ProjectDiscovery](https://github.com/projectdiscovery) - subfinder, httpx, nuclei, dnsx, dalfox
- [TomNomNom](https://github.com/tomnomnom) - waybackurls, anew, unfurl, assetfinder
- [OWASP Amass](https://github.com/owasp-amass/amass)
- [Findomain](https://github.com/Findomain/Findomain)
- [xurlfind3r](https://github.com/hueristiq/xurlfind3r)
- [jsubfinder](https://github.com/ThreatUnknown/jsubfinder)
- [sdlookup](https://github.com/j3ssie/sdlookup)
- [goop](https://github.com/nyancrimew/goop)
- [arjun](https://github.com/s0md3v/Arjun)
- [subjack](https://github.com/haccer/subjack)

---

**Happy Hunting!**
