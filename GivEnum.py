#!/usr/bin/env python3
"""
GivEnum - Advanced Web Enumeration Framework
Modern reconnaissance tool with comprehensive discovery capabilities
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
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs
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


class Logger:
    """Logging with colors"""

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
    """API configuration management"""
    
    def __init__(self):
        self.config_file = Path.home() / '.config' / 'givenum' / 'api_keys.json'
        self.keys = self.load_keys()
    
    def load_keys(self) -> Dict[str, str]:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_key(self, service: str, key: str):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.keys[service] = key
        with open(self.config_file, 'w') as f:
            json.dump(self.keys, f, indent=2)
    
    def get_key(self, service: str) -> Optional[str]:
        return self.keys.get(service)


class ToolChecker:
    """Check installed tools"""

    TOOLS = {
        'subdomain': ['subfinder', 'assetfinder', 'findomain', 'amass', 'chaos'],
        'dns': ['dnsx', 'puredns', 'massdns', 'shuffledns'],
        'http': ['httpx', 'hakcheckurl'],
        'ports': ['sdlookup'],  # Using sdlookup instead of nmap
        'url_collect': ['xurlfind3r', 'katana', 'gau', 'waybackurls', 'gospider'],
        'js': ['jsubfinder', 'subjs', 'getallurls', 'linkfinder'],
        'utils': ['anew', 'uro', 'unfurl', 'qsreplace', 'freq'],
        'git': ['goop', 'trufflehog', 'git-dumper'],
        'scanning': ['nuclei', 'jaeles', 'nikto'],
        'fuzzing': ['ffuf', 'feroxbuster', 'gobuster'],
        'analysis': ['webanalyze', 'retire'],
        'optional': ['gowitness', 'aquatone', 'eyewitness', 'subzy', 'dalfox', 'arjun', 'x8']
    }

    @staticmethod
    def check_tool(tool: str) -> bool:
        return shutil.which(tool) is not None

    @classmethod
    def check_all(cls, check_optional: bool = False) -> Dict[str, List[str]]:
        missing = []
        available = []

        for category, tools in cls.TOOLS.items():
            if category == 'optional' and not check_optional:
                continue

            for tool in tools:
                if cls.check_tool(tool):
                    available.append(tool)
                else:
                    missing.append(tool)

        return {'available': available, 'missing': missing}


class OutputManager:
    """Manage output structure"""

    def __init__(self, base_dir: str, domain: str):
        self.domain = domain
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = Path(base_dir) / f"{domain}_{self.timestamp}"

        self.dirs = {
            'root': self.base_dir,
            'subdomains': self.base_dir / 'subdomains',
            'dns': self.base_dir / 'dns',
            'http': self.base_dir / 'http',
            'ports': self.base_dir / 'ports',
            'urls': self.base_dir / 'urls',
            'js': self.base_dir / 'js',
            'secrets': self.base_dir / 'secrets',
            'screenshots': self.base_dir / 'screenshots',
            'tech': self.base_dir / 'tech',
            'vulnerabilities': self.base_dir / 'vulnerabilities',
            'parameters': self.base_dir / 'parameters',
            'fuzzing': self.base_dir / 'fuzzing',
            'git': self.base_dir / 'git',
            'cloud': self.base_dir / 'cloud',
            'api_data': self.base_dir / 'api_data',
            'diff': self.base_dir / 'diff',
            'reports': self.base_dir / 'reports',
            'logs': self.base_dir / 'logs',
        }

        self._create_structure()

    def _create_structure(self):
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        Logger.success(f"Output directory: {self.base_dir}")

    def get_path(self, category: str, filename: str) -> Path:
        return self.dirs[category] / filename


class SubdomainEnum:
    """Comprehensive subdomain enumeration"""

    def __init__(self, domain: str, output_mgr: OutputManager, api_config: APIConfig):
        self.domain = domain
        self.output_mgr = output_mgr
        self.api_config = api_config
        
    def run_subfinder(self) -> Set[str]:
        """Run subfinder with all sources"""
        if not ToolChecker.check_tool('subfinder'):
            return set()
        
        Logger.info("Running subfinder...")
        output_file = self.output_mgr.get_path('subdomains', 'subfinder.txt')
        
        try:
            cmd = ['subfinder', '-d', self.domain, '-all', '-silent', '-o', str(output_file)]
            subprocess.run(cmd, timeout=600, check=True)
            
            with open(output_file, 'r') as f:
                subs = set(line.strip() for line in f if line.strip())
            
            Logger.success(f"subfinder: {len(subs)} subdomains")
            return subs
        except Exception as e:
            Logger.error(f"subfinder error: {e}")
            return set()
    
    def run_assetfinder(self) -> Set[str]:
        """Run assetfinder"""
        if not ToolChecker.check_tool('assetfinder'):
            return set()
        
        Logger.info("Running assetfinder...")
        output_file = self.output_mgr.get_path('subdomains', 'assetfinder.txt')
        
        try:
            result = subprocess.run(
                ['assetfinder', '--subs-only', self.domain],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            subs = set(line.strip() for line in result.stdout.split('\n') if line.strip())
            
            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(subs)) + '\n')
            
            Logger.success(f"assetfinder: {len(subs)} subdomains")
            return subs
        except Exception as e:
            Logger.error(f"assetfinder error: {e}")
            return set()
    
    def run_amass(self) -> Set[str]:
        """Run amass passive"""
        if not ToolChecker.check_tool('amass'):
            return set()
        
        Logger.info("Running amass (passive)...")
        output_file = self.output_mgr.get_path('subdomains', 'amass.txt')
        
        try:
            cmd = ['amass', 'enum', '-passive', '-d', self.domain, '-o', str(output_file), '-silent']
            subprocess.run(cmd, timeout=900, check=True)
            
            with open(output_file, 'r') as f:
                subs = set(line.strip() for line in f if line.strip())
            
            Logger.success(f"amass: {len(subs)} subdomains")
            return subs
        except Exception as e:
            Logger.error(f"amass error: {e}")
            return set()
    
    def query_crtsh(self) -> Set[str]:
        """Query crt.sh CT logs"""
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
                        domain = domain.strip().replace('*', '')
                        if domain and domain.endswith(self.domain):
                            domains.add(domain)
                
                output_file = self.output_mgr.get_path('subdomains', 'crtsh.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(domains)) + '\n')
                
                Logger.success(f"crt.sh: {len(domains)} subdomains")
                return domains
        except Exception as e:
            Logger.error(f"crt.sh error: {e}")
        
        return set()
    
    def query_virustotal(self) -> Set[str]:
        """Query VirusTotal API"""
        api_key = self.api_config.get_key('virustotal')
        if not api_key:
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
                
                Logger.success(f"VirusTotal: {len(domains)} subdomains")
                return domains
        except Exception as e:
            Logger.error(f"VirusTotal error: {e}")
        
        return set()
    
    def run_all(self) -> Path:
        """Run all subdomain enumeration"""
        Logger.header("SUBDOMAIN ENUMERATION")
        
        all_subs = set()
        
        # Run tools in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.run_subfinder): 'subfinder',
                executor.submit(self.run_assetfinder): 'assetfinder',
                executor.submit(self.run_amass): 'amass',
                executor.submit(self.query_crtsh): 'crtsh',
                executor.submit(self.query_virustotal): 'virustotal'
            }
            
            for future in as_completed(futures):
                try:
                    subs = future.result()
                    all_subs.update(subs)
                except Exception as e:
                    Logger.error(f"Error in {futures[future]}: {e}")
        
        # Add main domain
        all_subs.add(self.domain)
        
        # Save consolidated
        output_file = self.output_mgr.get_path('subdomains', 'all_subdomains.txt')
        with open(output_file, 'w') as f:
            f.write('\n'.join(sorted(all_subs)) + '\n')
        
        Logger.success(f"Total unique subdomains: {len(all_subs)}")
        return output_file


class DNSResolver:
    """DNS resolution and enrichment"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def resolve_with_puredns(self, input_file: Path) -> Optional[Path]:
        """Resolve using puredns"""
        if not ToolChecker.check_tool('puredns'):
            Logger.warning("puredns not found")
            return input_file

        Logger.header("DNS RESOLUTION")
        Logger.info("Resolving with puredns...")

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
            Logger.error(f"puredns error: {e}")
            return input_file

    def enrich_with_dnsx(self, input_file: Path):
        """Enrich with DNS records"""
        if not ToolChecker.check_tool('dnsx'):
            return

        Logger.info("Enriching DNS records...")

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
        """Scan ports using sdlookup (Shodan internetdb)"""
        if not ToolChecker.check_tool('sdlookup'):
            Logger.warning("sdlookup not found")
            return
        
        Logger.header("PORT SCANNING")
        Logger.info("Scanning with sdlookup (Shodan internetdb)...")
        
        output_file = self.output_mgr.get_path('ports', 'sdlookup.json')
        
        try:
            cmd = ['sdlookup', '-l', str(input_file), '-o', str(output_file), '-json']
            subprocess.run(cmd, timeout=600, check=True)
            
            # Parse results
            if output_file.exists():
                with open(output_file, 'r') as f:
                    results = json.load(f)
                
                # Create summary
                summary_file = self.output_mgr.get_path('ports', 'summary.txt')
                with open(summary_file, 'w') as f:
                    for host, data in results.items():
                        ports = data.get('ports', [])
                        if ports:
                            f.write(f"{host}: {', '.join(map(str, ports))}\n")
                
                Logger.success(f"Port scan complete: {len(results)} hosts scanned")
        except Exception as e:
            Logger.error(f"sdlookup error: {e}")


