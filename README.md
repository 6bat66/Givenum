# WebEnum

**Advanced Web Enumeration Framework**

Comprehensive reconnaissance tool for web application security testing, bug bounty hunting, and penetration testing.

## Features

### Subdomain Discovery
- **Active Tools**: subfinder, assetfinder, findomain, amass, chaos
- **Passive Sources**: Certificate Transparency logs (crt.sh)
- **API Integration**: VirusTotal, SecurityTrails
- **JS Analysis**: Subdomain extraction from JavaScript files

### HTTP Analysis
- **Modern Probing**: httpx with full feature detection
- **Security Headers**: Automatic analysis of missing security headers
- **Favicon Intelligence**: Hash-based technology identification
- **Technology Detection**: webanalyze, retire.js integration
- **Screenshots**: gowitness for visual reconnaissance

### Port Scanning
- **Fast Scanning**: sdlookup using Shodan's internetdb (no slow nmap scans)
- **Service Detection**: Quick identification of open ports and services

### URL Discovery
- **Modern Crawlers**: xurlfind3r, katana for comprehensive coverage
- **Web Archives**: gau, waybackurls for historical data
- **Live Crawling**: gospider for real-time discovery
- **Smart Filtering**: uro for URL deduplication

### JavaScript Analysis
- **Subdomain Extraction**: jsubfinder for finding subdomains in JS
- **URL Extraction**: getallurls for comprehensive endpoint discovery
- **Secret Scanning**: trufflehog for finding leaked credentials
- **JS Collection**: subjs for gathering all JavaScript files

### Git Repository Analysis
- **Exposure Detection**: Automatic .git directory discovery
- **Repository Dumping**: goop for extracting exposed repositories
- **Secret Scanning**: trufflehog for finding secrets in git history

### Vulnerability Scanning
- **Template-Based**: Nuclei with 3000+ templates
- **Jaeles**: Additional vulnerability checks
- **nikto**: Web server scanner

### Parameter Discovery
- **Hidden Parameters**: Arjun, x8 for finding undocumented parameters
- **Analysis**: Automatic detection of interesting parameters
- **Fuzzing**: Parameter-based attack surface identification

### Directory Fuzzing
- **Modern Fuzzers**: feroxbuster, ffuf, gobuster
- **Smart Wordlists**: Configurable wordlist support
- **Fast Scanning**: Optimized for speed and accuracy

### Additional Features
- **Diff Tracking**: Compare scans to identify changes over time
- **Report Generation**: Professional Markdown reports
- **Cross-Platform**: Works on macOS and Debian/Kali
- **API Management**: Secure API key storage and management

## Installation

### Prerequisites

**Required:**
- Go 1.20+
- Python 3.8+
- git, wget, curl

**macOS:**
```bash
brew install go python3 git wget curl
```

**Debian/Kali:**
```bash
sudo apt update
sudo apt install golang-go python3 python3-pip git wget curl build-essential
```

### Quick Install

```bash
# Clone repository
git clone https://github.com/yourusername/webenum
cd webenum

# Make executable
chmod +x install_tools.sh

# Install all tools
./install_tools.sh

# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc
```

### Manual Tool Installation

If you prefer to install specific tools:

```bash
# Core subdomain tools
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/tomnomnom/assetfinder@latest

# HTTP probing
go install github.com/projectdiscovery/httpx/cmd/httpx@latest

# DNS resolution
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install github.com/d3mondev/puredns/v2@latest

# Port scanning (sdlookup instead of nmap)
go install github.com/j3ssie/sdlookup@latest

# Modern URL collection
go install github.com/hueristiq/xurlfind3r/cmd/xurlfind3r@latest
go install github.com/projectdiscovery/katana/cmd/katana@latest

# Vulnerability scanning
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
nuclei -update-templates

# Utilities
go install github.com/tomnomnom/anew@latest
pip3 install uro
```

## Configuration

### API Keys (Optional but Recommended)

Configure API keys for enhanced subdomain discovery:

```bash
python3 webenum.py --configure-api
```

**Supported APIs:**
- **VirusTotal**: https://www.virustotal.com/gui/join-us
- **SecurityTrails**: https://securitytrails.com/
- **Shodan**: https://www.shodan.io/

