#!/usr/bin/env python3
"""
GivEnum - Advanced Web Enumeration Tool
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
        config_dir = Path(os.environ.get('GIVENUM_CONFIG_DIR', Path.home() / '.config' / 'givenum'))
        self.config_file = config_dir / 'api_keys.json'
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
        'subdomain': ['subfinder', 'assetfinder', 'findomain', 'amass', 'knockpy', 'github-subdomains', 'uncover'],
        'dns': ['dnsx', 'puredns', 'massdns', 'tlsx'],
        'http': ['httpx', 'hakcheckurl'],
        'url_collect': ['xurlfind3r', 'waybackurls', 'gau', 'hakrawler', 'katana', 'meg'],
        'js_analysis': ['subjs', 'jsubfinder', 'getJS', 'trufflehog'],
        'utils': ['anew', 'uro', 'unfurl', 'qsreplace', 'freq'],
        'scanning': ['nuclei', 'sdlookup'],
        'git': ['goop', 'git-dumper'],
        'optional': ['gowitness', 'subzy', 'subjack', 'dalfox', 'sqlmap', 'arjun', 'photon']
    }

    @staticmethod
    def check_tool(tool: str) -> bool:
        """Check if a tool is installed"""
        return shutil.which(tool) is not None

    @staticmethod
    def check_python_module(module: str) -> bool:
        """Check if a Python module can be imported"""
        result = subprocess.run(
            [sys.executable, '-c', f'import {module}'],
            capture_output=True
        )
        return result.returncode == 0

    @classmethod
    def check_all(cls, check_optional: bool = False) -> Dict[str, List[str]]:
        """Check all tools and return status"""
        missing = []
        available = []

        for category, tools in cls.REQUIRED_TOOLS.items():
            if category == 'optional' and not check_optional:
                continue

            for tool in tools:
                available_for_tool = cls.check_tool(tool)
                if tool == 'photon':
                    available_for_tool = available_for_tool or cls.check_python_module('photon')

                if available_for_tool:
                    available.append(tool)
                else:
                    missing.append(tool)

        return {'available': available, 'missing': missing}


def count_nonempty_lines(file_path: Path) -> int:
    """Count non-empty lines in a file"""
    if not file_path or not file_path.exists():
        return 0

    with open(file_path, 'r') as f:
        return sum(1 for line in f if line.strip())


def matches_domain(hostname: str, domain: str) -> bool:
    """Return True when hostname is the root domain or one of its subdomains."""
    candidate = hostname.strip().rstrip('.').lower()
    root = domain.strip().rstrip('.').lower()

    if candidate.startswith('*.'):
        candidate = candidate[2:]

    return bool(candidate) and (candidate == root or candidate.endswith(f".{root}"))


# Module-level tool execution log — reset at scan start via reset_tool_log()
_tool_log: Dict[str, dict] = {}


def reset_tool_log():
    """Clear the tool log for a new scan."""
    global _tool_log
    _tool_log = {}


def run_logged(name: str, cmd: list, log_dir: Path, **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run wrapper that saves stderr to logs/<name>.log and tracks status.

    Handles both stderr=subprocess.DEVNULL (removed) and capture_output=True
    (converted to stdout=PIPE so callers can still read result.stdout).
    """
    log_file = log_dir / f"{name}.log"
    t0 = time.time()
    # capture_output=True sets both stdout and stderr to PIPE — split them
    if kwargs.pop('capture_output', False):
        kwargs['stdout'] = subprocess.PIPE
        kwargs.setdefault('text', True)
    # Always redirect stderr to the log file (remove any previous setting)
    kwargs.pop('stderr', None)
    try:
        with open(log_file, 'w') as lf:
            result = subprocess.run(cmd, stderr=lf, **kwargs)
        elapsed = round(time.time() - t0, 1)
        _tool_log[name] = {
            'status': 'ok' if result.returncode == 0 else 'fail',
            'rc': result.returncode,
            'elapsed': elapsed,
        }
        return result
    except subprocess.TimeoutExpired:
        _tool_log[name] = {'status': 'timeout', 'rc': -1, 'elapsed': round(time.time() - t0, 1)}
        raise
    except subprocess.CalledProcessError as e:
        _tool_log[name] = {'status': 'fail', 'rc': e.returncode, 'elapsed': round(time.time() - t0, 1)}
        raise
    except FileNotFoundError:
        _tool_log[name] = {'status': 'not_found', 'rc': -1, 'elapsed': 0}
        raise
    except Exception as e:
        _tool_log[name] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - t0, 1), 'msg': str(e)}
        raise


