#!/usr/bin/env python3
"""
WebEnum Results Analyzer
Analyzes and generates reports from enumeration results
"""

import os
import sys
import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Set
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
    """Analyzes enumeration results"""

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

        # Resolved hosts
        self.resolved = self._load_txt('dns/resolved.txt')

        # Active hosts
        self.alive = self._load_txt('http/alive.txt')

        # HTTPx JSON
        self.http_data = self._load_httpx_json('http/httpx_full.json')

        # URLs
        self.urls = self._load_txt('urls/urls_clean.txt')

        # JS files
        self.js_files = self._load_txt('js/js_files.txt')

    def _load_txt(self, relative_path: str) -> Set[str]:
        """Load text file"""
        file_path = self.results_dir / relative_path

        if not file_path.exists():
            return set()

        with open(file_path, 'r') as f:
            return set(line.strip() for line in f if line.strip())

    def _load_httpx_json(self, relative_path: str) -> List[Dict]:
        """Load httpx JSON file"""
        file_path = self.results_dir / relative_path

        if not file_path.exists():
            return []

        data = []
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return data

    def print_summary(self):
        """Print general summary"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'GENERAL SUMMARY'.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

        stats = [
            ("Subdomains found", len(self.subdomains)),
            ("Resolved subdomains", len(self.resolved)),
            ("Active HTTP hosts", len(self.alive)),
            ("Collected URLs", len(self.urls)),
            ("JavaScript files", len(self.js_files)),
        ]

        for name, count in stats:
            print(f"{Colors.OKGREEN}[+]{Colors.ENDC} {name:.<45} {Colors.OKBLUE}{count}{Colors.ENDC}")

    def analyze_technologies(self):
        """Analyze detected technologies"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'DETECTED TECHNOLOGIES'}{Colors.ENDC}\n")

        if not self.http_data:
            print(f"{Colors.WARNING}[!] No technology data{Colors.ENDC}")
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
        """Analyze HTTP status codes"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'HTTP STATUS CODES'}{Colors.ENDC}\n")

        if not self.http_data:
            print(f"{Colors.WARNING}[!] No HTTP data{Colors.ENDC}")
            return

        status_counter = Counter()

        for entry in self.http_data:
            status = entry.get('status_code', 0)
            status_counter[status] += 1

        for status, count in sorted(status_counter.items()):
            color = Colors.OKGREEN if 200 <= status < 300 else Colors.WARNING if status >= 400 else Colors.OKBLUE
            print(f"  {color}{status}{Colors.ENDC} {'█' * min(count, 40)} {count}")

    def find_interesting_hosts(self):
        """Find interesting hosts"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'INTERESTING HOSTS'}{Colors.ENDC}\n")

        if not self.http_data:
            print(f"{Colors.WARNING}[!] No HTTP data{Colors.ENDC}")
            return

        interesting = defaultdict(list)

        for entry in self.http_data:
            url = entry.get('url', '')
            title = entry.get('title', '')
            status = entry.get('status_code', 0)
            techs = entry.get('tech', [])

            # Admin/login pages
            if any(keyword in title.lower() for keyword in ['admin', 'login', 'dashboard', 'panel']):
                interesting['Admin/Login Pages'].append((url, title, status))

            # Interesting error pages
            if status in [403, 401]:
                interesting['Forbidden/Unauthorized'].append((url, title, status))

            # Jenkins, GitLab, etc.
            tech_names = ' '.join(techs).lower()
            if any(tech in tech_names for tech in ['jenkins', 'gitlab', 'jira', 'confluence']):
                interesting['Dev Tools'].append((url, ', '.join(techs), status))

            # APIs
            if 'api' in url.lower() or any('api' in t.lower() for t in techs):
                interesting['APIs'].append((url, ', '.join(techs), status))

        # Print results
        for category, items in interesting.items():
            if items:
                print(f"{Colors.OKGREEN}[+] {category}:{Colors.ENDC}")
                for item in items[:10]:  # Limit to 10 per category
                    url, info, status = item
                    print(f"    [{status}] {url}")
                    if info:
                        print(f"         → {info[:80]}")
                print()

    def analyze_urls(self):
        """Analyze collected URLs"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'URL ANALYSIS'}{Colors.ENDC}\n")

        if not self.urls:
            print(f"{Colors.WARNING}[!] No URLs collected{Colors.ENDC}")
            return

        # Extensions
        extensions = Counter()
        for url in self.urls:
            match = re.search(r'\.([a-z0-9]+)(?:\?|$)', url.lower())
            if match:
                extensions[match.group(1)] += 1

        print(f"{Colors.OKGREEN}[+] File extensions found:{Colors.ENDC}")
        for ext, count in extensions.most_common(15):
            print(f"    .{ext:.<20} {count}")

        # Interesting parameters
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

        # Sample URLs with interesting params
        if param_urls:
            print(f"\n{Colors.OKGREEN}[+] Sample URLs (first 5):{Colors.ENDC}")
            for param, url in param_urls[:5]:
                print(f"    [{param}] {url[:100]}")

    def find_potential_vulnerabilities(self):
        """Search for patterns that may indicate vulnerabilities"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'POTENTIAL AREAS OF INTEREST'}{Colors.ENDC}\n")

        findings = defaultdict(list)

        # Analyze URLs
        for url in self.urls:
            url_lower = url.lower()

            # LFI/Path traversal
            if any(pattern in url_lower for pattern in ['file=', 'path=', 'page=', 'include=']):
                findings['LFI/Path Traversal'].append(url)

            # Open redirect
            if any(pattern in url_lower for pattern in ['redirect=', 'url=', 'next=', 'return=']):
                findings['Open Redirect'].append(url)

            # SQLi
            if any(pattern in url_lower for pattern in ['id=', 'user=', 'product=', 'category=']):
                findings['SQL Injection (GET params)'].append(url)

            # SSRF
            if any(pattern in url_lower for pattern in ['url=', 'uri=', 'host=', 'target=']):
                findings['SSRF'].append(url)

        # Analyze hosts
        for entry in self.http_data:
            url = entry.get('url', '')
            title = entry.get('title', '').lower()

            # Git exposed
            if '.git' in url:
                findings['Exposed .git'].append(url)

            # Backup files
            if any(ext in url for ext in ['.bak', '.old', '.backup', '~']):
                findings['Backup Files'].append(url)

            # Debug mode
            if any(keyword in title for keyword in ['debug', 'stacktrace', 'exception']):
                findings['Debug/Error Pages'].append(url)

        # Print findings
        if not findings:
            print(f"{Colors.OKGREEN}[+] No obvious patterns detected{Colors.ENDC}")
            return

        for vuln_type, urls in findings.items():
            if urls:
                print(f"{Colors.WARNING}[!] {vuln_type}: {len(urls)} potential{Colors.ENDC}")
                for url in urls[:3]:  # Show only 3 examples
                    print(f"    → {url[:100]}")
                if len(urls) > 3:
                    print(f"    ... and {len(urls) - 3} more")
                print()

    def export_report(self, output_file: str):
        """Export report to markdown"""
        print(f"\n{Colors.OKBLUE}[*] Exporting report to {output_file}{Colors.ENDC}")

        report_lines = []

        # Header
        report_lines.append(f"# WebEnum Analysis Report")
        report_lines.append(f"\n**Directory:** `{self.results_dir}`\n")

        # Summary
        report_lines.append("## General Summary\n")
        report_lines.append(f"- **Subdomains found:** {len(self.subdomains)}")
        report_lines.append(f"- **Resolved subdomains:** {len(self.resolved)}")
        report_lines.append(f"- **Active HTTP hosts:** {len(self.alive)}")
        report_lines.append(f"- **Collected URLs:** {len(self.urls)}")
        report_lines.append(f"- **JavaScript files:** {len(self.js_files)}\n")

        # Technologies
        report_lines.append("## Detected Technologies\n")
        tech_counter = Counter()
        for entry in self.http_data:
            for tech in entry.get('tech', []):
                tech_counter[tech] += 1

        if tech_counter:
            report_lines.append("| Technology | Count |")
            report_lines.append("|------------|-------|")
            for tech, count in tech_counter.most_common(20):
                report_lines.append(f"| {tech} | {count} |")
        report_lines.append("")

        # Status Codes
        report_lines.append("## Status Codes\n")
        status_counter = Counter()
        for entry in self.http_data:
            status_counter[entry.get('status_code', 0)] += 1

        if status_counter:
            report_lines.append("| Status | Count |")
            report_lines.append("|--------|-------|")
            for status, count in sorted(status_counter.items()):
                report_lines.append(f"| {status} | {count} |")
        report_lines.append("")

        # Save
        with open(output_file, 'w') as f:
            f.write('\n'.join(report_lines))

        print(f"{Colors.OKGREEN}[+] Report saved!{Colors.ENDC}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze WebEnum results',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'results_dir',
        help='Directory with results (e.g.: results/example.com_20250121_123456/)'
    )

    parser.add_argument(
        '--export',
        help='Export report to markdown file'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Show summary only'
    )

    args = parser.parse_args()

    # Analyze
    analyzer = ResultsAnalyzer(args.results_dir)

    # Summary always shown
    analyzer.print_summary()

    if not args.summary_only:
        analyzer.analyze_technologies()
        analyzer.analyze_status_codes()
        analyzer.find_interesting_hosts()
        analyzer.analyze_urls()
        analyzer.find_potential_vulnerabilities()

    # Export if requested
    if args.export:
        analyzer.export_report(args.export)

    print(f"\n{Colors.OKGREEN}[+] Analysis complete!{Colors.ENDC}\n")


if __name__ == '__main__':
    main()
