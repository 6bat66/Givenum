#!/usr/bin/env python3
"""
WebEnum Enhanced - Advanced Web Enumeration Tool
Enhanced with API integration, certificate transparency, vulnerability scanning, and more
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
import base64

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
        'subdomain': ['subfinder', 'assetfinder', 'findomain', 'amass'],
        'dns': ['dnsx', 'puredns', 'massdns'],
        'http': ['httpx'],
        'url_collect': ['gau', 'waybackurls', 'hakrawler', 'getJS'],
        'utils': ['anew', 'uro', 'unfurl', 'qsreplace'],
        'scanning': ['nmap', 'nuclei', 'nikto'],
        'fuzzing': ['ffuf', 'dirsearch'],
        'optional': ['gowitness', 'subzy', 'subjack', 'kxss', 'dalfox', 'sqlmap', 'arjun', 'paramspider']
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

        # Enhanced directory structure
        self.dirs = {
            'root': self.base_dir,
            'subdomains': self.base_dir / 'subdomains',
            'dns': self.base_dir / 'dns',
            'http': self.base_dir / 'http',
            'urls': self.base_dir / 'urls',
            'js': self.base_dir / 'js',
            'screenshots': self.base_dir / 'screenshots',
            'takeover': self.base_dir / 'takeover',
            'ports': self.base_dir / 'ports',
            'vulnerabilities': self.base_dir / 'vulnerabilities',
            'fuzzing': self.base_dir / 'fuzzing',
            'parameters': self.base_dir / 'parameters',
            'git': self.base_dir / 'git',
            'cloud': self.base_dir / 'cloud',
            'archives': self.base_dir / 'archives',
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
                    # Handle wildcard and multiple domains
                    for domain in name.split('\n'):
                        domain = domain.strip().replace('*', '').replace('.', '', 1) if domain.startswith('*.') else domain.strip()
                        if domain and domain.endswith(self.domain):
                            domains.add(domain)
                
                output_file = self.output_mgr.get_path('subdomains', 'crtsh.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(domains)) + '\n')
                
                Logger.success(f"crt.sh: {len(domains)} domains found")
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
                
                Logger.success(f"CertSpotter: {len(domains)} domains found")
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
            Logger.warning("VirusTotal API key not configured, skipping...")
            return set()
        
        Logger.info("Querying VirusTotal...")
        
        try:
            url = f"https://www.virustotal.com/vtapi/v2/domain/report"
            params = {'apikey': api_key, 'domain': self.domain}
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                domains = set()
                
                for subdomain in data.get('subdomains', []):
                    domains.add(subdomain)
                
                output_file = self.output_mgr.get_path('api_data', 'virustotal.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(domains)) + '\n')
                
                # Save full JSON
                json_file = self.output_mgr.get_path('api_data', 'virustotal.json')
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                Logger.success(f"VirusTotal: {len(domains)} domains found")
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
                
                Logger.success(f"AlienVault: {len(domains)} domains found")
                return domains
                
        except Exception as e:
            Logger.error(f"Error querying AlienVault: {e}")
        
        return set()
    
    def query_securitytrails(self) -> Set[str]:
        """Query SecurityTrails API"""
        api_key = self.api_config.get_key('securitytrails')
        if not api_key:
            Logger.warning("SecurityTrails API key not configured, skipping...")
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
                
                Logger.success(f"SecurityTrails: {len(domains)} domains found")
                return domains
                
        except Exception as e:
            Logger.error(f"Error querying SecurityTrails: {e}")
        
        return set()


class SubdomainEnum:
    """Enhanced subdomain enumeration"""

    def __init__(self, domain: str, output_mgr: OutputManager, api_config: APIConfig):
        self.domain = domain
        self.output_mgr = output_mgr
        self.api_config = api_config
        self.tools = {
            'subfinder': ['subfinder', '-d', domain, '-all', '-silent'],
            'assetfinder': ['assetfinder', '--subs-only', domain],
            'findomain': ['findomain', '-t', domain, '-q'],
            'amass': ['amass', 'enum', '-passive', '-d', domain, '-silent']
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
                timeout=600  # Increased timeout for amass
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
        """Run all enumeration tools including APIs and CT logs"""
        Logger.header("SUBDOMAIN ENUMERATION")

        all_subs = set()

        # Traditional tools
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.run_tool, name, cmd): name
                for name, cmd in self.tools.items()
            }

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
    """Enhanced DNS resolution"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def resolve_with_puredns(self, input_file: Path) -> Optional[Path]:
        """Resolve subdomains using puredns"""
        if not ToolChecker.check_tool('puredns'):
            Logger.warning("puredns not found, skipping resolution...")
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

            # Count results
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
            Logger.warning("dnsx not found, skipping enrichment...")
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

        Logger.success("DNS records enriched")


