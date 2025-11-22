# WebEnum Enhanced - Quick Reference Cheat Sheet

## 🚀 Common Commands

### Initial Setup
```bash
# Install all tools
chmod +x install_tools_enhanced.sh
./install_tools_enhanced.sh

# Configure API keys
python3 webenum_enhanced.py --configure-api

# Verify installation
python3 webenum_enhanced.py --check-tools
```

### Basic Scans

```bash
# Standard scan
python3 webenum_enhanced.py -d example.com

# Fast scan (skip optional steps)
python3 webenum_enhanced.py -d example.com --skip-screenshots --skip-portscan --skip-vuln-scan

# Deep scan with fuzzing
python3 webenum_enhanced.py -d example.com --enable-fuzzing

# Custom output directory
python3 webenum_enhanced.py -d example.com -o /path/to/output
```

### Advanced Usage

```bash
# Batch processing multiple domains
./batch_enum_enhanced.sh domains.txt --skip-screenshots

# Compare with previous scan (automatic)
python3 webenum_enhanced.py -d example.com
# Check results/example.com_*/diff/ for changes

# View results
cat results/example.com_*/reports/report.md
python3 analyze_results.py results/example.com_20250122_123456/
```

---

## 📋 Workflow Examples

### Bug Bounty Recon
```bash
# Step 1: Passive enumeration only
python3 webenum_enhanced.py -d target.com \
    --skip-portscan \
    --skip-screenshots \
    --skip-vuln-scan

# Step 2: Review findings
cat results/target.com_*/subdomains/all_subdomains.txt
cat results/target.com_*/http/alive.txt

# Step 3: Deep dive on interesting hosts
python3 webenum_enhanced.py -d interesting.target.com --enable-fuzzing
```

### Red Team Assessment
```bash
# Stealthy passive-only scan
python3 webenum_enhanced.py -d corp.com \
    --skip-portscan \
    --skip-screenshots \
    --skip-fuzzing

# Check for low-hanging fruit
grep -i "admin\|login\|panel" results/corp.com_*/http/httpx_full.json
cat results/corp.com_*/git/exposed_git.txt
cat results/corp.com_*/vulnerabilities/nuclei_results.txt
```

### Continuous Monitoring
```bash
# Daily cron job
0 2 * * * cd /opt/webenum && python3 webenum_enhanced.py -d target.com --skip-screenshots

# Weekly full scan
0 3 * * 0 cd /opt/webenum && python3 webenum_enhanced.py -d target.com

# Alert on new findings
python3 check_diff.py results/target.com_* && notify-send "New findings!"
```

---

## 🔍 One-Liner Analysis

### Find Interesting Subdomains
```bash
# Admin panels
grep -i "admin\|panel\|dashboard" results/*/http/httpx_full.json

# Development environments
grep -i "dev\|staging\|test\|uat" results/*/subdomains/all_subdomains.txt

# Cloud services
cat results/*/cloud/*.txt

# Exposed Git repos
cat results/*/git/exposed_git.txt
```

### Extract Specific Data
```bash
# All URLs with parameters
grep '?' results/*/urls/urls_clean.txt

# JavaScript files
cat results/*/js/js_files.txt

# Interesting parameters
cat results/*/parameters/interesting_parameters.txt

# Technologies detected
jq '.tech' results/*/http/httpx_full.json | sort -u

# Status codes summary
jq '.status_code' results/*/http/httpx_full.json | sort | uniq -c
```

### Quick Stats
```bash
# Count subdomains
wc -l results/*/subdomains/all_subdomains.txt

# Count active hosts
wc -l results/*/http/alive.txt

# Count URLs
wc -l results/*/urls/urls_clean.txt

# Count vulnerabilities
wc -l results/*/vulnerabilities/nuclei_results.txt
```

---

## 🎯 Target-Specific Hunting

### Looking for Specific Vulnerabilities

#### SSRF Candidates
```bash
grep -E '(url=|uri=|target=|dest=|redirect=|proxy=)' results/*/urls/urls_clean.txt
```

#### LFI/Path Traversal
```bash
grep -E '(file=|path=|page=|include=|dir=|folder=)' results/*/urls/urls_clean.txt
```

#### SQL Injection
```bash
grep -E '(id=|user=|product=|category=|item=)' results/*/urls/urls_clean.txt
```

#### Open Redirect
```bash
grep -E '(redirect=|url=|return=|next=|callback=)' results/*/urls/urls_clean.txt
```

#### XSS Reflection Points
```bash
grep -E '(search=|query=|keyword=|q=|s=)' results/*/urls/urls_clean.txt
```

---

## 🛠️ Tool-Specific Commands

### Subfinder
```bash
# Run standalone
subfinder -d example.com -all -silent -o subs.txt
```

### HTTPx
```bash
# Probe URLs with tech detection
cat urls.txt | httpx -silent -tech-detect -status-code -title
```

### Nuclei
```bash
# Scan specific severity
cat alive.txt | nuclei -severity critical,high -silent

# Scan with specific templates
cat alive.txt | nuclei -t cves/ -t exposures/ -silent

# Update templates
nuclei -update-templates
```

### Ffuf
```bash
# Directory fuzzing
ffuf -u https://target.com/FUZZ -w wordlist.txt -mc 200,301,302 -o results.json

# Parameter fuzzing
ffuf -u https://target.com/page?FUZZ=test -w params.txt -mc 200
```

### Arjun
```bash
# Parameter discovery
arjun -u https://target.com/endpoint -oT params.txt

# From file
arjun -i urls.txt -oT params.txt
```

---

## 📊 Analysis Scripts

### Generate Summary Report
```bash
python3 analyze_results.py results/example.com_20250122_123456/
```

