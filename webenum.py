#!/usr/bin/env python3
"""
WebEnum - Comprehensive Web Enumeration Tool
Automates complete web target enumeration using multiple tools
"""

import os
import sys
import json
import subprocess
import argparse
import logging
import time
import platform
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

# Colors for output
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
    """Custom logging system with colors"""

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
    """Checks if required tools are installed"""

    REQUIRED_TOOLS = {
        'subdomain': ['subfinder', 'assetfinder', 'findomain'],
        'dns': ['dnsx', 'puredns', 'massdns'],
        'http': ['httpx'],
        'url_collect': ['gau', 'waybackurls', 'hakrawler', 'getJS'],
        'utils': ['anew', 'uro'],
        'optional': ['amass', 'gowitness', 'subzy', 'subjack', 'kxss']
    }

    @staticmethod
    def check_tool(tool: str) -> bool:
        """Check if a tool is installed"""
        return shutil.which(tool) is not None

    @classmethod
    def check_all(cls, check_optional: bool = False) -> Dict[str, List[str]]:
        """Check all tools and return status"""
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

    @staticmethod
    def get_gowitness_version() -> Optional[str]:
        """Get gowitness version to determine correct command syntax"""
        try:
            result = subprocess.run(
                ['gowitness', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except:
            return None


class OutputManager:
    """Manages output directories and files"""

    def __init__(self, base_dir: str, domain: str):
        self.domain = domain
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = Path(base_dir) / f"{domain}_{self.timestamp}"

        # Directory structure
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
        """Create directory structure"""
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        Logger.success(f"Structure created at: {self.base_dir}")

    def get_path(self, category: str, filename: str) -> Path:
        """Return full path for a file"""
        return self.dirs[category] / filename

    def dedupe_file(self, input_file: Path, output_file: Path):
        """Remove duplicates from a file"""
        if not input_file.exists():
            return

        try:
            lines = set()
            with open(input_file, 'r') as f:
                lines = set(line.strip() for line in f if line.strip())

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(lines)) + '\n')

            Logger.success(f"Dedupe: {len(lines)} unique lines saved to {output_file.name}")
        except Exception as e:
            Logger.error(f"Error in dedupe: {e}")


class SubdomainEnum:
    """Subdomain enumeration"""

    def __init__(self, domain: str, output_mgr: OutputManager):
        self.domain = domain
        self.output_mgr = output_mgr
        self.tools = {
            'subfinder': ['subfinder', '-d', domain, '-all', '-silent'],
            'assetfinder': ['assetfinder', '--subs-only', domain],
            'findomain': ['findomain', '-t', domain, '-q'],
        }

    def run_tool(self, tool_name: str, command: List[str]) -> Set[str]:
        """Run a tool and return results"""
        if not ToolChecker.check_tool(tool_name):
            Logger.warning(f"{tool_name} not found, skipping...")
            return set()

        Logger.info(f"Running {tool_name}...")
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

            Logger.success(f"{tool_name}: {len(subs)} subdomains found")
            return subs

        except subprocess.TimeoutExpired:
            Logger.warning(f"{tool_name} timeout")
        except Exception as e:
            Logger.error(f"Error running {tool_name}: {e}")

        return set()

    def run_all(self) -> Path:
        """Run all enumeration tools"""
        Logger.header("SUBDOMAIN ENUMERATION")

        all_subs = set()

        # Run tools in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.run_tool, name, cmd): name
                for name, cmd in self.tools.items()
            }

            for future in as_completed(futures):
                subs = future.result()
                all_subs.update(subs)

        # Add main domain
        all_subs.add(self.domain)

        # Save consolidated result
        output_file = self.output_mgr.get_path('subdomains', 'all_subdomains.txt')
        with open(output_file, 'w') as f:
            f.write('\n'.join(sorted(all_subs)) + '\n')

        Logger.success(f"Total: {len(all_subs)} unique subdomains")
        return output_file