class PortScanner:
    """Port scanning functionality"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def scan_with_nmap(self, input_file: Path, top_ports: int = 1000):
        """Scan ports with Nmap"""
        if not ToolChecker.check_tool('nmap'):
            Logger.warning("nmap not found, skipping port scan...")
            return
        
        Logger.header("PORT SCANNING")
        Logger.info(f"Scanning top {top_ports} ports with nmap...")
        
        output_file = self.output_mgr.get_path('ports', 'nmap_scan.txt')
        output_xml = self.output_mgr.get_path('ports', 'nmap_scan.xml')
        
        try:
            # Read targets
            with open(input_file, 'r') as f:
                targets = [line.strip() for line in f if line.strip()]
            
            # Create target list file
            target_file = self.output_mgr.get_path('ports', 'targets.txt')
            with open(target_file, 'w') as f:
                f.write('\n'.join(targets))
            
            # Run nmap
            cmd = [
                'nmap',
                '-iL', str(target_file),
                f'--top-ports={top_ports}',
                '-T4',
                '--open',
                '-oN', str(output_file),
                '-oX', str(output_xml)
            ]
            
            subprocess.run(cmd, timeout=3600, check=True)
            Logger.success(f"Port scan complete, results in {output_file.name}")
            
        except Exception as e:
            Logger.error(f"Error in nmap scan: {e}")


class HTTPProber:
    """Enhanced HTTP probing"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def probe_with_httpx(self, input_file: Path) -> Optional[Path]:
        """Probe for HTTP services with enhanced options"""
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

            # Extract just URLs
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

    def detect_waf(self, input_file: Path):
        """Detect WAF/CDN"""
        Logger.info("Detecting WAF/CDN...")
        
        output_file = self.output_mgr.get_path('http', 'waf_detected.txt')
        
        try:
            # Using httpx with CDN detection
            cmd = [
                'httpx',
                '-l', str(input_file),
                '-silent',
                '-cdn',
                '-waf',
                '-o', str(output_file)
            ]
            
            subprocess.run(cmd, timeout=300)
            Logger.success("WAF/CDN detection complete")
            
        except Exception as e:
            Logger.error(f"Error in WAF detection: {e}")

    def screenshot_with_gowitness(self, input_file: Path):
        """Take screenshots with gowitness"""
        if not ToolChecker.check_tool('gowitness'):
            Logger.warning("gowitness not found, skipping screenshots...")
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


