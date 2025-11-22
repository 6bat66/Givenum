# WebEnum Enhanced 🚀

**Advanced Web Enumeration Framework with API Integration, Vulnerability Scanning, and Cloud Detection**

## 🎯 What's New in Enhanced Version?

WebEnum Enhanced is a **completely rewritten** version of the original WebEnum tool with **15+ new techniques** and features inspired by modern bug bounty hunting and red team methodologies.

### Key Improvements Over Original

| Feature | Original | Enhanced | Improvement |
|---------|----------|----------|-------------|
| **Subdomain Sources** | 3 tools | 3 tools + 5 APIs + CT logs | +800% data sources |
| **Vulnerability Scanning** | ❌ | ✅ Nuclei integration | NEW |
| **Cloud Detection** | ❌ | ✅ AWS/Azure/GCP | NEW |
| **Port Scanning** | ❌ | ✅ Nmap integration | NEW |
| **Parameter Discovery** | ❌ | ✅ Arjun + Analysis | NEW |
| **Directory Fuzzing** | ❌ | ✅ ffuf integration | NEW |
| **Git Detection** | ❌ | ✅ Exposed .git finder | NEW |
| **Diff Tracking** | ❌ | ✅ Change monitoring | NEW |
| **API Integration** | ❌ | ✅ 5+ APIs | NEW |
| **Reports** | ❌ | ✅ MD + JSON | NEW |
| **WAF Detection** | ❌ | ✅ Built-in | NEW |

---

## ⚡ Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourname/webenum-enhanced
cd webenum-enhanced

# Install all tools
chmod +x install_tools_enhanced.sh
./install_tools_enhanced.sh

# Configure API keys (optional but recommended)
python3 webenum_enhanced.py --configure-api

# Verify installation
python3 webenum_enhanced.py --check-tools
```

### Basic Usage

```bash
# Standard scan
python3 webenum_enhanced.py -d example.com

# Fast scan (skip optional steps)
python3 webenum_enhanced.py -d example.com --skip-screenshots --skip-portscan

# Deep scan with all features
python3 webenum_enhanced.py -d example.com --enable-fuzzing

