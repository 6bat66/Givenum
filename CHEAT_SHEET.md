# WebEnum - Quick Reference

## 🚀 Common Commands

### Installation
```bash
# Install all tools
./install_tools.sh

# Configure API keys
python3 webenum.py --configure-api

# Check tools
python3 webenum.py --check-tools
```

### Basic Scans
```bash
# Standard scan
python3 webenum.py -d example.com

# Fast scan (skip optional steps)
python3 webenum.py -d example.com --skip-screenshots --skip-portscan --skip-vuln

# Deep scan with fuzzing
python3 webenum.py -d example.com --enable-fuzzing

# Custom output
python3 webenum.py -d example.com -o /path/to/output
```

### Batch Processing
```bash
# Multiple domains
./batch_enum.sh domains.txt --skip-screenshots
```

## 📁 Output Locations

### Key Files
```bash
# All subdomains
cat results/*/subdomains/all_subdomains.txt

# Active HTTP hosts
cat results/*/http/alive.txt

# All URLs
cat results/*/urls/all_urls_clean.txt

# Vulnerabilities
cat results/*/vulnerabilities/nuclei.txt

# Exposed Git repos
cat results/*/git/exposed.txt

# Final report
cat results/*/reports/report.md

# Changes from previous scan
cat results/*/diff/*.diff
```

## 🔍 Analysis Commands

### Quick Stats
```bash
# Count subdomains
wc -l results/*/subdomains/all_subdomains.txt

# Count active hosts
wc -l results/*/http/alive.txt

# Count URLs
wc -l results/*/urls/all_urls_clean.txt
```

### Find Interesting Data
```bash
# Admin panels
grep -i "admin\|panel\|dashboard" results/*/http/httpx.json

# Development environments
grep -i "dev\|staging\|test\|uat" results/*/subdomains/all_subdomains.txt

# API endpoints
grep -i "api" results/*/urls/all_urls_clean.txt

# Interesting parameters
cat results/*/parameters/interesting.txt
```

## 🎯 Hunting Workflows

### Bug Bounty Recon
```bash
# Step 1: Fast passive scan
python3 webenum.py -d target.com --skip-portscan --skip-screenshots --skip-vuln

# Step 2: Review findings
cat results/target.com_*/reports/report.md

# Step 3: Deep dive on interesting assets
python3 webenum.py -d api.target.com --enable-fuzzing
```

### Vulnerability Patterns

#### SSRF Candidates
```bash
grep -E '(url=|uri=|target=|dest=|redirect=|proxy=)' results/*/urls/all_urls_clean.txt
```

#### LFI/Path Traversal
```bash
grep -E '(file=|path=|page=|include=|dir=|folder=)' results/*/urls/all_urls_clean.txt
```

#### SQL Injection
```bash
grep -E '(id=|user=|product=|category=|item=)' results/*/urls/all_urls_clean.txt
```

#### Open Redirect
```bash
grep -E '(redirect=|url=|return=|next=|callback=)' results/*/urls/all_urls_clean.txt
```

#### XSS Reflection
```bash
grep -E '(search=|query=|keyword=|q=|s=)' results/*/urls/all_urls_clean.txt
```

## 🛠️ Tool-Specific Commands

### Subfinder (standalone)
```bash
subfinder -d example.com -all -o subdomains.txt
```

### HTTPx (standalone)
```bash
cat domains.txt | httpx -silent -tech-detect -status-code
```

### Nuclei (standalone)
```bash
cat urls.txt | nuclei -severity critical,high
```

### sdlookup (standalone)
```bash
sdlookup -d example.com
```

### katana (standalone)
```bash
katana -u https://example.com -depth 3 -js-crawl
```

### jsubfinder (standalone)
```bash
jsubfinder -f urls.txt
```

## 📊 Analysis Patterns

### Technology Stack
```bash
# Extract technologies from httpx results
jq '.tech[]' results/*/http/httpx.json | sort -u
```

### Status Codes
```bash
# Count status codes
jq '.status_code' results/*/http/httpx.json | sort | uniq -c | sort -rn
```

### Port Summary
```bash
# View open ports
cat results/*/ports/summary.txt
```

