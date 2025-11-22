# WebEnum Enhanced - New Techniques & Features

## 🚀 Overview of Enhancements

This enhanced version adds **15+ new techniques** inspired by modern bug bounty and penetration testing methodologies, including features from the "collector" script and cutting-edge recon tools.

---

## 📋 New Features Summary

### 1. **API Integration** (NEW! 🆕)
Passive subdomain enumeration using multiple APIs:
- **VirusTotal** - Subdomain and malware database
- **AlienVault OTX** - Open Threat Exchange
- **SecurityTrails** - DNS and infrastructure history
- **Shodan** - Internet-wide scanning (optional)

### 2. **Certificate Transparency Logs** (NEW! 🆕)
Discovers subdomains from SSL/TLS certificates:
- **crt.sh** - Free CT log search
- **CertSpotter** - SSL/TLS certificate monitoring

### 3. **Cloud Service Detection** (NEW! 🆕)
Automatically identifies cloud infrastructure:
- AWS (S3, CloudFront, ELB, Lambda)
- Azure (App Services, Blob Storage)
- Google Cloud Platform (App Engine, Cloud Functions)

### 4. **Port Scanning** (NEW! 🆕)
Infrastructure analysis with Nmap:
- Top 1000 ports scanning
- Service detection
- XML/TXT output formats

### 5. **Vulnerability Scanning** (NEW! 🆕)
Automated vulnerability detection:
- **Nuclei** - Template-based scanning
- Auto-updates vulnerability templates
- Severity-based filtering

### 6. **WAF/CDN Detection** (NEW! 🆕)
Identifies web application firewalls and CDNs:
- Cloudflare, AWS WAF, Akamai detection
- Helps plan bypass strategies

### 7. **Parameter Discovery** (NEW! 🆕)
Hidden parameter enumeration:
- **Arjun** - Parameter fuzzing
- Pattern-based interesting parameter detection
- Identifies injection points (id, file, url, etc.)

### 8. **Directory Fuzzing** (NEW! 🆕)
Web path discovery:
- **ffuf** - Fast web fuzzer
- Support for custom wordlists
- JSON output for parsing

### 9. **Git Repository Detection** (NEW! 🆕)
Finds exposed .git directories:
- Automatic detection of .git/config
- Lists exposed repositories
- Foundation for git-dumper integration

### 10. **Advanced Parameter Analysis** (NEW! 🆕)
Analyzes URL parameters for vulnerabilities:
- LFI/Path traversal patterns
- SQL injection candidates
- Open redirect possibilities
- SSRF potential targets
- XSS reflection points

### 11. **Diff Functionality** (NEW! 🆕)
Track changes between scans:
- Compares current vs. previous scans
- Shows new/removed subdomains
- Tracks infrastructure changes
- Helps identify attack surface expansion

### 12. **Enhanced Reporting** (NEW! 🆕)
Professional output formats:
- **Markdown reports** - Human-readable
- **JSON exports** - Machine-parseable
- Categorized findings
- Executive summaries

### 13. **API Key Management** (NEW! 🆕)
Secure credential storage:
- Interactive configuration
- Encrypted storage in ~/.config/webenum/
- Service-specific key management

### 14. **Enhanced Tool Support** (NEW! 🆕)
Expanded tool integration:
- 30+ reconnaissance tools
- Better error handling
- Parallel execution
- Timeout management

### 15. **Advanced JavaScript Analysis** (NEW! 🆕)
Deeper JS file inspection:
- Endpoint extraction
- API key discovery potential
- URL pattern matching

---

## 🎯 Usage Examples

### Basic Scan
```bash
python3 webenum_enhanced.py -d example.com
```

### Quick Scan (Skip Optional Steps)
```bash
python3 webenum_enhanced.py -d example.com \
    --skip-screenshots \
    --skip-portscan \
    --skip-vuln-scan
```

### Full Deep Scan
```bash
python3 webenum_enhanced.py -d example.com \
    --enable-fuzzing
```

### Configure API Keys
```bash
python3 webenum_enhanced.py --configure-api
```

### Check Tool Status
```bash
python3 webenum_enhanced.py --check-tools
```

---

## 🔧 Installation

### Automated Installation
```bash
chmod +x install_tools_enhanced.sh
./install_tools_enhanced.sh
```

### Manual Tool Installation

#### Core Tools
```bash
# Subdomain enumeration
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/tomnomnom/assetfinder@latest
go install github.com/owasp-amass/amass/v4/...@master

# DNS resolution
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install github.com/d3mondev/puredns/v2@latest

# HTTP probing
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
```

#### Scanning Tools
```bash
# Vulnerability scanning
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
nuclei -update-templates

# Port scanning
sudo apt install nmap  # Linux
brew install nmap      # macOS
```

#### Fuzzing Tools
```bash
# Directory fuzzing
go install github.com/ffuf/ffuf@latest

# Parameter discovery
pip3 install arjun
```

---

## 📊 Output Structure