def _track_captured(name: str, result: subprocess.CompletedProcess, t0: float, log_dir: Path):
    """Record status and save stderr for a capture_output=True subprocess call."""
    elapsed = round(time.time() - t0, 1)
    _tool_log[name] = {
        'status': 'ok' if result.returncode == 0 else 'fail',
        'rc': result.returncode,
        'elapsed': elapsed,
    }
    if result.stderr:
        (log_dir / f"{name}.log").write_text(result.stderr)


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
                    for candidate in name.split('\n'):
                        normalized = candidate.strip()
                        if normalized.startswith('*.'):
                            normalized = normalized[2:]
                        normalized = normalized.rstrip('.')
                        if matches_domain(normalized, self.domain):
                            domains.add(normalized)
                
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
                        normalized = name.strip().rstrip('.')
                        if matches_domain(normalized, self.domain):
                            domains.add(normalized.lstrip('*.'))
                
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
            headers = {
                'accept': 'application/json',
                'x-apikey': api_key,
            }
            url = f"https://www.virustotal.com/api/v3/domains/{self.domain}/subdomains?limit=40"

            domains = set()
            pages = []
            page_count = 0
            while url and page_count < 10:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code != 200:
                    Logger.warning(f"VirusTotal returned status {response.status_code}")
                    break

                data = response.json()
                pages.append(data)
                for entry in data.get('data', []):
                    domain = entry.get('id', '')
                    if domain and (domain == self.domain or domain.endswith(f".{self.domain}")):
                        domains.add(domain)

                url = data.get('links', {}).get('next')
                page_count += 1

            output_file = self.output_mgr.get_path('api_data', 'virustotal.txt')
            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(domains)) + '\n')

            json_file = self.output_mgr.get_path('api_data', 'virustotal.json')
            with open(json_file, 'w') as f:
                json.dump({'pages': pages, 'count': len(domains)}, f, indent=2)

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
                    normalized = hostname.strip().rstrip('.')
                    if matches_domain(normalized, self.domain):
                        domains.add(normalized)
                
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
            'amass': ['amass', 'enum', '-passive', '-d', domain, '-silent', '-timeout', '8'],
            'knockpy': ['knockpy', domain, '--silent'] if ToolChecker.check_tool('knockpy') else None
        }

    def run_tool(self, tool_name: str, command: List[str]) -> Set[str]:
        """Run a tool and return results"""
        if not command or not ToolChecker.check_tool(tool_name.split()[0]):
            return set()

        Logger.info(f"Running {tool_name}...")
        output_file = self.output_mgr.get_path('subdomains', f'{tool_name}.txt')

        try:
            _t0 = time.time()
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600
            )
            _track_captured(tool_name, result, _t0, self.output_mgr.dirs['logs'])

            subs = set(line.strip() for line in result.stdout.split('\n') if line.strip())

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(subs)) + '\n')

            if result.returncode == 0:
                Logger.success(f"{tool_name}: {len(subs)} subdomains")
            else:
                Logger.warning(f"{tool_name}: rc={result.returncode}, recovered {len(subs)} subdomains")
            return subs

        except subprocess.TimeoutExpired:
            _tool_log[tool_name] = {'status': 'timeout', 'rc': -1, 'elapsed': 600}
            Logger.warning(f"{tool_name} timeout")
        except Exception as e:
            Logger.error(f"Error running {tool_name}: {e}")

        return set()

    def _discover_with_uncover(self) -> Set[str]:
        """Multi-engine OSINT with uncover (Shodan/Censys/Fofa/Hunter/Netlas)"""
        if not ToolChecker.check_tool('uncover'):
            return set()

        Logger.info("Running uncover (multi-engine OSINT)...")
        output_file = self.output_mgr.get_path('subdomains', 'uncover.txt')

        shodan_key = self.api_config.get_key('shodan')
        censys_id = self.api_config.get_key('censys_id')
        censys_secret = self.api_config.get_key('censys_secret')
        fofa_email = self.api_config.get_key('fofa_email')
        fofa_key = self.api_config.get_key('fofa_key')
        hunter_key = self.api_config.get_key('hunter')
        netlas_key = self.api_config.get_key('netlas')

        engines = []
        if shodan_key:
            engines.append('shodan')
        if censys_id and censys_secret:
            engines.append('censys')
        if fofa_email and fofa_key:
            engines.append('fofa')
        if hunter_key:
            engines.append('hunter')
        if netlas_key:
            engines.append('netlas')

        if not engines:
            Logger.info("Skipping uncover: no compatible engine credentials configured")
            return set()

        try:
            _t0 = time.time()
            cmd = [
                'uncover',
                '-q', f'ssl:"{self.domain}"',
                '-e', ','.join(engines),
                '-f', 'host',
                '-silent', '-o', str(output_file),
            ]
            # Pass API keys via environment variables (uncover reads these natively)
            env = os.environ.copy()
            key_map = {
                'shodan':        ('SHODAN_API_KEY',   self.api_config.get_key('shodan')),
                'censys_id':     ('CENSYS_API_ID',    self.api_config.get_key('censys_id')),
                'censys_secret': ('CENSYS_API_SECRET',self.api_config.get_key('censys_secret')),
                'fofa_email':    ('FOFA_EMAIL',        self.api_config.get_key('fofa_email')),
                'fofa_key':      ('FOFA_KEY',          self.api_config.get_key('fofa_key')),
                'hunter':        ('HUNTER_API_KEY',    self.api_config.get_key('hunter')),
                'netlas':        ('NETLAS_API_KEY',    self.api_config.get_key('netlas')),
            }
            for _, (env_var, value) in key_map.items():
                if value:
                    env[env_var] = value
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
            _track_captured('uncover', result, _t0, self.output_mgr.dirs['logs'])

            if result.returncode != 0:
                Logger.warning(f"uncover exited with rc={result.returncode}")
                return set()

            if not output_file.exists():
                return set()

            with open(output_file) as f:
                raw = set(line.strip() for line in f if line.strip())

            # Filter to domain-related results and strip port suffixes
            subs = set()
            for entry in raw:
                host = entry.split(':')[0] if ':' in entry else entry
                if host and not host[0].isdigit() and matches_domain(host, self.domain):
                    subs.add(host.lstrip('*.'))

            Logger.success(f"uncover: {len(subs)} hosts via {','.join(engines)}")
            return subs

        except subprocess.TimeoutExpired:
            Logger.warning("uncover timeout")
            return set()
        except Exception as e:
            Logger.error(f"Error in uncover: {e}")
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

        # Uncover — multi-engine OSINT (Shodan, Censys, Fofa, Hunter, Netlas)
        all_subs.update(self._discover_with_uncover())

        # GitHub subdomain search
        github_token = self.api_config.get_key('github_token')
        if github_token and ToolChecker.check_tool('github-subdomains'):
            Logger.info("Running github-subdomains...")
            gh_file = self.output_mgr.get_path('subdomains', 'github_subdomains.txt')
            try:
                _t0 = time.time()
                result = subprocess.run(
                    ['github-subdomains', '-d', self.domain, '-t', github_token, '-o', str(gh_file)],
                    capture_output=True, text=True, timeout=300
                )
                _track_captured('github-subdomains', result, _t0, self.output_mgr.dirs['logs'])
                if gh_file.exists():
                    with open(gh_file) as f:
                        subs = set(line.strip() for line in f if line.strip())
                    all_subs.update(subs)
                    Logger.success(f"github-subdomains: {len(subs)} subdomains")
            except Exception as e:
                Logger.warning(f"github-subdomains error: {e}")

        # Add main domain
        all_subs.add(self.domain)

        # Save consolidated result
        output_file = self.output_mgr.get_path('subdomains', 'all_subdomains.txt')
        with open(output_file, 'w') as f:
            f.write('\n'.join(sorted(all_subs)) + '\n')

        Logger.success(f"Total: {len(all_subs)} unique subdomains")
        return output_file

    def bruteforce_with_puredns(self) -> Set[str]:
        """DNS brute-force subdomains with puredns"""
        if not ToolChecker.check_tool('puredns'):
            Logger.warning("puredns not found, skipping brute-force")
            return set()

        wordlist_candidates = [
            Path.home() / '.config' / 'givenum' / 'wordlists' / 'subdomains.txt',
            Path('/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt'),
            Path('/usr/share/seclists/Discovery/DNS/bitquark-subdomains-top100000.txt'),
            Path('/usr/share/wordlists/subdomains.txt'),
        ]
        wordlist = next((w for w in wordlist_candidates if w.exists()), None)

        if not wordlist:
            Logger.warning("No wordlist found for brute-force — place one at ~/.config/givenum/wordlists/subdomains.txt")
            return set()

        Logger.info(f"Brute-forcing subdomains with puredns ({wordlist.name})...")
        output_file = self.output_mgr.get_path('subdomains', 'bruteforce.txt')

        try:
            run_logged('puredns_bruteforce',
                       ['puredns', 'bruteforce', str(wordlist), self.domain, '-w', str(output_file)],
                       self.output_mgr.dirs['logs'], timeout=1800,
                       stdout=subprocess.DEVNULL)

            subs = set()
            if output_file.exists():
                with open(output_file, 'r') as f:
                    subs = set(line.strip() for line in f if line.strip())

            Logger.success(f"Brute-force: {len(subs)} subdomains found")
            return subs

        except subprocess.TimeoutExpired:
            Logger.warning("puredns brute-force timed out")
        except Exception as e:
            Logger.error(f"Error in brute-force: {e}")

        return set()


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
            run_logged('puredns_resolve',
                       ['puredns', 'resolve', str(input_file), '-w', str(output_file)],
                       self.output_mgr.dirs['logs'], timeout=600, check=True,
                       stdout=subprocess.DEVNULL)

            count = count_nonempty_lines(output_file)

            if count == 0:
                Logger.warning("puredns resolved 0 subdomains (wildcard DNS or no valid results)")
                fallback = self.resolve_with_dnsx_fallback(input_file)
                return fallback if fallback else input_file
            else:
                Logger.success(f"Resolved: {count} active subdomains")
            return output_file

        except Exception as e:
            Logger.error(f"Error in puredns: {e}")
            return input_file

    def resolve_with_dnsx_fallback(self, input_file: Path) -> Optional[Path]:
        """Resolve directly with dnsx (fallback when puredns returns 0)"""
        if not ToolChecker.check_tool('dnsx'):
            return None

        Logger.warning("puredns returned 0 — falling back to dnsx resolution...")
        output_file = self.output_mgr.get_path('dns', 'resolved.txt')

        try:
            with open(output_file, 'w') as out_f:
                run_logged('dnsx_fallback',
                           ['dnsx', '-l', str(input_file), '-a', '-silent'],
                           self.output_mgr.dirs['logs'], stdout=out_f, timeout=600)
            count = count_nonempty_lines(output_file)
            if count > 0:
                Logger.success(f"dnsx fallback: {count} resolved")
                return output_file
            Logger.warning("dnsx fallback also returned 0")
            Logger.info("Tip: this often happens with Akamai/Cloudflare CDN (anycast IPs differ per resolver)")
            Logger.info("httpx will still probe the raw subdomain list with its own DNS resolution")
            return None
        except Exception as e:
            Logger.error(f"dnsx fallback error: {e}")
            return None

    def enrich_with_dnsx(self, input_file: Path):
        """Enrich with DNS records using dnsx"""
        if not ToolChecker.check_tool('dnsx'):
            Logger.warning("dnsx not found")
            return

        Logger.info("Enriching with DNS records...")

        # A records
        a_records = self.output_mgr.get_path('dns', 'a_records.txt')
        with open(a_records, 'w') as out_f:
            run_logged('dnsx_a', ['dnsx', '-l', str(input_file), '-a', '-resp-only', '-silent'],
                       self.output_mgr.dirs['logs'], stdout=out_f, timeout=300)

        # CNAME records
        cname_records = self.output_mgr.get_path('dns', 'cname_records.txt')
        with open(cname_records, 'w') as out_f:
            run_logged('dnsx_cname', ['dnsx', '-l', str(input_file), '-cname', '-resp-only', '-silent'],
                       self.output_mgr.dirs['logs'], stdout=out_f, timeout=300)

        Logger.success("DNS enrichment complete")

    def discover_via_tlsx(self, resolved_file: Path) -> Set[str]:
        """Extract subdomains from TLS certificates using tlsx (SANs + CN)"""
        if not ToolChecker.check_tool('tlsx'):
            return set()

        Logger.info("Extracting subdomains from TLS certs with tlsx...")
        output_file = self.output_mgr.get_path('subdomains', 'tlsx.txt')

        try:
            _t0 = time.time()
            with open(output_file, 'w') as out_f:
                run_logged('tlsx',
                           ['tlsx', '-l', str(resolved_file), '-san', '-cn', '-silent', '-resp-only'],
                           self.output_mgr.dirs['logs'], stdout=out_f, timeout=600)

            if not output_file.exists():
                return set()

            with open(output_file) as f:
                raw = set(line.strip() for line in f if line.strip())

            # Keep only subdomains/domains (skip IPs and wildcards)
            domain_root = self.output_mgr.domain
            subs = set(
                d.lstrip('*.') for d in raw
                if d and not d[0].isdigit() and matches_domain(d, domain_root)
            )

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(subs)) + '\n')

            elapsed = round(time.time() - _t0, 1)
            _tool_log['tlsx'] = {'status': 'ok', 'rc': 0, 'elapsed': elapsed, 'found': len(subs)}
            Logger.success(f"tlsx: {len(subs)} domains from TLS certs")
            return subs

        except Exception as e:
            Logger.error(f"Error in tlsx: {e}")
            return set()


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
                ips = sorted({line.strip() for line in f if line.strip()})
            
            if not ips:
                Logger.warning("No IPs to scan")
                return
            
            # Create IP file for sdlookup
            ip_file = self.output_mgr.get_path('ports', 'ips.txt')
            with open(ip_file, 'w') as f:
                f.write('\n'.join(ips))
            
            # Run sdlookup
            cmd = ['sdlookup', '-i', str(ip_file), '-json', '-o', str(output_file)]
            run_logged('sdlookup', cmd, self.output_mgr.dirs['logs'], timeout=300, check=True)
            
            # Parse results (sdlookup outputs JSONL, one JSON object per line)
            if output_file.exists():
                with open(output_file, 'r') as f:
                    data = [json.loads(line) for line in f if line.strip()]

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
                '-ip',
                '-cdn',
                '-cname',
                '-content-length',
                '-web-server',
                '-json',
                '-o', str(json_file)
            ]

            run_logged('httpx', cmd, self.output_mgr.dirs['logs'], timeout=600, check=True,
                       stdout=subprocess.DEVNULL)

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
                if urls:
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
            _t0 = time.time()
            with open(input_file, 'r') as f:
                result = subprocess.run(
                    ['hakcheckurl'],
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            _track_captured('hakcheckurl', result, _t0, self.output_mgr.dirs['logs'])

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
                'gowitness', 'scan', 'file',
                '-f', str(input_file),
                '--screenshot-path', str(screenshots_dir),
                '--write-db',
                '--write-db-uri', f'sqlite://{db_file}'
            ]

            run_logged('gowitness', cmd, self.output_mgr.dirs['logs'], timeout=1800, check=True)
            Logger.success(f"Screenshots saved to {screenshots_dir}")

        except Exception as e:
            Logger.error(f"Error in gowitness: {e}")