class HTTPProber:
    """HTTP probing and analysis"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def probe_with_httpx(self, input_file: Path) -> Optional[Path]:
        """Comprehensive HTTP probing"""
        if not ToolChecker.check_tool('httpx'):
            return None

        Logger.header("HTTP PROBING")
        Logger.info("Probing with httpx...")

        output_file = self.output_mgr.get_path('http', 'alive.txt')
        json_file = self.output_mgr.get_path('http', 'httpx.json')

        try:
            cmd = [
                'httpx',
                '-l', str(input_file),
                '-silent',
                '-status-code',
                '-title',
                '-tech-detect',
                '-cdn',
                '-content-length',
                '-web-server',
                '-follow-redirects',
                '-json',
                '-o', str(json_file)
            ]

            subprocess.run(cmd, timeout=900, check=True)

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

            Logger.success(f"Active hosts: {len(urls)}")
            return output_file

        except Exception as e:
            Logger.error(f"httpx error: {e}")
            return None
    
    def analyze_security_headers(self, input_file: Path):
        """Analyze security headers"""
        Logger.info("Analyzing security headers...")
        
        headers_file = self.output_mgr.get_path('http', 'security_headers.json')
        
        try:
            with open(input_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            results = {}
            security_headers = [
                'strict-transport-security',
                'content-security-policy',
                'x-frame-options',
                'x-content-type-options',
                'x-xss-protection',
                'referrer-policy'
            ]
            
            for url in urls[:50]:  # Limit to prevent excessive requests
                try:
                    response = requests.get(url, timeout=10, verify=False, allow_redirects=True)
                    headers = {k.lower(): v for k, v in response.headers.items()}
                    
                    missing = []
                    present = []
                    
                    for header in security_headers:
                        if header in headers:
                            present.append({header: headers[header]})
                        else:
                            missing.append(header)
                    
                    if missing:
                        results[url] = {
                            'missing': missing,
                            'present': present
                        }
                except:
                    pass
            
            with open(headers_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            if results:
                Logger.warning(f"Found {len(results)} sites with missing security headers")
        except Exception as e:
            Logger.error(f"Security headers analysis error: {e}")
    
    def get_favicon_hashes(self, input_file: Path):
        """Calculate favicon hashes for tech identification"""
        Logger.info("Calculating favicon hashes...")
        
        favicon_file = self.output_mgr.get_path('tech', 'favicon_hashes.json')
        
        try:
            with open(input_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            hashes = {}
            
            for url in urls[:50]:
                try:
                    favicon_url = f"{url}/favicon.ico"
                    response = requests.get(favicon_url, timeout=10, verify=False)
                    
                    if response.status_code == 200:
                        # Calculate mmh3 hash
                        favicon_hash = hashlib.md5(response.content).hexdigest()
                        hashes[url] = favicon_hash
                except:
                    pass
            
            with open(favicon_file, 'w') as f:
                json.dump(hashes, f, indent=2)
            
            Logger.success(f"Favicon hashes: {len(hashes)}")
        except Exception as e:
            Logger.error(f"Favicon hash error: {e}")

    def screenshot_with_gowitness(self, input_file: Path):
        """Take screenshots"""
        if not ToolChecker.check_tool('gowitness'):
            return

        Logger.header("SCREENSHOTS")
        Logger.info("Capturing screenshots...")

        screenshots_dir = self.output_mgr.get_path('screenshots', '')

        try:
            cmd = [
                'gowitness', 'file',
                '-f', str(input_file),
                '--screenshot-path', str(screenshots_dir)
            ]

            subprocess.run(cmd, timeout=1800, check=True)
            Logger.success(f"Screenshots: {screenshots_dir}")

        except Exception as e:
            Logger.error(f"gowitness error: {e}")


class URLCollector:
    """Modern URL collection"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def collect_with_xurlfind3r(self, domain: str) -> Set[str]:
        """Collect URLs with xurlfind3r"""
        if not ToolChecker.check_tool('xurlfind3r'):
            return set()
        
        Logger.info("Running xurlfind3r...")
        output_file = self.output_mgr.get_path('urls', 'xurlfind3r.txt')
        
        try:
            cmd = ['xurlfind3r', '-d', domain, '-o', str(output_file)]
            subprocess.run(cmd, timeout=900, check=True)
            
            with open(output_file, 'r') as f:
                urls = set(line.strip() for line in f if line.strip())
            
            Logger.success(f"xurlfind3r: {len(urls)} URLs")
            return urls
        except Exception as e:
            Logger.error(f"xurlfind3r error: {e}")
            return set()
    
    def crawl_with_katana(self, input_file: Path) -> Set[str]:
        """Crawl with katana"""
        if not ToolChecker.check_tool('katana'):
            return set()
        
        Logger.info("Crawling with katana...")
        output_file = self.output_mgr.get_path('urls', 'katana.txt')
        
        try:
            cmd = [
                'katana',
                '-list', str(input_file),
                '-depth', '3',
                '-js-crawl',
                '-known-files', 'all',
                '-automatic-form-fill',
                '-output', str(output_file)
            ]
            
            subprocess.run(cmd, timeout=1800, check=True)
            
            with open(output_file, 'r') as f:
                urls = set(line.strip() for line in f if line.strip())
            
            Logger.success(f"katana: {len(urls)} URLs")
            return urls
        except Exception as e:
            Logger.error(f"katana error: {e}")
            return set()

    def collect_from_archives(self, domain: str) -> Set[str]:
        """Collect from web archives"""
        Logger.info("Collecting from archives...")
        
        all_urls = set()

        # GAU
        if ToolChecker.check_tool('gau'):
            try:
                result = subprocess.run(
                    ['gau', domain],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)
                Logger.success(f"gau: {len(urls)} URLs")
            except Exception as e:
                Logger.error(f"gau error: {e}")

        # Waybackurls
        if ToolChecker.check_tool('waybackurls'):
            try:
                result = subprocess.run(
                    ['waybackurls', domain],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_urls.update(urls)
                Logger.success(f"waybackurls: {len(urls)} URLs")
            except Exception as e:
                Logger.error(f"waybackurls error: {e}")

        return all_urls

    def run_all(self, domain: str, alive_file: Path) -> Path:
        """Run all URL collection"""
        Logger.header("URL COLLECTION")
        
        all_urls = set()
        
        # Modern tools
        all_urls.update(self.collect_with_xurlfind3r(domain))
        all_urls.update(self.crawl_with_katana(alive_file))
        
        # Archives
        all_urls.update(self.collect_from_archives(domain))
        
        # Save raw
        raw_file = self.output_mgr.get_path('urls', 'all_urls_raw.txt')
        with open(raw_file, 'w') as f:
            f.write('\n'.join(sorted(all_urls)) + '\n')
        
        Logger.info(f"Total URLs collected: {len(all_urls)}")
        
        # Clean with uro
        if ToolChecker.check_tool('uro'):
            clean_file = self.output_mgr.get_path('urls', 'all_urls_clean.txt')
            
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
                
                Logger.success(f"Cleaned URLs saved")
                return clean_file
            except Exception as e:
                Logger.error(f"uro error: {e}")
                return raw_file
        
        return raw_file


class JSAnalyzer:
    """JavaScript analysis with modern tools"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def find_subdomains_with_jsubfinder(self, url_file: Path) -> Set[str]:
        """Find subdomains in JS with jsubfinder"""
        if not ToolChecker.check_tool('jsubfinder'):
            return set()
        
        Logger.info("Finding subdomains in JS (jsubfinder)...")
        output_file = self.output_mgr.get_path('js', 'jsubfinder_subs.txt')
        
        try:
            cmd = ['jsubfinder', '-f', str(url_file), '-o', str(output_file)]
            subprocess.run(cmd, timeout=900, check=True)
            
            with open(output_file, 'r') as f:
                subs = set(line.strip() for line in f if line.strip())
            
            Logger.success(f"jsubfinder: {len(subs)} subdomains from JS")
            return subs
        except Exception as e:
            Logger.error(f"jsubfinder error: {e}")
            return set()
    
    def extract_urls_with_getallurls(self, url_file: Path) -> Set[str]:
        """Extract all URLs from JS"""
        if not ToolChecker.check_tool('getallurls'):
            return set()
        
        Logger.info("Extracting URLs from JS (getallurls)...")
        output_file = self.output_mgr.get_path('js', 'js_urls.txt')
        
        try:
            with open(url_file, 'r') as f:
                urls = f.read()
            
            result = subprocess.run(
                ['getallurls'],
                input=urls,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            extracted = set(line.strip() for line in result.stdout.split('\n') if line.strip())
            
            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(extracted)) + '\n')
            
            Logger.success(f"getallurls: {len(extracted)} URLs from JS")
            return extracted
        except Exception as e:
            Logger.error(f"getallurls error: {e}")
            return set()
    
    def collect_js_files(self, url_file: Path) -> Path:
        """Collect JS files with subjs"""
        if not ToolChecker.check_tool('subjs'):
            return None
        
        Logger.info("Collecting JS files (subjs)...")
        output_file = self.output_mgr.get_path('js', 'js_files.txt')
        
        try:
            cmd = ['subjs', '-i', str(url_file), '-o', str(output_file)]
            subprocess.run(cmd, timeout=900, check=True)
            
            Logger.success(f"JS files collected")
            return output_file
        except Exception as e:
            Logger.error(f"subjs error: {e}")
            return None
    
    def scan_for_secrets(self, js_file: Path):
        """Scan JS for secrets with trufflehog"""
        if not ToolChecker.check_tool('trufflehog'):
            return
        
        Logger.info("Scanning JS for secrets...")
        output_file = self.output_mgr.get_path('secrets', 'js_secrets.json')
        
        try:
            with open(js_file, 'r') as f:
                js_urls = [line.strip() for line in f if line.strip()]
            
            all_findings = []
            
            for js_url in js_urls[:20]:  # Limit to prevent excessive scanning
                try:
                    result = subprocess.run(
                        ['trufflehog', 'filesystem', '--json', js_url],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            try:
                                finding = json.loads(line)
                                all_findings.append(finding)
                            except:
                                pass
                except:
                    pass
            
            if all_findings:
                with open(output_file, 'w') as f:
                    json.dump(all_findings, f, indent=2)
                
                Logger.warning(f"Found {len(all_findings)} potential secrets!")
        except Exception as e:
            Logger.error(f"Secret scanning error: {e}")
    
    def run_all(self, url_file: Path) -> Dict[str, Set[str]]:
        """Run all JS analysis"""
        Logger.header("JAVASCRIPT ANALYSIS")
        
        results = {
            'subdomains': set(),
            'urls': set(),
            'js_files': None
        }
        
        # Collect JS files first
        js_files = self.collect_js_files(url_file)
        results['js_files'] = js_files
        
        # Find subdomains in JS
        results['subdomains'] = self.find_subdomains_with_jsubfinder(url_file)
        
        # Extract URLs
        results['urls'] = self.extract_urls_with_getallurls(url_file)
        
        # Scan for secrets
        if js_files:
            self.scan_for_secrets(js_files)
        
        return results


class GitAnalyzer:
    """Git repository analysis and dumping"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def check_git_exposure(self, url_file: Path) -> List[str]:
        """Check for exposed .git"""
        Logger.header("GIT REPOSITORY CHECK")
        Logger.info("Checking for exposed .git...")
        
        exposed = []
        
        try:
            with open(url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            for url in urls:
                git_url = f"{url}/.git/config"
                try:
                    response = requests.get(git_url, timeout=5, allow_redirects=False, verify=False)
                    if response.status_code == 200 and '[core]' in response.text:
                        exposed.append(url)
                        Logger.warning(f"Exposed .git: {url}")
                except:
                    pass
            
            if exposed:
                output_file = self.output_mgr.get_path('git', 'exposed.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(exposed) + '\n')
                
                Logger.warning(f"Found {len(exposed)} exposed repositories")
            else:
                Logger.success("No exposed .git found")
            
            return exposed
        except Exception as e:
            Logger.error(f"Git check error: {e}")
            return []
    
    def dump_repos_with_goop(self, exposed: List[str]):
        """Dump repos with goop"""
        if not ToolChecker.check_tool('goop') or not exposed:
            return
        
        Logger.info("Dumping repositories with goop...")
        
        dump_dir = self.output_mgr.get_path('git', 'dumps')
        dump_dir.mkdir(exist_ok=True)
        
        for url in exposed[:5]:  # Limit to prevent excessive dumping
            try:
                repo_name = urlparse(url).netloc.replace('.', '_')
                output_path = dump_dir / repo_name
                
                Logger.info(f"Dumping {url}...")
                cmd = ['goop', url, str(output_path)]
                subprocess.run(cmd, timeout=300, check=True)
                
                Logger.success(f"Dumped: {repo_name}")
            except Exception as e:
                Logger.error(f"Dump error for {url}: {e}")


class VulnScanner:
    """Vulnerability scanning"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def scan_with_nuclei(self, url_file: Path):
        """Scan with Nuclei"""
        if not ToolChecker.check_tool('nuclei'):
            return
        
        Logger.header("VULNERABILITY SCANNING")
        Logger.info("Scanning with Nuclei...")
        
        output_file = self.output_mgr.get_path('vulnerabilities', 'nuclei.txt')
        json_file = self.output_mgr.get_path('vulnerabilities', 'nuclei.json')
        
        try:
            # Update templates
            subprocess.run(['nuclei', '-update-templates'], timeout=300, stderr=subprocess.DEVNULL)
            
            cmd = [
                'nuclei',
                '-l', str(url_file),
                '-severity', 'medium,high,critical',
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
                            severity = data.get('info', {}).get('severity', 'unknown')
                            template = data.get('template-id', '')
                            matched = data.get('matched-at', '')
                            vulns.append(f"[{severity}] {template} - {matched}")
                        except:
                            pass
            
            with open(output_file, 'w') as f:
                f.write('\n'.join(vulns))
            
            if vulns:
                Logger.warning(f"Found {len(vulns)} vulnerabilities")
            else:
                Logger.success("No vulnerabilities found")
                
        except Exception as e:
            Logger.error(f"Nuclei error: {e}")


class ParameterDiscovery:
    """Parameter discovery and analysis"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def discover_with_arjun(self, url_file: Path):
        """Discover parameters with Arjun"""
        if not ToolChecker.check_tool('arjun'):
            return
        
        Logger.header("PARAMETER DISCOVERY")
        Logger.info("Discovering with Arjun...")
        
        output_file = self.output_mgr.get_path('parameters', 'arjun.txt')
        
        try:
            cmd = [
                'arjun',
                '-i', str(url_file),
                '-oT', str(output_file),
                '-t', '10',
                '--stable'
            ]
            
            subprocess.run(cmd, timeout=1800)
            Logger.success("Parameter discovery complete")
        except Exception as e:
            Logger.error(f"Arjun error: {e}")
    
    def discover_with_x8(self, url_file: Path):
        """Discover hidden parameters with x8"""
        if not ToolChecker.check_tool('x8'):
            return
        
        Logger.info("Discovering with x8...")
        
        output_file = self.output_mgr.get_path('parameters', 'x8.txt')
        
        try:
            with open(url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            # Limit to prevent excessive scanning
            for url in urls[:10]:
                cmd = ['x8', '-u', url, '-o', str(output_file), '--append']
                subprocess.run(cmd, timeout=300)
            
            Logger.success("x8 discovery complete")
        except Exception as e:
            Logger.error(f"x8 error: {e}")
    
    def analyze_parameters(self, url_file: Path):
        """Analyze URL parameters"""
        Logger.info("Analyzing parameters...")
        
        try:
            with open(url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            params = {}
            interesting = set()
            
            patterns = [
                'id', 'user', 'admin', 'key', 'token',
                'file', 'path', 'dir', 'document',
                'url', 'redirect', 'return', 'next',
                'email', 'debug', 'api'
            ]
            
            for url in urls:
                if '?' in url:
                    query_params = parse_qs(urlparse(url).query)
                    for param in query_params.keys():
                        params[param] = params.get(param, 0) + 1
                        
                        if any(p in param.lower() for p in patterns):
                            interesting.add(param)
            
            # Save analysis
            all_file = self.output_mgr.get_path('parameters', 'all_params.txt')
            with open(all_file, 'w') as f:
                for param, count in sorted(params.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"{param}: {count}\n")
            
            interesting_file = self.output_mgr.get_path('parameters', 'interesting.txt')
            with open(interesting_file, 'w') as f:
                f.write('\n'.join(sorted(interesting)))
            
            Logger.success(f"Parameters: {len(params)} total, {len(interesting)} interesting")
        except Exception as e:
            Logger.error(f"Parameter analysis error: {e}")


class FuzzingEngine:
    """Directory and file fuzzing"""
    
    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr
    
    def fuzz_with_feroxbuster(self, url_file: Path, wordlist: Optional[Path] = None):
        """Fuzz with feroxbuster"""
        if not ToolChecker.check_tool('feroxbuster'):
            return
        
        Logger.header("DIRECTORY FUZZING")
        Logger.info("Fuzzing with feroxbuster...")
        
        if not wordlist:
            wordlist = Path.home() / '.config' / 'givenum' / 'wordlists' / 'common.txt'
            if not wordlist.exists():
                Logger.warning("No wordlist found")
                return
        
        try:
            with open(url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            for idx, url in enumerate(urls[:5], 1):
                Logger.info(f"Fuzzing [{idx}/5]: {url}")
                
                output_file = self.output_mgr.get_path('fuzzing', f'ferox_{idx}.txt')
                
                cmd = [
                    'feroxbuster',
                    '-u', url,
                    '-w', str(wordlist),
                    '-t', '50',
                    '-C', '404',
                    '-o', str(output_file),
                    '--silent'
                ]
                
                subprocess.run(cmd, timeout=600)
            
            Logger.success("Fuzzing complete")
        except Exception as e:
            Logger.error(f"feroxbuster error: {e}")


class DiffManager:
    """Track changes between scans"""
    
    def __init__(self, output_mgr: OutputManager, domain: str):
        self.output_mgr = output_mgr
        self.domain = domain
        self.results_base = Path('./results')
    
    def find_previous_scan(self) -> Optional[Path]:
        domain_scans = sorted([
            d for d in self.results_base.iterdir()
            if d.is_dir() and d.name.startswith(f"{self.domain}_") and d != self.output_mgr.base_dir
        ], reverse=True)
        
        return domain_scans[0] if domain_scans else None
    
    def diff_results(self):
        Logger.header("DIFF ANALYSIS")
        
        previous = self.find_previous_scan()
        if not previous:
            Logger.info("No previous scan found")
            return
        
        Logger.info(f"Comparing with: {previous.name}")
        
        compare_files = [
            ('subdomains', 'all_subdomains.txt'),
            ('http', 'alive.txt'),
            ('urls', 'all_urls_clean.txt')
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
                        f.write("# NEW\n")
                        f.write('\n'.join(sorted(new_items)) + '\n\n')
                    if removed_items:
                        f.write("# REMOVED\n")
                        f.write('\n'.join(sorted(removed_items)) + '\n')
                
                Logger.info(f"{filename}: +{len(new_items)} new, -{len(removed_items)} removed")


class ReportGenerator:
    """Generate reports"""
    
    def __init__(self, output_mgr: OutputManager, domain: str):
        self.output_mgr = output_mgr
        self.domain = domain
    
    def generate_report(self):
        Logger.info("Generating report...")
        
        report_file = self.output_mgr.get_path('reports', 'report.md')
        
        lines = [
            f"# GivEnum Report: {self.domain}",
            f"\n**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n**Directory**: `{self.output_mgr.base_dir}`",
            "\n---\n",
            "## Summary\n"
        ]
        
        # Count items
        stats = {
            "Subdomains": self.output_mgr.get_path('subdomains', 'all_subdomains.txt'),
            "Resolved": self.output_mgr.get_path('dns', 'resolved.txt'),
            "Active HTTP": self.output_mgr.get_path('http', 'alive.txt'),
            "URLs": self.output_mgr.get_path('urls', 'all_urls_clean.txt'),
            "JS Files": self.output_mgr.get_path('js', 'js_files.txt'),
        }
        
        for name, path in stats.items():
            if path.exists():
                with open(path, 'r') as f:
                    count = sum(1 for line in f if line.strip())
                lines.append(f"- **{name}**: {count}")
        
        lines.append("\n---\n")
        
        # Vulnerabilities
        vuln_file = self.output_mgr.get_path('vulnerabilities', 'nuclei.txt')
        if vuln_file.exists():
            with open(vuln_file, 'r') as f:
                vulns = [line.strip() for line in f if line.strip()]
            
            if vulns:
                lines.append("## Vulnerabilities\n")
                for vuln in vulns[:20]:
                    lines.append(f"- {vuln}")
                lines.append("\n---\n")
        
        # Exposed Git
        git_file = self.output_mgr.get_path('git', 'exposed.txt')
        if git_file.exists():
            with open(git_file, 'r') as f:
                repos = [line.strip() for line in f if line.strip()]
            
            if repos:
                lines.append("## Exposed Git Repositories\n")
                for repo in repos:
                    lines.append(f"- {repo}")
                lines.append("\n---\n")
        
        # Save
        with open(report_file, 'w') as f:
            f.write('\n'.join(lines))
        
        Logger.success(f"Report: {report_file}")


class GivEnum:
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
        self.git_analyzer = GitAnalyzer(self.output_mgr)
        self.vuln_scanner = VulnScanner(self.output_mgr)
        self.param_discovery = ParameterDiscovery(self.output_mgr)
        self.fuzzing = FuzzingEngine(self.output_mgr)
        self.diff_manager = DiffManager(self.output_mgr, domain)
        self.report_generator = ReportGenerator(self.output_mgr, domain)

    def run(self, skip_screenshots: bool = False, skip_portscan: bool = False, 
            skip_vuln: bool = False, skip_fuzzing: bool = True):
        """Run full enumeration"""
        start_time = time.time()

        Logger.header(f"GIVENUM: {self.domain}")

        # 1. Subdomain enumeration
        subs_file = self.subdomain_enum.run_all()

        # 2. DNS resolution
        resolved_file = self.dns_resolver.resolve_with_puredns(subs_file)
        self.dns_resolver.enrich_with_dnsx(resolved_file)

        # 3. Port scanning (with sdlookup)
        if not skip_portscan:
            self.port_scanner.scan_with_sdlookup(resolved_file)

        # 4. HTTP probing
        alive_file = self.http_prober.probe_with_httpx(resolved_file)

        if not alive_file:
            Logger.error("No active hosts found")
            return

        # 5. Security analysis
        self.http_prober.analyze_security_headers(alive_file)
        self.http_prober.get_favicon_hashes(alive_file)

        # 6. Screenshots
        if not skip_screenshots:
            self.http_prober.screenshot_with_gowitness(alive_file)

        # 7. URL collection
        url_file = self.url_collector.run_all(self.domain, alive_file)

        # 8. JavaScript analysis
        js_results = self.js_analyzer.run_all(url_file)
        
        # Merge JS subdomains back
        if js_results['subdomains']:
            js_subs_file = self.output_mgr.get_path('subdomains', 'from_js.txt')
            with open(js_subs_file, 'w') as f:
                f.write('\n'.join(sorted(js_results['subdomains'])))

        # 9. Git analysis
        exposed_git = self.git_analyzer.check_git_exposure(alive_file)
        if exposed_git:
            self.git_analyzer.dump_repos_with_goop(exposed_git)

        # 10. Parameter discovery
        self.param_discovery.analyze_parameters(url_file)
        self.param_discovery.discover_with_arjun(url_file)
        self.param_discovery.discover_with_x8(url_file)

        # 11. Fuzzing
        if not skip_fuzzing:
            self.fuzzing.fuzz_with_feroxbuster(alive_file)

        # 12. Vulnerability scanning
        if not skip_vuln:
            self.vuln_scanner.scan_with_nuclei(alive_file)

        # 13. Diff tracking
        self.diff_manager.diff_results()

        # 14. Generate report
        self.report_generator.generate_report()

        # Summary
        elapsed = time.time() - start_time
        Logger.header("COMPLETE")
        Logger.success(f"Time: {elapsed/60:.2f} minutes")
        Logger.success(f"Results: {self.output_mgr.base_dir}")


def configure_api():
    """Configure API keys"""
    Logger.header("API CONFIGURATION")
    
    api_config = APIConfig()
    
    services = {
        'virustotal': 'VirusTotal',
        'securitytrails': 'SecurityTrails',
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
 ██     ██ ███████ ██████  ███████ ███    ██ ██    ██ ███    ███ 
 ██     ██ ██      ██   ██ ██      ████   ██ ██    ██ ████  ████ 
 ██  █  ██ █████   ██████  █████   ██ ██  ██ ██    ██ ██ ████ ██ 
 ██ ███ ██ ██      ██   ██ ██      ██  ██ ██ ██    ██ ██  ██  ██ 
  ███ ███  ███████ ██████  ███████ ██   ████  ██████  ██      ██ 
{Colors.ENDC}
{Colors.OKGREEN}Advanced Web Enumeration Framework{Colors.ENDC}
{Colors.WARNING}Modern reconnaissance with comprehensive discovery{Colors.ENDC}
"""

    print(banner)

    parser = argparse.ArgumentParser(description='GivEnum - Advanced reconnaissance')

    parser.add_argument('-d', '--domain', help='Target domain')
    parser.add_argument('-o', '--output', default='./results', help='Output directory')
    parser.add_argument('--skip-screenshots', action='store_true', help='Skip screenshots')
    parser.add_argument('--skip-portscan', action='store_true', help='Skip port scan')
    parser.add_argument('--skip-vuln', action='store_true', help='Skip vuln scan')
    parser.add_argument('--enable-fuzzing', action='store_true', help='Enable fuzzing')
    parser.add_argument('--check-tools', action='store_true', help='Check tools')
    parser.add_argument('--configure-api', action='store_true', help='Configure API keys')

    args = parser.parse_args()

    if args.configure_api:
        configure_api()
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
        Logger.info("Run: ./install_tools.sh")
        sys.exit(1)

    # Start
    try:
        enum = GivEnum(args.domain, args.output)
        enum.run(
            skip_screenshots=args.skip_screenshots,
            skip_portscan=args.skip_portscan,
            skip_vuln=args.skip_vuln,
            skip_fuzzing=not args.enable_fuzzing
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