class CloudDetector:
    """Detect cloud services (AWS, Azure, GCP)"""
    
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
        """Detect cloud services from hosts"""
        Logger.header("CLOUD SERVICE DETECTION")
        
        with open(input_file, 'r') as f:
            hosts = [line.strip() for line in f if line.strip()]
        
        cloud_services = {'AWS': [], 'Azure': [], 'GCP': [], 'Other': []}
        
        for host in hosts:
            found = False
            for cloud, patterns in self.cloud_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, host, re.IGNORECASE):
                        cloud_services[cloud].append(host)
                        found = True
                        break
                if found:
                    break
        
        # Save results
        for cloud, services in cloud_services.items():
            if services:
                output_file = self.output_mgr.get_path('cloud', f'{cloud.lower()}_services.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(services) + '\n')
                Logger.success(f"{cloud}: {len(services)} services detected")


class VulnScanner:
    """Vulnerability scanning with Nuclei"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def scan_with_nuclei(self, input_file: Path, severity: str = 'medium,high,critical'):
        """Scan with Nuclei"""
        if not ToolChecker.check_tool('nuclei'):
            Logger.warning("nuclei not found, skipping vulnerability scan...")
            return
        
        Logger.header("VULNERABILITY SCANNING")
        Logger.info("Scanning with Nuclei (this may take a while)...")
        
        output_file = self.output_mgr.get_path('vulnerabilities', 'nuclei_results.txt')
        json_file = self.output_mgr.get_path('vulnerabilities', 'nuclei_results.json')
        
        try:
            # Update templates first
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
            Logger.error(f"Error in Nuclei scan: {e}")


class URLCollector:
    """Enhanced URL collection"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def collect_from_archives(self, input_file: Path) -> Set[str]:
        """Collect URLs from web archives"""
        Logger.header("URL COLLECTION - ARCHIVES")

        all_urls = set()

        # GAU
        if ToolChecker.check_tool('gau'):
            Logger.info("Running gau...")
            gau_file = self.output_mgr.get_path('urls', 'gau.txt')

            try:
                with open(input_file, 'r') as f:
                    domains = [line.strip() for line in f if line.strip()]

                result = subprocess.run(
                    ['gau'] + domains,
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

    def crawl_live(self, input_file: Path) -> Set[str]:
        """Crawl live sites"""
        Logger.header("URL COLLECTION - LIVE CRAWL")

        all_urls = set()

        if ToolChecker.check_tool('hakrawler'):
            Logger.info("Running hakrawler...")
            hakrawler_file = self.output_mgr.get_path('urls', 'hakrawler.txt')

            try:
                with open(input_file, 'r') as f:
                    urls = f.read()

                result = subprocess.run(
                    ['hakrawler', '-depth', '3', '-plain'],
                    input=urls,
                    capture_output=True,
                    text=True,
                    timeout=900
                )

                crawled = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(crawled)

                with open(hakrawler_file, 'w') as f:
                    f.write('\n'.join(sorted(crawled)) + '\n')

                Logger.success(f"hakrawler: {len(crawled)} URLs")

            except Exception as e:
                Logger.error(f"Error in hakrawler: {e}")

        return all_urls

    def collect_js_files(self, input_file: Path) -> Optional[Path]:
        """Collect JavaScript files"""
        Logger.header("JAVASCRIPT FILE COLLECTION")

        if not ToolChecker.check_tool('getJS'):
            Logger.warning("getJS not found, skipping...")
            return None

        Logger.info("Collecting JavaScript files...")
        js_file = self.output_mgr.get_path('js', 'js_files.txt')

        try:
            with open(input_file, 'r') as f:
                urls = f.read()

            result = subprocess.run(
                ['getJS', '--input', '-', '--complete'],
                input=urls,
                capture_output=True,
                text=True,
                timeout=600
            )

            js_urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())

            with open(js_file, 'w') as f:
                f.write('\n'.join(sorted(js_urls)) + '\n')

            Logger.success(f"Collected {len(js_urls)} JavaScript files")
            return js_file

        except Exception as e:
            Logger.error(f"Error in getJS: {e}")
            return None

    def extract_from_js(self, js_file: Path) -> Set[str]:
        """Extract URLs from JavaScript files"""
        Logger.info("Extracting endpoints from JavaScript...")

        # Simple regex-based extraction
        url_pattern = re.compile(r'["\']((https?://|/)[^"\']+)["\']')
        extracted = set()

        try:
            with open(js_file, 'r') as f:
                js_urls = [line.strip() for line in f if line.strip()]

            for js_url in js_urls[:50]:  # Limit to prevent excessive requests
                try:
                    response = requests.get(js_url, timeout=10, verify=False)
                    matches = url_pattern.findall(response.text)
                    for match in matches:
                        extracted.add(match[0])
                except:
                    pass

            Logger.success(f"Extracted {len(extracted)} URLs from JavaScript")
            return extracted

        except Exception as e:
            Logger.error(f"Error extracting from JS: {e}")
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
            Logger.warning("uro not found, skipping cleaning...")
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


class ParameterDiscovery:
    """Discover parameters in URLs and test for vulnerabilities"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def discover_parameters(self, url_file: Path):
        """Discover parameters using Arjun"""
        if not ToolChecker.check_tool('arjun'):
            Logger.warning("arjun not found, skipping parameter discovery...")
            return
        
        Logger.header("PARAMETER DISCOVERY")
        Logger.info("Discovering hidden parameters with Arjun...")
        
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
        """Analyze parameters from URLs"""
        Logger.info("Analyzing URL parameters...")
        
        params = {}
        interesting_params = set()
        
        # Patterns for interesting parameters
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
                        
                        # Check if interesting
                        param_lower = param.lower()
                        if any(pattern in param_lower for pattern in sensitive_patterns):
                            interesting_params.add(param)
            
            # Save all parameters
            all_params_file = self.output_mgr.get_path('parameters', 'all_parameters.txt')
            with open(all_params_file, 'w') as f:
                for param, count in sorted(params.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"{param}: {count}\n")
            
            # Save interesting parameters
            interesting_file = self.output_mgr.get_path('parameters', 'interesting_parameters.txt')
            with open(interesting_file, 'w') as f:
                f.write('\n'.join(sorted(interesting_params)))
            
            Logger.success(f"Found {len(params)} unique parameters, {len(interesting_params)} interesting")
            
        except Exception as e:
            Logger.error(f"Error analyzing parameters: {e}")


class FuzzingEngine:
    """Directory and file fuzzing"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def fuzz_with_ffuf(self, url_file: Path, wordlist: Optional[Path] = None):
        """Fuzz directories with ffuf"""
        if not ToolChecker.check_tool('ffuf'):
            Logger.warning("ffuf not found, skipping fuzzing...")
            return
        
        Logger.header("DIRECTORY FUZZING")
        
        # Default wordlist
        if not wordlist:
            wordlist = Path.home() / '.config' / 'webenum' / 'wordlists' / 'common.txt'
            if not wordlist.exists():
                Logger.warning("No wordlist specified and default not found")
                return
        
        Logger.info(f"Fuzzing with ffuf using {wordlist.name}...")
        
        try:
            with open(url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            # Limit to first 10 URLs to prevent excessive scanning
            for idx, url in enumerate(urls[:10], 1):
                Logger.info(f"Fuzzing [{idx}/10]: {url}")
                
                output_file = self.output_mgr.get_path('fuzzing', f'ffuf_{idx}.json')
                
                cmd = [
                    'ffuf',
                    '-u', f'{url}/FUZZ',
                    '-w', str(wordlist),
                    '-mc', '200,204,301,302,307,401,403',
                    '-fs', '0',
                    '-t', '50',
                    '-o', str(output_file),
                    '-of', 'json',
                    '-s'
                ]
                
                subprocess.run(cmd, timeout=600, stderr=subprocess.DEVNULL)
            
            Logger.success("Fuzzing complete")
            
        except Exception as e:
            Logger.error(f"Error in ffuf: {e}")


class GitDumper:
    """Attempt to dump exposed .git repositories"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def check_git_exposure(self, url_file: Path):
        """Check for exposed .git directories"""
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


class DiffManager:
    """Track changes between scans"""
    
    def __init__(self, output_mgr: OutputManager, domain: str):
        self.output_mgr = output_mgr
        self.domain = domain
        self.results_base = Path('./results')
    
    def find_previous_scan(self) -> Optional[Path]:
        """Find the most recent previous scan for the domain"""
        domain_scans = sorted([
            d for d in self.results_base.iterdir()
            if d.is_dir() and d.name.startswith(f"{self.domain}_") and d != self.output_mgr.base_dir
        ], reverse=True)
        
        return domain_scans[0] if domain_scans else None
    
    def diff_results(self):
        """Compare current scan with previous scan"""
        Logger.header("DIFF ANALYSIS")
        
        previous = self.find_previous_scan()
        if not previous:
            Logger.info("No previous scan found for comparison")
            return
        
        Logger.info(f"Comparing with: {previous.name}")
        
        # Files to compare
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
            
            # Load files
            with open(current_file, 'r') as f:
                current_lines = set(line.strip() for line in f if line.strip())
            
            with open(previous_file, 'r') as f:
                previous_lines = set(line.strip() for line in f if line.strip())
            
            # Calculate diff
            new_items = current_lines - previous_lines
            removed_items = previous_lines - current_lines
            
            if new_items or removed_items:
                # Save diff
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
        
        # Count items
        stats = {
            "Subdomains": self.output_mgr.get_path('subdomains', 'all_subdomains.txt'),
            "Resolved Hosts": self.output_mgr.get_path('dns', 'resolved.txt'),
            "Active HTTP": self.output_mgr.get_path('http', 'alive.txt'),
            "URLs Collected": self.output_mgr.get_path('urls', 'urls_clean.txt'),
            "JavaScript Files": self.output_mgr.get_path('js', 'js_files.txt'),
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
                lines.append("## 🚨 Vulnerabilities Found\n")
                for vuln in vulns:
                    lines.append(f"- {vuln}")
                lines.append("\n---\n")
        
        # Exposed Git
        git_file = self.output_mgr.get_path('git', 'exposed_git.txt')
        if git_file.exists():
            with open(git_file, 'r') as f:
                git_repos = [line.strip() for line in f if line.strip()]
            
            if git_repos:
                lines.append("## ⚠️ Exposed Git Repositories\n")
                for repo in git_repos:
                    lines.append(f"- {repo}")
                lines.append("\n---\n")
        
        # Cloud Services
        cloud_dirs = self.output_mgr.get_path('cloud', '')
        if cloud_dirs.exists():
            cloud_files = list(cloud_dirs.glob('*.txt'))
            if cloud_files:
                lines.append("## ☁️ Cloud Services\n")
                for cloud_file in cloud_files:
                    with open(cloud_file, 'r') as f:
                        count = sum(1 for line in f if line.strip())
                    cloud_name = cloud_file.stem.replace('_services', '').upper()
                    lines.append(f"- **{cloud_name}**: {count}")
                lines.append("\n---\n")
        
        # Interesting Parameters
        params_file = self.output_mgr.get_path('parameters', 'interesting_parameters.txt')
        if params_file.exists():
            with open(params_file, 'r') as f:
                params = [line.strip() for line in f if line.strip()]
            
            if params:
                lines.append("## 🔍 Interesting Parameters\n")
                for param in params[:20]:
                    lines.append(f"- `{param}`")
                lines.append("\n---\n")
        
        # Save report
        with open(report_file, 'w') as f:
            f.write('\n'.join(lines))
        
        Logger.success(f"Report saved: {report_file}")
    
    def generate_json_report(self):
        """Generate JSON report"""
        Logger.info("Generating JSON report...")
        
        report = {
            'domain': self.domain,
            'timestamp': datetime.now().isoformat(),
            'scan_directory': str(self.output_mgr.base_dir),
            'statistics': {},
            'findings': {}
        }
        
        # Statistics
        stats_files = {
            'subdomains': self.output_mgr.get_path('subdomains', 'all_subdomains.txt'),
            'resolved_hosts': self.output_mgr.get_path('dns', 'resolved.txt'),
            'active_http': self.output_mgr.get_path('http', 'alive.txt'),
            'urls': self.output_mgr.get_path('urls', 'urls_clean.txt'),
        }
        
        for key, path in stats_files.items():
            if path.exists():
                with open(path, 'r') as f:
                    report['statistics'][key] = sum(1 for line in f if line.strip())
        
        # Findings
        vuln_file = self.output_mgr.get_path('vulnerabilities', 'nuclei_results.json')
        if vuln_file.exists():
            with open(vuln_file, 'r') as f:
                report['findings']['vulnerabilities'] = [json.loads(line) for line in f]
        
        # Save
        json_file = self.output_mgr.get_path('reports', 'report.json')
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        Logger.success(f"JSON report saved: {json_file}")


class TakeoverChecker:
    """Check for subdomain takeover"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def check_with_subzy(self, input_file: Path):
        """Check for takeover with subzy"""
        if not ToolChecker.check_tool('subzy'):
            Logger.warning("subzy not found, skipping takeover check...")
            return

        Logger.header("SUBDOMAIN TAKEOVER CHECK")
        Logger.info("Checking for takeover with subzy...")

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
                Logger.warning(f"Possible takeovers found! See {output_file.name}")
            else:
                Logger.success("No takeover detected")

        except Exception as e:
            Logger.warning(f"Error in subzy: {e}")


class WebEnum:
    """Enhanced main enumeration class"""

    def __init__(self, domain: str, output_dir: str = './results', api_config: APIConfig = None):
        self.domain = domain
        self.output_mgr = OutputManager(output_dir, domain)
        self.api_config = api_config or APIConfig()

        # Components
        self.subdomain_enum = SubdomainEnum(domain, self.output_mgr, self.api_config)
        self.dns_resolver = DNSResolver(self.output_mgr)
        self.http_prober = HTTPProber(self.output_mgr)
        self.port_scanner = PortScanner(self.output_mgr)
        self.url_collector = URLCollector(self.output_mgr)
        self.vuln_scanner = VulnScanner(self.output_mgr)
        self.cloud_detector = CloudDetector(self.output_mgr)
        self.param_discovery = ParameterDiscovery(self.output_mgr)
        self.fuzzing = FuzzingEngine(self.output_mgr)
        self.git_dumper = GitDumper(self.output_mgr)
        self.takeover_checker = TakeoverChecker(self.output_mgr)
        self.diff_manager = DiffManager(self.output_mgr, domain)
        self.report_generator = ReportGenerator(self.output_mgr, domain)

    def run_full_enum(self, skip_screenshots: bool = False, skip_portscan: bool = False, 
                     skip_vuln_scan: bool = False, skip_fuzzing: bool = True):
        """Run complete enhanced enumeration"""
        start_time = time.time()

        Logger.header(f"ENHANCED WEB ENUMERATION: {self.domain}")

        # 1. Subdomain enumeration (with APIs and CT logs)
        subs_file = self.subdomain_enum.run_all()

        # 2. DNS Resolution
        resolved_file = self.dns_resolver.resolve_with_puredns(subs_file)
        self.dns_resolver.enrich_with_dnsx(resolved_file)

        # 3. Cloud detection
        self.cloud_detector.detect(resolved_file)

        # 4. Port scanning (optional)
        if not skip_portscan:
            self.port_scanner.scan_with_nmap(resolved_file, top_ports=100)

        # 5. HTTP Probing
        alive_file = self.http_prober.probe_with_httpx(resolved_file)

        if not alive_file:
            Logger.error("No active hosts found! Aborting...")
            return

        # 6. WAF Detection
        self.http_prober.detect_waf(alive_file)

        # 7. Screenshots (optional)
        if not skip_screenshots:
            self.http_prober.screenshot_with_gowitness(alive_file)
        else:
            Logger.info("Skipping screenshots (--skip-screenshots)")

        # 8. URL Collection
        all_urls = set()

        # 8a. Historical archives
        archive_urls = self.url_collector.collect_from_archives(alive_file)
        all_urls.update(archive_urls)

        # 8b. Live crawling
        crawl_urls = self.url_collector.crawl_live(alive_file)
        all_urls.update(crawl_urls)

        # 8c. JavaScript
        js_file = self.url_collector.collect_js_files(alive_file)
        if js_file:
            js_urls = self.url_collector.extract_from_js(js_file)
            all_urls.update(js_urls)

        # 9. URL Cleaning
        if all_urls:
            self.url_collector.clean_urls(all_urls)
            clean_urls = self.output_mgr.get_path('urls', 'urls_clean.txt')
            
            # 10. Parameter Analysis
            self.param_discovery.analyze_parameters(clean_urls)
            self.param_discovery.discover_parameters(clean_urls)

        # 11. Git exposure check
        self.git_dumper.check_git_exposure(alive_file)

        # 12. Directory fuzzing (optional, disabled by default)
        if not skip_fuzzing:
            self.fuzzing.fuzz_with_ffuf(alive_file)

        # 13. Vulnerability scanning (optional)
        if not skip_vuln_scan:
            self.vuln_scanner.scan_with_nuclei(alive_file)

        # 14. Takeover check
        self.takeover_checker.check_with_subzy(resolved_file)

        # 15. Diff with previous scan
        self.diff_manager.diff_results()

        # 16. Generate reports
        self.report_generator.generate_markdown_report()
        self.report_generator.generate_json_report()

        # Final summary
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
        Logger.info(f"Report: {self.output_mgr.get_path('reports', 'report.md')}")


def print_installation_help():
    """Print helpful installation instructions"""
    system = platform.system()
    
    Logger.header("INSTALLATION HELP")
    
    print("""
Enhanced WebEnum requires additional tools:

Core Tools (required):
  - subfinder, assetfinder, findomain, amass
  - dnsx, puredns, massdns
  - httpx
  - gau, waybackurls, hakrawler, getJS
  - anew, uro

Scanning Tools (recommended):
  - nuclei (vulnerability scanning)
  - nmap (port scanning)
  - ffuf (fuzzing)

Optional Tools:
  - gowitness (screenshots)
  - arjun (parameter discovery)
  - subzy, subjack (takeover detection)

Installation:
  1. Run: ./install_tools_enhanced.sh
  2. Configure API keys: webenum_enhanced.py --configure-api

API Keys (optional but recommended):
  - VirusTotal: https://www.virustotal.com/gui/join-us
  - SecurityTrails: https://securitytrails.com/
  - CertSpotter: https://sslmate.com/certspotter/
""")


def configure_api_keys():
    """Interactive API key configuration"""
    Logger.header("API KEY CONFIGURATION")
    
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
            Logger.info(f"{name}: {'*' * 20} (configured)")
            update = input(f"  Update? [y/N]: ").strip().lower()
            if update != 'y':
                continue
        
        api_key = input(f"  Enter {name} API key (or press Enter to skip): ").strip()
        if api_key:
            api_config.save_key(key, api_key)
            Logger.success(f"{name} API key saved")
    
    Logger.success(f"Configuration saved to: {api_config.config_file}")


def main():
    banner = f"""
{Colors.OKCYAN}{Colors.BOLD}
╦ ╦┌─┐┌┐ ╔═╗┌┐┌┬ ┬┌┬┐  ╔═╗┌┐┌┬ ┬┌─┐┌┐┌┌─┐┌─┐┌┬┐
║║║├┤ ├┴┐║╣ ││││ ││││  ║╣ │││├─┤├─┤││││  ├┤  ││
╚╩╝└─┘└─┘╚═╝┘└┘└─┘┴ ┴  ╚═╝┘└┘┴ ┴┴ ┴┘└┘└─┘└─┘─┴┘
{Colors.ENDC}
{Colors.OKGREEN}Enhanced Web Enumeration Tool v2.0{Colors.ENDC}
{Colors.WARNING}Features: API Integration, CT Logs, Vuln Scanning, Cloud Detection{Colors.ENDC}
"""

    print(banner)

    parser = argparse.ArgumentParser(
        description='WebEnum Enhanced - Advanced web enumeration tool',
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
        '--skip-portscan',
        action='store_true',
        help='Skip port scanning'
    )

    parser.add_argument(
        '--skip-vuln-scan',
        action='store_true',
        help='Skip vulnerability scanning with Nuclei'
    )

    parser.add_argument(
        '--enable-fuzzing',
        action='store_true',
        help='Enable directory fuzzing (disabled by default)'
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

    parser.add_argument(
        '--configure-api',
        action='store_true',
        help='Configure API keys'
    )

    args = parser.parse_args()

    # Configure API keys
    if args.configure_api:
        configure_api_keys()
        sys.exit(0)

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
            Logger.info("To install missing tools, run: ./install_tools_enhanced.sh")
            Logger.info("For detailed instructions, run: python3 webenum_enhanced.py --install-help")

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
        Logger.info("Run: ./install_tools_enhanced.sh")
        Logger.info("Or: python3 webenum_enhanced.py --install-help")
        sys.exit(1)

    # Start enumeration
    try:
        enum = WebEnum(args.domain, args.output)
        enum.run_full_enum(
            skip_screenshots=args.skip_screenshots,
            skip_portscan=args.skip_portscan,
            skip_vuln_scan=args.skip_vuln_scan,
            skip_fuzzing=not args.enable_fuzzing
        )
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