```
results/
└── example.com_20250122_123456/
    ├── subdomains/
    │   ├── all_subdomains.txt      # Consolidated
    │   ├── subfinder.txt
    │   ├── assetfinder.txt
    │   ├── amass.txt
    │   ├── crtsh.txt               # NEW!
    │   └── certspotter.txt         # NEW!
    ├── dns/
    │   ├── resolved.txt
    │   ├── a_records.txt
    │   └── cname_records.txt
    ├── http/
    │   ├── alive.txt
    │   ├── httpx_full.json
    │   └── waf_detected.txt        # NEW!
    ├── ports/                      # NEW!
    │   ├── nmap_scan.txt
    │   └── nmap_scan.xml
    ├── urls/
    │   ├── urls_raw.txt
    │   ├── urls_clean.txt
    │   ├── gau.txt
    │   ├── waybackurls.txt
    │   └── hakrawler.txt
    ├── js/
    │   └── js_files.txt
    ├── vulnerabilities/            # NEW!
    │   ├── nuclei_results.txt
    │   └── nuclei_results.json
    ├── parameters/                 # NEW!
    │   ├── all_parameters.txt
    │   ├── interesting_parameters.txt
    │   └── arjun_params.txt
    ├── fuzzing/                    # NEW!
    │   └── ffuf_1.json
    ├── cloud/                      # NEW!
    │   ├── aws_services.txt
    │   ├── azure_services.txt
    │   └── gcp_services.txt
    ├── git/                        # NEW!
    │   └── exposed_git.txt
    ├── api_data/                   # NEW!
    │   ├── virustotal.txt
    │   ├── virustotal.json
    │   ├── alienvault.txt
    │   └── securitytrails.txt
    ├── diff/                       # NEW!
    │   ├── all_subdomains.txt.diff
    │   └── alive.txt.diff
    ├── reports/                    # NEW!
    │   ├── report.md
    │   └── report.json
    ├── takeover/
    │   └── subzy_results.txt
    ├── screenshots/
    │   └── [gowitness output]
    └── logs/
```

---

## 🎓 Methodology & Workflow

### Phase 1: Passive Reconnaissance
1. **API-based enumeration** - Query multiple passive sources
2. **Certificate Transparency** - SSL/TLS certificate mining
3. **DNS enumeration** - Subdomain discovery
4. **Resolution** - Filter live domains

### Phase 2: Active Discovery
1. **Port scanning** - Identify open services
2. **HTTP probing** - Find web applications
3. **Technology detection** - Stack fingerprinting
4. **WAF detection** - Identify protection mechanisms

### Phase 3: Content Discovery
1. **URL collection** - Historical & live crawling
2. **JavaScript analysis** - Extract endpoints
3. **Parameter discovery** - Find hidden parameters
4. **Directory fuzzing** (optional) - Brute force paths

### Phase 4: Vulnerability Assessment
1. **Nuclei scanning** - Template-based checks
2. **Git exposure** - Source code leaks
3. **Subdomain takeover** - Unclaimed resources
4. **Cloud misconfigurations** - S3 buckets, etc.

### Phase 5: Reporting & Analysis
1. **Diff analysis** - Track changes
2. **Report generation** - Comprehensive documentation
3. **Prioritization** - Focus on high-value targets

---

## 🔍 Advanced Techniques

### 1. Certificate Transparency Mining
```python
# Queries crt.sh for all certificates
# Discovers subdomains from:
# - Current certificates
# - Expired certificates
# - Wildcard certificates
# - SAN (Subject Alternative Names)
```

### 2. API Correlation
```python
# Combines data from multiple sources
# Cross-validates findings
# Identifies discrepancies
# Reduces false positives
```

### 3. Cloud Asset Discovery
```python
# Pattern matching for cloud services
# S3 bucket enumeration potential
# Azure blob detection
# GCP resource identification
```

### 4. Parameter-based Attack Surface
```python
# Identifies potential vulnerabilities:
# - file= → LFI/Path Traversal
# - id= → SQL Injection
# - url= → Open Redirect/SSRF
# - search= → XSS
```

### 5. Historical Data Analysis
```python
# Web archive analysis
# Discovers:
# - Old/forgotten endpoints
# - Deprecated APIs
# - Development/staging environments
# - Backup files
```

---

## ⚙️ Configuration Options

### API Keys
Create `~/.config/webenum/api_keys.json`:
```json
{
  "virustotal": "your_vt_api_key",
  "securitytrails": "your_st_api_key",
  "certspotter": "your_cs_api_key",
  "shodan": "your_shodan_api_key"
}
```

### Custom Wordlists
Place wordlists in `~/.config/webenum/wordlists/`:
- `subdomains-top1m.txt` - Subdomain bruteforcing
- `common.txt` - Common web paths
- `raft-small-directories.txt` - Directory enumeration
- `burp-parameter-names.txt` - Parameter fuzzing

---

## 🛡️ Security Features

### Rate Limiting
- Respects API rate limits
- Implements backoff strategies
- Prevents IP blocking

### Error Handling
- Graceful timeout management
- Continued execution on failures
- Detailed error logging

### Data Privacy
- No data sent to third parties (except APIs)
- Local storage only
- Encrypted API key storage

---