### Export to CSV
```bash
# Convert JSON to CSV
jq -r '.url, .status_code, .title' results/*/http/httpx_full.json | paste - - - > hosts.csv
```

### Find New Discoveries
```bash
# Compare with previous scan
diff results/example.com_OLD/subdomains/all_subdomains.txt \
     results/example.com_NEW/subdomains/all_subdomains.txt
```

---

## 🔐 API Key Management

### Configure All Services
```bash
python3 webenum_enhanced.py --configure-api
```

### Manual Configuration
```bash
# Create config file
mkdir -p ~/.config/webenum
cat > ~/.config/webenum/api_keys.json << 'EOF'
{
  "virustotal": "your_api_key_here",
  "securitytrails": "your_api_key_here",
  "certspotter": "your_api_key_here",
  "shodan": "your_api_key_here"
}
EOF
```

### Test API Keys
```bash
# VirusTotal
curl "https://www.virustotal.com/vtapi/v2/domain/report?apikey=YOUR_KEY&domain=google.com"

# SecurityTrails
curl -H "APIKEY: YOUR_KEY" "https://api.securitytrails.com/v1/domain/google.com/subdomains"
```

---

## 💡 Pro Tips

### 1. Scope Management
```bash
# Create scope file
cat > scope.txt << 'EOF'
example.com
*.example.com
app.example.com
EOF

# Filter results
grep -f scope.txt results/*/subdomains/all_subdomains.txt > in_scope.txt
```

### 2. Prioritize Targets
```bash
# High-value subdomains
grep -E '(admin|api|portal|dashboard|internal|stage|dev)' results/*/subdomains/all_subdomains.txt
```

### 3. Quick Wins
```bash
# Check for:
# - Exposed .git directories
cat results/*/git/exposed_git.txt

# - Subdomain takeovers
cat results/*/takeover/subzy_results.txt

# - High/Critical vulnerabilities
grep -E '(critical|high)' results/*/vulnerabilities/nuclei_results.txt

# - Interesting parameters
cat results/*/parameters/interesting_parameters.txt
```

### 4. Automation
```bash
# Create alias
echo 'alias webenum="python3 /path/to/webenum_enhanced.py"' >> ~/.bashrc

# Use it
webenum -d target.com
```

### 5. Notification on Completion
```bash
# With notify-send (Linux)
python3 webenum_enhanced.py -d target.com && notify-send "Scan Complete"

# With osascript (macOS)
python3 webenum_enhanced.py -d target.com && osascript -e 'display notification "Scan Complete"'

# With Slack webhook
python3 webenum_enhanced.py -d target.com && \
  curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Scan complete for target.com"}' \
  YOUR_SLACK_WEBHOOK_URL
```

---

## 🐛 Debugging

### Check Tool Availability
```bash
python3 webenum_enhanced.py --check-tools
```

### View Logs
```bash
# Real-time log monitoring
tail -f results/*/logs/*.log

# Search for errors
grep -i error results/*/logs/*.log
```

### Test Individual Tools
```bash
# Subfinder
subfinder -d example.com -silent

# HTTPx
echo "https://example.com" | httpx -silent

# Nuclei
nuclei -u https://example.com -silent
```

---

## 📦 Wordlists

### Default Location
```
~/.config/webenum/wordlists/
├── subdomains-top1m.txt
├── common.txt
├── raft-small-directories.txt
└── burp-parameter-names.txt
```

### Download Additional Wordlists
```bash
# SecLists (comprehensive)
git clone https://github.com/danielmiessler/SecLists.git

# Assetnote wordlists
git clone https://github.com/assetnote/commonspeak2-wordlists.git

# jhaddix all.txt
wget https://gist.githubusercontent.com/jhaddix/86a06c5dc309d08580a018c66354a056/raw/all.txt
```

---

## 🎓 Training Resources

### Practice Targets
- [HackTheBox](https://www.hackthebox.com/)
- [PortSwigger Web Security Academy](https://portswigger.net/web-security)
- [TryHackMe](https://tryhackme.com/)
- [PentesterLab](https://pentesterlab.com/)

### Bug Bounty Platforms
- [HackerOne](https://www.hackerone.com/)
- [Bugcrowd](https://www.bugcrowd.com/)
- [Intigriti](https://www.intigriti.com/)
- [YesWeHack](https://www.yeswehack.com/)

---

## 🔗 Useful Integrations

### With Other Tools

#### Burp Suite
```bash
# Export URLs for Burp
cat results/*/urls/urls_clean.txt > burp_targets.txt
# Import into Burp Suite
```

#### OWASP ZAP
```bash
# Generate ZAP context
python3 generate_zap_context.py results/*/http/alive.txt
```

#### Metasploit
```bash
# Generate hosts file for MSF
awk '{print $1}' results/*/dns/a_records.txt > msf_targets.txt
```

---

## ⚡ Performance Tuning

### Faster Scans
```bash
# Skip time-consuming steps
python3 webenum_enhanced.py -d target.com \
    --skip-portscan \
    --skip-screenshots \
    --skip-fuzzing \
    --skip-vuln-scan
```

### Resource Limits
```bash
# Limit memory (Linux)
ulimit -m 4000000  # 4GB

# Limit processes
ulimit -u 200
```

---

## 📱 Mobile Testing

### Mobile Subdomains
```bash
# Look for mobile-specific
grep -E '(m\.|mobile\.|api\.|app\.)' results/*/subdomains/all_subdomains.txt
```

---

## 🎯 Takeaways

**Remember:**
1. Always get permission before scanning
2. Start passive, then go active
3. Use API keys for better results
4. Review diff output regularly
5. Automate repetitive tasks
6. Combine tools for best results
7. Manual verification is crucial
8. Document your findings

---

**Happy Hunting! 🎯**

For detailed documentation, see: `ENHANCED_FEATURES.md`