class DNSResolver:
    """DNS resolution and validation"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def resolve_with_puredns(self, input_file: Path) -> Optional[Path]:
        """Resolve subdomains using puredns"""
        if not ToolChecker.check_tool('puredns'):
            Logger.warning("puredns not found, skipping resolution...")
            return input_file

        # Check for massdns dependency
        if not ToolChecker.check_tool('massdns'):
            Logger.warning("massdns not found (required by puredns)")
            Logger.info("Install: brew install massdns  OR  git clone https://github.com/blechschmidt/massdns && make")
            return input_file

        Logger.header("DNS RESOLUTION")
        Logger.info("Resolving subdomains with puredns...")

        output_file = self.output_mgr.get_path('dns', 'resolved.txt')

        try:
            subprocess.run(
                ['puredns', 'resolve', str(input_file), '-w', str(output_file)],
                timeout=600,
                check=True
            )

            # Count lines
            with open(output_file, 'r') as f:
                count = sum(1 for _ in f)

            Logger.success(f"Resolved: {count} subdomains")
            return output_file

        except subprocess.CalledProcessError as e:
            Logger.error(f"puredns failed: {e}")
            Logger.warning("Using unresolved subdomain list instead")
            return input_file
        except subprocess.TimeoutExpired:
            Logger.warning("puredns timeout, using original list")
            return input_file
        except Exception as e:
            Logger.error(f"Error in puredns: {e}")
            return input_file

    def enrich_with_dnsx(self, input_file: Path) -> Optional[Path]:
        """Enrich DNS data with dnsx"""
        if not ToolChecker.check_tool('dnsx'):
            Logger.warning("dnsx not found, skipping...")
            return input_file

        Logger.info("Enriching DNS data with dnsx...")

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

            Logger.success(f"DNS data saved to {output_file.name}")
            return input_file

        except Exception as e:
            Logger.error(f"Error in dnsx: {e}")
            return input_file


class HTTPProber:
    """HTTP probing and fingerprinting"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def probe_with_httpx(self, input_file: Path) -> Optional[Path]:
        """Perform HTTP probing with httpx"""
        if not ToolChecker.check_tool('httpx'):
            Logger.error("httpx is required! Install: go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest")
            return None

        Logger.header("HTTP PROBING")
        Logger.info("Checking active hosts with httpx...")

        json_output = self.output_mgr.get_path('http', 'httpx_full.json')
        alive_output = self.output_mgr.get_path('http', 'alive.txt')

        try:
            # Run httpx
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

            # Extract only alive URLs
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
                Logger.warning(f"Error processing JSON: {e}")

            with open(alive_output, 'w') as f:
                f.write('\n'.join(alive_urls) + '\n')

            Logger.success(f"Active hosts: {len(alive_urls)}")
            return alive_output

        except subprocess.TimeoutExpired:
            Logger.warning("httpx timeout")
        except Exception as e:
            Logger.error(f"Error in httpx: {e}")

        return None

    def screenshot_with_gowitness(self, input_file: Path):
        """Take screenshots with gowitness"""
        if not ToolChecker.check_tool('gowitness'):
            Logger.warning("gowitness not found, skipping screenshots...")
            return

        Logger.info("Taking screenshots with gowitness...")

        screenshot_dir = self.output_mgr.dirs['screenshots']

        # Try to determine correct command syntax
        # Newer versions use: gowitness scan file -f <file>
        # Older versions use: gowitness file -f <file>
        
        commands_to_try = [
            # New syntax (v3.x)
            ['gowitness', 'scan', 'file', '-f', str(input_file), '-P', str(screenshot_dir), '--disable-db'],
            # Alternative new syntax
            ['gowitness', 'scan', 'file', '-f', str(input_file), '--screenshot-path', str(screenshot_dir)],
            # Old syntax (v2.x)
            ['gowitness', 'file', '-f', str(input_file), '-P', str(screenshot_dir)],
        ]

        success = False
        for cmd in commands_to_try:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                if result.returncode == 0:
                    Logger.success(f"Screenshots saved to {screenshot_dir}")
                    success = True
                    break
                    
            except subprocess.TimeoutExpired:
                Logger.warning("gowitness timeout")
                break
            except Exception:
                continue

        if not success:
            Logger.warning("Could not capture screenshots - gowitness command syntax may have changed")
            Logger.info("Try manually: gowitness scan file -f alive.txt --screenshot-path ./screenshots")


