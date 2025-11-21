#!/usr/bin/env python3
"""
WebEnum Results Analyzer
Analisa e gera relatórios dos resultados da enumeração
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
    """Analisa resultados da enumeração"""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)

        if not self.results_dir.exists():
            print(f"{Colors.FAIL}[-] Diretório não encontrado: {results_dir}{Colors.ENDC}")
            sys.exit(1)

        self.load_data()

    def load_data(self):
        """Carrega todos os dados"""
        print(f"{Colors.OKBLUE}[*] Carregando dados de {self.results_dir}{Colors.ENDC}")

        # Subdomínios
        self.subdomains = self._load_txt('subdomains/all_subdomains.txt')

        # Hosts resolvidos
        self.resolved = self._load_txt('dns/resolved.txt')

        # Hosts ativos
        self.alive = self._load_txt('http/alive.txt')

        # HTTPx JSON
        self.http_data = self._load_httpx_json('http/httpx_full.json')

        # URLs
        self.urls = self._load_txt('urls/urls_clean.txt')

        # JS files
        self.js_files = self._load_txt('js/js_files.txt')

    def _load_txt(self, relative_path: str) -> Set[str]:
        """Carrega arquivo de texto"""
        file_path = self.results_dir / relative_path

        if not file_path.exists():
            return set()

        with open(file_path, 'r') as f:
            return set(line.strip() for line in f if line.strip())

    def _load_httpx_json(self, relative_path: str) -> List[Dict]:
        """Carrega arquivo JSON do httpx"""
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
        """Imprime sumário geral"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'SUMÁRIO GERAL'.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

        stats = [
            ("Subdomínios encontrados", len(self.subdomains)),
            ("Subdomínios resolvidos", len(self.resolved)),
            ("Hosts com HTTP ativo", len(self.alive)),
            ("URLs coletadas", len(self.urls)),
            ("Arquivos JavaScript", len(self.js_files)),
        ]

        for name, count in stats:
            print(f"{Colors.OKGREEN}[+]{Colors.ENDC} {name:.<45} {Colors.OKBLUE}{count}{Colors.ENDC}")

    def analyze_technologies(self):
        """Analisa tecnologias detectadas"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'TECNOLOGIAS DETECTADAS'}{Colors.ENDC}\n")

        if not self.http_data:
            print(f"{Colors.WARNING}[!] Sem dados de tecnologia{Colors.ENDC}")
            return

        tech_counter = Counter()

        for entry in self.http_data:
            techs = entry.get('tech', [])
            for tech in techs:
                tech_counter[tech] += 1

        if not tech_counter:
            print(f"{Colors.WARNING}[!] Nenhuma tecnologia detectada{Colors.ENDC}")
            return

        # Top 15
        for tech, count in tech_counter.most_common(15):
            bar = '█' * min(count, 50)
            print(f"  {Colors.OKCYAN}{tech:.<40}{Colors.ENDC} {bar} {count}")

    def analyze_status_codes(self):
        """Analisa códigos de status HTTP"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'CÓDIGOS DE STATUS HTTP'}{Colors.ENDC}\n")

        if not self.http_data:
            print(f"{Colors.WARNING}[!] Sem dados HTTP{Colors.ENDC}")
            return

        status_counter = Counter()

        for entry in self.http_data:
            status = entry.get('status_code', 0)
            status_counter[status] += 1

        for status, count in sorted(status_counter.items()):
            color = Colors.OKGREEN if 200 <= status < 300 else Colors.WARNING if status >= 400 else Colors.OKBLUE
            print(f"  {color}{status}{Colors.ENDC} {'█' * min(count, 40)} {count}")

    def find_interesting_hosts(self):
        """Encontra hosts interessantes"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'HOSTS INTERESSANTES'}{Colors.ENDC}\n")

        if not self.http_data:
            print(f"{Colors.WARNING}[!] Sem dados HTTP{Colors.ENDC}")
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

            # Páginas de erro interessantes
            if status in [403, 401]:
                interesting['Forbidden/Unauthorized'].append((url, title, status))

            # Jenkins, GitLab, etc.
            tech_names = ' '.join(techs).lower()
            if any(tech in tech_names for tech in ['jenkins', 'gitlab', 'jira', 'confluence']):
                interesting['Dev Tools'].append((url, ', '.join(techs), status))

            # APIs
            if 'api' in url.lower() or any('api' in t.lower() for t in techs):
                interesting['APIs'].append((url, ', '.join(techs), status))

        # Imprime resultados
        for category, items in interesting.items():
            if items:
                print(f"{Colors.OKGREEN}[+] {category}:{Colors.ENDC}")
                for item in items[:10]:  # Limita a 10 por categoria
                    url, info, status = item
                    print(f"    [{status}] {url}")
                    if info:
                        print(f"         → {info[:80]}")
                print()

    def analyze_urls(self):
        """Analisa URLs coletadas"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'ANÁLISE DE URLs'}{Colors.ENDC}\n")

        if not self.urls:
            print(f"{Colors.WARNING}[!] Nenhuma URL coletada{Colors.ENDC}")
            return

        # Extensões
        extensions = Counter()
        for url in self.urls:
            match = re.search(r'\.([a-z0-9]+)(?:\?|$)', url.lower())
            if match:
                extensions[match.group(1)] += 1

        print(f"{Colors.OKGREEN}[+] Extensões de arquivo encontradas:{Colors.ENDC}")
        for ext, count in extensions.most_common(15):
            print(f"    .{ext:.<20} {count}")

        # Parâmetros interessantes
        print(f"\n{Colors.OKGREEN}[+] Parâmetros interessantes:{Colors.ENDC}")
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

        # Exemplos de URLs com params interessantes
        if param_urls:
            print(f"\n{Colors.OKGREEN}[+] Exemplos de URLs (primeiras 5):{Colors.ENDC}")
            for param, url in param_urls[:5]:
                print(f"    [{param}] {url[:100]}")

    def find_potential_vulnerabilities(self):
        """Busca padrões que podem indicar vulnerabilidades"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'POTENCIAIS ÁREAS DE INTERESSE'}{Colors.ENDC}\n")

        findings = defaultdict(list)

        # Analisa URLs
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

        # Analisa hosts
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

        # Imprime findings
        if not findings:
            print(f"{Colors.OKGREEN}[+] Nenhum padrão óbvio detectado{Colors.ENDC}")
            return

        for vuln_type, urls in findings.items():
            if urls:
                print(f"{Colors.WARNING}[!] {vuln_type}: {len(urls)} potencial(is){Colors.ENDC}")
                for url in urls[:3]:  # Mostra apenas 3 exemplos
                    print(f"    → {url[:100]}")
                if len(urls) > 3:
                    print(f"    ... e mais {len(urls) - 3}")
                print()

    def export_report(self, output_file: str):
        """Exporta relatório em markdown"""
        print(f"\n{Colors.OKBLUE}[*] Exportando relatório para {output_file}{Colors.ENDC}")

        report_lines = []

        # Header
        report_lines.append(f"# WebEnum Analysis Report")
        report_lines.append(f"\n**Diretório:** `{self.results_dir}`\n")

        # Summary
        report_lines.append("## Sumário Geral\n")
        report_lines.append(f"- **Subdomínios encontrados:** {len(self.subdomains)}")
        report_lines.append(f"- **Subdomínios resolvidos:** {len(self.resolved)}")
        report_lines.append(f"- **Hosts com HTTP ativo:** {len(self.alive)}")
        report_lines.append(f"- **URLs coletadas:** {len(self.urls)}")
        report_lines.append(f"- **Arquivos JavaScript:** {len(self.js_files)}\n")

        # Technologies
        report_lines.append("## Tecnologias Detectadas\n")
        tech_counter = Counter()
        for entry in self.http_data:
            for tech in entry.get('tech', []):
                tech_counter[tech] += 1

        if tech_counter:
            report_lines.append("| Tecnologia | Quantidade |")
            report_lines.append("|------------|-----------|")
            for tech, count in tech_counter.most_common(20):
                report_lines.append(f"| {tech} | {count} |")
        report_lines.append("")

        # Status Codes
        report_lines.append("## Códigos de Status\n")
        status_counter = Counter()
        for entry in self.http_data:
            status_counter[entry.get('status_code', 0)] += 1

        if status_counter:
            report_lines.append("| Status | Quantidade |")
            report_lines.append("|--------|-----------|")
            for status, count in sorted(status_counter.items()):
                report_lines.append(f"| {status} | {count} |")
        report_lines.append("")

        # Save
        with open(output_file, 'w') as f:
            f.write('\n'.join(report_lines))

        print(f"{Colors.OKGREEN}[+] Relatório salvo!{Colors.ENDC}")


def main():
    parser = argparse.ArgumentParser(
        description='Analisa resultados do WebEnum',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'results_dir',
        help='Diretório com os resultados (ex: results/example.com_20250121_123456/)'
    )

    parser.add_argument(
        '--export',
        help='Exportar relatório para arquivo markdown'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Mostrar apenas sumário'
    )

    args = parser.parse_args()

    # Analisa
    analyzer = ResultsAnalyzer(args.results_dir)

    # Sumário sempre
    analyzer.print_summary()

    if not args.summary_only:
        analyzer.analyze_technologies()
        analyzer.analyze_status_codes()
        analyzer.find_interesting_hosts()
        analyzer.analyze_urls()
        analyzer.find_potential_vulnerabilities()

    # Exporta se solicitado
    if args.export:
        analyzer.export_report(args.export)

    print(f"\n{Colors.OKGREEN}[+] Análise concluída!{Colors.ENDC}\n")


if __name__ == '__main__':
    main()
