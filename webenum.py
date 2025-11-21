#!/usr/bin/env python3
"""
WebEnum - Comprehensive Web Enumeration Tool
Automatiza enumeração completa de alvos web usando múltiplas ferramentas
"""

import os
import sys
import json
import subprocess
import argparse
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

# Cores para output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Logger:
    """Sistema de logging customizado com cores"""

    @staticmethod
    def info(msg: str):
        print(f"{Colors.OKBLUE}[*]{Colors.ENDC} {msg}")

    @staticmethod
    def success(msg: str):
        print(f"{Colors.OKGREEN}[+]{Colors.ENDC} {msg}")

    @staticmethod
    def warning(msg: str):
        print(f"{Colors.WARNING}[!]{Colors.ENDC} {msg}")

    @staticmethod
    def error(msg: str):
        print(f"{Colors.FAIL}[-]{Colors.ENDC} {msg}")

    @staticmethod
    def header(msg: str):
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{msg.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


class ToolChecker:
    """Verifica se as ferramentas necessárias estão instaladas"""

    REQUIRED_TOOLS = {
        'subdomain': ['subfinder', 'assetfinder', 'findomain'],
        'dns': ['dnsx', 'puredns'],
        'http': ['httpx'],
        'url_collect': ['gau', 'waybackurls', 'hakrawler', 'getJS'],
        'utils': ['anew', 'uro'],
        'optional': ['amass', 'gowitness', 'subzy', 'subjack', 'kxss']
    }

    @staticmethod
    def check_tool(tool: str) -> bool:
        """Verifica se uma ferramenta está instalada"""
        return shutil.which(tool) is not None

    @classmethod
    def check_all(cls, check_optional: bool = False) -> Dict[str, List[str]]:
        """Verifica todas as ferramentas e retorna o status"""
        missing = []
        available = []

        for category, tools in cls.REQUIRED_TOOLS.items():
            if category == 'optional' and not check_optional:
                continue

            for tool in tools:
                if cls.check_tool(tool):
                    available.append(tool)
                else:
                    missing.append(tool)

        return {'available': available, 'missing': missing}


class OutputManager:
    """Gerencia diretórios e arquivos de output"""

    def __init__(self, base_dir: str, domain: str):
        self.domain = domain
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = Path(base_dir) / f"{domain}_{self.timestamp}"

        # Estrutura de diretórios
        self.dirs = {
            'root': self.base_dir,
            'subdomains': self.base_dir / 'subdomains',
            'dns': self.base_dir / 'dns',
            'http': self.base_dir / 'http',
            'urls': self.base_dir / 'urls',
            'js': self.base_dir / 'js',
            'screenshots': self.base_dir / 'screenshots',
            'takeover': self.base_dir / 'takeover',
            'logs': self.base_dir / 'logs',
        }

        self._create_structure()

    def _create_structure(self):
        """Cria a estrutura de diretórios"""
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        Logger.success(f"Estrutura criada em: {self.base_dir}")

    def get_path(self, category: str, filename: str) -> Path:
        """Retorna o caminho completo para um arquivo"""
        return self.dirs[category] / filename

    def dedupe_file(self, input_file: Path, output_file: Path):
        """Remove duplicatas de um arquivo"""
        if not input_file.exists():
            return

        try:
            lines = set()
            with open(input_file, 'r') as f:
                lines = set(line.strip() for line in f if line.strip())

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(lines)) + '\n')

            Logger.success(f"Dedupe: {len(lines)} linhas únicas salvas em {output_file.name}")
        except Exception as e:
            Logger.error(f"Erro no dedupe: {e}")