## 📈 Performance Improvements

### Parallel Execution
- Concurrent subdomain enumeration
- Parallel HTTP probing
- Thread-pool management

### Smart Caching
- Prevents duplicate API calls
- Reuses DNS resolution
- Diff-based incremental scanning

### Resource Management
- Configurable timeouts
- Memory-efficient file processing
- Automatic cleanup

---

## 🔄 Comparison: Original vs Enhanced

| Feature | Original | Enhanced |
|---------|----------|----------|
| Subdomain Sources | 3 tools | 3 tools + 5 APIs + CT logs |
| DNS Resolution | ✓ | ✓ Enhanced |
| HTTP Probing | ✓ | ✓ + WAF detection |
| Port Scanning | ✗ | ✓ Nmap |
| Vulnerability Scanning | ✗ | ✓ Nuclei |
| Cloud Detection | ✗ | ✓ AWS/Azure/GCP |
| Parameter Discovery | ✗ | ✓ Arjun + Analysis |
| Directory Fuzzing | ✗ | ✓ ffuf |
| Git Detection | ✗ | ✓ |
| Diff Tracking | ✗ | ✓ |
| API Integration | ✗ | ✓ |
| Report Formats | ✗ | ✓ MD + JSON |

---

## 🎯 Use Cases

### Bug Bounty Hunting
```bash
# Full recon for bug bounty
python3 webenum_enhanced.py -d target.com --enable-fuzzing
```

### Red Team Engagements
```bash
# Stealthy reconnaissance
python3 webenum_enhanced.py -d target.com \
    --skip-portscan \
    --skip-screenshots
```

### Continuous Monitoring
```bash
# Daily scans with diff
python3 webenum_enhanced.py -d target.com --skip-vuln-scan
# Diff automatically tracks changes
```

### Vulnerability Assessment
```bash
# Focus on vulnerabilities
python3 webenum_enhanced.py -d target.com \
    --skip-screenshots \
    --skip-fuzzing
```

---

## 🐛 Troubleshooting

### Common Issues

**1. API Rate Limiting**
```bash
# Use API keys for higher limits
python3 webenum_enhanced.py --configure-api
```

**2. Missing Tools**
```bash
# Check what's installed
python3 webenum_enhanced.py --check-tools

# Install missing tools
./install_tools_enhanced.sh
```

**3. Massdns Not Found**
```bash
# macOS
brew install massdns

# Linux
git clone https://github.com/blechschmidt/massdns
cd massdns && make && sudo make install
```

**4. Nuclei Templates Outdated**
```bash
nuclei -update-templates
```

---

## 📚 Resources & References

### Inspired By
- [Collector](https://github.com/skateforever/pentest-scripts) - Bash automation
- [ProjectDiscovery](https://github.com/projectdiscovery) - Tool suite
- [TomNomNom's Tools](https://github.com/tomnomnom) - Utilities
- [Bug Bounty Methodology](https://www.bugcrowd.com/resources/)

### Additional Reading
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Subdomain Enumeration Guide](https://0xpatrik.com/subdomain-enumeration-2019/)
- [Nuclei Templates](https://github.com/projectdiscovery/nuclei-templates)
- [Certificate Transparency](https://certificate.transparency.dev/)

---

## 🚦 Roadmap

### Planned Features
- [ ] Shodan integration for IP enumeration
- [ ] DNSDumpster API integration
- [ ] Automated git-dumper for exposed repos
- [ ] GraphQL endpoint discovery
- [ ] API fuzzing with custom payloads
- [ ] CORS misconfiguration detection
- [ ] Favicon hash matching
- [ ] HTML report generation
- [ ] Slack/Discord notifications
- [ ] Docker containerization

---

## 📝 Best Practices

### 1. Always Use API Keys
```bash
# More data = better results
python3 webenum_enhanced.py --configure-api
```

### 2. Run Regular Scans
```bash
# Track changes over time
# Schedule daily/weekly scans
crontab -e
0 2 * * * /path/to/webenum_enhanced.py -d target.com
```

### 3. Review Diff Output
```bash
# Check diff/ directory after each scan
# Focus on new subdomains
# Investigate removed hosts (potential takedown)
```

### 4. Start Passive, Then Active
```bash
# Phase 1: Passive only
python3 webenum_enhanced.py -d target.com \
    --skip-portscan --skip-vuln-scan --skip-fuzzing

# Phase 2: Active scanning on interesting targets
```

### 5. Combine with Manual Testing
```bash
# Automated tools find breadth
# Manual testing finds depth
# Use reports as starting points
```

---

## ⚖️ Legal & Ethical

**IMPORTANT:** Only scan targets you have permission to test!

- Get written authorization
- Respect scope limitations
- Follow responsible disclosure
- Obey rate limits
- Don't cause service disruption

---

## 🤝 Contributing

Ideas for improvement:
1. Fork the repository
2. Create feature branch
3. Add your enhancements
4. Submit pull request

---

## 📧 Support

For issues or questions:
- Check `--help` output
- Review documentation
- Check tool logs in `logs/` directory

---

**Happy Hunting! 🎯**
