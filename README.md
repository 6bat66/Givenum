# WebEnum - Comprehensive Web Enumeration Toolkit

🎯 **Complete automated web enumeration tool** that collects maximum information about a domain without invasive scanning.

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Bash](https://img.shields.io/badge/Bash-4.0+-green.svg)](https://www.gnu.org/software/bash/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [Output Structure](#-output-structure)
- [Advanced Usage](#-advanced-usage)
- [Tools Reference](#-tools-reference)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## ✨ Features

### Enumeration Pipeline

1. **Subdomain Discovery** → subfinder, assetfinder, findomain, amass
2. **DNS Resolution** → puredns, dnsx (validation & enrichment)
3. **HTTP Probing** → httpx (tech detection, status codes, titles)
4. **URL Collection** → gau, waybackurls, hakrawler (historical & live)
5. **JavaScript Analysis** → getJS, subjs (endpoint extraction)
6. **Screenshots** → gowitness (optional visual reconnaissance)
7. **Takeover Detection** → subzy (vulnerable CNAME checks)

### Key Benefits

- ⚡ **Parallel Execution** - Fast enumeration using concurrent processing
- 📊 **15+ Tools Integrated** - Best-in-class reconnaissance tools
- 🎨 **Color-Coded Output** - Easy-to-read terminal interface
- 📁 **Organized Results** - Clean directory structure
- 🔍 **Automatic Analysis** - Built-in result analyzer
- 📝 **Report Generation** - Export to Markdown format
- 🔄 **Batch Processing** - Enumerate multiple domains
- 🛡️ **Error Handling** - Graceful handling of tool failures

---

## 🚀 Quick Start

### 1. Install Tools

```bash
chmod +x install_tools.sh
./install_tools.sh
source ~/.bashrc
```

### 2. Verify Installation

```bash
./webenum.py --check-tools
```

### 3. Run Enumeration

```bash
# Fast mode (recommended for first run)
./webenum.py -d example.com --skip-screenshots

# Full mode with screenshots
./webenum.py -d example.com
```

### 4. Analyze Results

```bash
./analyze_results.py results/example.com_*/
```

---

## 📦 Installation

### Prerequisites

- **Python 3.6+**
- **Go 1.19+**
- **Linux/macOS** (Windows via WSL)

### Automated Installation (Recommended)

```bash
# Download and run installer
./install_tools.sh

# Reload shell configuration
source ~/.bashrc

# Verify tools
./webenum.py --check-tools
```

### Manual Installation

#### Critical Tools (Required)

```bash
# Subdomain enumeration
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# HTTP probing
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
```

#### Recommended Tools

```bash
# More subdomain sources
go install github.com/tomnomnom/assetfinder@latest

# Findomain (binary download)
wget https://github.com/Findomain/Findomain/releases/latest/download/findomain-linux
chmod +x findomain-linux
sudo mv findomain-linux /usr/local/bin/findomain

# DNS tools
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install github.com/d3mondev/puredns/v2@latest

# URL collection
go install github.com/lc/gau/v2/cmd/gau@latest
go install github.com/tomnomnom/waybackurls@latest
go install github.com/hakluke/hakrawler@latest

# Utilities
go install -v github.com/tomnomnom/anew@latest
pip3 install uro
```

#### Optional Tools (Enhance Results)

```bash
# Deep subdomain enumeration (slow but thorough)
go install -v github.com/owasp-amass/amass/v4/...@master

# Screenshots
go install github.com/sensepost/gowitness@latest

# JavaScript analysis
go install github.com/003random/getJS@latest
go install -v github.com/lc/subjs@latest

# Subdomain takeover
go install -v github.com/LukaSikic/subzy@latest
```

### Configure PATH

Ensure Go binaries are in your PATH:

```bash
export PATH=$PATH:$(go env GOPATH)/bin
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
source ~/.bashrc
```

---

## 📖 Usage

### Basic Commands

```bash
# Single domain enumeration
./webenum.py -d target.com --skip-screenshots

# Custom output directory
./webenum.py -d target.com -o /path/to/output

# Full enumeration with screenshots
./webenum.py -d target.com

# Check tool installation status
./webenum.py --check-tools
```

### Batch Processing

Process multiple domains from a file:

```bash
# Create domains file
cat > targets.txt << EOF
example.com
target1.com
target2.com
EOF

# Run batch enumeration
./batch_enum.sh targets.txt --skip-screenshots
```

### Result Analysis

```bash
# Interactive analysis with all sections
./analyze_results.py results/example.com_*/

# Export to Markdown report
./analyze_results.py results/example.com_*/ --export report.md

# Quick summary only
./analyze_results.py results/example.com_*/ --summary-only
```

---

## 📁 Output Structure

WebEnum creates an organized directory structure for each run:

```
results/
└── example.com_20250121_143022/
    ├── subdomains/
    │   ├── subfinder.txt
    │   ├── assetfinder.txt
    │   ├── findomain.txt
    │   └── all_subdomains.txt     ⭐ All discovered subdomains
    │
    ├── dns/
    │   ├── resolved.txt            ⭐ Resolved subdomains
    │   └── dnsx_full.json          DNS enrichment data
    │
    ├── http/
    │   ├── alive.txt               ⭐ Active HTTP/HTTPS hosts
    │   └── httpx_full.json         ⭐ Complete data (tech, status, titles)
    │
    ├── urls/
    │   ├── urls_raw.txt            Raw collected URLs
    │   └── urls_clean.txt          ⭐ Cleaned & normalized URLs
    │
    ├── js/
    │   └── js_files.txt            JavaScript file URLs
    │
    ├── screenshots/
    │   └── *.png                   Visual screenshots
    │
    ├── takeover/
    │   └── subzy_results.txt       Takeover check results
    │
    └── logs/
```

### Key Files

| File | Description | Use Case |
|------|-------------|----------|
| `all_subdomains.txt` | All discovered subdomains | Feed into other tools |
| `resolved.txt` | Subdomains with DNS records | Valid targets |
| `alive.txt` | Active web services | HTTP testing targets |
| `httpx_full.json` | Complete HTTP data | Technology analysis |
| `urls_clean.txt` | Normalized URLs | Parameter testing, fuzzing |

---

## 🔍 Advanced Usage

### One-Liners for Analysis

#### Find Admin Panels

```bash
cat results/*/http/httpx_full.json | \
  jq -r 'select(.title | test("admin|login|dashboard"; "i")) | .url'
```

#### List All Technologies

```bash
cat results/*/http/httpx_full.json | \
  jq -r '.tech[]' | sort | uniq -c | sort -rn
```

#### Extract URLs with Interesting Parameters

```bash
cat results/*/urls/urls_clean.txt | \
  grep -E "\?(id|user|file|page|path)="
```

#### Find Hosts by Status Code

```bash
# Find all 403 Forbidden
cat results/*/http/httpx_full.json | \
  jq -r 'select(.status_code == 403) | .url'

# Find all redirects
cat results/*/http/httpx_full.json | \
  jq -r 'select(.status_code >= 300 and .status_code < 400) | "\(.url) -> \(.location)"'
```

#### Find API Endpoints

```bash
cat results/*/urls/urls_clean.txt | \
  grep -iE '/api/|/v[0-9]+/|graphql'
```

### Integration with Other Tools

#### Nuclei (Vulnerability Scanning)

```bash
# Scan for CVEs
cat results/*/http/alive.txt | \
  nuclei -t cves/ -severity high,critical -o nuclei_results.txt

# Scan for misconfigurations
cat results/*/http/alive.txt | \
  nuclei -t misconfiguration/ -o nuclei_misconfig.txt
```

#### FFuf (Directory Bruteforce)

```bash
# Bruteforce common paths
cat results/*/http/alive.txt | while read url; do
  ffuf -u "$url/FUZZ" -w /path/to/wordlist.txt \
    -mc 200,204,301,302,307,401,403 \
    -o "ffuf_$(echo $url | md5sum | cut -d' ' -f1).json" -of json
done
```

#### Kxss (XSS Parameter Detection)

```bash
# Find reflected parameters
cat results/*/urls/urls_clean.txt | \
  kxss | tee possible_xss.txt
```

#### ParamSpider (Parameter Discovery)

```bash
# Find hidden parameters
cat results/*/http/alive.txt | while read url; do
  domain=$(echo $url | sed 's|https\?://||' | cut -d/ -f1)
  paramspider -d "$domain"
done
```

### Comparing Enumeration Runs

```bash
# Find new subdomains between two runs
comm -13 \
  <(sort old_run/subdomains/all_subdomains.txt) \
  <(sort new_run/subdomains/all_subdomains.txt)

# Find new active hosts
comm -13 \
  <(sort old_run/http/alive.txt) \
  <(sort new_run/http/alive.txt)
```

### Continuous Monitoring with Cron

```bash
# Add to crontab (crontab -e)
# Run every Monday at 2 AM
0 2 * * 1 cd /path/to/webenum && \
  ./webenum.py -d target.com --skip-screenshots && \
  ./analyze_results.py results/target.com_*/ --export ~/reports/weekly_$(date +\%Y\%m\%d).md
```

---

## 🛠️ Tools Reference

### Tool Categories

#### Critical (Required)
- **subfinder** - Fast subdomain enumeration using passive sources
- **httpx** - HTTP probing with technology detection

#### Recommended (High Priority)
- **assetfinder** - Additional subdomain sources
- **findomain** - Fast multi-source subdomain discovery
- **puredns** - Mass DNS resolution with validation
- **dnsx** - DNS enrichment (A, AAAA, CNAME records)
- **gau** - Fetch URLs from AlienVault's Open Threat Exchange, Wayback Machine, and Common Crawl
- **waybackurls** - Fetch all URLs from Wayback Machine
- **hakrawler** - Fast web crawler for URL discovery
- **anew** - Append lines to file, but only if they don't already appear
- **uro** - URL normalization and deduplication

#### Optional (Enhance Results)
- **amass** - Deep subdomain enumeration (slow but comprehensive)
- **gowitness** - Screenshot capture tool
- **getJS** - Extract JavaScript file URLs
- **subjs** - Find URLs/endpoints in JavaScript files
- **subzy** - Subdomain takeover vulnerability checker

### Tool Comparison

| Tool | Speed | Coverage | Resource Usage | Best For |
|------|-------|----------|----------------|----------|
| subfinder | ⚡⚡⚡ | ⭐⭐⭐ | Low | Quick scans |
| assetfinder | ⚡⚡⚡ | ⭐⭐ | Low | Supplementary |
| findomain | ⚡⚡⚡ | ⭐⭐⭐ | Low | Speed + coverage |
| amass | ⚡ | ⭐⭐⭐⭐⭐ | High | Thorough recon |
| httpx | ⚡⚡ | N/A | Medium | Verification |
| gau | ⚡⚡ | ⭐⭐⭐⭐ | Low | Historical URLs |
| hakrawler | ⚡⚡ | ⭐⭐⭐ | Medium | Live crawling |

---

## 🐛 Troubleshooting

### Common Issues

#### "httpx is required!" Error

```bash
# Install httpx
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

# Verify installation
which httpx

# If not found, check PATH
export PATH=$PATH:$(go env GOPATH)/bin
echo $PATH
```

#### "No active hosts found"

**Possible causes:**
1. Domain has no web services
2. DNS resolution issues
3. Firewall/rate limiting

**Solutions:**
```bash
# Test DNS
dig example.com

# Test httpx manually
echo "www.example.com" | httpx -silent

# Try with verbose mode
echo "www.example.com" | httpx -verbose
```

#### Scripts Not Executable

```bash
# Make scripts executable
chmod +x *.py *.sh

# Verify
ls -la *.py *.sh
```

#### Tool Not Found

```bash
# Check if tool is installed
which subfinder

# If missing, reinstall
./install_tools.sh

# Verify Go bin directory
echo $(go env GOPATH)/bin
ls $(go env GOPATH)/bin
```

#### Timeout Errors

**For large domains:**
- Use `--skip-screenshots` to reduce runtime
- Run during off-peak hours
- Consider using a VPS with better bandwidth
- Split enumeration into smaller batches

#### Permission Denied

```bash
# Ensure proper ownership
chown -R $USER:$USER .

# Fix permissions
chmod +x *.sh *.py
chmod 644 *.txt *.md
```

---

## 💡 Best Practices

### Performance Optimization

1. **First Run**: Use `--skip-screenshots` for faster enumeration
2. **Large Domains**: Expect 30+ minutes for major targets
3. **Resource Management**: Close unnecessary applications
4. **Network**: Use stable, high-bandwidth connection

### Security Considerations

1. **Rate Limiting**: Tools respect rate limits automatically
2. **User Agents**: httpx uses random user agents
3. **Respectful Scanning**: No aggressive scanning by default
4. **Legal**: Only scan authorized targets

### Workflow Recommendations

```
Phase 1: Quick Discovery
  └─> ./webenum.py -d target.com --skip-screenshots

Phase 2: Analysis
  └─> ./analyze_results.py results/target.com_*/

Phase 3: Deep Dive
  └─> Review interesting hosts, technologies, URLs

Phase 4: Targeted Testing
  └─> Use nuclei, ffuf on specific findings

Phase 5: Reporting
  └─> ./analyze_results.py results/target.com_*/ --export report.md
```

---

## 📊 Example Scenarios

### Bug Bounty Reconnaissance

```bash
# Initial broad enumeration
./webenum.py -d target.com -o ~/bugbounty/target/

# Analyze for interesting findings
./analyze_results.py ~/bugbounty/target/target.com_*/

# Extract WordPress sites for deeper testing
cat ~/bugbounty/target/*/http/httpx_full.json | \
  jq -r 'select(.tech[] | test("WordPress")) | .url' > wordpress_targets.txt

# Check for common misconfigurations
cat wordpress_targets.txt | nuclei -t wordpress/
```

### Penetration Testing

```bash
# Comprehensive enumeration with screenshots
./webenum.py -d client.com -o ~/pentests/client_2025/

# Generate detailed report
./analyze_results.py ~/pentests/client_2025/client.com_*/ \
  --export ~/pentests/client_2025/recon_report.md

# Visual review of interesting pages
firefox ~/pentests/client_2025/*/screenshots/
```

### Asset Discovery

```bash
# Batch process multiple domains
cat company_domains.txt | while read domain; do
  ./webenum.py -d "$domain" -o ~/asset_discovery/ --skip-screenshots
done

# Consolidate findings
for dir in ~/asset_discovery/*/; do
  ./analyze_results.py "$dir" --summary-only
done
```

---

## 🤝 Contributing

Contributions are welcome! Here are some ideas:

### Feature Requests
- Additional tool integrations
- Dashboard/web interface
- Database storage for results
- Notification support (Discord, Slack, Telegram)
- Multi-domain parallel processing
- Custom wordlist management

### Code Contributions
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Reporting Issues
- Use GitHub Issues
- Provide error messages
- Include environment details
- Steps to reproduce

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🌟 Acknowledgments

Built with excellent tools from the security community:

- [ProjectDiscovery](https://github.com/projectdiscovery) - subfinder, httpx, dnsx, nuclei
- [TomNomNom](https://github.com/tomnomnom) - waybackurls, anew, gau, unfurl
- [OWASP Amass](https://github.com/owasp-amass/amass) - Deep subdomain enumeration
- [HakLuke](https://github.com/hakluke) - hakrawler
- [Findomain](https://github.com/Findomain/Findomain) - Fast subdomain discovery
- [PureDNS](https://github.com/d3mondev/puredns) - Mass DNS resolution

Special thanks to the bug bounty and pentesting community for continuous feedback and improvements.

---

## 📞 Support

- **Documentation**: This README
- **Issues**: [GitHub Issues](https://github.com/yourusername/webenum/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/webenum/discussions)

---

## 📈 Project Status

- ✅ Core functionality complete
- ✅ All major tools integrated
- ✅ Comprehensive documentation
- ✅ Error handling and edge cases
- 🔄 Continuous improvements
- 📋 Feature requests welcome

---

## 🎯 Roadmap

### v1.1 (Planned)
- [ ] HTML report generation
- [ ] Database backend for results
- [ ] Improved diff functionality
- [ ] Custom tool configurations

### v1.2 (Future)
- [ ] Web interface
- [ ] Real-time notifications
- [ ] Cloud deployment support
- [ ] API endpoints

---

**WebEnum** - Enumerate. Analyze. Conquer. 🎯

*Made with ❤️ by @6bat66 for the Bug Bounty & Penetration Testing community*

---

## ⭐ Star History

If you find this tool useful, please consider giving it a star on GitHub!

[![Star History](https://img.shields.io/github/stars/yourusername/webenum?style=social)](https://github.com/yourusername/webenum/stargazers)