# Batch processing
./batch_enum_enhanced.sh domains.txt --skip-screenshots
```

---

## 📦 Core Features

### 1. **Multi-Source Subdomain Enumeration**

Combines **8+ data sources**:
- **Tools**: subfinder, assetfinder, findomain, amass
- **APIs**: VirusTotal, SecurityTrails, AlienVault
- **CT Logs**: crt.sh, CertSpotter

```bash
# Example output:
# subfinder: 450 subdomains
# amass: 380 subdomains
# crt.sh: 520 subdomains
# VirusTotal: 290 subdomains
# Total: 1,200+ unique subdomains
```

### 2. **Vulnerability Scanning**

Automated detection using Nuclei:
- 3,000+ vulnerability templates
- CVE detection
- Misconfigurations
- Exposed panels
- Default credentials

```bash
# Scans for:
# - CVEs (Log4j, Spring4Shell, etc.)
# - Exposed admin panels
# - Backup files
# - Configuration errors
# - And much more...
```

### 3. **Cloud Asset Discovery**

Automatically identifies cloud services:
- **AWS**: S3 buckets, CloudFront, ELB, Lambda
- **Azure**: App Services, Blob Storage
- **GCP**: App Engine, Cloud Functions, Storage

### 4. **Parameter-Based Attack Surface**

Discovers potential vulnerability classes:
- **LFI/Path Traversal**: `file=`, `path=`, `page=`
- **SQL Injection**: `id=`, `user=`, `product=`
- **Open Redirect**: `redirect=`, `url=`, `next=`
- **SSRF**: `url=`, `uri=`, `target=`
- **XSS**: `search=`, `query=`, `q=`

### 5. **Diff Tracking**

Monitors changes between scans:
```bash
# Automatically compares with previous scan
# Shows:
# - New subdomains discovered
# - Removed/inactive hosts
# - Infrastructure changes
```

### 6. **Professional Reporting**

Multiple output formats:
- **Markdown**: Human-readable reports
- **JSON**: Machine-parseable data
- **Summary**: Quick statistics

---

## 🛠️ Tool Requirements

### Critical (Required)
- subfinder
- httpx
- dnsx

### DNS Tools (Recommended)
- puredns
- massdns

### Scanning Tools (Important)
- nuclei (vulnerability scanning)
- nmap (port scanning)

### URL Collection (Important)
- gau
- waybackurls
- hakrawler
- getJS

### Fuzzing (Optional)
- ffuf
- arjun

### Optional Enhancements
- gowitness (screenshots)
- subzy/subjack (takeover)
- dalfox (XSS testing)
- sqlmap (SQL injection)

---

## 📊 Output Structure

```
results/example.com_20250122_123456/
├── subdomains/          # Subdomain enumeration results
│   ├── all_subdomains.txt
│   ├── subfinder.txt
│   ├── amass.txt
│   ├── crtsh.txt       ← NEW!
│   └── certspotter.txt ← NEW!
│
├── api_data/           ← NEW! API query results
│   ├── virustotal.json
│   ├── alienvault.txt
│   └── securitytrails.txt
│
├── dns/
│   ├── resolved.txt
│   ├── a_records.txt
│   └── cname_records.txt
│
├── http/
│   ├── alive.txt
│   ├── httpx_full.json
│   └── waf_detected.txt ← NEW!
│
├── ports/              ← NEW! Port scan results
│   ├── nmap_scan.txt
│   └── nmap_scan.xml
│
├── urls/
│   ├── urls_raw.txt
│   ├── urls_clean.txt
│   └── gau.txt
│
├── vulnerabilities/    ← NEW! Nuclei findings
│   ├── nuclei_results.txt
│   └── nuclei_results.json
│
├── parameters/         ← NEW! Parameter analysis
│   ├── interesting_parameters.txt
│   └── arjun_params.txt
│
├── cloud/              ← NEW! Cloud assets
│   ├── aws_services.txt
│   ├── azure_services.txt
│   └── gcp_services.txt
│
├── git/                ← NEW! Exposed repos
│   └── exposed_git.txt
│
├── diff/               ← NEW! Change tracking
│   └── all_subdomains.txt.diff
│
└── reports/            ← NEW! Professional reports
    ├── report.md
    └── report.json
```

---

## 🎓 Usage Scenarios

### Bug Bounty Hunting

```bash
# Phase 1: Passive recon
python3 webenum_enhanced.py -d target.com \
    --skip-portscan \
    --skip-screenshots \
    --skip-fuzzing

# Phase 2: Review findings
cat results/target.com_*/reports/report.md

# Phase 3: Deep dive on interesting assets
python3 webenum_enhanced.py -d interesting.target.com --enable-fuzzing
```

### Red Team Assessment

```bash
# Stealthy reconnaissance
python3 webenum_enhanced.py -d corp.com \
    --skip-portscan \
    --skip-screenshots \
    --skip-vuln-scan
```

### Continuous Monitoring

```bash
# Daily scans via cron
0 2 * * * cd /opt/webenum && python3 webenum_enhanced.py -d target.com

