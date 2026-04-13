#!/usr/bin/env python3
"""
GivEnum Results Analyzer
Analyze and generate reports from scan results
"""

import os
import sys
import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
import re

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class ResultsAnalyzer:
    """Analyze scan results"""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)

        if not self.results_dir.exists():
            print(f"{Colors.FAIL}[-] Directory not found: {results_dir}{Colors.ENDC}")
            sys.exit(1)

        self.load_data()

    def load_data(self):
        """Load all data"""
        print(f"{Colors.OKBLUE}[*] Loading data from {self.results_dir}{Colors.ENDC}")

        # Subdomains
        self.subdomains = self._load_txt('subdomains/all_subdomains.txt')
        self.bruteforce_subs = self._load_txt('subdomains/bruteforce.txt')

        # Resolved
        self.resolved = self._load_txt('dns/resolved.txt')

        # Active
        self.alive = self._load_txt('http/alive.txt')

        # HTTPx data
        self.http_data = self._load_httpx_json('http/httpx_full.json')

        # URLs
        self.urls = self._load_txt('urls/urls_clean.txt')

        # JS files
        self.js_files = self._load_txt('js/all_js_files.txt')

        # Active scan findings
        self.open_ports = self._load_txt('ports/open_ports.txt')
        self.nuclei_results = self._load_txt('vulnerabilities/nuclei_results.txt')
        self.dalfox_results = self._load_txt('vulnerabilities/dalfox_results.txt')
        self.subjack_results = self._load_txt('takeover/subjack_results.txt')
        self.parameters = self._load_txt('parameters/interesting_parameters.txt')

    def _load_txt(self, relative_path: str) -> set:
        """Load text file"""
        file_path = self.results_dir / relative_path

        if not file_path.exists():
            return set()

        with open(file_path, 'r') as f:
            return set(line.strip() for line in f if line.strip())

    def _load_httpx_json(self, relative_path: str) -> list:
        """Load httpx JSON"""
        file_path = self.results_dir / relative_path

        if not file_path.exists():
            return []

        data = []
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except:
                    continue

        return data

    def print_summary(self):
        """Print summary"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'SUMMARY'.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

        # Passive findings
        passive_stats = [
            ("Subdomains found", len(self.subdomains)),
            ("Resolved", len(self.resolved)),
            ("Active HTTP", len(self.alive)),
            ("URLs collected", len(self.urls)),
            ("JS files", len(self.js_files)),
            ("Interesting parameters", len(self.parameters)),
        ]

        print(f"{Colors.OKBLUE}[*] Passive{Colors.ENDC}")
        for name, count in passive_stats:
            print(f"    {name:.<43} {Colors.OKBLUE}{count}{Colors.ENDC}")

        # Active findings (only show if data exists)
        active_stats = [
            ("Brute-forced subdomains", len(self.bruteforce_subs)),
            ("Hosts with open ports", len(self.open_ports)),
            ("Nuclei findings", len(self.nuclei_results)),
            ("Dalfox XSS findings", len(self.dalfox_results)),
            ("Takeover candidates (subjack)", len(self.subjack_results)),
        ]

        active_data = [(n, c) for n, c in active_stats if c > 0]
        if active_data:
            print(f"\n{Colors.WARNING}[!] Active (--active mode){Colors.ENDC}")
            for name, count in active_data:
                color = Colors.FAIL if count > 0 else Colors.OKBLUE
                print(f"    {name:.<43} {color}{count}{Colors.ENDC}")
        else:
            print(f"\n{Colors.WARNING}[!] No active scan data (run with --active){Colors.ENDC}")

    def analyze_technologies(self):
        """Analyze technologies"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'TECHNOLOGIES'}{Colors.ENDC}\n")

        if not self.http_data:
            print(f"{Colors.WARNING}[!] No data{Colors.ENDC}")
            return

        tech_counter = Counter()

        for entry in self.http_data:
            techs = entry.get('tech', [])
            for tech in techs:
                tech_counter[tech] += 1

        if not tech_counter:
            print(f"{Colors.WARNING}[!] No technologies detected{Colors.ENDC}")
            return

        # Top 15
        for tech, count in tech_counter.most_common(15):
            bar = '█' * min(count, 50)
            print(f"  {Colors.OKCYAN}{tech:.<40}{Colors.ENDC} {bar} {count}")

    def analyze_status_codes(self):
        """Analyze status codes"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'STATUS CODES'}{Colors.ENDC}\n")

        if not self.http_data:
            print(f"{Colors.WARNING}[!] No data{Colors.ENDC}")
            return

        status_counter = Counter()

        for entry in self.http_data:
            status = entry.get('status_code', 0)
            status_counter[status] += 1

        for status, count in sorted(status_counter.items()):
            if 200 <= status < 300:
                color = Colors.OKGREEN
            elif status >= 400:
                color = Colors.WARNING
            else:
                color = Colors.OKBLUE
            
            print(f"  {color}{status}{Colors.ENDC} {'█' * min(count, 40)} {count}")

    def find_interesting_hosts(self):
        """Find interesting hosts"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'INTERESTING HOSTS'}{Colors.ENDC}\n")

        if not self.http_data:
            print(f"{Colors.WARNING}[!] No data{Colors.ENDC}")
            return

        interesting = defaultdict(list)

        for entry in self.http_data:
            url = entry.get('url', '')
            title = entry.get('title', '')
            status = entry.get('status_code', 0)
            techs = entry.get('tech', [])

            # Admin/login
            if any(keyword in title.lower() for keyword in ['admin', 'login', 'dashboard', 'panel']):
                interesting['Admin/Login'].append((url, title, status))

            # Errors
            if status in [403, 401]:
                interesting['Forbidden/Unauthorized'].append((url, title, status))

            # Dev tools
            tech_names = ' '.join(techs).lower()
            if any(tech in tech_names for tech in ['jenkins', 'gitlab', 'jira', 'confluence']):
                interesting['Dev Tools'].append((url, ', '.join(techs), status))

            # APIs
            if 'api' in url.lower() or any('api' in t.lower() for t in techs):
                interesting['APIs'].append((url, ', '.join(techs), status))

        # Print
        for category, items in interesting.items():
            if items:
                print(f"{Colors.OKGREEN}[+] {category}:{Colors.ENDC}")
                for item in items[:10]:
                    url, info, status = item
                    print(f"    [{status}] {url}")
                    if info:
                        print(f"         → {info[:80]}")
                print()

    def analyze_urls(self):
        """Analyze URLs"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'URL ANALYSIS'}{Colors.ENDC}\n")

        if not self.urls:
            print(f"{Colors.WARNING}[!] No URLs{Colors.ENDC}")
            return

        # Extensions
        extensions = Counter()
        for url in self.urls:
            match = re.search(r'\.([a-z0-9]+)(?:\?|$)', url.lower())
            if match:
                extensions[match.group(1)] += 1

        print(f"{Colors.OKGREEN}[+] File extensions:{Colors.ENDC}")
        for ext, count in extensions.most_common(15):
            print(f"    .{ext:.<20} {count}")

        # Parameters
        print(f"\n{Colors.OKGREEN}[+] Interesting parameters:{Colors.ENDC}")
        interesting_params = ['id', 'user', 'admin', 'debug', 'file', 'path', 'url', 'redirect', 'page']
        param_urls = []

        for url in self.urls:
            if '?' in url:
                params = re.findall(r'[?&]([^=&]+)=', url)
                for param in params:
                    if param.lower() in interesting_params:
                        param_urls.append((param, url))
                        break

        param_counter = Counter(p[0] for p in param_urls)
        for param, count in param_counter.most_common(10):
            print(f"    {param:.<20} {count}")

        # Sample URLs
        if param_urls:
            print(f"\n{Colors.OKGREEN}[+] Sample URLs (first 5):{Colors.ENDC}")
            for param, url in param_urls[:5]:
                print(f"    [{param}] {url[:100]}")

    def analyze_active_findings(self):
        """Analyze and display findings from active scan tools"""
        has_data = any([self.nuclei_results, self.dalfox_results,
                        self.subjack_results, self.open_ports, self.bruteforce_subs])

        if not has_data:
            print(f"\n{Colors.WARNING}[!] No active scan data — run with --active to get nuclei/dalfox/subjack results{Colors.ENDC}")
            return

        print(f"\n{Colors.HEADER}{Colors.BOLD}{'ACTIVE SCAN FINDINGS'}{Colors.ENDC}\n")

        # Brute-forced subdomains
        if self.bruteforce_subs:
            print(f"{Colors.OKGREEN}[+] Brute-forced subdomains ({len(self.bruteforce_subs)}):{Colors.ENDC}")
            for sub in sorted(self.bruteforce_subs)[:15]:
                print(f"    {sub}")
            if len(self.bruteforce_subs) > 15:
                print(f"    ... and {len(self.bruteforce_subs) - 15} more")
            print()

        # Open ports
        if self.open_ports:
            print(f"{Colors.OKGREEN}[+] Open ports:{Colors.ENDC}")
            for entry in sorted(self.open_ports)[:20]:
                print(f"    {entry}")
            print()

        # Nuclei findings — grouped by severity
        if self.nuclei_results:
            severity_order = ['critical', 'high', 'medium', 'low', 'info']
            grouped = defaultdict(list)
            for finding in self.nuclei_results:
                sev = 'unknown'
                m = re.match(r'\[(critical|high|medium|low|info)\]', finding, re.IGNORECASE)
                if m:
                    sev = m.group(1).lower()
                grouped[sev].append(finding)

            print(f"{Colors.FAIL}[!] Nuclei findings ({len(self.nuclei_results)}):{Colors.ENDC}")
            for sev in severity_order:
                if grouped[sev]:
                    color = Colors.FAIL if sev in ('critical', 'high') else Colors.WARNING
                    print(f"  {color}[{sev.upper()}] {len(grouped[sev])} findings{Colors.ENDC}")
                    for f in grouped[sev][:5]:
                        print(f"    → {f[:100]}")
                    if len(grouped[sev]) > 5:
                        print(f"    ... and {len(grouped[sev]) - 5} more")
            print()

        # Dalfox XSS
        if self.dalfox_results:
            print(f"{Colors.FAIL}[!] Dalfox XSS findings ({len(self.dalfox_results)}):{Colors.ENDC}")
            for finding in list(self.dalfox_results)[:10]:
                print(f"    → {finding[:100]}")
            if len(self.dalfox_results) > 10:
                print(f"    ... and {len(self.dalfox_results) - 10} more")
            print()

        # Subjack takeover
        if self.subjack_results:
            print(f"{Colors.FAIL}[!] Subjack takeover candidates ({len(self.subjack_results)}):{Colors.ENDC}")
            for finding in self.subjack_results:
                print(f"    → {finding}")
            print()

    def find_vulnerabilities(self):
        """Find potential vulnerabilities"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'POTENTIAL VULNERABILITIES'}{Colors.ENDC}\n")

        findings = defaultdict(list)

        # Analyze URLs
        for url in self.urls:
            url_lower = url.lower()

            # LFI
            if any(p in url_lower for p in ['file=', 'path=', 'page=', 'include=']):
                findings['LFI/Path Traversal'].append(url)

            # Open redirect
            if any(p in url_lower for p in ['redirect=', 'url=', 'next=', 'return=']):
                findings['Open Redirect'].append(url)

            # SQLi
            if any(p in url_lower for p in ['id=', 'user=', 'product=', 'category=']):
                findings['SQL Injection'].append(url)

            # SSRF
            if any(p in url_lower for p in ['url=', 'uri=', 'host=', 'target=']):
                findings['SSRF'].append(url)

        # Check hosts
        for entry in self.http_data:
            url = entry.get('url', '')
            title = entry.get('title', '').lower()

            # Git
            if '.git' in url:
                findings['Exposed .git'].append(url)

            # Backups
            if any(ext in url for ext in ['.bak', '.old', '.backup', '~']):
                findings['Backup Files'].append(url)

            # Debug
            if any(keyword in title for keyword in ['debug', 'stacktrace', 'exception']):
                findings['Debug/Error'].append(url)

        # Print
        if not findings:
            print(f"{Colors.OKGREEN}[+] No obvious patterns{Colors.ENDC}")
            return

        for vuln_type, urls in findings.items():
            if urls:
                print(f"{Colors.WARNING}[!] {vuln_type}: {len(urls)}{Colors.ENDC}")
                for url in urls[:3]:
                    print(f"    → {url[:100]}")
                if len(urls) > 3:
                    print(f"    ... and {len(urls) - 3} more")
                print()

    def export_report(self, output_file: str):
        """Export report"""
        print(f"\n{Colors.OKBLUE}[*] Exporting to {output_file}{Colors.ENDC}")

        lines = []

        # Header
        lines.append(f"# GivEnum Analysis Report")
        lines.append(f"\n**Directory:** `{self.results_dir}`\n")

        # Summary
        lines.append("## Summary\n")
        lines.append(f"- **Subdomains:** {len(self.subdomains)}")
        if self.bruteforce_subs:
            lines.append(f"- **Brute-forced subdomains:** {len(self.bruteforce_subs)}")
        lines.append(f"- **Resolved:** {len(self.resolved)}")
        lines.append(f"- **Active HTTP:** {len(self.alive)}")
        lines.append(f"- **URLs:** {len(self.urls)}")
        lines.append(f"- **JS files:** {len(self.js_files)}")
        if self.open_ports:
            lines.append(f"- **Hosts with open ports:** {len(self.open_ports)}")
        if self.nuclei_results:
            lines.append(f"- **Nuclei findings:** {len(self.nuclei_results)}")
        if self.dalfox_results:
            lines.append(f"- **XSS findings (dalfox):** {len(self.dalfox_results)}")
        if self.subjack_results:
            lines.append(f"- **Takeover candidates (subjack):** {len(self.subjack_results)}")
        lines.append("")

        # Technologies
        lines.append("## Technologies\n")
        tech_counter = Counter()
        for entry in self.http_data:
            for tech in entry.get('tech', []):
                tech_counter[tech] += 1

        if tech_counter:
            lines.append("| Technology | Count |")
            lines.append("|------------|-------|")
            for tech, count in tech_counter.most_common(20):
                lines.append(f"| {tech} | {count} |")
        lines.append("")

        # Status codes
        lines.append("## Status Codes\n")
        status_counter = Counter()
        for entry in self.http_data:
            status_counter[entry.get('status_code', 0)] += 1

        if status_counter:
            lines.append("| Status | Count |")
            lines.append("|--------|-------|")
            for status, count in sorted(status_counter.items()):
                lines.append(f"| {status} | {count} |")
        lines.append("")

        # Open ports
        if self.open_ports:
            lines.append("## Open Ports\n")
            lines.append("| Host | Ports |")
            lines.append("|------|-------|")
            for entry in sorted(self.open_ports)[:50]:
                parts = entry.split(': ', 1)
                if len(parts) == 2:
                    lines.append(f"| {parts[0]} | {parts[1]} |")
                else:
                    lines.append(f"| {entry} | — |")
            lines.append("")

        # Nuclei findings
        if self.nuclei_results:
            lines.append("## Nuclei Findings\n")
            for finding in sorted(self.nuclei_results):
                lines.append(f"- {finding}")
            lines.append("")

        # Dalfox findings
        if self.dalfox_results:
            lines.append("## XSS Findings (dalfox)\n")
            for finding in self.dalfox_results:
                lines.append(f"- {finding}")
            lines.append("")

        # Subjack findings
        if self.subjack_results:
            lines.append("## Takeover Candidates (subjack)\n")
            for finding in self.subjack_results:
                lines.append(f"- {finding}")
            lines.append("")

        # Interesting parameters
        if self.parameters:
            lines.append("## Interesting Parameters\n")
            for param in sorted(self.parameters):
                lines.append(f"- {param}")
            lines.append("")

        # Save
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))

        print(f"{Colors.OKGREEN}[+] Report saved{Colors.ENDC}")


def main():
    parser = argparse.ArgumentParser(description='Analyze GivEnum results')

    parser.add_argument(
        'results_dir',
        help='Results directory (e.g., results/example.com_20250122_123456/)'
    )

    parser.add_argument(
        '--export',
        help='Export report to file'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Show summary only'
    )

    args = parser.parse_args()

    # Analyze
    analyzer = ResultsAnalyzer(args.results_dir)

    # Summary
    analyzer.print_summary()

    if not args.summary_only:
        analyzer.analyze_technologies()
        analyzer.analyze_status_codes()
        analyzer.find_interesting_hosts()
        analyzer.analyze_urls()
        analyzer.find_vulnerabilities()
        analyzer.analyze_active_findings()

    # Export
    if args.export:
        analyzer.export_report(args.export)

    print(f"\n{Colors.OKGREEN}[+] Analysis complete{Colors.ENDC}\n")


if __name__ == '__main__':
    main()