### Security Headers
```bash
# Check missing headers
jq '.[] | select(.missing | length > 0)' results/*/http/security_headers.json
```

## 🔄 Continuous Monitoring

### Cron Jobs
```bash
# Daily scan
0 2 * * * cd /opt/webenum && python3 webenum.py -d target.com --skip-screenshots

# Weekly full scan
0 3 * * 0 cd /opt/webenum && python3 webenum.py -d target.com

# Check for new findings
0 9 * * * cat /opt/webenum/results/target.com_*/diff/*.diff | mail -s "New Findings" you@example.com
```

### Compare Scans
```bash
# Find differences between two scans
diff results/target.com_OLD/subdomains/all_subdomains.txt \
     results/target.com_NEW/subdomains/all_subdomains.txt
```

## 💡 Pro Tips

### 1. API Keys
```bash
# Always configure API keys for better results
python3 webenum.py --configure-api

# Result: 50-200% more subdomains
```

### 2. Start Passive
```bash
# Begin with passive techniques
python3 webenum.py -d target.com --skip-portscan --skip-screenshots
```

### 3. Review Diffs
```bash
# Always check changes
cat results/*/diff/*.diff
```

### 4. Focus on High Value
```bash
# Look for admin/API endpoints
grep -i "admin\|api\|portal" results/*/subdomains/all_subdomains.txt
```

### 5. Verify Manually
```bash
# Always verify automated findings
# Don't rely solely on tool output
```

## 🐛 Debugging

### Check Tool Availability
```bash
python3 webenum.py --check-tools
```

### View Logs
```bash
# Check scan logs
tail -f results/*/logs/*.log
```

### Test Individual Tools
```bash
# Test subfinder
subfinder -d example.com -silent

# Test httpx
echo "https://example.com" | httpx -silent

# Test nuclei
nuclei -u https://example.com -silent
```

## 📦 Export Results

### For Burp Suite
```bash
cat results/*/urls/all_urls_clean.txt > burp_targets.txt
```

### For Nmap
```bash
awk '{print $1}' results/*/dns/a_records.txt > nmap_targets.txt
```

### For Further Testing
```bash
# Active hosts
cat results/*/http/alive.txt > active_hosts.txt

# All subdomains
cat results/*/subdomains/all_subdomains.txt > subdomains.txt
```

## ⚡ Performance

### Speed Up Scans
```bash
# Skip time-consuming steps
python3 webenum.py -d example.com \
    --skip-screenshots \
    --skip-portscan \
    --skip-fuzzing \
    --skip-vuln
```

### Limit Resources
```bash
# Limit memory (Linux)
ulimit -m 4000000  # 4GB

# Monitor resources
watch -n 5 'ps aux | grep webenum'
```

## 🔒 Security

### Scope Management
```bash
# Create scope file
cat > scope.txt << EOF
*.example.com
!admin.example.com
EOF

# Filter results
grep -f scope.txt results/*/subdomains/all_subdomains.txt
```

### Rate Limiting
```bash
# Use delays in batch processing
./batch_enum.sh domains.txt --delay 60
```

## 📚 Integration Examples

### With Other Tools

#### Aquatone
```bash
cat results/*/http/alive.txt | aquatone
```

#### MassDNS
```bash
massdns -r resolvers.txt -o S -w resolved.txt results/*/subdomains/all_subdomains.txt
```

#### Gau + Nuclei
```bash
gau example.com | nuclei -t cves/
```

#### httpx + Nuclei
```bash
cat results/*/http/alive.txt | nuclei -severity critical,high
```

## 🎓 Learning Resources

### Practice Targets
- HackTheBox
- PortSwigger Web Security Academy
- TryHackMe
- PentesterLab

### Bug Bounty Platforms
- HackerOne
- Bugcrowd
- Intigriti
- YesWeHack

## 🆘 Quick Help

```bash
# Help
python3 webenum.py -h

# Tool check
python3 webenum.py --check-tools

# API config
python3 webenum.py --configure-api
```

---

**Remember:**
1. Always get authorization
2. Start passive, then active
3. Use API keys
4. Review diffs regularly
5. Verify findings manually

**Happy Hunting! 🎯**