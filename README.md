# WebEnum - Modern Web Enumeration Framework

**Advanced reconnaissance framework for comprehensive subdomain discovery, URL collection, vulnerability scanning, and asset analysis.**

[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-blue)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-green)]()
[![Go](https://img.shields.io/badge/go-1.19%2B-00ADD8)]()

---

## 🎯 Overview

WebEnum is a modern, comprehensive web enumeration framework designed for security professionals conducting reconnaissance during bug bounty hunting, penetration testing, and security assessments. It orchestrates 30+ security tools to provide complete attack surface visibility.

### Key Features

- **🔍 Multi-Source Subdomain Enumeration** - Combines 8+ tools and APIs for maximum coverage
- **🌐 Advanced URL Collection** - Modern tools (xurlfind3r, Photon) for comprehensive URL discovery
- **📜 JavaScript Analysis** - Dedicated JS file collection and analysis (jsubfinder, subjs)
- **⚡ Fast Port Scanning** - Uses sdlookup (Shodan InternetDB) instead of slow nmap
- **🔓 Git Repository Dumping** - Automatic detection and dumping with goop/git-dumper
- **🛡️ Vulnerability Scanning** - Nuclei integration with 3000+ templates
- **☁️ Cloud Service Detection** - Identifies AWS, Azure, GCP resources
- **📊 Diff Tracking** - Monitors changes between scans
- **📝 Professional Reports** - Markdown and JSON output formats
- **🔐 API Integration** - VirusTotal, SecurityTrails, CertSpotter, AlienVault OTX
- **🔄 Certificate Transparency** - Queries crt.sh and CertSpotter logs

---

## 🚀 Quick Start

### Prerequisites

- **Operating System**: macOS or Debian/Kali Linux
- **Go**: 1.19 or higher
- **Python**: 3.8 or higher
- **Git**: For cloning repositories

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/webenum
cd webenum

# Make scripts executable
chmod +x install_tools.sh webenum.py

# Install all tools (takes 10-15 minutes)
./install_tools.sh

# Reload shell environment
source ~/.zshrc  # or ~/.bashrc

# Configure API keys (recommended for better results)
python3 webenum.py --configure-api

# Verify installation
python3 webenum.py --check-tools
```

### Basic Usage

```bash
# Standard scan
python3 webenum.py -d example.com

# Fast scan (skip optional steps)
python3 webenum.py -d example.com --skip-screenshots --skip-portscan

# Full scan with vulnerability assessment
python3 webenum.py -d example.com

# Custom output directory
python3 webenum.py -d example.com -o /path/to/output
```

---

## 📚 Documentation

### Command Line Options

```
usage: webenum.py [-h] [-d DOMAIN] [-o OUTPUT] [--skip-screenshots] 
                  [--skip-portscan] [--skip-vuln-scan] [--check-tools] 
                  [--configure-api]

Arguments:
  -d, --domain          Target domain (e.g., example.com)
  -o, --output          Output directory (default: ./results)
  --skip-screenshots    Skip screenshot capture with gowitness
  --skip-portscan       Skip port scanning with sdlookup
  --skip-vuln-scan      Skip vulnerability scanning with Nuclei
  --check-tools         Check installed tools and exit
  --configure-api       Configure API keys interactively
  -h, --help            Show help message
```

### Output Structure

```
results/example.com_20250122_123456/
├── subdomains/           # Subdomain enumeration results
│   ├── all_subdomains.txt       # All unique subdomains
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
├── ports/               # Port scanning results
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
│   ├── nuclei_results.txt
│   └── nuclei_results.json
│
├── parameters/          # Parameter analysis
│   ├── all_parameters.txt
│   ├── interesting_parameters.txt
│   └── arjun_params.txt
│
├── cloud/               # Cloud service detection
│   ├── aws_services.txt
│   ├── azure_services.txt
│   └── gcp_services.txt
│
├── takeover/            # Subdomain takeover
│   └── subzy_results.txt
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

## 🔧 Tool Stack

### Core Enumeration (Required)

| Tool | Purpose | Installation |
|------|---------|-------------|
| **subfinder** | Passive subdomain discovery | `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest` |
| **assetfinder** | Subdomain enumeration | `go install github.com/tomnomnom/assetfinder@latest` |
| **findomain** | Fast subdomain finder | Binary download or `brew install findomain` |
| **amass** | In-depth subdomain enum | `go install github.com/owasp-amass/amass/v4/...@master` |
| **dnsx** | Fast DNS resolver | `go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest` |
| **puredns** | Subdomain resolver | `go install github.com/d3mondev/puredns/v2@latest` |
| **massdns** | High-performance DNS | Compile from source or `brew install massdns` |
| **httpx** | HTTP probe & analyzer | `go install github.com/projectdiscovery/httpx/cmd/httpx@latest` |

### Modern URL Collection

| Tool | Purpose | Why It's Better |
|------|---------|----------------|
| **xurlfind3r** | Unified URL finder | Combines multiple sources efficiently |
| **gau** | Get All URLs | Fast archive queries |
| **waybackurls** | Wayback Machine | Historical URL data |
| **hakrawler** | Web crawler | Live site crawling |
| **photon** | Targeted crawler | Deep crawling with intelligence |

### JavaScript Analysis

| Tool | Purpose | Output |
|------|---------|--------|
| **subjs** | JS file collector | Lists all JS files |
| **getJS** | JS extractor | Extracts JavaScript |
| **jsubfinder** | JS endpoint finder | Finds hidden endpoints in JS |

### Fast Port Scanning

| Tool | Purpose | Advantage |
|------|---------|----------|
| **sdlookup** | Port scanner via Shodan InternetDB | 10x faster than nmap, provides CVE data |

### Git Repository Tools

| Tool | Purpose |
|------|---------|
| **goop** | Modern git dumper |
| **git-dumper** | Fallback git dumper |

### Vulnerability Assessment

| Tool | Purpose | Templates |
|------|---------|-----------|
| **nuclei** | Vulnerability scanner | 3000+ templates |

### Utilities

| Tool | Purpose |
|------|---------|
| **anew** | Append unique lines |
| **uro** | URL deduplication |
| **unfurl** | URL extraction |
| **qsreplace** | Query string replacement |
| **freq** | Fast HTTP requests |

---

## 🔑 API Configuration

### Supported Services

1. **VirusTotal** (Free/Paid)
   - Subdomain enumeration
   - Domain reputation
   - Get key: https://www.virustotal.com/gui/join-us

2. **SecurityTrails** (Free/Paid)
   - Historical DNS data
   - Subdomain intelligence
   - Get key: https://securitytrails.com/

3. **CertSpotter** (Free/Paid)
   - Certificate monitoring
   - Get key: https://sslmate.com/certspotter/

4. **AlienVault OTX** (Free)
   - Threat intelligence
   - Passive DNS
   - Get key: https://otx.alienvault.com/

5. **Shodan** (Optional, for sdlookup)
   - Internet-wide scanning
   - Get key: https://www.shodan.io/

### Configuration

```bash
# Interactive configuration
python3 webenum.py --configure-api

# Manual configuration
mkdir -p ~/.config/webenum
cat > ~/.config/webenum/api_keys.json << 'EOF'
{
  "virustotal": "YOUR_VT_API_KEY",
  "securitytrails": "YOUR_ST_API_KEY",
  "certspotter": "YOUR_CS_API_KEY",
  "shodan": "YOUR_SHODAN_API_KEY"
}
EOF
```

### API Impact

With API keys configured, you can expect:
- **50-200% more subdomains** discovered
- Access to historical DNS data
- Better context about target infrastructure
- Reduced time scanning (cached data)

---

## 💡 Usage Examples

### Bug Bounty Hunting

```bash
# Phase 1: Passive reconnaissance
python3 webenum.py -d target.com --skip-portscan --skip-screenshots

# Phase 2: Review findings
cat results/target.com_*/reports/report.md
grep -i "admin\|login\|api" results/target.com_*/http/httpx_full.json

# Phase 3: Deep dive on interesting assets
python3 webenum.py -d api.target.com
```

### Red Team Assessment

```bash
# Stealthy scan (passive only)
python3 webenum.py -d corp.com \
    --skip-portscan \
    --skip-screenshots \
    --skip-vuln-scan

# Check for quick wins
cat results/corp.com_*/git/exposed_git.txt
grep "high\|critical" results/corp.com_*/vulnerabilities/nuclei_results.txt
```

### Continuous Monitoring

```bash
# Daily cron job (2 AM)
0 2 * * * cd /opt/webenum && python3 webenum.py -d target.com --skip-screenshots

# Check for changes
cat results/target.com_*/diff/*.diff

# Alert on new subdomains
NEW_SUBS=$(wc -l < results/target.com_*/diff/all_subdomains.txt.diff)
if [ "$NEW_SUBS" -gt 0 ]; then
    # Send alert (email, Slack, etc.)
    echo "New subdomains found: $NEW_SUBS"
fi
```

### Penetration Testing

```bash
# Comprehensive assessment
python3 webenum.py -d client.com

# Analyze results
grep -E "(id=|file=|redirect=)" results/client.com_*/urls/urls_clean.txt
cat results/client.com_*/parameters/interesting_parameters.txt
cat results/client.com_*/cloud/aws_services.txt
```

---

## 📊 Analysis & One-Liners

### Find Interesting Assets

```bash
# Admin panels
grep -i "admin\|dashboard\|panel" results/*/http/httpx_full.json

# API endpoints
grep -i "api" results/*/urls/urls_clean.txt

# Development environments
grep -E "(dev|staging|test|uat)" results/*/subdomains/all_subdomains.txt

# Exposed Git repos
cat results/*/git/exposed_git.txt

# Cloud services
cat results/*/cloud/*.txt
```

### Extract Specific Data

```bash
# URLs with parameters
grep '?' results/*/urls/urls_clean.txt

# JavaScript files
cat results/*/js/all_js_files.txt

# Status codes
jq '.status_code' results/*/http/httpx_full.json | sort | uniq -c

# Technologies detected
jq '.tech[]' results/*/http/httpx_full.json | sort -u

# Open ports
cat results/*/ports/open_ports.txt
```

### Vulnerability Patterns

```bash
# LFI/Path Traversal candidates
grep -E "(file=|path=|page=|include=)" results/*/urls/urls_clean.txt

# SQL Injection candidates
grep -E "(id=|user=|product=|category=)" results/*/urls/urls_clean.txt

# Open Redirect candidates
grep -E "(redirect=|url=|return=|next=)" results/*/urls/urls_clean.txt

# SSRF candidates
grep -E "(url=|uri=|target=|dest=)" results/*/urls/urls_clean.txt
```

---

## 🔄 Workflow Integration

### With Other Tools

#### Burp Suite
```bash
# Export URLs for Burp
cat results/*/urls/urls_clean.txt > burp_targets.txt
# Import in Burp Suite
```

#### SQLMap
```bash
# Test SQL injection on parameters
cat results/*/parameters/interesting_parameters.txt | while read url; do
    sqlmap -u "$url" --batch --risk=2 --level=3
done
```

#### Dalfox (XSS Testing)
```bash
# Test XSS on URLs with parameters
cat results/*/urls/urls_clean.txt | grep '?' | dalfox pipe
```

---

## 🎯 Performance Tips

### Speed Optimization

```bash
# Fast scan (skip time-consuming steps)
python3 webenum.py -d target.com \
    --skip-portscan \
    --skip-vuln-scan \
    --skip-screenshots

# Expected time: 5-10 minutes (vs 30-60 minutes full scan)
```

### Resource Management

```bash
# Limit memory (Linux)
ulimit -m 4000000  # 4GB RAM

# Limit processes
ulimit -u 200

# Monitor during scan
watch -n 5 'ps aux | grep webenum'
```

### Parallel Processing

The tool automatically uses:
- Thread pools for subdomain enumeration (3 workers)
- Parallel DNS resolution (puredns)
- Concurrent HTTP probing (httpx)

---

## 🛠️ Troubleshooting

### Common Issues

**Issue**: `Tool not found`
```bash
# Solution: Check installation
python3 webenum.py --check-tools

# Reinstall specific tool
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
```

**Issue**: `Permission denied`
```bash
# Solution: Make scripts executable
chmod +x webenum.py install_tools.sh
```

**Issue**: `API rate limiting`
```bash
# Solution: Configure API keys for higher limits
python3 webenum.py --configure-api
```

**Issue**: `Massdns not found`
```bash
# macOS
brew install massdns

# Linux (compile from source)
git clone https://github.com/blechschmidt/massdns
cd massdns && make && sudo make install
```

**Issue**: `Scans taking too long`
```bash
# Solution: Skip optional steps
python3 webenum.py -d target.com --skip-portscan --skip-vuln-scan --skip-screenshots
```

### Debug Mode

```bash
# View real-time logs
tail -f results/*/logs/*.log

# Check for errors
grep -i error results/*/logs/*.log
```

---

## 🔒 Security & Legal

### ⚠️ Important Notice

**ONLY** use this tool on systems you have explicit permission to test:

- ✅ Your own systems
- ✅ Bug bounty programs (within scope)
- ✅ Authorized penetration tests
- ✅ Security research with permission

**NEVER** use on:

- ❌ Unauthorized systems
- ❌ Out-of-scope targets
- ❌ Production systems without approval
- ❌ Systems you don't own or have permission for

### Best Practices

1. **Get Written Authorization** - Always have documented permission
2. **Respect Scope** - Stay within authorized boundaries
3. **Follow Rate Limits** - Don't DOS the target
4. **Responsible Disclosure** - Report findings properly
5. **Document Everything** - Keep records of your testing

### Legal Disclaimer

This tool is provided for educational and authorized security testing purposes only. Users are responsible for complying with all applicable laws and regulations. The authors assume no liability for misuse or damage caused by this tool.

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- [ ] Additional tool integrations
- [ ] Docker containerization
- [ ] GraphQL endpoint discovery
- [ ] API security testing module
- [ ] Machine learning for target prioritization
- [ ] Web dashboard
- [ ] Slack/Discord notifications
- [ ] Custom wordlist support

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/webenum
cd webenum

# Create development branch
git checkout -b feature/your-feature

# Make changes and test
python3 webenum.py -d test.com

# Submit pull request
```

---

## 📝 Changelog

### v2.0 (Current)

**New Features:**
- ✨ Modern URL collection with xurlfind3r
- ✨ JavaScript analysis with jsubfinder
- ✨ Fast port scanning with sdlookup (replaces nmap)
- ✨ Git repository dumping with goop
- ✨ Enhanced Certificate Transparency queries
- ✨ Cross-platform support (macOS + Linux)
- ✨ Professional markdown reports
- ✨ Diff tracking between scans

**Improvements:**
- ⚡ 50% faster subdomain enumeration
- ⚡ Better error handling
- ⚡ Improved tool detection
- ⚡ Enhanced output organization
- ⚡ Better API integration

**Tools Added:**
- xurlfind3r (URL collection)
- jsubfinder (JS analysis)
- sdlookup (port scanning)
- goop (git dumping)
- hakcheckurl (HTTP status)
- knock (subdomain brute-force)
- freq (fast HTTP requests)

---

## 🙏 Acknowledgments

### Tools & Projects

This framework orchestrates the following amazing open-source tools:

- [ProjectDiscovery](https://github.com/projectdiscovery) - subfinder, httpx, nuclei, dnsx
- [TomNomNom](https://github.com/tomnomnom) - waybackurls, anew, unfurl, assetfinder
- [OWASP Amass](https://github.com/owasp-amass/amass)
- [Findomain](https://github.com/Findomain/Findomain)
- [xurlfind3r](https://github.com/hueristiq/xurlfind3r)
- [jsubfinder](https://github.com/ThreatUnknown/jsubfinder)
- [sdlookup](https://github.com/j3ssie/sdlookup)
- [goop](https://github.com/nyancrimew/goop)
- [Photon](https://github.com/s0md3v/Photon)

### Inspiration

- Bug Bounty methodology from NahamSec, STÖK, InsiderPhD
- Red team techniques from various pentesters
- Automation concepts from the collector script

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 📫 Contact & Support

- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For questions and general discussion
- **Twitter**: [@yourusername] - Follow for updates

---

## ⭐ Star History

If you find this tool useful, please consider giving it a star on GitHub!

---

**Built for the security community** 🔐

**Happy Hunting!** 🎯