# Check diff for changes
cat results/target.com_*/diff/*.diff
```

### Penetration Testing

```bash
# Comprehensive assessment
python3 webenum_enhanced.py -d target.com --enable-fuzzing
```

---

## 🔐 API Configuration

### Supported APIs

1. **VirusTotal** (Free/Paid)
   - Subdomain enumeration
   - Malware/reputation data
   - Get key: https://www.virustotal.com/

2. **SecurityTrails** (Free/Paid)
   - DNS history
   - Subdomain intelligence
   - Get key: https://securitytrails.com/

3. **AlienVault OTX** (Free)
   - Threat intelligence
   - Passive DNS
   - Get key: https://otx.alienvault.com/

4. **CertSpotter** (Free/Paid)
   - Certificate monitoring
   - Get key: https://sslmate.com/certspotter/

### Configuration

```bash
# Interactive setup
python3 webenum_enhanced.py --configure-api

# Manual setup
mkdir -p ~/.config/webenum
cat > ~/.config/webenum/api_keys.json << 'EOF'
{
  "virustotal": "YOUR_API_KEY",
  "securitytrails": "YOUR_API_KEY",
  "alienvault": "YOUR_API_KEY",
  "certspotter": "YOUR_API_KEY"
}
EOF
```

---

## 📚 Documentation

- **[ENHANCED_FEATURES.md](ENHANCED_FEATURES.md)** - Detailed feature documentation
- **[CHEAT_SHEET.md](CHEAT_SHEET.md)** - Quick reference guide
- **[INSTALL.md](INSTALL.md)** - Installation instructions

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- [ ] Additional API integrations
- [ ] Docker containerization
- [ ] GraphQL endpoint discovery
- [ ] Automated exploitation modules
- [ ] Machine learning for target prioritization
- [ ] Web interface

---

## 📋 Comparison Matrix

### vs. Original WebEnum

| Aspect | Original | Enhanced |
|--------|----------|----------|
| **Lines of Code** | ~900 | ~2,400 |
| **Features** | 8 | 23+ |
| **Data Sources** | 6 | 15+ |
| **Output Directories** | 8 | 14 |
| **Vulnerability Detection** | Manual | Automated |
| **Cloud Detection** | None | AWS/Azure/GCP |
| **Change Tracking** | None | Built-in |
| **Reporting** | Console | MD/JSON |

### vs. Other Tools

| Tool | Focus | WebEnum Enhanced Advantage |
|------|-------|---------------------------|
| **Amass** | Subdomain enum | Broader scope: vuln scanning + cloud + params |
| **Recon-ng** | Modular recon | Simpler, more automated |
| **Subfinder** | Fast subdomain enum | Complete workflow, not just discovery |
| **Nuclei** | Vuln scanning | Includes full recon pipeline |
| **Burp Suite** | Manual testing | Automated reconnaissance |

---

## ⚖️ Legal Notice

**IMPORTANT**: Only use this tool on systems you have permission to test!

- Unauthorized scanning is illegal
- Get written authorization
- Respect scope limitations
- Follow responsible disclosure
- Obey rate limits

---

## 🐛 Known Issues & Limitations

1. **API Rate Limits**: Free API tiers have limits
2. **False Positives**: Nuclei may flag non-issues
3. **Resource Usage**: Full scans are CPU/memory intensive
4. **Time**: Comprehensive scans can take 30-60 minutes
5. **Dependencies**: Requires many external tools

---

## 🔮 Roadmap

### v2.1 (Next Release)
- [ ] Docker container
- [ ] Shodan integration
- [ ] HTML reports
- [ ] Slack notifications

### v2.2
- [ ] GraphQL discovery
- [ ] API security testing
- [ ] CORS misconfiguration detection
- [ ] Favicon hash intelligence

### v3.0
- [ ] Machine learning prioritization
- [ ] Web dashboard
- [ ] Team collaboration features
- [ ] Automated exploitation

---

## 📞 Support

- **Documentation**: See `/docs` folder
- **Issues**: GitHub Issues
- **Questions**: Discussions tab
- **Updates**: Follow on Twitter [@yourhandle]

---

## 🙏 Credits & Inspiration

### Tools Used
- ProjectDiscovery (subfinder, httpx, nuclei, dnsx)
- TomNomNom (waybackurls, anew, unfurl, etc.)
- OWASP Amass
- Many others - see tools list

### Inspired By
- Collector script (bash automation)
- NahamSec's methodology
- Bug Bounty best practices
- Red team techniques

---

## 📜 License

MIT License - See LICENSE file

---

## ⭐ Star History

If you find this tool useful, please consider giving it a star!

---

**Built with ❤️ for the security community**

*Happy Hunting! 🎯*