class URLCollector:
    """URL collection from multiple sources"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def collect_from_archives(self, hosts_file: Path) -> Set[str]:
        """Collect URLs from historical archives"""
        Logger.header("URL COLLECTION")

        all_urls = set()

        # GAU
        if ToolChecker.check_tool('gau'):
            Logger.info("Collecting URLs with gau...")
            try:
                with open(hosts_file, 'r') as f:
                    result = subprocess.run(
                        ['gau', '--subs', '--threads', '5'],
                        stdin=f,
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)
                Logger.success(f"gau: {len(urls)} URLs")
            except Exception as e:
                Logger.warning(f"Error in gau: {e}")

        # Waybackurls
        if ToolChecker.check_tool('waybackurls'):
            Logger.info("Collecting URLs with waybackurls...")
            try:
                with open(hosts_file, 'r') as f:
                    result = subprocess.run(
                        ['waybackurls'],
                        stdin=f,
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)
                Logger.success(f"waybackurls: {len(urls)} URLs")
            except Exception as e:
                Logger.warning(f"Error in waybackurls: {e}")

        # Save raw
        raw_file = self.output_mgr.get_path('urls', 'urls_raw.txt')
        with open(raw_file, 'w') as f:
            f.write('\n'.join(all_urls) + '\n')

        return all_urls

    def crawl_live(self, hosts_file: Path) -> Set[str]:
        """Crawl active sites"""
        all_urls = set()

        # Hakrawler
        if ToolChecker.check_tool('hakrawler'):
            Logger.info("Crawling with hakrawler...")
            try:
                with open(hosts_file, 'r') as f:
                    result = subprocess.run(
                        ['hakrawler', '-plain', '-depth', '2'],
                        stdin=f,
                        capture_output=True,
                        text=True,
                        timeout=900
                    )
                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)
                Logger.success(f"hakrawler: {len(urls)} URLs")
            except Exception as e:
                Logger.warning(f"Error in hakrawler: {e}")

        return all_urls

    def collect_js_files(self, hosts_file: Path) -> Path:
        """Collect JavaScript files"""
        if not ToolChecker.check_tool('getJS'):
            Logger.warning("getJS not found, skipping JS collection...")
            return None

        Logger.info("Collecting JS files with getJS...")

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

            Logger.success(f"JS files: {len(js_urls)}")
            return js_file

        except Exception as e:
            Logger.warning(f"Error in getJS: {e}")
            return None

    def extract_from_js(self, js_file: Path) -> Set[str]:
        """Extract endpoints from JS files"""
        if not js_file or not ToolChecker.check_tool('subjs'):
            return set()

        Logger.info("Extracting endpoints from JS files...")

        try:
            with open(js_file, 'r') as f:
                result = subprocess.run(
                    ['subjs'],
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=600
                )

            urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
            Logger.success(f"Endpoints extracted from JS: {len(urls)}")
            return urls

        except Exception as e:
            Logger.warning(f"Error in subjs: {e}")
            return set()

    def clean_urls(self, urls: Set[str]) -> Path:
        """Clean and normalize URLs"""
        if not ToolChecker.check_tool('uro'):
            Logger.warning("uro not found, saving URLs without cleaning...")
            clean_file = self.output_mgr.get_path('urls', 'urls_clean.txt')
            with open(clean_file, 'w') as f:
                f.write('\n'.join(sorted(urls)) + '\n')
            return clean_file

        Logger.info("Cleaning URLs with uro...")

        # Save temporary
        temp_file = self.output_mgr.get_path('urls', 'temp_urls.txt')
        with open(temp_file, 'w') as f:
            f.write('\n'.join(urls) + '\n')

        clean_file = self.output_mgr.get_path('urls', 'urls_clean.txt')

        try:
            with open(temp_file, 'r') as f:
                result = subprocess.run(
                    ['uro'],
                    stdin=f,
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

            Logger.success(f"Clean URLs: {count}")
            return clean_file

        except Exception as e:
            Logger.error(f"Error in uro: {e}")
            if temp_file.exists():
                temp_file.rename(clean_file)
            return clean_file


class TakeoverChecker:
    """Check for subdomain takeover"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def check_with_subzy(self, subdomains_file: Path):
        """Check takeover with subzy"""
        if not ToolChecker.check_tool('subzy'):
            Logger.warning("subzy not found, skipping takeover check...")
            return

        Logger.info("Checking takeover with subzy...")

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
                Logger.warning(f"Possible takeovers found! See {output_file.name}")
            else:
                Logger.success("No takeover detected")

        except Exception as e:
            Logger.warning(f"Error in subzy: {e}")