class URLCollector:
    """Advanced URL collection with modern tools"""

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    @staticmethod
    def _extract_host(value: str) -> str:
        """Normalize a URL or hostname to a bare host"""
        value = value.strip()
        if not value:
            return ''

        if '://' not in value:
            value = f'https://{value}'

        parsed = urlparse(value)
        return (parsed.hostname or parsed.netloc or '').strip().lower()

    def _load_hosts(self, input_file: Path, limit: Optional[int] = None) -> List[str]:
        with open(input_file, 'r') as f:
            hosts = sorted({
                self._extract_host(line)
                for line in f
                if self._extract_host(line)
            })
        return hosts[:limit] if limit else hosts

    @staticmethod
    def _chunked(items: List[str], chunk_size: int) -> List[List[str]]:
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

    @staticmethod
    def _append_log(log_file: Path, header: str, content: str):
        if not content:
            return
        with open(log_file, 'a') as f:
            f.write(f"\n=== {header} ===\n")
            f.write(content.rstrip() + '\n')

    @staticmethod
    def _summarize_batch_status(total: int, failures: int, timeouts: int) -> Tuple[str, int]:
        if total <= 0:
            return 'ok', 0
        if failures + timeouts < total:
            return 'ok', 0
        if timeouts and failures == 0:
            return 'timeout', -1
        return 'fail', 1

    @staticmethod
    def _parse_meg_urls(content: str) -> Set[str]:
        urls = set()
        for line in content.splitlines():
            match = re.search(r'(https?://\S+)\s+\((\d{3})\b', line.strip())
            if match and match.group(2) == '200':
                urls.add(match.group(1))
        return urls

    def collect_with_xurlfind3r(self, input_file: Path) -> Set[str]:
        """Collect URLs using xurlfind3r (modern, efficient)"""
        if not ToolChecker.check_tool('xurlfind3r'):
            Logger.warning("xurlfind3r not found")
            return set()
        
        Logger.info("Collecting URLs with xurlfind3r...")
        output_file = self.output_mgr.get_path('urls', 'xurlfind3r.txt')
        log_file = self.output_mgr.get_path('logs', 'xurlfind3r.log')
        
        try:
            domains = self._load_hosts(input_file, limit=30)
            if not domains:
                _tool_log['xurlfind3r'] = {'status': 'ok', 'rc': 0, 'elapsed': 0, 'hosts': 0, 'timeouts': 0, 'failures': 0}
                with open(output_file, 'w') as f:
                    f.write('')
                Logger.success("xurlfind3r: 0 URLs (no hosts to process)")
                return set()

            all_urls = set()
            _t0 = time.time()
            timeouts = 0
            failures = 0

            for idx, domain in enumerate(domains, start=1):
                try:
                    result = subprocess.run(
                        ['xurlfind3r', '-d', domain, '--silent'],
                        capture_output=True,
                        text=True,
                        timeout=90
                    )
                    self._append_log(log_file, f"{domain} (rc={result.returncode})", result.stderr)

                    if result.returncode != 0:
                        failures += 1
                        Logger.warning(f"xurlfind3r [{idx}/{len(domains)}] failed on {domain} (rc={result.returncode})")
                        continue

                    urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                    all_urls.update(urls)
                    if idx == 1 or idx == len(domains) or idx % 10 == 0:
                        Logger.info(f"xurlfind3r progress: {idx}/{len(domains)} hosts, {len(all_urls)} URLs")

                except subprocess.TimeoutExpired as e:
                    timeouts += 1
                    self._append_log(log_file, f"{domain} (timeout)", (e.stderr or '') if isinstance(e.stderr, str) else '')
                    Logger.warning(f"xurlfind3r timeout on {domain} [{idx}/{len(domains)}]")
                except Exception as e:
                    failures += 1
                    self._append_log(log_file, f"{domain} (error)", str(e))
                    Logger.warning(f"xurlfind3r error on {domain}: {e}")

            status, rc = self._summarize_batch_status(len(domains), failures, timeouts)
            _tool_log['xurlfind3r'] = {
                'status': status,
                'rc': rc,
                'elapsed': round(time.time() - _t0, 1),
                'hosts': len(domains),
                'timeouts': timeouts,
                'failures': failures,
            }

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(all_urls)) + '\n')

            Logger.success(
                f"xurlfind3r: {len(all_urls)} URLs "
                f"(hosts={len(domains)}, timeouts={timeouts}, failures={failures})"
            )
            return all_urls
            
        except Exception as e:
            Logger.error(f"Error in xurlfind3r: {e}")
            return set()

    def collect_with_katana(self, input_file: Path) -> Set[str]:
        """Crawl URLs with katana (ProjectDiscovery)"""
        if not ToolChecker.check_tool('katana'):
            return set()

        Logger.info("Crawling with katana...")
        output_file = self.output_mgr.get_path('urls', 'katana.txt')
        log_file = self.output_mgr.get_path('logs', 'katana.log')

        try:
            _t0 = time.time()
            with open(input_file, 'r') as f:
                hosts = [line.strip() for line in f if line.strip()]
            if not hosts:
                return set()

            all_urls = set()
            for idx, host in enumerate(hosts[:50], start=1):
                try:
                    result = subprocess.run(
                        ['katana', '-u', host, '-silent', '-depth', '2', '-jc',
                         '-timeout', '10', '-rate-limit', '150'],
                        capture_output=True,
                        text=True,
                        timeout=90
                    )
                    self._append_log(log_file, f"{host} (rc={result.returncode})", result.stderr)
                    batch_urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                    all_urls.update(batch_urls)
                    if idx == 1 or idx % 10 == 0 or idx == len(hosts):
                        Logger.info(f"katana progress: {idx}/{min(len(hosts), 50)} hosts, {len(all_urls)} URLs")
                except subprocess.TimeoutExpired:
                    self._append_log(log_file, f"{host} (timeout)", '')
                    Logger.warning(f"katana timeout on {host}")
                except Exception as e:
                    self._append_log(log_file, f"{host} (error)", str(e))

            _track_captured('katana', type('obj', (object,), {'returncode': 0, 'stderr': ''})(), _t0, self.output_mgr.dirs['logs'])
            _tool_log['katana'] = {'status': 'ok', 'rc': 0, 'elapsed': round(time.time() - _t0, 1), 'urls': len(all_urls)}

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(all_urls)) + '\n')

            Logger.success(f"katana: {len(all_urls)} URLs")
            return all_urls

        except Exception as e:
            Logger.error(f"Error in katana: {e}")
            return set()

    def collect_from_archives(self, input_file: Path) -> Set[str]:
        """Collect URLs from web archives"""
        Logger.header("URL COLLECTION")

        all_urls = set()

        # xurlfind3r (primary)
        all_urls.update(self.collect_with_xurlfind3r(input_file))

        # katana (active crawler)
        all_urls.update(self.collect_with_katana(input_file))

        # hakrawler (crawl-based)
        all_urls.update(self.collect_with_hakrawler(input_file))

        # GAU — run only on root domain + www to avoid per-subdomain archive explosion
        # (gau takes 3+ min per domain; running on all 200 subdomains would never finish)
        if ToolChecker.check_tool('gau'):
            Logger.info("Running gau (root domain + www)...")
            gau_file = self.output_mgr.get_path('urls', 'gau.txt')
            gau_log = self.output_mgr.get_path('logs', 'gau.log')

            try:
                # Only the root domain and www — archives are richest there
                root = self.output_mgr.domain
                archive_targets = list({root, f'www.{root}'})

                urls = set()
                timeouts = 0
                failures = 0
                _t0 = time.time()
                for idx, domain in enumerate(archive_targets, start=1):
                    try:
                        result = subprocess.run(
                            ['gau', '--timeout', '60'],
                            input=domain,
                            capture_output=True,
                            text=True,
                            timeout=240
                        )
                        self._append_log(gau_log, f"{domain} (rc={result.returncode})", result.stderr)

                        if result.returncode != 0:
                            failures += 1
                            Logger.warning(f"gau failed on {domain} (rc={result.returncode})")
                            continue

                        batch_urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                        urls.update(batch_urls)
                        all_urls.update(batch_urls)
                        Logger.info(f"gau: {domain} → {len(batch_urls)} URLs (total: {len(urls)})")

                    except subprocess.TimeoutExpired:
                        timeouts += 1
                        self._append_log(gau_log, f"{domain} (timeout)", '')
                        Logger.warning(f"gau timeout on {domain}")
                    except Exception as e:
                        failures += 1
                        Logger.warning(f"gau error on {domain}: {e}")

                status, rc = self._summarize_batch_status(len(archive_targets), failures, timeouts)
                _tool_log['gau'] = {
                    'status': status,
                    'rc': rc,
                    'elapsed': round(time.time() - _t0, 1),
                    'timeouts': timeouts,
                    'failures': failures,
                }

                with open(gau_file, 'w') as f:
                    f.write('\n'.join(sorted(urls)) + '\n')

                Logger.success(f"gau: {len(urls)} URLs (timeouts={timeouts}, failures={failures})")

            except Exception as e:
                Logger.error(f"Error in gau: {e}")

        # Waybackurls — root domain + www only (same reason as gau: ~3 min per domain)
        if ToolChecker.check_tool('waybackurls'):
            Logger.info("Running waybackurls (root domain + www)...")
            wayback_file = self.output_mgr.get_path('urls', 'waybackurls.txt')
            wayback_log = self.output_mgr.get_path('logs', 'waybackurls.log')

            try:
                root = self.output_mgr.domain
                archive_targets = list({root, f'www.{root}'})

                urls = set()
                timeouts = 0
                failures = 0
                _t0 = time.time()
                for idx, domain in enumerate(archive_targets, start=1):
                    try:
                        result = subprocess.run(
                            ['waybackurls', domain],
                            capture_output=True,
                            text=True,
                            timeout=240
                        )
                        self._append_log(wayback_log, f"{domain} (rc={result.returncode})", result.stderr)

                        if result.returncode != 0:
                            failures += 1
                            Logger.warning(f"waybackurls failed on {domain} (rc={result.returncode})")
                            continue

                        batch_urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                        urls.update(batch_urls)
                        all_urls.update(batch_urls)
                        Logger.info(f"waybackurls: {domain} → {len(batch_urls)} URLs (total: {len(urls)})")

                    except subprocess.TimeoutExpired:
                        timeouts += 1
                        self._append_log(wayback_log, f"{domain} (timeout)", '')
                        Logger.warning(f"waybackurls timeout on {domain}")
                    except Exception as e:
                        failures += 1
                        Logger.warning(f"waybackurls error on {domain}: {e}")

                status, rc = self._summarize_batch_status(len(archive_targets), failures, timeouts)
                _tool_log['waybackurls'] = {
                    'status': status,
                    'rc': rc,
                    'elapsed': round(time.time() - _t0, 1),
                    'timeouts': timeouts,
                    'failures': failures,
                }

                with open(wayback_file, 'w') as f:
                    f.write('\n'.join(sorted(urls)) + '\n')

                Logger.success(f"waybackurls: {len(urls)} URLs (timeouts={timeouts}, failures={failures})")

            except Exception as e:
                Logger.error(f"Error in waybackurls: {e}")

        return all_urls

    def collect_with_hakrawler(self, input_file: Path) -> Set[str]:
        """Crawl URLs with hakrawler"""
        if not ToolChecker.check_tool('hakrawler'):
            Logger.warning("hakrawler not found")
            return set()

        Logger.info("Crawling with hakrawler...")
        output_file = self.output_mgr.get_path('urls', 'hakrawler.txt')

        try:
            _t0 = time.time()
            with open(input_file, 'r') as f:
                result = subprocess.run(
                    ['hakrawler', '-d', '2', '-u', '-timeout', '10'],
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
            _track_captured('hakrawler', result, _t0, self.output_mgr.dirs['logs'])

            urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(urls)) + '\n')

            Logger.success(f"hakrawler: {len(urls)} URLs")
            return urls

        except Exception as e:
            Logger.error(f"Error in hakrawler: {e}")
            return set()

    def probe_paths_with_meg(self, input_file: Path) -> Set[str]:
        """Probe common paths on all hosts with meg"""
        if not ToolChecker.check_tool('meg'):
            Logger.warning("meg not found")
            return set()

        Logger.info("Probing paths with meg...")

        meg_dir = self.output_mgr.get_path('urls', 'meg_out')
        meg_dir.mkdir(exist_ok=True)
        log_file = self.output_mgr.get_path('logs', 'meg.log')

        # Common paths worth probing
        interesting_paths = [
            '/robots.txt', '/sitemap.xml', '/.well-known/security.txt',
            '/crossdomain.xml', '/clientaccesspolicy.xml',
            '/api', '/api/v1', '/api/v2', '/swagger.json', '/openapi.json',
            '/.env', '/config.json', '/package.json',
        ]

        paths_file = self.output_mgr.get_path('urls', 'meg_paths.txt')
        with open(paths_file, 'w') as f:
            f.write('\n'.join(interesting_paths) + '\n')

        try:
            _t0 = time.time()
            result = subprocess.run(
                ['meg', '-d', '1000', '-s', '200', '-v', str(paths_file), str(input_file), str(meg_dir)],
                capture_output=True,
                text=True,
                timeout=600
            )
            _track_captured('meg', result, _t0, self.output_mgr.dirs['logs'])
            self._append_log(log_file, f"meg stdout (rc={result.returncode})", result.stdout)

            found = self._parse_meg_urls(result.stdout)
            index_file = meg_dir / 'index'
            if index_file.exists():
                with open(index_file, 'r', errors='ignore') as f:
                    found.update(self._parse_meg_urls(f.read()))

            results_file = self.output_mgr.get_path('urls', 'meg_found.txt')
            with open(results_file, 'w') as f:
                f.write('\n'.join(sorted(found)) + '\n')

            Logger.success(f"meg: {len(found)} interesting paths found")
            return found

        except Exception as e:
            Logger.error(f"Error in meg: {e}")
            return set()

    def analyze_with_freq(self, input_file: Path):
        """Score URLs/words by character frequency to surface anomalies"""
        if not ToolChecker.check_tool('freq'):
            Logger.warning("freq not found")
            return

        Logger.info("Scoring endpoints with freq...")

        output_file = self.output_mgr.get_path('urls', 'freq_scores.txt')

        # freq needs a pre-built corpus file; fall back gracefully if absent
        corpus_candidates = [
            Path.home() / '.config' / 'givenum' / 'freq_corpus.txt',
            Path('/usr/share/dict/words'),
        ]
        corpus = next((c for c in corpus_candidates if c.exists()), None)
        if not corpus:
            Logger.warning("freq: no corpus file found, skipping")
            return

        try:
            _t0 = time.time()
            with open(input_file, 'r') as f:
                result = subprocess.run(
                    ['freq', str(corpus)],
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            _track_captured('freq', result, _t0, self.output_mgr.dirs['logs'])

            with open(output_file, 'w') as f:
                f.write(result.stdout)

            Logger.success(f"freq: scores saved to {output_file}")

        except Exception as e:
            Logger.error(f"Error in freq: {e}")

    def crawl_with_photon(self, url: str) -> Set[str]:
        """Targeted crawling with Photon"""
        if not (ToolChecker.check_tool('photon') or ToolChecker.check_python_module('photon')):
            return set()
        
        Logger.info(f"Crawling {url} with Photon...")
        
        output_dir = self.output_mgr.get_path('urls', 'photon')
        output_dir.mkdir(exist_ok=True)
        
        try:
            if ToolChecker.check_tool('photon'):
                cmd = ['photon']
            else:
                cmd = [sys.executable, '-m', 'photon']

            cmd.extend([
                '-u', url,
                '-l', '2',
                '-t', '10',
                '--timeout', '5',
                '-o', str(output_dir)
            ])
            
            run_logged('photon', cmd, self.output_mgr.dirs['logs'], timeout=300)

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

        clean_file = self.output_mgr.get_path('urls', 'urls_clean.txt')

        if not ToolChecker.check_tool('uro'):
            Logger.warning("uro not found — using raw URL set as cleaned output")
            with open(clean_file, 'w') as f:
                f.write('\n'.join(sorted(urls)) + '\n')
            return

        try:
            _t0 = time.time()
            with open(raw_file, 'r') as f:
                result = subprocess.run(
                    ['uro'],
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            _track_captured('uro', result, _t0, self.output_mgr.dirs['logs'])

            cleaned_urls = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            if result.returncode != 0 or not cleaned_urls:
                Logger.warning("uro returned no cleaned URLs — falling back to raw URL set")
                cleaned_urls = sorted(urls)

            with open(clean_file, 'w') as f:
                f.write('\n'.join(cleaned_urls) + '\n')

            cleaned_count = len(cleaned_urls)
            Logger.success(f"Cleaned URLs: {cleaned_count}")

        except Exception as e:
            Logger.error(f"Error in uro: {e}")
            with open(clean_file, 'w') as f:
                f.write('\n'.join(sorted(urls)) + '\n')


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
            _t0 = time.time()
            result = subprocess.run(
                ['subjs', '-i', str(input_file)],
                capture_output=True,
                text=True,
                timeout=300
            )
            _track_captured('subjs', result, _t0, self.output_mgr.dirs['logs'])

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
            _t0 = time.time()
            for url in urls[:100]:  # Limit to prevent excessive scanning
                result = subprocess.run(
                    ['jsubfinder', '-u', url, '-silent'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                findings = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                all_findings.update(findings)
            if urls:
                _track_captured('jsubfinder', result, _t0, self.output_mgr.dirs['logs'])

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
                _t0 = time.time()
                result = subprocess.run(
                    ['getJS', '--input', str(alive_file), '--complete'],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                _track_captured('getJS', result, _t0, self.output_mgr.dirs['logs'])

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

        if all_js:
            self.download_js_files(all_js)
        
        # Analyze with jsubfinder
        if all_js:
            self.analyze_with_jsubfinder(all_js_file)

        # Secret scanning with trufflehog
        self.scan_secrets_with_trufflehog()

        return all_js

    def download_js_files(self, js_urls: Set[str], limit: int = 50, max_bytes: int = 2_000_000):
        """Download a capped subset of discovered JS files for local inspection/secret scanning."""
        Logger.info(f"Downloading up to {limit} JS files for local analysis...")

        download_dir = self.output_mgr.get_path('js', 'downloaded')
        download_dir.mkdir(exist_ok=True)
        _t0 = time.time()
        downloaded = 0
        failures = 0

        session = requests.Session()
        headers = {'User-Agent': 'GivEnum/1.0 (+https://github.com/6bat66/Givenum)'}

        for url in sorted(js_urls)[:limit]:
            try:
                response = session.get(url, headers=headers, timeout=15, stream=True)
                if response.status_code != 200:
                    failures += 1
                    continue

                content_type = response.headers.get('content-type', '').lower()
                url_path = urlparse(url).path.lower()
                if 'javascript' not in content_type and not url_path.endswith(('.js', '.mjs', '.cjs')):
                    failures += 1
                    continue

                chunks = bytearray()
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    chunks.extend(chunk)
                    if len(chunks) > max_bytes:
                        chunks = bytearray()
                        break

                if not chunks:
                    failures += 1
                    continue

                name = Path(urlparse(url).path).name or 'script.js'
                safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', name)[:80] or 'script.js'
                digest = hashlib.sha1(url.encode('utf-8')).hexdigest()[:12]
                output_file = download_dir / f"{digest}_{safe_name}"
                with open(output_file, 'wb') as f:
                    f.write(chunks)
                downloaded += 1

            except Exception:
                failures += 1

        _tool_log['js_download'] = {
            'status': 'ok' if downloaded > 0 or failures == 0 else 'fail',
            'rc': 0 if downloaded > 0 else (1 if failures else 0),
            'elapsed': round(time.time() - _t0, 1),
            'downloaded': downloaded,
            'failures': failures,
        }

        Logger.success(f"Downloaded {downloaded} JS files (failures={failures})")

    def scan_secrets_with_trufflehog(self):
        """Scan downloaded JS and git dumps for secrets with trufflehog"""
        if not ToolChecker.check_tool('trufflehog'):
            return

        Logger.info("Scanning for secrets with trufflehog...")
        output_file = self.output_mgr.get_path('js', 'trufflehog_secrets.json')
        scan_paths = [
            self.output_mgr.dirs['js'],
            self.output_mgr.dirs['git'],
        ]

        findings = []
        for scan_path in scan_paths:
            if not scan_path.exists():
                continue
            try:
                _t0 = time.time()
                result = subprocess.run(
                    ['trufflehog', 'filesystem', str(scan_path),
                     '--json', '--no-verification'],
                    capture_output=True, text=True, timeout=300
                )
                _track_captured(f'trufflehog_{scan_path.name}', result, _t0, self.output_mgr.dirs['logs'])

                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line:
                        try:
                            findings.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            except subprocess.TimeoutExpired:
                Logger.warning(f"trufflehog timeout on {scan_path.name}")
            except Exception as e:
                Logger.warning(f"trufflehog error on {scan_path.name}: {e}")

        if findings:
            with open(output_file, 'w') as f:
                json.dump(findings, f, indent=2)
            Logger.warning(f"trufflehog: {len(findings)} potential secrets found → {output_file}")
            # Write a readable summary
            summary_file = self.output_mgr.get_path('js', 'trufflehog_summary.txt')
            with open(summary_file, 'w') as f:
                for item in findings:
                    det = item.get('DetectorName', 'unknown')
                    raw = item.get('Raw', '')[:80]
                    src = item.get('SourceMetadata', {}).get('Data', {})
                    f.write(f"[{det}] {raw}\n  source: {src}\n\n")
        else:
            Logger.success("trufflehog: no secrets found")


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
            run_logged('goop', cmd, self.output_mgr.dirs['logs'], timeout=300)
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
            run_logged('git_dumper', cmd, self.output_mgr.dirs['logs'], timeout=300)
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
            run_logged('nuclei_update', ['nuclei', '-update-templates'],
                       self.output_mgr.dirs['logs'], timeout=300)

            cmd = [
                'nuclei',
                '-l', str(input_file),
                '-severity', severity,
                '-silent',
                '-jsonl-export', str(json_file)
            ]

            run_logged('nuclei', cmd, self.output_mgr.dirs['logs'], timeout=3600, check=True)
            
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
                if vulns:
                    f.write('\n'.join(vulns) + '\n')
            
            if vulns:
                Logger.warning(f"Found {len(vulns)} potential vulnerabilities!")
            else:
                Logger.success("No vulnerabilities found")

        except Exception as e:
            Logger.error(f"Error in Nuclei: {e}")

    def scan_with_dalfox(self, url_file: Path):
        """Scan parameterized URLs for XSS with dalfox"""
        if not ToolChecker.check_tool('dalfox'):
            Logger.warning("dalfox not found")
            return

        Logger.header("XSS SCANNING")
        Logger.info("Scanning for XSS with dalfox...")

        try:
            with open(url_file, 'r') as f:
                param_urls = [line.strip() for line in f if '?' in line and line.strip()]

            if not param_urls:
                Logger.info("No parameterized URLs to scan with dalfox")
                return

            # Limit to avoid excessive scanning
            targets = param_urls[:100]
            Logger.info(f"Scanning {len(targets)} parameterized URLs...")

            targets_file = self.output_mgr.get_path('vulnerabilities', 'dalfox_targets.txt')
            output_file = self.output_mgr.get_path('vulnerabilities', 'dalfox_results.txt')

            with open(targets_file, 'w') as f:
                f.write('\n'.join(targets) + '\n')

            run_logged('dalfox',
                       ['dalfox', 'file', str(targets_file), '--silence', '--no-color', '--output', str(output_file)],
                       self.output_mgr.dirs['logs'], timeout=1800)

            found = count_nonempty_lines(output_file) if output_file.exists() else 0
            if found > 0:
                Logger.warning(f"dalfox: {found} potential XSS found! → {output_file}")
            else:
                Logger.success("dalfox: no XSS found")

        except subprocess.TimeoutExpired:
            Logger.warning("dalfox timed out")
        except Exception as e:
            Logger.error(f"Error in dalfox: {e}")


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

        hosts = []
        with open(input_file, 'r') as f:
            hosts.extend(line.strip() for line in f if line.strip())

        cname_records_file = self.output_mgr.get_path('dns', 'cname_records.txt')
        if cname_records_file.exists():
            with open(cname_records_file, 'r') as f:
                hosts.extend(line.strip() for line in f if line.strip())

        cloud_services = {'AWS': set(), 'Azure': set(), 'GCP': set()}

        for host in hosts:
            for cloud, patterns in self.cloud_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, host, re.IGNORECASE):
                        cloud_services[cloud].add(host)
                        break
        
        # Save results
        for cloud, services in cloud_services.items():
            if services:
                output_file = self.output_mgr.get_path('cloud', f'{cloud.lower()}_services.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(services)) + '\n')
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
            
            run_logged('arjun', cmd, self.output_mgr.dirs['logs'], timeout=1800)
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
        json_file = self.output_mgr.get_path('takeover', 'subzy_results.json')

        try:
            result = run_logged(
                'subzy',
                ['subzy', 'run', '--targets', str(input_file), '--output', str(json_file)],
                self.output_mgr.dirs['logs'],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )

            with open(output_file, 'w') as f:
                f.write(result.stdout)

            findings = []
            if json_file.exists():
                with open(json_file, 'r') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    findings = data
                elif isinstance(data, dict):
                    findings = [data]

            if findings:
                Logger.warning("Possible takeovers found!")
            else:
                Logger.success("No takeover detected")

        except Exception as e:
            Logger.warning(f"Error in subzy: {e}")

    def check_with_subjack(self, input_file: Path):
        """Check for subdomain takeover with subjack"""
        if not ToolChecker.check_tool('subjack'):
            Logger.warning("subjack not found")
            return

        Logger.info("Checking takeovers with subjack...")
        output_file = self.output_mgr.get_path('takeover', 'subjack_results.txt')

        log_dir = self.output_mgr.dirs['logs']
        try:
            run_logged(
                'subjack',
                ['subjack', '-w', str(input_file), '-o', str(output_file),
                 '-ssl', '-timeout', '30', '-c',
                 str(Path.home() / 'go' / 'pkg' / 'mod' / 'github.com' / 'haccer' / 'subjack@v0.0.0-20201112041112-049c369c6946' / 'fingerprints.json')],
                log_dir,
                timeout=600,
            )
        except FileNotFoundError:
            # Try without fingerprints path (newer versions bundle it)
            try:
                run_logged(
                    'subjack',
                    ['subjack', '-w', str(input_file), '-o', str(output_file), '-ssl', '-timeout', '30'],
                    log_dir,
                    timeout=600,
                )
            except Exception as e:
                Logger.error(f"Error in subjack: {e}")
                return
        except Exception as e:
            Logger.error(f"Error in subjack: {e}")
            return

        if output_file.exists() and count_nonempty_lines(output_file) > 0:
            Logger.warning(f"subjack: potential takeovers found! → {output_file}")
        else:
            Logger.success("subjack: no takeovers found")


class NotificationManager:
    """Send scan diff notifications to Discord and/or Telegram"""

    def __init__(self, api_config: APIConfig, enabled: bool = True):
        self.api_config = api_config
        self.enabled = enabled

    def _discord_color(self, summary: dict) -> int:
        """Pick embed color based on severity of findings"""
        if summary.get('new_vulns'):
            return 0xFF4444   # red — new vulnerabilities
        if any(v.get('new') for v in summary.get('changes', {}).values()):
            return 0xFFA500   # orange — new items found
        return 0x00CC66       # green — no changes

    def send_discord(self, summary: dict):
        webhook_url = self.api_config.get_key('discord_webhook')
        if not webhook_url:
            return

        domain = summary.get('domain', 'unknown')
        timestamp = summary.get('timestamp', '')
        changes = summary.get('changes', {})

        fields = []
        for category, data in changes.items():
            new_count = len(data.get('new', []))
            removed_count = len(data.get('removed', []))
            if new_count or removed_count:
                value = f"+{new_count} new" if new_count else ""
                if removed_count:
                    value += f"  -{removed_count} removed" if value else f"-{removed_count} removed"
                fields.append({"name": category.replace('_', ' ').title(), "value": value, "inline": True})

        if not fields:
            fields.append({"name": "Status", "value": "No changes detected", "inline": False})

        embed = {
            "title": f"GivEnum Scan — {domain}",
            "description": f"Scan completed at {timestamp}",
            "color": self._discord_color(summary),
            "fields": fields,
            "footer": {"text": "GivEnum | github.com/6bat66/Givenum"}
        }

        try:
            import urllib.request
            data = json.dumps({"embeds": [embed]}).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            urllib.request.urlopen(req, timeout=10)
            Logger.success("Discord notification sent")
        except Exception as e:
            Logger.warning(f"Discord notification failed: {e}")

    def send_telegram(self, summary: dict):
        token = self.api_config.get_key('telegram_token')
        chat_id = self.api_config.get_key('telegram_chat_id')
        if not token or not chat_id:
            return

        domain = summary.get('domain', 'unknown')
        timestamp = summary.get('timestamp', '')
        changes = summary.get('changes', {})

        lines = [f"*GivEnum — {domain}*", f"_{timestamp}_", ""]

        has_changes = False
        for category, data in changes.items():
            new_items = data.get('new', [])
            removed_items = data.get('removed', [])
            if new_items or removed_items:
                has_changes = True
                label = category.replace('_', ' ').title()
                if new_items:
                    lines.append(f"✅ `+{len(new_items)}` new {label}")
                    for item in sorted(new_items)[:5]:
                        lines.append(f"  • `{item}`")
                    if len(new_items) > 5:
                        lines.append(f"  _...and {len(new_items)-5} more_")
                if removed_items:
                    lines.append(f"🔴 `-{len(removed_items)}` removed {label}")

        if not has_changes:
            lines.append("No changes detected since last scan.")

        new_vulns = summary.get('new_vulns', [])
        if new_vulns:
            lines.append("")
            lines.append(f"🚨 *{len(new_vulns)} new vulnerability findings*")
            for v in new_vulns[:3]:
                lines.append(f"  • `{v}`")

        text = '\n'.join(lines)

        try:
            import urllib.request, urllib.parse
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }).encode('utf-8')
            req = urllib.request.Request(url, data=data, method='POST')
            urllib.request.urlopen(req, timeout=10)
            Logger.success("Telegram notification sent")
        except Exception as e:
            Logger.warning(f"Telegram notification failed: {e}")

    def notify(self, summary: dict):
        if not self.enabled:
            return
        self.send_discord(summary)
        self.send_telegram(summary)


class DiffManager:
    """Track changes between scans"""

    COMPARE_FILES = [
        ('subdomains', 'all_subdomains.txt'),
        ('http',       'alive.txt'),
        ('urls',       'urls_clean.txt'),
        ('ports',      'open_ports.txt'),
        ('vulnerabilities', 'nuclei_results.txt'),
        ('takeover',   'subzy_results.txt'),
    ]

    def __init__(self, output_mgr: OutputManager, domain: str,
                 notifier: 'NotificationManager' = None):
        self.output_mgr = output_mgr
        self.domain = domain
        self.current_scan_dir = self.output_mgr.base_dir.resolve()
        self.results_base = self.current_scan_dir.parent
        self.notifier = notifier

    def find_previous_scan(self) -> Optional[Path]:
        """Find most recent previous scan"""
        if not self.results_base.exists():
            return None
        domain_scans = sorted([
            d for d in self.results_base.iterdir()
            if d.is_dir() and d.name.startswith(f"{self.domain}_") and d.resolve() != self.current_scan_dir
        ], reverse=True)
        return domain_scans[0] if domain_scans else None

    def diff_results(self):
        """Compare with previous scan, save diffs, and send notifications"""
        Logger.header("DIFF ANALYSIS")

        previous = self.find_previous_scan()
        if not previous:
            Logger.info("No previous scan found — diff skipped")
            return

        Logger.info(f"Comparing with: {previous.name}")

        summary = {
            'domain': self.domain,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'previous_scan': previous.name,
            'changes': {},
            'new_vulns': [],
        }

        for category, filename in self.COMPARE_FILES:
            current_file = self.output_mgr.get_path(category, filename)
            previous_file = previous / category / filename

            if not current_file.exists() or not previous_file.exists():
                continue

            with open(current_file, 'r') as f:
                current_lines = set(line.strip() for line in f if line.strip())
            with open(previous_file, 'r') as f:
                previous_lines = set(line.strip() for line in f if line.strip())

            new_items = sorted(current_lines - previous_lines)
            removed_items = sorted(previous_lines - current_lines)

            if new_items or removed_items:
                diff_file = self.output_mgr.get_path('diff', f'{filename}.diff')
                with open(diff_file, 'w') as f:
                    if new_items:
                        f.write("# NEW ITEMS\n")
                        f.write('\n'.join(new_items) + '\n\n')
                    if removed_items:
                        f.write("# REMOVED ITEMS\n")
                        f.write('\n'.join(removed_items) + '\n')

                Logger.info(f"{filename}: +{len(new_items)} new, -{len(removed_items)} removed")

                key = f"{category}/{filename}"
                summary['changes'][key] = {'new': new_items, 'removed': removed_items}

                if category == 'vulnerabilities':
                    summary['new_vulns'] = new_items

        # Save structured summary
        summary_file = self.output_mgr.get_path('diff', 'diff_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        if not summary['changes']:
            Logger.success("No changes since last scan")

        # Send notifications
        if self.notifier:
            self.notifier.notify(summary)


class ReportGenerator:
    """Generate comprehensive reports"""
    
    def __init__(self, output_mgr: OutputManager, domain: str):
        self.output_mgr = output_mgr
        self.domain = domain

    def _read_lines(self, category: str, filename: str) -> List[str]:
        """Read non-empty lines from an output file."""
        file_path = self.output_mgr.get_path(category, filename)
        if not file_path.exists():
            return []

        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    
    def generate_markdown_report(self, scan_mode: str = 'passive'):
        """Generate markdown report"""
        Logger.info("Generating markdown report...")
        
        report_file = self.output_mgr.get_path('reports', 'report.md')
        
        lines = [
            f"# Enumeration Report: {self.domain}",
            f"\n**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n**Mode**: `{scan_mode}`",
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
    
    def generate_json_report(self, scan_mode: str = 'passive'):
        """Generate JSON report"""
        statistics = {
            'subdomains': len(self._read_lines('subdomains', 'all_subdomains.txt')),
            'bruteforce_subdomains': len(self._read_lines('subdomains', 'bruteforce.txt')),
            'resolved': len(self._read_lines('dns', 'resolved.txt')),
            'active_http': len(self._read_lines('http', 'alive.txt')),
            'urls': len(self._read_lines('urls', 'urls_clean.txt')),
            'js_files': len(self._read_lines('js', 'all_js_files.txt')),
            'interesting_parameters': len(self._read_lines('parameters', 'interesting_parameters.txt')),
            'open_ports': len(self._read_lines('ports', 'open_ports.txt')),
            'nuclei_findings': len(self._read_lines('vulnerabilities', 'nuclei_results.txt')),
            'dalfox_findings': len(self._read_lines('vulnerabilities', 'dalfox_results.txt')),
            'subzy_findings': len(self._read_lines('takeover', 'subzy_results.txt')),
            'subjack_findings': len(self._read_lines('takeover', 'subjack_results.txt')),
            'git_exposures': len(self._read_lines('git', 'exposed_git.txt')),
            'cloud_aws': len(self._read_lines('cloud', 'aws_services.txt')),
            'cloud_azure': len(self._read_lines('cloud', 'azure_services.txt')),
            'cloud_gcp': len(self._read_lines('cloud', 'gcp_services.txt')),
        }

        diff_summary = {}
        diff_summary_file = self.output_mgr.get_path('diff', 'diff_summary.json')
        if diff_summary_file.exists():
            with open(diff_summary_file, 'r') as f:
                diff_summary = json.load(f)

        report = {
            'domain': self.domain,
            'timestamp': datetime.now().isoformat(),
            'scan_mode': scan_mode,
            'scan_directory': str(self.output_mgr.base_dir),
            'statistics': statistics,
            'findings': {
                'nuclei': self._read_lines('vulnerabilities', 'nuclei_results.txt'),
                'dalfox': self._read_lines('vulnerabilities', 'dalfox_results.txt'),
                'takeover': {
                    'subzy': self._read_lines('takeover', 'subzy_results.txt'),
                    'subjack': self._read_lines('takeover', 'subjack_results.txt'),
                },
                'git_exposure': self._read_lines('git', 'exposed_git.txt'),
                'parameters': self._read_lines('parameters', 'interesting_parameters.txt'),
                'cloud': {
                    'aws': self._read_lines('cloud', 'aws_services.txt'),
                    'azure': self._read_lines('cloud', 'azure_services.txt'),
                    'gcp': self._read_lines('cloud', 'gcp_services.txt'),
                },
                'diff': diff_summary,
            }
        }

        json_file = self.output_mgr.get_path('reports', 'report.json')
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2)


class GivEnum:
    """Main enumeration orchestrator"""

    def __init__(self, domain: str, output_dir: str = './results',
                 api_config: APIConfig = None, notify: bool = True):
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
        self.notifier = NotificationManager(self.api_config, enabled=notify)
        self.diff_manager = DiffManager(self.output_mgr, domain, notifier=self.notifier)
        self.report_generator = ReportGenerator(self.output_mgr, domain)

    def run_full_enum(self, skip_screenshots: bool = False, skip_portscan: bool = False,
                     skip_vuln_scan: bool = False, active: bool = False):
        """Run complete enumeration.

        Passive mode (default): subdomain discovery, DNS, HTTP, URL/JS collection,
        git exposure, takeover checks (subzy), diff, reports.

        Active mode (--active): adds brute-force, port scan, nuclei, dalfox, subjack, arjun.
        """
        start_time = time.time()
        reset_tool_log()

        if active:
            Logger.header(f"WEB ENUMERATION (ACTIVE): {self.domain}")
        else:
            Logger.header(f"WEB ENUMERATION (PASSIVE): {self.domain}")
            Logger.info("Tip: use --active to enable brute-force, port scan, nuclei, dalfox, subjack")

        # 1. Subdomain enumeration (passive sources)
        subs_file = self.subdomain_enum.run_all()

        # 1b. DNS brute-force (active only)
        if active:
            Logger.header("DNS BRUTE-FORCE")
            brute_subs = self.subdomain_enum.bruteforce_with_puredns()
            if brute_subs:
                with open(subs_file, 'r') as f:
                    existing = set(line.strip() for line in f if line.strip())
                merged = existing | brute_subs
                with open(subs_file, 'w') as f:
                    f.write('\n'.join(sorted(merged)) + '\n')
                Logger.success(f"After brute-force: {len(merged)} total subdomains")

        # 2. DNS Resolution
        resolved_file = self.dns_resolver.resolve_with_puredns(subs_file)
        self.dns_resolver.enrich_with_dnsx(resolved_file)

        # 2b. TLS cert extraction — find subdomains in SANs of live certs
        tlsx_subs = self.dns_resolver.discover_via_tlsx(resolved_file)
        if tlsx_subs:
            with open(resolved_file) as f:
                existing_resolved = set(line.strip() for line in f if line.strip())
            new_from_tls = tlsx_subs - existing_resolved
            if new_from_tls:
                Logger.success(f"tlsx found {len(new_from_tls)} new subdomains from TLS certs")
                with open(resolved_file, 'a') as f:
                    for sub in sorted(new_from_tls):
                        f.write(sub + '\n')
                # Also merge into all_subdomains.txt
                all_subs_file = self.output_mgr.get_path('subdomains', 'all_subdomains.txt')
                existing_all = set()
                if all_subs_file.exists():
                    with open(all_subs_file) as f:
                        existing_all = set(line.strip() for line in f if line.strip())
                with open(all_subs_file, 'w') as f:
                    f.write('\n'.join(sorted(existing_all | new_from_tls)) + '\n')

        if count_nonempty_lines(resolved_file) == 0:
            Logger.warning("No resolved subdomains found, stopping after DNS phase")
            self._finalize_run(start_time, active=active)
            return

        # 3. Cloud detection
        self.cloud_detector.detect(resolved_file)

        # 4. Port scanning (active only)
        if active and not skip_portscan:
            self.port_scanner.scan_with_sdlookup(resolved_file)

        # 5. HTTP Probing
        alive_file = self.http_prober.probe_with_httpx(resolved_file)

        if not alive_file or count_nonempty_lines(alive_file) == 0:
            Logger.warning("No active hosts found, stopping after HTTP probing")
            self._finalize_run(start_time, active=active)
            return

        self.http_prober.check_urls_with_hakcheckurl(alive_file)

        # 6. Screenshots
        if not skip_screenshots:
            self.http_prober.screenshot_with_gowitness(alive_file)

        # 7. URL Collection
        all_urls = self.url_collector.collect_from_archives(alive_file)

        # 8. Probe common paths with meg
        all_urls.update(self.url_collector.probe_paths_with_meg(alive_file))

        # 9. Photon crawl (first 5 alive hosts to avoid excess)
        try:
            with open(alive_file, 'r') as f:
                photon_targets = [l.strip() for l in f if l.strip()][:5]
            for target_url in photon_targets:
                all_urls.update(self.url_collector.crawl_with_photon(target_url))
        except Exception as e:
            Logger.error(f"Error during Photon crawl: {e}")

        # 10. Clean URLs
        if all_urls:
            self.url_collector.clean_urls(all_urls)
            clean_urls = self.output_mgr.get_path('urls', 'urls_clean.txt')

            # 11. Frequency analysis with freq
            if clean_urls.exists():
                self.url_collector.analyze_with_freq(clean_urls)

            # 12. Parameter analysis — passive; arjun brute-force only in active
            if clean_urls.exists():
                self.param_discovery.analyze_parameters(clean_urls)
                if active:
                    self.param_discovery.discover_with_arjun(clean_urls)

        # 13. JavaScript Analysis
        self.js_analyzer.analyze_all(alive_file)

        # 14. Git exposure
        self.git_dumper.check_and_dump(alive_file)

        # 15. Vulnerability scanning (active only)
        if active and not skip_vuln_scan:
            self.vuln_scanner.scan_with_nuclei(alive_file)

            # 15b. XSS scanning with dalfox (active only)
            clean_urls = self.output_mgr.get_path('urls', 'urls_clean.txt')
            if clean_urls.exists():
                self.vuln_scanner.scan_with_dalfox(clean_urls)

        # 16. Takeover check
        self.takeover_checker.check_with_subzy(resolved_file)
        if active:
            self.takeover_checker.check_with_subjack(resolved_file)

        # 17. Diff tracking
        self.diff_manager.diff_results()

        # 18. Generate reports
        self.report_generator.generate_markdown_report(scan_mode='active' if active else 'passive')
        self.report_generator.generate_json_report(scan_mode='active' if active else 'passive')
        self._generate_analysis_report()

        # Summary
        self._print_summary(time.time() - start_time)

    def _finalize_run(self, start_time: float, active: bool = False):
        """Write partial results and print a summary before exiting early"""
        self.diff_manager.diff_results()
        self.report_generator.generate_markdown_report(scan_mode='active' if active else 'passive')
        self.report_generator.generate_json_report(scan_mode='active' if active else 'passive')
        self._generate_analysis_report()
        elapsed = time.time() - start_time
        self._print_summary(elapsed)

    def _generate_analysis_report(self):
        """Generate analysis.md using the standalone analyzer when available."""
        analyzer_script = Path(__file__).with_name('analyze_results.py')
        if not analyzer_script.exists():
            Logger.warning("analyze_results.py not found — skipping analysis.md generation")
            return

        analysis_file = self.output_mgr.get_path('reports', 'analysis.md')
        Logger.info("Generating analysis report...")

        try:
            _t0 = time.time()
            result = subprocess.run(
                [sys.executable, '-u', str(analyzer_script), str(self.output_mgr.base_dir), '--export', str(analysis_file)],
                capture_output=True,
                text=True,
                timeout=300
            )
            _track_captured('analyze_results', result, _t0, self.output_mgr.dirs['logs'])

            if result.returncode == 0 and analysis_file.exists():
                Logger.success(f"Analysis: {analysis_file}")
            else:
                Logger.warning("Analysis report generation did not complete successfully")

        except Exception as e:
            Logger.warning(f"Error generating analysis report: {e}")

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
                    Logger.info(f"{name}: {count_nonempty_lines(path)}")
                except:
                    pass

        Logger.success(f"\nTime: {elapsed_time/60:.2f} minutes")
        Logger.success(f"Results: {self.output_mgr.base_dir}")
        Logger.info(f"Report: {self.output_mgr.get_path('reports', 'report.md')}")
        analysis_file = self.output_mgr.get_path('reports', 'analysis.md')
        if analysis_file.exists():
            Logger.info(f"Analysis: {analysis_file}")

        # Tool execution summary
        if _tool_log:
            Logger.header("TOOL EXECUTION SUMMARY")
            ok = fail = skip = 0
            for tool, info in sorted(_tool_log.items()):
                st = info['status']
                if st == 'ok':
                    icon = Colors.OKGREEN + '✓' + Colors.ENDC
                    ok += 1
                elif st == 'not_found':
                    icon = Colors.WARNING + '—' + Colors.ENDC
                    skip += 1
                else:
                    icon = Colors.FAIL + '✗' + Colors.ENDC
                    fail += 1
                Logger.info(f"  {icon} {tool:<22} {st:<10} {info['elapsed']}s")
            Logger.info(f"\n  ok={ok}  fail={fail}  not_found={skip}")
            summary_path = self.output_mgr.get_path('logs', 'execution_summary.json')
            with open(summary_path, 'w') as f:
                json.dump(_tool_log, f, indent=2)


def configure_api_keys():
    """Interactive API key configuration"""
    Logger.header("API CONFIGURATION")
    
    api_config = APIConfig()
    
    services = {
        'virustotal': 'VirusTotal',
        'securitytrails': 'SecurityTrails',
        'certspotter': 'CertSpotter',
        'shodan': 'Shodan (also used by uncover)',
        'censys_id': 'Censys API ID (uncover)',
        'censys_secret': 'Censys API Secret (uncover)',
        'fofa_email': 'Fofa Email (uncover)',
        'fofa_key': 'Fofa API Key (uncover)',
        'hunter': 'Hunter.io API Key (uncover)',
        'netlas': 'Netlas API Key (uncover)',
        'github_token': 'GitHub Personal Access Token (github-subdomains)',
        'discord_webhook': 'Discord Webhook URL',
        'telegram_token': 'Telegram Bot Token',
        'telegram_chat_id': 'Telegram Chat ID',
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
        description='GivEnum - Advanced web enumeration',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-d', '--domain', help='Target domain')
    parser.add_argument('-o', '--output', default='./results', help='Output directory')
    parser.add_argument('--active', action='store_true',
                        help='Enable active scanning (brute-force, port scan, nuclei, dalfox, subjack, arjun)')
    parser.add_argument('--skip-screenshots', action='store_true', help='Skip screenshots')
    parser.add_argument('--skip-portscan', action='store_true', help='Skip port scan (active mode only)')
    parser.add_argument('--skip-vuln-scan', action='store_true', help='Skip vulnerability scan (active mode only)')
    parser.add_argument('--check-tools', action='store_true', help='Check tools')
    parser.add_argument('--configure-api', action='store_true', help='Configure API keys')
    parser.add_argument('--no-notify', action='store_true',
                        help='Disable Discord/Telegram notifications for this run')

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
        enum = GivEnum(args.domain, args.output, notify=not args.no_notify)
        enum.run_full_enum(
            skip_screenshots=args.skip_screenshots,
            skip_portscan=args.skip_portscan,
            skip_vuln_scan=args.skip_vuln_scan,
            active=args.active
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
