#!/usr/bin/env python3
"""
WebEnum - Advanced Web Enumeration Tool
Modern reconnaissance framework with comprehensive subdomain discovery,
URL collection, vulnerability scanning, and asset analysis.
"""

import os
import sys
import json
import subprocess
import argparse
import logging
import time
import platform
import requests
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs
import shutil
import hashlib

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


class APIConfig:
    """API Keys Configuration"""
    
    def __init__(self):
        self.config_file = Path.home() / '.config' / 'webenum' / 'api_keys.json'
        self.keys = self.load_keys()
    
    def load_keys(self) -> Dict[str, str]:
        """Load API keys from config file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_key(self, service: str, key: str):
        """Save API key"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.keys[service] = key
        with open(self.config_file, 'w') as f:
            json.dump(self.keys, f, indent=2)
    
    def get_key(self, service: str) -> Optional[str]:
        """Get API key for service"""
        return self.keys.get(service)


class ToolChecker:
    """Checks if required tools are installed"""

    REQUIRED_TOOLS = {
        'subdomain': ['subfinder', 'assetfinder', 'findomain', 'amass', 'knockpy'],
        'dns': ['dnsx', 'puredns', 'massdns', 'dnsvalidator'],
        'http': ['httpx', 'hakcheckurl'],
        'url_collect': ['xurlfind3r', 'waybackurls', 'gau', 'hakrawler', 'photon', 'meg'],
        'js_analysis': ['subjs', 'jsubfinder', 'getJS'],
        'utils': ['anew', 'uro', 'unfurl', 'qsreplace', 'freq'],
        'scanning': ['nuclei', 'sdlookup'],
        'git': ['goop', 'git-dumper'],
        'optional': ['gowitness', 'subzy', 'subjack', 'dalfox', 'sqlmap', 'arjun']
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
            'ports': self.base_dir / 'ports',
            'urls': self.base_dir / 'urls',
            'js': self.base_dir / 'js',
            'screenshots': self.base_dir / 'screenshots',
            'vulnerabilities': self.base_dir / 'vulnerabilities',
            'parameters': self.base_dir / 'parameters',
            'git': self.base_dir / 'git',
            'cloud': self.base_dir / 'cloud',
            'takeover': self.base_dir / 'takeover',
            'api_data': self.base_dir / 'api_data',
            'diff': self.base_dir / 'diff',
            'reports': self.base_dir / 'reports',
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


class CertificateTransparency:
    """Certificate Transparency Log Enumeration"""
    
    def __init__(self, domain: str, output_mgr: OutputManager):
        self.domain = domain
        self.output_mgr = output_mgr
    
    def query_crtsh(self) -> Set[str]:
        """Query crt.sh for subdomains"""
        Logger.info("Querying crt.sh...")
        
        try:
            url = f"https://crt.sh/?q=%.{self.domain}&output=json"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                domains = set()
                
                for entry in data:
                    name = entry.get('name_value', '')
                    for domain in name.split('\n'):
                        domain = domain.strip().replace('*', '').replace('.', '', 1) if domain.startswith('*.') else domain.strip()
                        if domain and domain.endswith(self.domain):
                            domains.add(domain)
                
                output_file = self.output_mgr.get_path('subdomains', 'crtsh.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(domains)) + '\n')
                
                Logger.success(f"crt.sh: {len(domains)} domains")
                return domains
                
        except Exception as e:
            Logger.error(f"Error querying crt.sh: {e}")
        
        return set()
    
    def query_certspotter(self, api_key: Optional[str] = None) -> Set[str]:
        """Query CertSpotter API"""
        Logger.info("Querying CertSpotter...")
        
        try:
            url = f"https://api.certspotter.com/v1/issuances?domain={self.domain}&include_subdomains=true&expand=dns_names"
            headers = {}
            
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                domains = set()
                
                for entry in data:
                    for name in entry.get('dns_names', []):
                        if name.endswith(self.domain):
                            domains.add(name)
                
                output_file = self.output_mgr.get_path('subdomains', 'certspotter.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(domains)) + '\n')
                
                Logger.success(f"CertSpotter: {len(domains)} domains")
                return domains
                
        except Exception as e:
            Logger.error(f"Error querying CertSpotter: {e}")
        
        return set()


class PassiveAPIs:
    """Passive API enumeration sources"""
    
    def __init__(self, domain: str, output_mgr: OutputManager, api_config: APIConfig):
        self.domain = domain
        self.output_mgr = output_mgr
        self.api_config = api_config
    
    def query_virustotal(self) -> Set[str]:
        """Query VirusTotal API"""
        api_key = self.api_config.get_key('virustotal')
        if not api_key:
            Logger.warning("VirusTotal API key not configured")
            return set()
        
        Logger.info("Querying VirusTotal...")
        
        try:
            url = f"https://www.virustotal.com/vtapi/v2/domain/report"
            params = {'apikey': api_key, 'domain': self.domain}
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                domains = set(data.get('subdomains', []))
                
                output_file = self.output_mgr.get_path('api_data', 'virustotal.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(domains)) + '\n')
                
                json_file = self.output_mgr.get_path('api_data', 'virustotal.json')
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                Logger.success(f"VirusTotal: {len(domains)} domains")
                return domains
                
        except Exception as e:
            Logger.error(f"Error querying VirusTotal: {e}")
        
        return set()
    
    def query_alienvault(self) -> Set[str]:
        """Query AlienVault OTX"""
        Logger.info("Querying AlienVault OTX...")
        
        try:
            url = f"https://otx.alienvault.com/api/v1/indicators/domain/{self.domain}/passive_dns"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                domains = set()
                
                for entry in data.get('passive_dns', []):
                    hostname = entry.get('hostname', '')
                    if hostname.endswith(self.domain):
                        domains.add(hostname)
                
                output_file = self.output_mgr.get_path('api_data', 'alienvault.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(domains)) + '\n')
                
                Logger.success(f"AlienVault: {len(domains)} domains")
                return domains
                
        except Exception as e:
            Logger.error(f"Error querying AlienVault: {e}")
        
        return set()
    
    def query_securitytrails(self) -> Set[str]:
        """Query SecurityTrails API"""
        api_key = self.api_config.get_key('securitytrails')
        if not api_key:
            Logger.warning("SecurityTrails API key not configured")
            return set()
        
        Logger.info("Querying SecurityTrails...")
        
        try:
            url = f"https://api.securitytrails.com/v1/domain/{self.domain}/subdomains"
            headers = {'APIKEY': api_key}
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                domains = set()
                
                for subdomain in data.get('subdomains', []):
                    full_domain = f"{subdomain}.{self.domain}"
                    domains.add(full_domain)
                
                output_file = self.output_mgr.get_path('api_data', 'securitytrails.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(domains)) + '\n')
                
                Logger.success(f"SecurityTrails: {len(domains)} domains")
                return domains
                
        except Exception as e:
            Logger.error(f"Error querying SecurityTrails: {e}")
        
        return set()


class SubdomainEnum:
    """Comprehensive subdomain enumeration"""

    def __init__(self, domain: str, output_mgr: OutputManager, api_config: APIConfig):
        self.domain = domain
        self.output_mgr = output_mgr
        self.api_config = api_config
        self.tools = {
            'subfinder': ['subfinder', '-d', domain, '-all', '-silent'],
            'assetfinder': ['assetfinder', '--subs-only', domain],
            'findomain': ['findomain', '-t', domain, '-q'],
            'amass': ['amass', 'enum', '-passive', '-d', domain, '-silent'],
            'knockpy': ['knockpy', domain, '--silent'] if ToolChecker.check_tool('knockpy') else None
        }

    def run_tool(self, tool_name: str, command: List[str]) -> Set[str]:
        """Run a tool and return results"""
        if not command or not ToolChecker.check_tool(tool_name.split()[0]):
            return set()

        Logger.info(f"Running {tool_name}...")
        output_file = self.output_mgr.get_path('subdomains', f'{tool_name}.txt')

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600
            )

            subs = set(line.strip() for line in result.stdout.split('\n') if line.strip())

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(subs)) + '\n')

            Logger.success(f"{tool_name}: {len(subs)} subdomains")
            return subs

        except subprocess.TimeoutExpired:
            Logger.warning(f"{tool_name} timeout")
        except Exception as e:
            Logger.error(f"Error running {tool_name}: {e}")

        return set()

    def run_all(self) -> Path:
        """Run all enumeration tools including APIs and CT logs"""
        Logger.header("SUBDOMAIN ENUMERATION")

        all_subs = set()

        # Traditional tools with parallel execution
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            for name, cmd in self.tools.items():
                if cmd:
                    futures[executor.submit(self.run_tool, name, cmd)] = name

            for future in as_completed(futures):
                subs = future.result()
                all_subs.update(subs)

        # Certificate Transparency
        ct = CertificateTransparency(self.domain, self.output_mgr)
        all_subs.update(ct.query_crtsh())
        all_subs.update(ct.query_certspotter(self.api_config.get_key('certspotter')))

        # Passive APIs
        apis = PassiveAPIs(self.domain, self.output_mgr, self.api_config)
        all_subs.update(apis.query_virustotal())
        all_subs.update(apis.query_alienvault())
        all_subs.update(apis.query_securitytrails())

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
            Logger.warning("puredns not found, skipping resolution")
            return input_file

        if not ToolChecker.check_tool('massdns'):
            Logger.warning("massdns not found (required by puredns)")
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

            with open(output_file, 'r') as f:
                count = sum(1 for line in f if line.strip())

            Logger.success(f"Resolved: {count} active subdomains")
            return output_file

        except Exception as e:
            Logger.error(f"Error in puredns: {e}")
            return input_file

    def enrich_with_dnsx(self, input_file: Path):
        """Enrich with DNS records using dnsx"""
        if not ToolChecker.check_tool('dnsx'):
            Logger.warning("dnsx not found")
            return

        Logger.info("Enriching with DNS records...")

        # A records
        a_records = self.output_mgr.get_path('dns', 'a_records.txt')
        subprocess.run(
            ['dnsx', '-l', str(input_file), '-a', '-resp-only', '-silent'],
            stdout=open(a_records, 'w'),
            stderr=subprocess.DEVNULL,
            timeout=300
        )

        # CNAME records
        cname_records = self.output_mgr.get_path('dns', 'cname_records.txt')
        subprocess.run(
            ['dnsx', '-l', str(input_file), '-cname', '-resp-only', '-silent'],
            stdout=open(cname_records, 'w'),
            stderr=subprocess.DEVNULL,
            timeout=300
        )

        Logger.success("DNS enrichment complete")


class PortScanner:
    """Fast port scanning with sdlookup"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def scan_with_sdlookup(self, input_file: Path):
        """Scan with sdlookup (fast Shodan InternetDB queries)"""
        if not ToolChecker.check_tool('sdlookup'):
            Logger.warning("sdlookup not found, skipping port scan")
            return
        
        Logger.header("PORT SCANNING")
        Logger.info("Scanning ports with sdlookup (via Shodan InternetDB)...")
        
        output_file = self.output_mgr.get_path('ports', 'sdlookup_results.json')
        output_txt = self.output_mgr.get_path('ports', 'open_ports.txt')
        
        try:
            # Get IPs from A records
            a_records_file = self.output_mgr.get_path('dns', 'a_records.txt')
            if not a_records_file.exists():
                Logger.warning("No A records file found")
                return
            
            with open(a_records_file, 'r') as f:
                ips = [line.strip() for line in f if line.strip()]
            
            if not ips:
                Logger.warning("No IPs to scan")
                return
            
            # Create IP file for sdlookup
            ip_file = self.output_mgr.get_path('ports', 'ips.txt')
            with open(ip_file, 'w') as f:
                f.write('\n'.join(ips))
            
            # Run sdlookup
            cmd = ['sdlookup', '-i', str(ip_file), '-json', '-o', str(output_file)]
            subprocess.run(cmd, timeout=300, check=True)
            
            # Parse results
            if output_file.exists():
                with open(output_file, 'r') as f:
                    data = json.load(f)
                
                summary = []
                for result in data:
                    ip = result.get('ip', '')
                    ports = result.get('ports', [])
                    vulns = result.get('vulns', [])
                    
                    if ports:
                        summary.append(f"{ip}: {','.join(map(str, ports))}")
                        if vulns:
                            summary.append(f"  └─ Vulns: {','.join(vulns)}")
                
                with open(output_txt, 'w') as f:
                    f.write('\n'.join(summary))
                
                Logger.success(f"Port scan complete: {len(data)} IPs scanned")
            
        except Exception as e:
            Logger.error(f"Error in sdlookup: {e}")


class HTTPProber:
    """HTTP probing and status checking"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def probe_with_httpx(self, input_file: Path) -> Optional[Path]:
        """Probe for HTTP services"""
        if not ToolChecker.check_tool('httpx'):
            Logger.error("httpx not found!")
            return None

        Logger.header("HTTP PROBING")
        Logger.info("Probing for active HTTP services...")

        output_file = self.output_mgr.get_path('http', 'alive.txt')
        json_file = self.output_mgr.get_path('http', 'httpx_full.json')

        try:
            cmd = [
                'httpx',
                '-l', str(input_file),
                '-silent',
                '-status-code',
                '-title',
                '-tech-detect',
                '-cdn',
                '-cname',
                '-content-length',
                '-web-server',
                '-json',
                '-o', str(json_file)
            ]

            subprocess.run(cmd, timeout=600, check=True)

            # Extract URLs
            urls = []
            with open(json_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        urls.append(data.get('url', ''))
                    except:
                        pass

            with open(output_file, 'w') as f:
                f.write('\n'.join(urls) + '\n')

            Logger.success(f"Found {len(urls)} active HTTP services")
            return output_file

        except Exception as e:
            Logger.error(f"Error in httpx: {e}")
            return None

    def check_urls_with_hakcheckurl(self, input_file: Path):
        """Quick URL status checking with hakcheckurl"""
        if not ToolChecker.check_tool('hakcheckurl'):
            return
        
        Logger.info("Checking URL status with hakcheckurl...")
        
        output_file = self.output_mgr.get_path('http', 'url_status.txt')
        
        try:
            with open(input_file, 'r') as f:
                result = subprocess.run(
                    ['hakcheckurl'],
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            
            with open(output_file, 'w') as f:
                f.write(result.stdout)
            
            Logger.success("URL status check complete")
            
        except Exception as e:
            Logger.error(f"Error in hakcheckurl: {e}")

    def screenshot_with_gowitness(self, input_file: Path):
        """Take screenshots with gowitness"""
        if not ToolChecker.check_tool('gowitness'):
            Logger.warning("gowitness not found")
            return

        Logger.header("SCREENSHOTS")
        Logger.info("Capturing screenshots...")

        screenshots_dir = self.output_mgr.get_path('screenshots', '')
        db_file = screenshots_dir / 'gowitness.sqlite3'

        try:
            cmd = [
                'gowitness', 'file',
                '-f', str(input_file),
                '--screenshot-path', str(screenshots_dir),
                '--db-path', str(db_file)
            ]

            subprocess.run(cmd, timeout=1800, check=True)
            Logger.success(f"Screenshots saved to {screenshots_dir}")

        except Exception as e:
            Logger.error(f"Error in gowitness: {e}")


class URLCollector:
    """Advanced URL collection with modern tools"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def collect_with_xurlfind3r(self, input_file: Path) -> Set[str]:
        """Collect URLs using xurlfind3r (modern, efficient)"""
        if not ToolChecker.check_tool('xurlfind3r'):
            Logger.warning("xurlfind3r not found")
            return set()
        
        Logger.info("Collecting URLs with xurlfind3r...")
        output_file = self.output_mgr.get_path('urls', 'xurlfind3r.txt')
        
        try:
            with open(input_file, 'r') as f:
                domains = [line.strip() for line in f if line.strip()]
            
            all_urls = set()
            for domain in domains[:50]:  # Limit to prevent excessive API calls
                result = subprocess.run(
                    ['xurlfind3r', '-d', domain, '-silent'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)
            
            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(all_urls)) + '\n')
            
            Logger.success(f"xurlfind3r: {len(all_urls)} URLs")
            return all_urls
            
        except Exception as e:
            Logger.error(f"Error in xurlfind3r: {e}")
            return set()

    def collect_from_archives(self, input_file: Path) -> Set[str]:
        """Collect URLs from web archives"""
        Logger.header("URL COLLECTION")

        all_urls = set()

        # xurlfind3r (primary)
        all_urls.update(self.collect_with_xurlfind3r(input_file))

        # GAU (backup)
        if ToolChecker.check_tool('gau'):
            Logger.info("Running gau...")
            gau_file = self.output_mgr.get_path('urls', 'gau.txt')

            try:
                with open(input_file, 'r') as f:
                    domains = [line.strip() for line in f if line.strip()]

                result = subprocess.run(
                    ['gau'] + domains[:30],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)

                with open(gau_file, 'w') as f:
                    f.write('\n'.join(sorted(urls)) + '\n')

                Logger.success(f"gau: {len(urls)} URLs")

            except Exception as e:
                Logger.error(f"Error in gau: {e}")

        # Waybackurls
        if ToolChecker.check_tool('waybackurls'):
            Logger.info("Running waybackurls...")
            wayback_file = self.output_mgr.get_path('urls', 'waybackurls.txt')

            try:
                with open(input_file, 'r') as f:
                    domains = f.read()

                result = subprocess.run(
                    ['waybackurls'],
                    input=domains,
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)

                with open(wayback_file, 'w') as f:
                    f.write('\n'.join(sorted(urls)) + '\n')

                Logger.success(f"waybackurls: {len(urls)} URLs")

            except Exception as e:
                Logger.error(f"Error in waybackurls: {e}")

        return all_urls

    def crawl_with_photon(self, url: str) -> Set[str]:
        """Targeted crawling with Photon"""
        if not ToolChecker.check_tool('photon'):
            return set()
        
        Logger.info(f"Crawling {url} with Photon...")
        
        output_dir = self.output_mgr.get_path('urls', 'photon')
        output_dir.mkdir(exist_ok=True)
        
        try:
            cmd = [
                'python3', '-m', 'photon',
                '-u', url,
                '-l', '2',
                '-t', '10',
                '--timeout', '5',
                '-o', str(output_dir)
            ]
            
            subprocess.run(cmd, timeout=300, stderr=subprocess.DEVNULL)
            
            # Collect results
            urls = set()
            url_file = output_dir / urlparse(url).netloc / 'urls.txt'
            if url_file.exists():
                with open(url_file, 'r') as f:
                    urls = set(line.strip() for line in f if line.strip())
            
            Logger.success(f"Photon: {len(urls)} URLs")
            return urls
            
        except Exception as e:
            Logger.error(f"Error in Photon: {e}")
            return set()

    def clean_urls(self, urls: Set[str]):
        """Clean and deduplicate URLs with uro"""
        Logger.header("URL CLEANING")

        # Save raw URLs
        raw_file = self.output_mgr.get_path('urls', 'urls_raw.txt')
        with open(raw_file, 'w') as f:
            f.write('\n'.join(sorted(urls)) + '\n')

        Logger.info(f"Raw URLs: {len(urls)}")

        if not ToolChecker.check_tool('uro'):
            Logger.warning("uro not found")
            return

        # Clean with uro
        clean_file = self.output_mgr.get_path('urls', 'urls_clean.txt')

        try:
            with open(raw_file, 'r') as f:
                result = subprocess.run(
                    ['uro'],
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=300
                )

            with open(clean_file, 'w') as f:
                f.write(result.stdout)

            cleaned_count = len(result.stdout.split('\n'))
            Logger.success(f"Cleaned URLs: {cleaned_count}")

        except Exception as e:
            Logger.error(f"Error in uro: {e}")


class JSAnalyzer:
    """Modern JavaScript file analysis"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def collect_with_subjs(self, input_file: Path) -> Set[str]:
        """Collect JS files with subjs"""
        if not ToolChecker.check_tool('subjs'):
            return set()
        
        Logger.info("Collecting JS files with subjs...")
        output_file = self.output_mgr.get_path('js', 'subjs.txt')
        
        try:
            with open(input_file, 'r') as f:
                result = subprocess.run(
                    ['subjs'],
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            
            js_urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
            
            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(js_urls)) + '\n')
            
            Logger.success(f"subjs: {len(js_urls)} JS files")
            return js_urls
            
        except Exception as e:
            Logger.error(f"Error in subjs: {e}")
            return set()

    def analyze_with_jsubfinder(self, input_file: Path) -> Set[str]:
        """Analyze JS files with jsubfinder"""
        if not ToolChecker.check_tool('jsubfinder'):
            return set()
        
        Logger.info("Analyzing JS files with jsubfinder...")
        output_file = self.output_mgr.get_path('js', 'jsubfinder_results.txt')
        
        try:
            with open(input_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            all_findings = set()
            
            for url in urls[:100]:  # Limit to prevent excessive scanning
                result = subprocess.run(
                    ['jsubfinder', '-u', url, '-silent'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                findings = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_findings.update(findings)
            
            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(all_findings)) + '\n')
            
            Logger.success(f"jsubfinder: {len(all_findings)} findings")
            return all_findings
            
        except Exception as e:
            Logger.error(f"Error in jsubfinder: {e}")
            return set()

    def analyze_all(self, alive_file: Path) -> Set[str]:
        """Complete JS analysis"""
        Logger.header("JAVASCRIPT ANALYSIS")
        
        all_js = set()
        
        # Collect JS files
        all_js.update(self.collect_with_subjs(alive_file))
        
        if ToolChecker.check_tool('getJS'):
            Logger.info("Collecting with getJS...")
            getjs_file = self.output_mgr.get_path('js', 'getjs.txt')
            
            try:
                with open(alive_file, 'r') as f:
                    urls = f.read()
                
                result = subprocess.run(
                    ['getJS', '--input', '-', '--complete'],
                    input=urls,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                js_urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_js.update(js_urls)
                
                with open(getjs_file, 'w') as f:
                    f.write('\n'.join(sorted(js_urls)) + '\n')
                
                Logger.success(f"getJS: {len(js_urls)} JS files")
                
            except Exception as e:
                Logger.error(f"Error in getJS: {e}")
        
        # Save all JS files
        all_js_file = self.output_mgr.get_path('js', 'all_js_files.txt')
        with open(all_js_file, 'w') as f:
            f.write('\n'.join(sorted(all_js)) + '\n')
        
        # Analyze with jsubfinder
        if all_js:
            self.analyze_with_jsubfinder(all_js_file)
        
        return all_js


class GitDumper:
    """Git repository dumping with goop"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def check_and_dump(self, url_file: Path):
        """Check for exposed .git and dump if found"""
        Logger.header("GIT REPOSITORY CHECK")
        Logger.info("Checking for exposed .git directories...")
        
        exposed = []
        
        try:
            with open(url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            for url in urls:
                git_url = f"{url}/.git/config"
                try:
                    response = requests.get(git_url, timeout=5, allow_redirects=False)
                    if response.status_code == 200 and '[core]' in response.text:
                        exposed.append(url)
                        Logger.warning(f"Exposed .git found: {url}")
                        
                        # Attempt to dump with goop
                        if ToolChecker.check_tool('goop'):
                            self._dump_with_goop(url)
                        elif ToolChecker.check_tool('git-dumper'):
                            self._dump_with_git_dumper(url)
                except:
                    pass
            
            if exposed:
                output_file = self.output_mgr.get_path('git', 'exposed_git.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(exposed))
                
                Logger.warning(f"Found {len(exposed)} exposed .git repositories!")
            else:
                Logger.success("No exposed .git repositories found")
                
        except Exception as e:
            Logger.error(f"Error checking git exposure: {e}")
    
    def _dump_with_goop(self, url: str):
        """Dump repository with goop"""
        Logger.info(f"Dumping with goop: {url}")
        
        output_dir = self.output_mgr.get_path('git', urlparse(url).netloc)
        output_dir.mkdir(exist_ok=True)
        
        try:
            cmd = ['goop', url, str(output_dir)]
            subprocess.run(cmd, timeout=300)
            Logger.success(f"Repository dumped to {output_dir}")
        except Exception as e:
            Logger.error(f"Error dumping with goop: {e}")
    
    def _dump_with_git_dumper(self, url: str):
        """Dump repository with git-dumper"""
        Logger.info(f"Dumping with git-dumper: {url}")
        
        output_dir = self.output_mgr.get_path('git', urlparse(url).netloc)
        output_dir.mkdir(exist_ok=True)
        
        try:
            git_url = f"{url}/.git/"
            cmd = ['git-dumper', git_url, str(output_dir)]
            subprocess.run(cmd, timeout=300)
            Logger.success(f"Repository dumped to {output_dir}")
        except Exception as e:
            Logger.error(f"Error dumping with git-dumper: {e}")


class VulnScanner:
    """Vulnerability scanning with Nuclei"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def scan_with_nuclei(self, input_file: Path, severity: str = 'medium,high,critical'):
        """Scan with Nuclei"""
        if not ToolChecker.check_tool('nuclei'):
            Logger.warning("nuclei not found")
            return
        
        Logger.header("VULNERABILITY SCANNING")
        Logger.info("Scanning with Nuclei...")
        
        output_file = self.output_mgr.get_path('vulnerabilities', 'nuclei_results.txt')
        json_file = self.output_mgr.get_path('vulnerabilities', 'nuclei_results.json')
        
        try:
            # Update templates
            Logger.info("Updating Nuclei templates...")
            subprocess.run(['nuclei', '-update-templates'], timeout=300, stderr=subprocess.DEVNULL)
            
            cmd = [
                'nuclei',
                '-l', str(input_file),
                '-severity', severity,
                '-silent',
                '-json',
                '-o', str(json_file)
            ]
            
            subprocess.run(cmd, timeout=3600)
            
            # Parse results
            vulns = []
            if json_file.exists():
                with open(json_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            vulns.append(f"[{data.get('info', {}).get('severity', 'unknown')}] {data.get('template-id', '')} - {data.get('matched-at', '')}")
                        except:
                            pass
            
            with open(output_file, 'w') as f:
                f.write('\n'.join(vulns))
            
            if vulns:
                Logger.warning(f"Found {len(vulns)} potential vulnerabilities!")
            else:
                Logger.success("No vulnerabilities found")
                
        except Exception as e:
            Logger.error(f"Error in Nuclei: {e}")


class CloudDetector:
    """Detect cloud services"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
        
        self.cloud_patterns = {
            'AWS': [
                r'\.amazonaws\.com$',
                r'\.s3\..*\.amazonaws\.com$',
                r'\.cloudfront\.net$',
                r'\.elasticbeanstalk\.com$',
                r'\.elb\.amazonaws\.com$'
            ],
            'Azure': [
                r'\.azurewebsites\.net$',
                r'\.blob\.core\.windows\.net$',
                r'\.cloudapp\.azure\.com$',
                r'\.azure\.com$'
            ],
            'GCP': [
                r'\.appspot\.com$',
                r'\.cloudfunctions\.net$',
                r'\.storage\.googleapis\.com$',
                r'\.run\.app$'
            ]
        }
    
    def detect(self, input_file: Path):
        """Detect cloud services"""
        Logger.header("CLOUD SERVICE DETECTION")
        
        with open(input_file, 'r') as f:
            hosts = [line.strip() for line in f if line.strip()]
        
        cloud_services = {'AWS': [], 'Azure': [], 'GCP': []}
        
        for host in hosts:
            for cloud, patterns in self.cloud_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, host, re.IGNORECASE):
                        cloud_services[cloud].append(host)
                        break
        
        # Save results
        for cloud, services in cloud_services.items():
            if services:
                output_file = self.output_mgr.get_path('cloud', f'{cloud.lower()}_services.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(services) + '\n')
                Logger.success(f"{cloud}: {len(services)} services")


class ParameterDiscovery:
    """Parameter discovery and analysis"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def discover_with_arjun(self, url_file: Path):
        """Discover parameters with Arjun"""
        if not ToolChecker.check_tool('arjun'):
            return
        
        Logger.header("PARAMETER DISCOVERY")
        Logger.info("Discovering parameters with Arjun...")
        
        output_file = self.output_mgr.get_path('parameters', 'arjun_params.txt')
        
        try:
            cmd = [
                'arjun',
                '-i', str(url_file),
                '-oT', str(output_file),
                '-t', '5',
                '--stable'
            ]
            
            subprocess.run(cmd, timeout=1800)
            Logger.success("Parameter discovery complete")
            
        except Exception as e:
            Logger.error(f"Error in Arjun: {e}")
    
    def analyze_parameters(self, url_file: Path):
        """Analyze URL parameters"""
        Logger.info("Analyzing URL parameters...")
        
        params = {}
        interesting_params = set()
        
        sensitive_patterns = [
            'id', 'user', 'admin', 'password', 'key', 'token',
            'file', 'path', 'dir', 'folder', 'document',
            'url', 'redirect', 'return', 'next', 'callback',
            'email', 'username', 'debug', 'test', 'api'
        ]
        
        try:
            with open(url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            for url in urls:
                if '?' in url:
                    query_params = parse_qs(urlparse(url).query)
                    for param in query_params.keys():
                        params[param] = params.get(param, 0) + 1
                        
                        param_lower = param.lower()
                        if any(pattern in param_lower for pattern in sensitive_patterns):
                            interesting_params.add(param)
            
            # Save results
            all_params_file = self.output_mgr.get_path('parameters', 'all_parameters.txt')
            with open(all_params_file, 'w') as f:
                for param, count in sorted(params.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"{param}: {count}\n")
            
            interesting_file = self.output_mgr.get_path('parameters', 'interesting_parameters.txt')
            with open(interesting_file, 'w') as f:
                f.write('\n'.join(sorted(interesting_params)))
            
            Logger.success(f"Found {len(params)} unique parameters, {len(interesting_params)} interesting")
            
        except Exception as e:
            Logger.error(f"Error analyzing parameters: {e}")


class TakeoverChecker:
    """Subdomain takeover detection"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def check_with_subzy(self, input_file: Path):
        """Check for takeover with subzy"""
        if not ToolChecker.check_tool('subzy'):
            Logger.warning("subzy not found")
            return

        Logger.header("SUBDOMAIN TAKEOVER CHECK")
        Logger.info("Checking with subzy...")

        output_file = self.output_mgr.get_path('takeover', 'subzy_results.txt')

        try:
            result = subprocess.run(
                ['subzy', 'run', '--targets', str(input_file)],
                capture_output=True,
                text=True,
                timeout=300
            )

            with open(output_file, 'w') as f:
                f.write(result.stdout)

            if result.stdout.strip():
                Logger.warning(f"Possible takeovers found!")
            else:
                Logger.success("No takeover detected")

        except Exception as e:
            Logger.warning(f"Error in subzy: {e}")


class DiffManager:
    """Track changes between scans"""
    
    def __init__(self, output_mgr: OutputManager, domain: str):
        self.output_mgr = output_mgr
        self.domain = domain
        self.results_base = Path('./results')
    
    def find_previous_scan(self) -> Optional[Path]:
        """Find most recent previous scan"""
        domain_scans = sorted([
            d for d in self.results_base.iterdir()
            if d.is_dir() and d.name.startswith(f"{self.domain}_") and d != self.output_mgr.base_dir
        ], reverse=True)
        
        return domain_scans[0] if domain_scans else None
    
    def diff_results(self):
        """Compare with previous scan"""
        Logger.header("DIFF ANALYSIS")
        
        previous = self.find_previous_scan()
        if not previous:
            Logger.info("No previous scan found")
            return
        
        Logger.info(f"Comparing with: {previous.name}")
        
        compare_files = [
            ('subdomains', 'all_subdomains.txt'),
            ('http', 'alive.txt'),
            ('urls', 'urls_clean.txt')
        ]
        
        for category, filename in compare_files:
            current_file = self.output_mgr.get_path(category, filename)
            previous_file = previous / category / filename
            
            if not current_file.exists() or not previous_file.exists():
                continue
            
            with open(current_file, 'r') as f:
                current_lines = set(line.strip() for line in f if line.strip())
            
            with open(previous_file, 'r') as f:
                previous_lines = set(line.strip() for line in f if line.strip())
            
            new_items = current_lines - previous_lines
            removed_items = previous_lines - current_lines
            
            if new_items or removed_items:
                diff_file = self.output_mgr.get_path('diff', f'{filename}.diff')
                with open(diff_file, 'w') as f:
                    if new_items:
                        f.write("# NEW ITEMS\n")
                        f.write('\n'.join(sorted(new_items)) + '\n\n')
                    if removed_items:
                        f.write("# REMOVED ITEMS\n")
                        f.write('\n'.join(sorted(removed_items)) + '\n')
                
                Logger.info(f"{filename}: +{len(new_items)} new, -{len(removed_items)} removed")


class ReportGenerator:
    """Generate comprehensive reports"""
    
    def __init__(self, output_mgr: OutputManager, domain: str):
        self.output_mgr = output_mgr
        self.domain = domain
    
    def generate_markdown_report(self):
        """Generate markdown report"""
        Logger.info("Generating markdown report...")
        
        report_file = self.output_mgr.get_path('reports', 'report.md')
        
        lines = [
            f"# Enumeration Report: {self.domain}",
            f"\n**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n**Scan Directory**: `{self.output_mgr.base_dir}`",
            "\n---\n",
            "## Summary\n"
        ]
        
        # Statistics
        stats = {
            "Subdomains": self.output_mgr.get_path('subdomains', 'all_subdomains.txt'),
            "Resolved Hosts": self.output_mgr.get_path('dns', 'resolved.txt'),
            "Active HTTP": self.output_mgr.get_path('http', 'alive.txt'),
            "URLs Collected": self.output_mgr.get_path('urls', 'urls_clean.txt'),
            "JavaScript Files": self.output_mgr.get_path('js', 'all_js_files.txt'),
        }
        
        for name, path in stats.items():
            if path.exists():
                with open(path, 'r') as f:
                    count = sum(1 for line in f if line.strip())
                lines.append(f"- **{name}**: {count}")
        
        lines.append("\n---\n")
        
        # Vulnerabilities
        vuln_file = self.output_mgr.get_path('vulnerabilities', 'nuclei_results.txt')
        if vuln_file.exists():
            with open(vuln_file, 'r') as f:
                vulns = [line.strip() for line in f if line.strip()]
            
            if vulns:
                lines.append("## 🚨 Vulnerabilities\n")
                for vuln in vulns[:20]:
                    lines.append(f"- {vuln}")
                lines.append("\n---\n")
        
        # Git exposure
        git_file = self.output_mgr.get_path('git', 'exposed_git.txt')
        if git_file.exists():
            with open(git_file, 'r') as f:
                repos = [line.strip() for line in f if line.strip()]
            
            if repos:
                lines.append("## ⚠️ Exposed Git Repositories\n")
                for repo in repos:
                    lines.append(f"- {repo}")
                lines.append("\n---\n")
        
        # Save report
        with open(report_file, 'w') as f:
            f.write('\n'.join(lines))
        
        Logger.success(f"Report: {report_file}")
    
    def generate_json_report(self):
        """Generate JSON report"""
        report = {
            'domain': self.domain,
            'timestamp': datetime.now().isoformat(),
            'statistics': {},
            'findings': {}
        }
        
        stats_files = {
            'subdomains': self.output_mgr.get_path('subdomains', 'all_subdomains.txt'),
            'resolved': self.output_mgr.get_path('dns', 'resolved.txt'),
            'active_http': self.output_mgr.get_path('http', 'alive.txt'),
            'urls': self.output_mgr.get_path('urls', 'urls_clean.txt'),
        }
        
        for key, path in stats_files.items():
            if path.exists():
                with open(path, 'r') as f:
                    report['statistics'][key] = sum(1 for line in f if line.strip())
        
        json_file = self.output_mgr.get_path('reports', 'report.json')
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2)


class WebEnum:
    """Main enumeration orchestrator"""

    def __init__(self, domain: str, output_dir: str = './results', api_config: APIConfig = None):
        self.domain = domain
        self.output_mgr = OutputManager(output_dir, domain)
        self.api_config = api_config or APIConfig()

        # Components
        self.subdomain_enum = SubdomainEnum(domain, self.output_mgr, self.api_config)
        self.dns_resolver = DNSResolver(self.output_mgr)
        self.port_scanner = PortScanner(self.output_mgr)
        self.http_prober = HTTPProber(self.output_mgr)
        self.url_collector = URLCollector(self.output_mgr)
        self.js_analyzer = JSAnalyzer(self.output_mgr)
        self.git_dumper = GitDumper(self.output_mgr)
        self.vuln_scanner = VulnScanner(self.output_mgr)
        self.cloud_detector = CloudDetector(self.output_mgr)
        self.param_discovery = ParameterDiscovery(self.output_mgr)
        self.takeover_checker = TakeoverChecker(self.output_mgr)
        self.diff_manager = DiffManager(self.output_mgr, domain)
        self.report_generator = ReportGenerator(self.output_mgr, domain)

    def run_full_enum(self, skip_screenshots: bool = False, skip_portscan: bool = False, 
                     skip_vuln_scan: bool = False):
        """Run complete enumeration"""
        start_time = time.time()

        Logger.header(f"WEB ENUMERATION: {self.domain}")

        # 1. Subdomain enumeration
        subs_file = self.subdomain_enum.run_all()

        # 2. DNS Resolution
        resolved_file = self.dns_resolver.resolve_with_puredns(subs_file)
        self.dns_resolver.enrich_with_dnsx(resolved_file)

        # 3. Cloud detection
        self.cloud_detector.detect(resolved_file)

        # 4. Port scanning
        if not skip_portscan:
            self.port_scanner.scan_with_sdlookup(resolved_file)

        # 5. HTTP Probing
        alive_file = self.http_prober.probe_with_httpx(resolved_file)

        if not alive_file:
            Logger.error("No active hosts found!")
            return

        self.http_prober.check_urls_with_hakcheckurl(alive_file)

        # 6. Screenshots
        if not skip_screenshots:
            self.http_prober.screenshot_with_gowitness(alive_file)

        # 7. URL Collection
        all_urls = self.url_collector.collect_from_archives(alive_file)

        # 8. Clean URLs
        if all_urls:
            self.url_collector.clean_urls(all_urls)
            clean_urls = self.output_mgr.get_path('urls', 'urls_clean.txt')
            
            # 9. Parameter Analysis
            if clean_urls.exists():
                self.param_discovery.analyze_parameters(clean_urls)
                self.param_discovery.discover_with_arjun(clean_urls)

        # 10. JavaScript Analysis
        self.js_analyzer.analyze_all(alive_file)

        # 11. Git exposure
        self.git_dumper.check_and_dump(alive_file)

        # 12. Vulnerability scanning
        if not skip_vuln_scan:
            self.vuln_scanner.scan_with_nuclei(alive_file)

        # 13. Takeover check
        self.takeover_checker.check_with_subzy(resolved_file)

        # 14. Diff tracking
        self.diff_manager.diff_results()

        # 15. Generate reports
        self.report_generator.generate_markdown_report()
        self.report_generator.generate_json_report()

        # Summary
        elapsed = time.time() - start_time
        self._print_summary(elapsed)

    def _print_summary(self, elapsed_time: float):
        """Print final summary"""
        Logger.header("SUMMARY")

        summary = {
            "Subdomains": self.output_mgr.get_path('subdomains', 'all_subdomains.txt'),
            "Resolved": self.output_mgr.get_path('dns', 'resolved.txt'),
            "Active HTTP": self.output_mgr.get_path('http', 'alive.txt'),
            "URLs": self.output_mgr.get_path('urls', 'urls_clean.txt'),
        }

        for name, path in summary.items():
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        count = sum(1 for line in f if line.strip())
                    Logger.info(f"{name}: {count}")
                except:
                    pass

        Logger.success(f"\nTime: {elapsed_time/60:.2f} minutes")
        Logger.success(f"Results: {self.output_mgr.base_dir}")
        Logger.info(f"Report: {self.output_mgr.get_path('reports', 'report.md')}")


def configure_api_keys():
    """Interactive API key configuration"""
    Logger.header("API CONFIGURATION")
    
    api_config = APIConfig()
    
    services = {
        'virustotal': 'VirusTotal',
        'securitytrails': 'SecurityTrails',
        'certspotter': 'CertSpotter',
        'shodan': 'Shodan'
    }
    
    for key, name in services.items():
        current = api_config.get_key(key)
        if current:
            Logger.info(f"{name}: configured")
            update = input(f"  Update? [y/N]: ").strip().lower()
            if update != 'y':
                continue
        
        api_key = input(f"  {name} API key (Enter to skip): ").strip()
        if api_key:
            api_config.save_key(key, api_key)
            Logger.success(f"{name} saved")
    
    Logger.success(f"Config: {api_config.config_file}")


def main():
    banner = f"""
{Colors.OKCYAN}{Colors.BOLD}
╦ ╦┌─┐┌┐ ╔═╗┌┐┌┬ ┬┌┬┐
║║║├┤ ├┴┐║╣ ││││ ││││
╚╩╝└─┘└─┘╚═╝┘└┘└─┘┴ ┴
{Colors.ENDC}
{Colors.OKGREEN}Modern Web Enumeration Framework{Colors.ENDC}
{Colors.WARNING}Advanced reconnaissance for security professionals{Colors.ENDC}
"""

    print(banner)

    parser = argparse.ArgumentParser(
        description='WebEnum - Advanced web enumeration',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-d', '--domain', help='Target domain')
    parser.add_argument('-o', '--output', default='./results', help='Output directory')
    parser.add_argument('--skip-screenshots', action='store_true', help='Skip screenshots')
    parser.add_argument('--skip-portscan', action='store_true', help='Skip port scan')
    parser.add_argument('--skip-vuln-scan', action='store_true', help='Skip vulnerability scan')
    parser.add_argument('--check-tools', action='store_true', help='Check tools')
    parser.add_argument('--configure-api', action='store_true', help='Configure API keys')

    args = parser.parse_args()

    if args.configure_api:
        configure_api_keys()
        sys.exit(0)

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

        sys.exit(0)

    if not args.domain:
        parser.print_help()
        sys.exit(1)

    # Check critical tools
    critical = ['subfinder', 'httpx', 'dnsx']
    missing = [t for t in critical if not ToolChecker.check_tool(t)]

    if missing:
        Logger.error(f"Missing critical tools: {', '.join(missing)}")
        sys.exit(1)

    # Run enumeration
    try:
        enum = WebEnum(args.domain, args.output)
        enum.run_full_enum(
            skip_screenshots=args.skip_screenshots,
            skip_portscan=args.skip_portscan,
            skip_vuln_scan=args.skip_vuln_scan
        )
    except KeyboardInterrupt:
        Logger.warning("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        Logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()