class WebEnum:
    """Main enumeration class"""

    def __init__(self, domain: str, output_dir: str = './results'):
        self.domain = domain
        self.output_mgr = OutputManager(output_dir, domain)

        # Components
        self.subdomain_enum = SubdomainEnum(domain, self.output_mgr)
        self.dns_resolver = DNSResolver(self.output_mgr)
        self.http_prober = HTTPProber(self.output_mgr)
        self.url_collector = URLCollector(self.output_mgr)
        self.takeover_checker = TakeoverChecker(self.output_mgr)

    def run_full_enum(self, skip_screenshots: bool = False):
        """Run complete enumeration"""
        start_time = time.time()

        Logger.header(f"WEB ENUMERATION: {self.domain}")

        # 1. Subdomain enumeration
        subs_file = self.subdomain_enum.run_all()

        # 2. DNS Resolution
        resolved_file = self.dns_resolver.resolve_with_puredns(subs_file)
        self.dns_resolver.enrich_with_dnsx(resolved_file)

        # 3. HTTP Probing
        alive_file = self.http_prober.probe_with_httpx(resolved_file)

        if not alive_file:
            Logger.error("No active hosts found! Aborting...")
            return

        # 4. Screenshots (optional)
        if not skip_screenshots:
            self.http_prober.screenshot_with_gowitness(alive_file)
        else:
            Logger.info("Skipping screenshots (--skip-screenshots)")

        # 5. URL Collection
        all_urls = set()

        # 5a. Historical archives
        archive_urls = self.url_collector.collect_from_archives(alive_file)
        all_urls.update(archive_urls)

        # 5b. Live crawling
        crawl_urls = self.url_collector.crawl_live(alive_file)
        all_urls.update(crawl_urls)

        # 5c. JavaScript
        js_file = self.url_collector.collect_js_files(alive_file)
        if js_file:
            js_urls = self.url_collector.extract_from_js(js_file)
            all_urls.update(js_urls)

        # 6. URL Cleaning
        if all_urls:
            self.url_collector.clean_urls(all_urls)

        # 7. Takeover check
        self.takeover_checker.check_with_subzy(resolved_file)

        # Final report
        elapsed = time.time() - start_time
        self._print_summary(elapsed)

    def _print_summary(self, elapsed_time: float):
        """Print final summary"""
        Logger.header("FINAL SUMMARY")

        summary = {
            "Subdomains": self.output_mgr.get_path('subdomains', 'all_subdomains.txt'),
            "Resolved hosts": self.output_mgr.get_path('dns', 'resolved.txt'),
            "Active hosts": self.output_mgr.get_path('http', 'alive.txt'),
            "Collected URLs": self.output_mgr.get_path('urls', 'urls_clean.txt'),
            "JS files": self.output_mgr.get_path('js', 'js_files.txt'),
        }

        for name, path in summary.items():
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        count = sum(1 for line in f if line.strip())
                    Logger.info(f"{name}: {count}")
                except:
                    pass

        Logger.success(f"\nTotal time: {elapsed_time/60:.2f} minutes")
        Logger.success(f"Results saved to: {self.output_mgr.base_dir}")


