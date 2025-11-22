# Givenum - Comprehensive Web Enumeration Toolkit

🎯 **Complete automated web enumeration tool** that collects maximum information about a domain without invasive scanning.

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Bash](https://img.shields.io/badge/Bash-4.0+-green.svg)](https://www.gnu.org/software/bash/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey.svg)]()

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
2. **DNS Resolution** → puredns, massdns, dnsx (validation & enrichment)
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
- 🍎 **Cross-Platform** - Works on Linux and macOS (Intel & Apple Silicon)

---

## 🚀 Quick Start

### 1. Install Tools

```bash
chmod +x install_tools.sh
./install_tools.sh
```

**macOS users:**
```bash
source ~/.zshrc
```

**Linux users:**
```bash
source ~/.bashrc
```

### 2. Verify Installation

```bash
python3 webenum.py --check-tools
```

### 3. Run Enumeration

```bash
# Fast mode (recommended for first run)
python3 webenum.py -d example.com --skip-screenshots

# Full mode with screenshots
python3 webenum.py -d example.com
```

### 4. Analyze Results

```bash
python3 analyze_results.py results/example.com_*/
```

---

## 📦 Installation

### Prerequisites

- **Python 3.6+**
- **Go 1.19+**
- **Git** and **Build Tools**
- **Linux/macOS** (Windows via WSL2)

### Platform-Specific Setup

#### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install go python3 git

# Optional: massdns via Homebrew
brew install massdns
```

#### Linux (Ubuntu/Debian)

```bash
# Install dependencies
sudo apt update
sudo apt install -y golang-go python3 python3-pip git build-essential
```

#### Linux (Fedora/RHEL)

```bash
# Install dependencies
sudo dnf install -y golang python3 python3-pip git gcc make
```

### Automated Installation (Recommended)

The installation script automatically:
- Installs all Go-based tools
- Installs Python tools (uro)
- Compiles massdns from source if needed
- Configures PATH for all tools
- Detects your OS and architecture

```bash
# Run installer
chmod +x install_tools.sh
./install_tools.sh

# Reload shell configuration
source ~/.bashrc  # Linux
source ~/.zshrc   # macOS

# Verify tools
python3 webenum.py --check-tools
```

### Manual Installation

#### Critical Tools (Required)

```bash
# Subdomain enumeration
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# HTTP probing
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
```

#### DNS Tools (Highly Recommended)

```bash
# DNS tools
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install github.com/d3mondev/puredns/v2@latest

# massdns (required by puredns)
# macOS
brew install massdns

# Linux - compile from source
git clone https://github.com/blechschmidt/massdns
cd massdns
make
sudo make install
```

#### Recommended Tools

```bash
# More subdomain sources
go install github.com/tomnomnom/assetfinder@latest

# Findomain (binary download)
# Get correct binary for your platform from:
# https://github.com/Findomain/Findomain/releases/latest

# URL collection
go install github.com/lc/gau/v2/cmd/gau@latest
go install github.com/tomnomnom/waybackurls@latest
go install github.com/hakluke/hakrawler@latest

# Utilities
go install -v github.com/tomnomnom/anew@latest

# Python tools
python3 -m pip install --user uro
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

Ensure Go and Python binaries are in your PATH:

```bash
# Add to shell config (~/.bashrc or ~/.zshrc)
export PATH=$PATH:$(go env GOPATH)/bin
export PATH=$PATH:$(python3 -m site --user-base)/bin

# Reload shell
source ~/.bashrc  # or ~/.zshrc
```

### Installation Help

For platform-specific installation guidance:

```bash
python3 webenum.py --install-help
```

---

## 📖 Usage

### Basic Commands

```bash
# Single domain enumeration
python3 webenum.py -d target.com --skip-screenshots

# Custom output directory
python3 webenum.py -d target.com -o /path/to/output

# Full enumeration with screenshots
python3 webenum.py -d target.com

# Check tool installation status
python3 webenum.py --check-tools

# Get installation help
python3 webenum.py --install-help
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
python3 analyze_results.py results/example.com_*/

# Export to Markdown report
python3 analyze_results.py results/example.com_*/ --export report.md

# Quick summary only
python3 analyze_results.py results/example.com_*/ --summary-only
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
  python3 webenum.py -d target.com --skip-screenshots && \
  python3 analyze_results.py results/target.com_*/ --export ~/reports/weekly_$(date +\%Y\%m\%d).md
```

---

## 🛠️ Tools Reference

### Tool Categories

#### Critical (Required)
- **subfinder** - Fast subdomain enumeration using passive sources
- **httpx** - HTTP probing with technology detection

#### DNS Tools (Highly Recommended)
- **massdns** - Fast DNS resolver (required by puredns)
- **puredns** - Mass DNS resolution with validation
- **dnsx** - DNS enrichment (A, AAAA, CNAME records)

#### Recommended (High Priority)
- **assetfinder** - Additional subdomain sources
- **findomain** - Fast multi-source subdomain discovery
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

#### "massdns not found" Error

**This is required for DNS resolution with puredns.**

```bash
# macOS
brew install massdns

# Linux - compile from source
git clone https://github.com/blechschmidt/massdns
cd massdns
make
sudo make install

# Or run installer again
./install_tools.sh
```

**Note:** The tool will work without massdns, but DNS resolution will be limited.

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

#### gowitness Screenshots Failing

**The gowitness command syntax changed in newer versions.**

```bash
# Update to latest version
go install github.com/sensepost/gowitness@latest

# Or skip screenshots
python3 webenum.py -d example.com --skip-screenshots
```

The tool now automatically tries multiple gowitness command formats and will work with both old and new versions.

#### "uro not found" Error

```bash
# Install with user flag (no sudo needed)
python3 -m pip install --user uro

# Add Python user bin to PATH
export PATH="$PATH:$(python3 -m site --user-base)/bin"

# Make permanent
echo 'export PATH=$PATH:'"$(python3 -m site --user-base)/bin" >> ~/.bashrc
source ~/.bashrc
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

#### Tool Not Found After Installation

```bash
# Check if tool is installed
which subfinder

# If missing, reinstall
./install_tools.sh

# Verify Go bin directory
echo $(go env GOPATH)/bin
ls $(go env GOPATH)/bin

# Reload shell
source ~/.bashrc  # or ~/.zshrc
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
  └─> python3 webenum.py -d target.com --skip-screenshots

Phase 2: Analysis
  └─> python3 analyze_results.py results/target.com_*/

Phase 3: Deep Dive
  └─> Review interesting hosts, technologies, URLs

Phase 4: Targeted Testing
  └─> Use nuclei, ffuf on specific findings

Phase 5: Reporting
  └─> python3 analyze_results.py results/target.com_*/ --export report.md
```

---

## 📊 Example Scenarios

### Bug Bounty Reconnaissance

```bash
# Initial broad enumeration
python3 webenum.py -d target.com -o ~/bugbounty/target/

# Analyze for interesting findings
python3 analyze_results.py ~/bugbounty/target/target.com_*/

# Extract WordPress sites for deeper testing
cat ~/bugbounty/target/*/http/httpx_full.json | \
  jq -r 'select(.tech[] | test("WordPress")) | .url' > wordpress_targets.txt

# Check for common misconfigurations
cat wordpress_targets.txt | nuclei -t wordpress/
```

### Penetration Testing

```bash
# Comprehensive enumeration with screenshots
python3 webenum.py -d client.com -o ~/pentests/client_2025/

# Generate detailed report
python3 analyze_results.py ~/pentests/client_2025/client.com_*/ \
  --export ~/pentests/client_2025/recon_report.md

# Visual review of interesting pages
firefox ~/pentests/client_2025/*/screenshots/
```

### Asset Discovery

```bash
# Batch process multiple domains
cat company_domains.txt | while read domain; do
  python3 webenum.py -d "$domain" -o ~/asset_discovery/ --skip-screenshots
done

# Consolidate findings
for dir in ~/asset_discovery/*/; do
  python3 analyze_results.py "$dir" --summary-only
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
- Include environment details (OS, architecture)
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
- [massdns](https://github.com/blechschmidt/massdns) - Fast DNS resolver

Special thanks to the bug bounty and pentesting community for continuous feedback and improvements.

---

## 📞 Support

- **Documentation**: This README
- **Installation Help**: `python3 webenum.py --install-help`
- **Tool Check**: `python3 webenum.py --check-tools`
- **Issues**: [GitHub Issues](https://github.com/yourusername/givenum/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/givenum/discussions)

---

## 📈 Project Status

- ✅ Core functionality complete
- ✅ All major tools integrated
- ✅ Comprehensive documentation
- ✅ Cross-platform support (Linux & macOS)
- ✅ Error handling and edge cases
- 🔄 Continuous improvements
- 📋 Feature requests welcome

---

## 🎯 Roadmap

### v1.1 (Current)
- [x] Fixed massdns installation
- [x] Fixed gowitness compatibility
- [x] Fixed uro installation
- [x] Cross-platform support (macOS & Linux)
- [x] Better error handling

### v1.2 (Planned)
- [ ] HTML report generation
- [ ] Database backend for results
- [ ] Improved diff functionality
- [ ] Custom tool configurations

### v1.3 (Future)
- [ ] Web interface
- [ ] Real-time notifications
- [ ] Cloud deployment support
- [ ] API endpoints

---

**Givenum** - Enumerate. Analyze. Conquer. 🎯

*Made with ❤️ by @6bat66 for the Bug Bounty & Penetration Testing community*

---

## ⭐ Star History

If you find this tool useful, please consider giving it a star on GitHub!

[![Star History](https://img.shields.io/github/stars/yourusername/givenum?style=social)](https://github.com/yourusername/givenum/stargazers)