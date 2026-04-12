# WebEnum - Quick Reference

## 🚀 Installation

```bash
# Install all tools
chmod +x install_tools.sh
./install_tools.sh

# Configure API keys
python3 GivEnum.py --configure-api

# Verify installation
python3 GivEnum.py --check-tools
```

## ⚡ Common Commands

### Basic Scans

```bash
# Passive scan (default) — subdomain discovery, HTTP, URLs, JS, git, takeover
python3 GivEnum.py -d example.com

# Active scan — adds brute-force, port scan, nuclei, dalfox (XSS), subjack, arjun
python3 GivEnum.py -d example.com --active

# Active but skip heavy steps
python3 GivEnum.py -d example.com --active --skip-screenshots --skip-portscan

# Active but skip vuln scan (nuclei + dalfox)
python3 GivEnum.py -d example.com --active --skip-vuln-scan

# Custom output directory
python3 GivEnum.py -d example.com -o /path/to/output
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

### Batch Processing

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

### Analysis

```bash
# Analyze results
python3 analyze_results.py results/example.com_20250122_123456/

# Summary only
python3 analyze_results.py results/example.com_*/ --summary-only

# Export report
python3 analyze_results.py results/example.com_*/ --export report.md
```

## 📊 One-Liners

### Find Interesting Assets

```bash
# Admin panels
grep -i "admin\|dashboard\|panel" results/*/http/httpx_full.json

# API endpoints
grep -i "api" results/*/urls/urls_clean.txt

# Development environments
grep -E "(dev|staging|test)" results/*/subdomains/all_subdomains.txt

# Exposed Git
cat results/*/git/exposed_git.txt

# Cloud services
cat results/*/cloud/*.txt

# Vulnerabilities
cat results/*/vulnerabilities/nuclei_results.txt
```

### Extract Data

```bash
# All URLs with parameters
grep '?' results/*/urls/urls_clean.txt

# JavaScript files
cat results/*/js/all_js_files.txt

# Open ports
cat results/*/ports/open_ports.txt

# Status codes
jq '.status_code' results/*/http/httpx_full.json | sort | uniq -c

# Technologies
jq '.tech[]' results/*/http/httpx_full.json | sort -u

# Interesting parameters
cat results/*/parameters/interesting_parameters.txt
```

### Vulnerability Hunting

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

## 🎯 Workflows

### Bug Bounty Recon

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
# Stealthy passive reconnaissance
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
0 2 * * * cd /opt/webenum && python3 GivEnum.py -d target.com --skip-screenshots

# Check changes
cat results/target.com_*/diff/*.diff

# Alert on new findings
NEW=$(wc -l < results/target.com_*/diff/all_subdomains.txt.diff)
[ "$NEW" -gt 0 ] && echo "New subdomains: $NEW"
```

## 🔧 Tool Integration

### With Burp Suite

```bash
# Export for Burp
cat results/*/urls/urls_clean.txt > burp_targets.txt
```

### With SQLMap

```bash
# Test SQL injection
cat results/*/urls/urls_clean.txt | grep '?' | head -10 | while read url; do
    sqlmap -u "$url" --batch --risk=2
done
```

### With Dalfox

```bash
# Test XSS
cat results/*/urls/urls_clean.txt | grep '?' | dalfox pipe
```

## 📈 Statistics

### Count Results

```bash
# Subdomains
wc -l results/*/subdomains/all_subdomains.txt

# Active hosts
wc -l results/*/http/alive.txt

# URLs
wc -l results/*/urls/urls_clean.txt

# JS files
wc -l results/*/js/all_js_files.txt

# Vulnerabilities
wc -l results/*/vulnerabilities/nuclei_results.txt
```

### Compare Scans

```bash
# Compare subdomains
diff results/example.com_OLD/subdomains/all_subdomains.txt \
     results/example.com_NEW/subdomains/all_subdomains.txt

# New subdomains
comm -13 results/example.com_OLD/subdomains/all_subdomains.txt \
         results/example.com_NEW/subdomains/all_subdomains.txt
```

## 🛠️ Troubleshooting

### Check Installation

```bash
# Verify tools
python3 GivEnum.py --check-tools

# Check specific tool
which subfinder httpx nuclei
```

### Fix Missing Tools

```bash
# Reinstall specific tool
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# Reinstall all
./install_tools.sh
```

### View Logs

```bash
# Real-time monitoring
tail -f results/*/logs/*.log

# Check for errors
grep -i error results/*/logs/*.log
```

## 🎓 Pro Tips

### API Keys

```bash
# Always configure for better results
python3 GivEnum.py --configure-api

# Expect 50-200% more subdomains with APIs
```

### Speed Optimization

```bash
# Skip time-consuming steps for fast scans
python3 GivEnum.py -d target.com \
    --skip-portscan \
    --skip-vuln-scan \
    --skip-screenshots
```

### Automated Monitoring

```bash
# Add to crontab
crontab -e

# Daily 2 AM scan
0 2 * * * cd /opt/webenum && python3 GivEnum.py -d target.com --skip-screenshots >> /var/log/webenum.log 2>&1
```

### Diff Tracking

```bash
# Always review diff between scans
cat results/target.com_*/diff/*.diff

# Focus on new subdomains
grep "^+" results/target.com_*/diff/all_subdomains.txt.diff
```

### Result Organization

```bash
# Archive old results
tar -czf target.com_$(date +%Y%m).tar.gz results/target.com_*
mv target.com_*.tar.gz archives/

# Keep last 3 scans
ls -dt results/target.com_* | tail -n +4 | xargs rm -rf
```

## 📚 Quick References

### File Locations

```
~/.config/givenum/api_keys.json    # API keys
~/.config/givenum/wordlists/       # Wordlists
./results/                          # Scan results
./batch_logs/                       # Batch processing logs
```

### Important Files

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

### Output Formats

```
.txt  - Plain text lists
.json - JSON structured data
.md   - Markdown reports
.diff - Difference from previous scan
```

## ⚠️ Remember

1. **Always get permission** before scanning
2. **Configure API keys** for better results
3. **Review diff output** to track changes
4. **Start passive** then go active
5. **Combine tools** for best coverage
6. **Verify findings** manually
7. **Document everything**

## 🔗 Resources

- **Documentation**: README.md
- **Tool Check**: `python3 GivEnum.py --check-tools`
- **API Setup**: `python3 GivEnum.py --configure-api`
- **Help**: `python3 GivEnum.py --help`

---

**Happy Hunting! 🎯**