def print_installation_help():
    """Print helpful installation instructions"""
    system = platform.system()
    
    Logger.header("INSTALLATION HELP")
    
    if system == "Darwin":  # macOS
        print("""
macOS Installation:

1. Install Homebrew (if not installed):
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

2. Install dependencies:
   brew install go python3 massdns

3. Run the installation script:
   ./install_tools.sh

4. Manual massdns installation (if brew fails):
   git clone https://github.com/blechschmidt/massdns
   cd massdns && make
   sudo make install
""")
    else:  # Linux
        print("""
Linux Installation:

1. Install dependencies:
   # Ubuntu/Debian
   sudo apt update && sudo apt install -y golang-go python3 python3-pip git build-essential

   # Fedora
   sudo dnf install -y golang python3 python3-pip git gcc make

2. Install massdns:
   git clone https://github.com/blechschmidt/massdns
   cd massdns && make
   sudo make install

3. Run the installation script:
   ./install_tools.sh
""")


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
        description='WebEnum - Complete web enumeration tool',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '-d', '--domain',
        help='Target domain (e.g.: example.com)'
    )

    parser.add_argument(
        '-o', '--output',
        default='./results',
        help='Output directory (default: ./results)'
    )

    parser.add_argument(
        '--skip-screenshots',
        action='store_true',
        help='Skip screenshot capture'
    )

    parser.add_argument(
        '--check-tools',
        action='store_true',
        help='Check installed tools and exit'
    )

    parser.add_argument(
        '--install-help',
        action='store_true',
        help='Show installation instructions'
    )

    args = parser.parse_args()

    # Show installation help
    if args.install_help:
        print_installation_help()
        sys.exit(0)

    # Check tools
    if args.check_tools:
        Logger.header("TOOL CHECK")
        status = ToolChecker.check_all(check_optional=True)

        Logger.success("Available:")
        for tool in status['available']:
            print(f"  ✓ {tool}")

        if status['missing']:
            Logger.warning("\nMissing:")
            for tool in status['missing']:
                print(f"  ✗ {tool}")
            
            print("\n" + "="*60)
            Logger.info("To install missing tools, run: ./install_tools.sh")
            Logger.info("For detailed instructions, run: ./webenum.py --install-help")

        sys.exit(0)

    # Require domain if not checking tools
    if not args.domain:
        parser.print_help()
        sys.exit(1)

    # Check critical tools
    critical_tools = ['subfinder', 'httpx']
    missing_critical = [t for t in critical_tools if not ToolChecker.check_tool(t)]

    if missing_critical:
        Logger.error(f"Missing critical tools: {', '.join(missing_critical)}")
        Logger.info("Run: ./install_tools.sh")
        Logger.info("Or: ./webenum.py --install-help")
        sys.exit(1)

    # Warn about massdns
    if not ToolChecker.check_tool('massdns'):
        Logger.warning("massdns not found - DNS resolution will be limited")
        Logger.info(f"Install on {'macOS: brew install massdns' if platform.system() == 'Darwin' else 'Linux: see --install-help'}")

    # Start enumeration
    try:
        enum = WebEnum(args.domain, args.output)
        enum.run_full_enum(skip_screenshots=args.skip_screenshots)
    except KeyboardInterrupt:
        Logger.warning("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        Logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()