class SubdomainEnum:
    """Enumeração de subdomínios"""

    def __init__(self, domain: str, output_mgr: OutputManager):
        self.domain = domain
        self.output_mgr = output_mgr
        self.tools = {
            'subfinder': ['subfinder', '-d', domain, '-all', '-silent'],
            'assetfinder': ['assetfinder', '--subs-only', domain],
            'findomain': ['findomain', '-t', domain, '-q'],
        }

    def run_tool(self, tool_name: str, command: List[str]) -> Set[str]:
        """Executa uma ferramenta e retorna resultados"""
        if not ToolChecker.check_tool(tool_name):
            Logger.warning(f"{tool_name} não encontrado, pulando...")
            return set()

        Logger.info(f"Executando {tool_name}...")
        output_file = self.output_mgr.get_path('subdomains', f'{tool_name}.txt')

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300
            )

            subs = set(line.strip() for line in result.stdout.split('\n') if line.strip())

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(subs)) + '\n')

            Logger.success(f"{tool_name}: {len(subs)} subdomínios encontrados")
            return subs

        except subprocess.TimeoutExpired:
            Logger.warning(f"{tool_name} timeout")
        except Exception as e:
            Logger.error(f"Erro ao executar {tool_name}: {e}")

        return set()

    def run_all(self) -> Path:
        """Executa todas as ferramentas de enumeração"""
        Logger.header("ENUMERAÇÃO DE SUBDOMÍNIOS")

        all_subs = set()

        # Executa ferramentas em paralelo
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.run_tool, name, cmd): name
                for name, cmd in self.tools.items()
            }

            for future in as_completed(futures):
                subs = future.result()
                all_subs.update(subs)

        # Adiciona domínio principal
        all_subs.add(self.domain)

        # Salva resultado consolidado
        output_file = self.output_mgr.get_path('subdomains', 'all_subdomains.txt')
        with open(output_file, 'w') as f:
            f.write('\n'.join(sorted(all_subs)) + '\n')

        Logger.success(f"Total: {len(all_subs)} subdomínios únicos")
        return output_file