API keys are stored securely in `~/.config/webenum/api_keys.json`

### Tool Verification

Check which tools are installed:

```bash
python3 webenum.py --check-tools
```

## Usage

### Basic Scan

```bash
python3 webenum.py -d example.com
```

### Custom Output Directory

```bash
python3 webenum.py -d example.com -o /path/to/output
```

### Skip Optional Steps

```bash
# Skip screenshots (faster)
python3 webenum.py -d example.com --skip-screenshots

# Skip port scanning
python3 webenum.py -d example.com --skip-portscan

# Skip vulnerability scanning
python3 webenum.py -d example.com --skip-vuln

# Combine multiple skips
python3 webenum.py -d example.com --skip-screenshots --skip-portscan --skip-vuln
```

### Enable Fuzzing

```bash
python3 webenum.py -d example.com --enable-fuzzing
```

### Full Options

```bash
python3 webenum.py -h
```

## Output Structure

```
results/example.com_20250122_123456/
├── subdomains/
│   ├── all_subdomains.txt    # Consolidated subdomains
│   ├── subfinder.txt
│   ├── assetfinder.txt
│   ├── amass.txt
│   ├── crtsh.txt
│   └── from_js.txt           # Subdomains found in JS
├── dns/
│   ├── resolved.txt          # Active subdomains
│   ├── a_records.txt
│   └── cname_records.txt
├── http/
│   ├── alive.txt             # Active HTTP services
│   ├── httpx.json            # Detailed HTTP data
│   └── security_headers.json # Security header analysis
├── ports/
│   ├── sdlookup.json         # Port scan results
│   └── summary.txt           # Port summary
├── urls/
│   ├── all_urls_raw.txt      # All discovered URLs
│   ├── all_urls_clean.txt    # Deduplicated URLs
│   ├── xurlfind3r.txt
│   └── katana.txt
├── js/
│   ├── js_files.txt          # JavaScript files
│   ├── jsubfinder_subs.txt   # Subdomains from JS
│   └── js_urls.txt           # URLs from JS
├── secrets/
│   └── js_secrets.json       # Secrets found in JS
├── tech/
│   └── favicon_hashes.json   # Favicon hashes
├── vulnerabilities/
│   ├── nuclei.txt            # Vulnerabilities found
│   └── nuclei.json
├── parameters/
│   ├── all_params.txt        # All parameters
│   ├── interesting.txt       # Interesting parameters
│   ├── arjun.txt
│   └── x8.txt
├── git/
│   ├── exposed.txt           # Exposed .git repositories
│   └── dumps/                # Dumped repositories
├── diff/
│   └── *.diff                # Changes from previous scan
└── reports/
    └── report.md             # Final report
```

## Workflow Examples

### Bug Bounty Reconnaissance

```bash
# Phase 1: Fast passive scan
python3 webenum.py -d target.com \
    --skip-portscan \
    --skip-screenshots \
    --skip-vuln

# Review results
cat results/target.com_*/reports/report.md

# Phase 2: Deep scan on interesting assets
python3 webenum.py -d interesting.target.com --enable-fuzzing
```

### Red Team Assessment

```bash
# Stealthy scan (passive only)
python3 webenum.py -d corp.com \
    --skip-portscan \
    --skip-screenshots \
    --skip-vuln
```

### Continuous Monitoring

```bash
# Daily scan via cron
0 2 * * * cd /path/to/webenum && python3 webenum.py -d target.com

# Check for changes
cat results/target.com_*/diff/*.diff
```

### Penetration Testing

```bash
# Comprehensive scan with all features
python3 webenum.py -d target.com --enable-fuzzing
```

## Batch Processing

Process multiple domains:

```bash
# Create domains file
cat > domains.txt << EOF
example.com
target.com
test.com
EOF

# Run batch scan
./batch_enum.sh domains.txt --skip-screenshots
```

## Results Analysis

### View Summary

```bash
# Quick statistics
python3 analyze_results.py results/example.com_20250122_123456/ --summary-only

# Detailed analysis
python3 analyze_results.py results/example.com_20250122_123456/
```

### Find Specific Data