class DNSResolver:
    """Resolução e validação DNS"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def resolve_with_puredns(self, input_file: Path) -> Optional[Path]:
        """Resolve subdomínios usando puredns"""
        if not ToolChecker.check_tool('puredns'):
            Logger.warning("puredns não encontrado, pulando resolução...")
            return input_file

        Logger.header("RESOLUÇÃO DNS")
        Logger.info("Resolvendo subdomínios com puredns...")

        output_file = self.output_mgr.get_path('dns', 'resolved.txt')

        try:
            subprocess.run(
                ['puredns', 'resolve', str(input_file), '-w', str(output_file)],
                timeout=600,
                check=True
            )

            # Conta linhas
            with open(output_file, 'r') as f:
                count = sum(1 for _ in f)

            Logger.success(f"Resolvidos: {count} subdomínios")
            return output_file

        except subprocess.TimeoutExpired:
            Logger.warning("puredns timeout, usando lista original")
            return input_file
        except Exception as e:
            Logger.error(f"Erro no puredns: {e}")
            return input_file

    def enrich_with_dnsx(self, input_file: Path) -> Optional[Path]:
        """Enriquece dados DNS com dnsx"""
        if not ToolChecker.check_tool('dnsx'):
            Logger.warning("dnsx não encontrado, pulando...")
            return input_file

        Logger.info("Enriquecendo dados DNS com dnsx...")

        output_file = self.output_mgr.get_path('dns', 'dnsx_full.json')

        try:
            subprocess.run(
                [
                    'dnsx', '-l', str(input_file),
                    '-resp', '-a', '-aaaa', '-cname',
                    '-json', '-o', str(output_file)
                ],
                timeout=300,
                check=True
            )

            Logger.success(f"Dados DNS salvos em {output_file.name}")
            return input_file

        except Exception as e:
            Logger.error(f"Erro no dnsx: {e}")
            return input_file


class HTTPProber:
    """HTTP probing e fingerprinting"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def probe_with_httpx(self, input_file: Path) -> Optional[Path]:
        """Faz HTTP probing com httpx"""
        if not ToolChecker.check_tool('httpx'):
            Logger.error("httpx é obrigatório! Instale: go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest")
            return None

        Logger.header("HTTP PROBING")
        Logger.info("Verificando hosts ativos com httpx...")

        json_output = self.output_mgr.get_path('http', 'httpx_full.json')
        alive_output = self.output_mgr.get_path('http', 'alive.txt')

        try:
            # Executa httpx
            subprocess.run(
                [
                    'httpx', '-l', str(input_file),
                    '-ports', '80,443,8080,8443,8000,8888,9000',
                    '-title', '-tech-detect', '-status-code',
                    '-follow-redirects', '-random-agent',
                    '-json', '-o', str(json_output)
                ],
                timeout=900,
                check=True
            )

            # Extrai apenas URLs vivas
            alive_urls = []
            try:
                with open(json_output, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            if 'url' in data:
                                alive_urls.append(data['url'])
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                Logger.warning(f"Erro ao processar JSON: {e}")

            with open(alive_output, 'w') as f:
                f.write('\n'.join(alive_urls) + '\n')

            Logger.success(f"Hosts ativos: {len(alive_urls)}")
            return alive_output

        except subprocess.TimeoutExpired:
            Logger.warning("httpx timeout")
        except Exception as e:
            Logger.error(f"Erro no httpx: {e}")

        return None

    def screenshot_with_gowitness(self, input_file: Path):
        """Tira screenshots com gowitness"""
        if not ToolChecker.check_tool('gowitness'):
            Logger.warning("gowitness não encontrado, pulando screenshots...")
            return

        Logger.info("Tirando screenshots com gowitness...")

        screenshot_dir = self.output_mgr.dirs['screenshots']

        try:
            subprocess.run(
                ['gowitness', 'file', '-f', str(input_file), '-P', str(screenshot_dir)],
                timeout=600
            )
            Logger.success(f"Screenshots salvos em {screenshot_dir}")
        except Exception as e:
            Logger.warning(f"Erro no gowitness: {e}")


class URLCollector:
    """Coleta de URLs de múltiplas fontes"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def collect_from_archives(self, hosts_file: Path) -> Set[str]:
        """Coleta URLs de arquivos históricos"""
        Logger.header("COLETA DE URLs")

        all_urls = set()

        # GAU
        if ToolChecker.check_tool('gau'):
            Logger.info("Coletando URLs com gau...")
            try:
                result = subprocess.run(
                    ['gau', '--subs', '--threads', '5'],
                    stdin=open(hosts_file, 'r'),
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)
                Logger.success(f"gau: {len(urls)} URLs")
            except Exception as e:
                Logger.warning(f"Erro no gau: {e}")

        # Waybackurls
        if ToolChecker.check_tool('waybackurls'):
            Logger.info("Coletando URLs com waybackurls...")
            try:
                result = subprocess.run(
                    ['waybackurls'],
                    stdin=open(hosts_file, 'r'),
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)
                Logger.success(f"waybackurls: {len(urls)} URLs")
            except Exception as e:
                Logger.warning(f"Erro no waybackurls: {e}")

        # Salva raw
        raw_file = self.output_mgr.get_path('urls', 'urls_raw.txt')
        with open(raw_file, 'w') as f:
            f.write('\n'.join(all_urls) + '\n')

        return all_urls

    def crawl_live(self, hosts_file: Path) -> Set[str]:
        """Crawl sites ativos"""
        all_urls = set()

        # Hakrawler
        if ToolChecker.check_tool('hakrawler'):
            Logger.info("Crawling com hakrawler...")
            try:
                result = subprocess.run(
                    ['hakrawler', '-plain', '-depth', '2'],
                    stdin=open(hosts_file, 'r'),
                    capture_output=True,
                    text=True,
                    timeout=900
                )
                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)
                Logger.success(f"hakrawler: {len(urls)} URLs")
            except Exception as e:
                Logger.warning(f"Erro no hakrawler: {e}")

        return all_urls

    def collect_js_files(self, hosts_file: Path) -> Path:
        """Coleta arquivos JavaScript"""
        if not ToolChecker.check_tool('getJS'):
            Logger.warning("getJS não encontrado, pulando coleta de JS...")
            return None

        Logger.info("Coletando arquivos JS com getJS...")

        js_file = self.output_mgr.get_path('js', 'js_files.txt')

        try:
            result = subprocess.run(
                ['getJS', '--input', str(hosts_file), '--complete'],
                capture_output=True,
                text=True,
                timeout=600
            )

            js_urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())

            with open(js_file, 'w') as f:
                f.write('\n'.join(js_urls) + '\n')

            Logger.success(f"Arquivos JS: {len(js_urls)}")
            return js_file

        except Exception as e:
            Logger.warning(f"Erro no getJS: {e}")
            return None

    def extract_from_js(self, js_file: Path) -> Set[str]:
        """Extrai endpoints de arquivos JS"""
        if not js_file or not ToolChecker.check_tool('subjs'):
            return set()

        Logger.info("Extraindo endpoints de arquivos JS...")

        try:
            result = subprocess.run(
                ['subjs'],
                stdin=open(js_file, 'r'),
                capture_output=True,
                text=True,
                timeout=600
            )

            urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
            Logger.success(f"Endpoints extraídos do JS: {len(urls)}")
            return urls

        except Exception as e:
            Logger.warning(f"Erro no subjs: {e}")
            return set()

    def clean_urls(self, urls: Set[str]) -> Path:
        """Limpa e normaliza URLs"""
        if not ToolChecker.check_tool('uro'):
            Logger.warning("uro não encontrado, salvando URLs sem limpeza...")
            clean_file = self.output_mgr.get_path('urls', 'urls_clean.txt')
            with open(clean_file, 'w') as f:
                f.write('\n'.join(sorted(urls)) + '\n')
            return clean_file

        Logger.info("Limpando URLs com uro...")

        # Salva temporário
        temp_file = self.output_mgr.get_path('urls', 'temp_urls.txt')
        with open(temp_file, 'w') as f:
            f.write('\n'.join(urls) + '\n')

        clean_file = self.output_mgr.get_path('urls', 'urls_clean.txt')

        try:
            result = subprocess.run(
                ['uro'],
                stdin=open(temp_file, 'r'),
                capture_output=True,
                text=True,
                timeout=300
            )

            with open(clean_file, 'w') as f:
                f.write(result.stdout)

            # Remove temp
            temp_file.unlink()

            with open(clean_file, 'r') as f:
                count = sum(1 for _ in f)

            Logger.success(f"URLs limpas: {count}")
            return clean_file

        except Exception as e:
            Logger.error(f"Erro no uro: {e}")
            temp_file.rename(clean_file)
            return clean_file


class TakeoverChecker:
    """Verifica subdomain takeover"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def check_with_subzy(self, subdomains_file: Path):
        """Verifica takeover com subzy"""
        if not ToolChecker.check_tool('subzy'):
            Logger.warning("subzy não encontrado, pulando takeover check...")
            return

        Logger.header("VERIFICAÇÃO DE TAKEOVER")
        Logger.info("Verificando takeover com subzy...")

        output_file = self.output_mgr.get_path('takeover', 'subzy_results.txt')

        try:
            result = subprocess.run(
                ['subzy', 'run', '--targets', str(subdomains_file), '--hide_fails'],
                capture_output=True,
                text=True,
                timeout=600
            )

            with open(output_file, 'w') as f:
                f.write(result.stdout)

            if result.stdout.strip():
                Logger.warning(f"Possíveis takeovers encontrados! Veja {output_file.name}")
            else:
                Logger.success("Nenhum takeover detectado")

        except Exception as e:
            Logger.warning(f"Erro no subzy: {e}")


class WebEnum:
    """Classe principal de enumeração"""

    def __init__(self, domain: str, output_dir: str = './results'):
        self.domain = domain
        self.output_mgr = OutputManager(output_dir, domain)

        # Componentes
        self.subdomain_enum = SubdomainEnum(domain, self.output_mgr)
        self.dns_resolver = DNSResolver(self.output_mgr)
        self.http_prober = HTTPProber(self.output_mgr)
        self.url_collector = URLCollector(self.output_mgr)
        self.takeover_checker = TakeoverChecker(self.output_mgr)

    def run_full_enum(self, skip_screenshots: bool = False):
        """Executa enumeração completa"""
        start_time = time.time()

        Logger.header(f"ENUMERAÇÃO WEB: {self.domain}")

        # 1. Enumeração de subdomínios
        subs_file = self.subdomain_enum.run_all()

        # 2. Resolução DNS
        resolved_file = self.dns_resolver.resolve_with_puredns(subs_file)
        self.dns_resolver.enrich_with_dnsx(resolved_file)

        # 3. HTTP Probing
        alive_file = self.http_prober.probe_with_httpx(resolved_file)

        if not alive_file:
            Logger.error("Nenhum host ativo encontrado! Abortando...")
            return

        # 4. Screenshots (opcional)
        if not skip_screenshots:
            self.http_prober.screenshot_with_gowitness(alive_file)

        # 5. Coleta de URLs
        all_urls = set()

        # 5a. Arquivos históricos
        archive_urls = self.url_collector.collect_from_archives(alive_file)
        all_urls.update(archive_urls)

        # 5b. Crawling live
        crawl_urls = self.url_collector.crawl_live(alive_file)
        all_urls.update(crawl_urls)

        # 5c. JavaScript
        js_file = self.url_collector.collect_js_files(alive_file)
        if js_file:
            js_urls = self.url_collector.extract_from_js(js_file)
            all_urls.update(js_urls)

        # 6. Limpeza de URLs
        if all_urls:
            self.url_collector.clean_urls(all_urls)

        # 7. Takeover check
        self.takeover_checker.check_with_subzy(resolved_file)

        # Relatório final
        elapsed = time.time() - start_time
        self._print_summary(elapsed)

    def _print_summary(self, elapsed_time: float):
        """Imprime sumário final"""
        Logger.header("SUMÁRIO FINAL")

        summary = {
            "Subdomínios": self.output_mgr.get_path('subdomains', 'all_subdomains.txt'),
            "Hosts resolvidos": self.output_mgr.get_path('dns', 'resolved.txt'),
            "Hosts ativos": self.output_mgr.get_path('http', 'alive.txt'),
            "URLs coletadas": self.output_mgr.get_path('urls', 'urls_clean.txt'),
            "Arquivos JS": self.output_mgr.get_path('js', 'js_files.txt'),
        }

        for name, path in summary.items():
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        count = sum(1 for line in f if line.strip())
                    Logger.info(f"{name}: {count}")
                except:
                    pass

        Logger.success(f"\nTempo total: {elapsed_time/60:.2f} minutos")
        Logger.success(f"Resultados salvos em: {self.output_mgr.base_dir}")


def main():
    banner = f"""
{Colors.OKCYAN}{Colors.BOLD}
╦ ╦┌─┐┌┐ ╔═╗┌┐┌┬ ┬┌┬┐
║║║├┤ ├┴┐║╣ ││││ ││││
╚╩╝└─┘└─┘╚═╝┘└┘└─┘┴ ┴
{Colors.ENDC}
{Colors.OKGREEN}Comprehensive Web Enumeration Tool{Colors.ENDC}
{Colors.WARNING}By: @6bat66{Colors.ENDC}
"""

    print(banner)

    parser = argparse.ArgumentParser(
        description='WebEnum - Ferramenta completa de enumeração web',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '-d', '--domain',
        required=True,
        help='Domínio alvo (ex: example.com)'
    )

    parser.add_argument(
        '-o', '--output',
        default='./results',
        help='Diretório de output (padrão: ./results)'
    )

    parser.add_argument(
        '--skip-screenshots',
        action='store_true',
        help='Pula captura de screenshots'
    )

    parser.add_argument(
        '--check-tools',
        action='store_true',
        help='Verifica ferramentas instaladas e sai'
    )

    args = parser.parse_args()

    # Verifica ferramentas
    if args.check_tools:
        Logger.header("VERIFICAÇÃO DE FERRAMENTAS")
        status = ToolChecker.check_all(check_optional=True)

        Logger.success("Disponíveis:")
        for tool in status['available']:
            print(f"  ✓ {tool}")

        if status['missing']:
            Logger.warning("\nFaltando:")
            for tool in status['missing']:
                print(f"  ✗ {tool}")

        sys.exit(0)

    # Verifica ferramentas críticas
    critical_tools = ['subfinder', 'httpx']
    missing_critical = [t for t in critical_tools if not ToolChecker.check_tool(t)]

    if missing_critical:
        Logger.error(f"Ferramentas críticas faltando: {', '.join(missing_critical)}")
        Logger.info("Instale com: go install -v github.com/projectdiscovery/<tool>/cmd/<tool>@latest")
        sys.exit(1)

    # Inicia enumeração
    try:
        enum = WebEnum(args.domain, args.output)
        enum.run_full_enum(skip_screenshots=args.skip_screenshots)
    except KeyboardInterrupt:
        Logger.warning("\nInterrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        Logger.error(f"Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