```bash
# Check subdomains
cat results/*/subdomains/all_subdomains.txt

# Check active hosts
cat results/*/http/alive.txt

# Check vulnerabilities
cat results/*/vulnerabilities/nuclei.txt

# Check exposed git repos
cat results/*/git/exposed.txt

# View report
cat results/*/reports/report.md
```

### Check for Changes

```bash
# View diff from previous scan
cat results/example.com_*/diff/*.diff
```

## Performance Tips

### Speed Up Scans

```bash
# Skip time-consuming steps
python3 webenum.py -d example.com \
    --skip-screenshots \
    --skip-portscan \
    --skip-fuzzing
```

### Optimize for Large Targets

- Use `--skip-screenshots` to save time
- Limit fuzzing to specific targets only
- Use API keys for faster subdomain discovery

### Resource Management

```bash
# Limit memory usage (Linux)
ulimit -m 4000000  # 4GB limit

# Monitor resource usage
watch -n 5 'ps aux | grep webenum'
```

## Troubleshooting

### Missing Tools

```bash
# Check which tools are missing
python3 webenum.py --check-tools

# Reinstall missing tools
./install_tools.sh
```

### Permission Errors

```bash
# Fix tool permissions
chmod +x install_tools.sh
chmod +x batch_enum.sh

# Fix Go binary path
export PATH=$PATH:$(go env GOPATH)/bin
```

### API Rate Limits

Configure API keys to avoid rate limits:

```bash
python3 webenum.py --configure-api
```

### Tool Not Found

Reload your shell configuration:

```bash
source ~/.bashrc  # or ~/.zshrc

# Or add to PATH manually
export PATH=$PATH:$HOME/go/bin
```

## Best Practices

### 1. Always Get Authorization
Never scan targets without explicit permission.

### 2. Start Passive
Begin with passive techniques before active scanning.

### 3. Use API Keys
Configure API keys for better subdomain discovery (50-200% more results).

### 4. Regular Scans
Run scans regularly to track infrastructure changes via diff tracking.

### 5. Review Diffs
Always check the diff/ directory after each scan.

### 6. Verify Findings
Manually verify automated findings before reporting.

### 7. Respect Rate Limits
Use appropriate delays and respect API rate limits.

### 8. Document Everything
Keep detailed notes of your findings and methodology.

## Advanced Usage

### Custom Wordlists

```bash
# Place wordlists in config directory
mkdir -p ~/.config/webenum/wordlists/
wget https://example.com/custom-wordlist.txt \
    -O ~/.config/webenum/wordlists/custom.txt

# Tool will use wordlists automatically
```

### Integration with Other Tools

```bash
# Export results for Burp Suite
cat results/*/urls/all_urls_clean.txt > burp_targets.txt

# Export subdomains for further testing
cat results/*/subdomains/all_subdomains.txt > subdomains.txt
```

### Automation

```bash
# Create alias
echo 'alias webenum="python3 /path/to/webenum.py"' >> ~/.bashrc

# Use alias
webenum -d target.com
```

## Contributing

Contributions welcome! Areas for improvement:

- Additional reconnaissance tools
- More API integrations
- Enhanced reporting formats
- Performance optimizations
- Better error handling

## Tool Credits

This framework integrates many excellent open-source tools:

- **ProjectDiscovery**: subfinder, httpx, dnsx, nuclei, katana, chaos
- **TomNomNom**: assetfinder, waybackurls, anew, unfurl, qsreplace
- **OWASP**: amass
- **Community Tools**: gau, gospider, jsubfinder, sdlookup, feroxbuster, and many more

## Legal & Ethical

**Important**: Only use this tool on systems you have permission to test.

- Get written authorization before scanning
- Respect scope limitations
- Follow responsible disclosure practices
- Obey rate limits and ToS
- Never cause service disruption

Unauthorized scanning is illegal and unethical.

## Support

- **Issues**: Report bugs via GitHub Issues
- **Questions**: Use GitHub Discussions
- **Documentation**: Check CHEAT_SHEET.md for quick reference

## License

MIT License - See LICENSE file for details

---

**Happy Hunting!** 🎯

For quick reference commands, see [CHEAT_SHEET.md](CHEAT_SHEET.md)