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
import urllib3.util.connection as _urllib3_conn
import re
import threading

# Force IPv4 for all Python requests/urllib3 calls.
#
# Why: in Docker, many target hosts publish AAAA records that point to IPv6
# addresses unreachable from the container's bridge network. When `requests`
# resolves both A and AAAA, it may try the AAAA first and fail with
#   [Errno 101] Network is unreachable
# or
#   [Errno 111] Connection refused
# while the Go-based tools (httpx, subfinder, dnsx) don't have this problem
# because they use their own resolver and prefer IPv4.
#
# Concretely this bug killed crt.sh / VirusTotal / AlienVault mid-scan and
# made git-dump / JS-download report 0/50 successes for 4 scans in a row
# (bscash, tesla x2, paypal). Disabling IPv6 at the urllib3 layer is a
# one-line fix that costs us only true IPv6-only hosts (<0.1% of the web).
_urllib3_conn.HAS_IPV6 = False
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs
import shutil
import hashlib
import socket
import dns.resolver

# ── CPU awareness ─────────────────────────────────────────────────────────────
# Used to scale tool thread counts to available hardware automatically.
_CPU_COUNT: int = os.cpu_count() or 2


def _get_proxy_flag() -> list:
    """Return ['-proxy', url] if proxy is enabled in proxy.json, else [].

    Supports two modes:
      'single'  — uses the fixed http/https URL (e.g. Burp Suite)
      'rotate'  — picks a random valid proxy from the fetched free list
    """
    try:
        config_dir = Path(os.environ.get('GIVENUM_CONFIG_DIR', Path.home() / '.config' / 'givenum'))
        proxy_file = config_dir / 'proxy.json'
        if not proxy_file.exists():
            return []
        cfg = json.loads(proxy_file.read_text())
        if not cfg.get('enabled'):
            return []

        mode = cfg.get('mode', 'single')

        if mode == 'rotate':
            proxies = [p for p in cfg.get('proxies', []) if p.get('valid')]
            if not proxies:
                return []
            import random
            # Prefer low-latency top-20% with 70% probability
            top = max(1, len(proxies) // 5)
            chosen = proxies[random.randint(0, top - 1)] if random.random() < 0.7 else \
                     proxies[random.randint(0, len(proxies) - 1)]
            url = chosen.get('url', '')
            if url:
                return ['-proxy', url.strip()]
        else:
            url = cfg.get('https') or cfg.get('http') or ''
            if url:
                return ['-proxy', url.strip()]
    except Exception:
        pass
    return []


def _apply_proxy_env():
    """Set HTTP_PROXY / HTTPS_PROXY env-vars so all sub-processes inherit them.
    Called once at scan start by GivEnum.__init__."""
    try:
        config_dir = Path(os.environ.get('GIVENUM_CONFIG_DIR', Path.home() / '.config' / 'givenum'))
        proxy_file = config_dir / 'proxy.json'
        if not proxy_file.exists():
            return
        cfg = json.loads(proxy_file.read_text())
        if not cfg.get('enabled'):
            return
        flag = _get_proxy_flag()
        if not flag:
            return
        url = flag[1]
        os.environ['HTTP_PROXY']  = url
        os.environ['http_proxy']  = url
        os.environ['HTTPS_PROXY'] = url
        os.environ['https_proxy'] = url
        no_proxy = cfg.get('noProxy', '')
        if no_proxy:
            os.environ['NO_PROXY'] = no_proxy
            os.environ['no_proxy'] = no_proxy
        Logger.info(f"[PROXY] routing traffic via {url}")
    except Exception:
        pass

# Realistic browser User-Agent to avoid blocks on passive scans
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)


def _api_request(url: str, headers: dict | None = None, timeout: int = 30,
                 max_retries: int = 2, backoff: float = 3.0) -> requests.Response | None:
    """HTTP GET with retry, backoff, and consistent User-Agent."""
    hdrs = {'User-Agent': USER_AGENT}
    if headers:
        hdrs.update(headers)
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=hdrs, timeout=timeout)
            if resp.status_code == 429:
                wait = backoff * (2 ** attempt)
                Logger.warning(f"Rate-limited (429) on {url}, waiting {wait:.0f}s")
                time.sleep(wait)
                continue
            return resp
        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(backoff * (attempt + 1))
            else:
                raise
    return None


# ── ProjectDiscovery-style terminal output ────────────────────────────────────

class Logger:
    """Thread-safe logger with ProjectDiscovery visual style.

    Prefix palette:
        [INF] cyan    — informational / progress
        [FND] green   — findings / success
        [WRN] yellow  — non-fatal warnings
        [ERR] red     — errors
    Section headers use thin unicode rule lines instead of === boxes.
    """

    _lock = threading.Lock()

    # ANSI palette
    _C_INF  = '\033[36m'   # cyan
    _C_FND  = '\033[32m'   # green
    _C_WRN  = '\033[33m'   # yellow
    _C_ERR  = '\033[31m'   # red
    _C_DIM  = '\033[2m'    # dim  (separators, decorative)
    _C_BOLD = '\033[1m'
    _C_RST  = '\033[0m'

    @classmethod
    def _emit(cls, tag: str, color: str, msg: str) -> None:
        line = f"{color}[{tag}]{cls._C_RST} {msg}"
        with cls._lock:
            print(line, flush=True)

    @classmethod
    def info(cls, msg: str) -> None:
        cls._emit('INF', cls._C_INF, msg)

    @classmethod
    def success(cls, msg: str) -> None:
        cls._emit('FND', cls._C_FND, msg)

    @classmethod
    def warning(cls, msg: str) -> None:
        cls._emit('WRN', cls._C_WRN, msg)

    @classmethod
    def error(cls, msg: str) -> None:
        cls._emit('ERR', cls._C_ERR, msg)

    @classmethod
    def header(cls, title: str) -> None:
        rule = f"{cls._C_DIM}{'─' * 56}{cls._C_RST}"
        label = f"{cls._C_BOLD}{title}{cls._C_RST}"
        with cls._lock:
            print(f"\n{rule}\n {label}\n{rule}\n", flush=True)


# Legacy alias — keeps old Colors.* references (e.g. in the banner) working
class Colors:
    HEADER   = Logger._C_DIM
    OKBLUE   = Logger._C_INF
    OKCYAN   = Logger._C_INF
    OKGREEN  = Logger._C_FND
    WARNING  = Logger._C_WRN
    FAIL     = Logger._C_ERR
    ENDC     = Logger._C_RST
    BOLD     = Logger._C_BOLD
    UNDERLINE = '\033[4m'


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
            except (OSError, json.JSONDecodeError) as e:
                Logger.warning(f"Could not load API config from {self.config_file}: {e}")
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

    def sync_subfinder_config(self) -> Optional[Path]:
        """Generate a subfinder provider-config.yaml from configured keys.

        Returns the path to the generated file (to be passed via `-pc`), or None
        if no applicable keys are configured.  This keeps user-owned
        ~/.config/subfinder/provider-config.yaml untouched.
        """
        # Mapping: api_keys.json key → list of subfinder provider entries
        providers: Dict[str, List[str]] = {}
        kv = self.keys
        if kv.get('virustotal'):
            providers['virustotal'] = [kv['virustotal']]
        if kv.get('securitytrails'):
            providers['securitytrails'] = [kv['securitytrails']]
        if kv.get('shodan'):
            providers['shodan'] = [kv['shodan']]
        if kv.get('certspotter'):
            providers['certspotter'] = [kv['certspotter']]
        if kv.get('censys_id') and kv.get('censys_secret'):
            providers['censys'] = [f"{kv['censys_id']}:{kv['censys_secret']}"]
        if kv.get('fofa_email') and kv.get('fofa_key'):
            providers['fofa'] = [f"{kv['fofa_email']}:{kv['fofa_key']}"]
        if kv.get('github_token'):
            providers['github'] = [kv['github_token']]
        if kv.get('hunter'):
            providers['hunterhow'] = [kv['hunter']]
        if kv.get('netlas'):
            providers['netlas'] = [kv['netlas']]

        if not providers:
            return None

        out_dir = self.config_file.parent / 'derived' / 'subfinder'
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / 'provider-config.yaml'
        lines = ['# Auto-generated by GivEnum — do not edit; source: api_keys.json']
        for name, values in providers.items():
            lines.append(f'{name}:')
            for v in values:
                # yaml-safe: wrap in double quotes and escape any "
                lines.append(f'  - "{v.replace(chr(34), chr(92) + chr(34))}"')
        out_file.write_text('\n'.join(lines) + '\n')
        return out_file

    def sync_amass_config(self) -> Optional[Path]:
        """Generate an amass v4 config.yaml + datasources.yaml from configured keys.

        Returns the path to the top-level config.yaml (to be passed via `-config`),
        or None if no applicable keys are configured.
        """
        # amass v4 datasource schema: name, ttl, creds.account.{apikey,secret,username,password}
        ds_entries: List[str] = []
        kv = self.keys

        def _entry(name: str, apikey: str = '', secret: str = '',
                   username: str = '', password: str = '', ttl: int = 4320) -> str:
            lines = [f'  - name: {name}', f'    ttl: {ttl}',
                     '    creds:', '      account:']
            if apikey:
                lines.append(f'        apikey: "{apikey}"')
            if secret:
                lines.append(f'        secret: "{secret}"')
            if username:
                lines.append(f'        username: "{username}"')
            if password:
                lines.append(f'        password: "{password}"')
            return '\n'.join(lines)

        if kv.get('virustotal'):
            ds_entries.append(_entry('VirusTotal', apikey=kv['virustotal']))
        if kv.get('securitytrails'):
            ds_entries.append(_entry('SecurityTrails', apikey=kv['securitytrails']))
        if kv.get('shodan'):
            ds_entries.append(_entry('Shodan', apikey=kv['shodan'], ttl=10080))
        if kv.get('certspotter'):
            ds_entries.append(_entry('CertSpotter', apikey=kv['certspotter']))
        if kv.get('censys_id') and kv.get('censys_secret'):
            ds_entries.append(_entry('Censys', apikey=kv['censys_id'],
                                     secret=kv['censys_secret'], ttl=10080))
        if kv.get('fofa_email') and kv.get('fofa_key'):
            ds_entries.append(_entry('FOFA', username=kv['fofa_email'],
                                     apikey=kv['fofa_key']))
        if kv.get('github_token'):
            ds_entries.append(_entry('GitHub', apikey=kv['github_token']))
        if kv.get('hunter'):
            ds_entries.append(_entry('HunterIO', apikey=kv['hunter']))
        if kv.get('netlas'):
            ds_entries.append(_entry('Netlas', apikey=kv['netlas']))

        if not ds_entries:
            return None

        out_dir = self.config_file.parent / 'derived' / 'amass'
        out_dir.mkdir(parents=True, exist_ok=True)
        datasources_file = out_dir / 'datasources.yaml'
        config_file = out_dir / 'config.yaml'

        datasources_file.write_text(
            '# Auto-generated by GivEnum — do not edit; source: api_keys.json\n'
            'datasources:\n' + '\n'.join(ds_entries) + '\n'
        )
        config_file.write_text(
            '# Auto-generated by GivEnum — do not edit; source: api_keys.json\n'
            'scope: {}\n'
            'options:\n'
            f'  datasources: "{datasources_file}"\n'
        )
        return config_file


class ProxyConfig:
    """Proxy configuration — reads proxy.json written by the web UI."""

    def __init__(self):
        config_dir = Path(os.environ.get('GIVENUM_CONFIG_DIR', Path.home() / '.config' / 'givenum'))
        self.proxy_file = config_dir / 'proxy.json'
        self._cfg = self._load()

    def _load(self) -> dict:
        if self.proxy_file.exists():
            try:
                with open(self.proxy_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @property
    def enabled(self) -> bool:
        return bool(self._cfg.get('enabled', False))

    @property
    def http(self) -> str:
        return str(self._cfg.get('http', '')).strip()

    @property
    def https(self) -> str:
        return str(self._cfg.get('https', '')).strip()

    @property
    def no_proxy(self) -> str:
        return str(self._cfg.get('noProxy', '')).strip()

    def apply_env(self):
        """Inject proxy settings into os.environ so all child processes inherit them."""
        if not self.enabled:
            return
        if self.http:
            os.environ['HTTP_PROXY']  = self.http
            os.environ['http_proxy']  = self.http
        if self.https:
            os.environ['HTTPS_PROXY'] = self.https
            os.environ['https_proxy'] = self.https
        if self.no_proxy:
            os.environ['NO_PROXY']    = self.no_proxy
            os.environ['no_proxy']    = self.no_proxy

    def get_httpx_flag(self) -> list:
        """Return ['-proxy', url] for httpx/nuclei if enabled."""
        url = self.https or self.http
        if self.enabled and url:
            return ['-proxy', url]
        return []


class ToolChecker:
    """Checks if required tools are installed"""

    REQUIRED_TOOLS = {
        'subdomain': ['subfinder', 'assetfinder', 'findomain', 'amass', 'knockpy', 'github-subdomains', 'uncover'],
        'dns': ['dnsx', 'puredns', 'massdns', 'tlsx'],
        'http': ['httpx', 'hakcheckurl'],
        'url_collect': ['urlfinder', 'gau', 'hakrawler', 'katana', 'meg'],
        'js_analysis': ['subjs', 'jsubfinder', 'getJS', 'trufflehog'],
        'utils': ['anew', 'uro', 'unfurl', 'qsreplace', 'freq'],
        'scanning': ['nuclei', 'sdlookup'],
        'git': ['goop', 'git-dumper'],
        'optional': ['gowitness', 'subzy', 'subjack', 'dalfox', 'sqlmap', 'arjun', 'photon',
                     'jwt_tool', 's3scanner', 'byp4xx', 'kr']
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

    # P0 — without these the scan literally cannot start.
    CRITICAL_PASSIVE = ['subfinder', 'httpx', 'dnsx']
    CRITICAL_ACTIVE  = ['naabu', 'nuclei']

    # P1 — recommended; scan can run but loses a meaningful capability.
    RECOMMENDED_PASSIVE = ['amass', 'assetfinder', 'urlfinder', 'gau', 'katana', 'gowitness']
    RECOMMENDED_ACTIVE  = ['ffuf', 'dalfox', 'subzy']

    @classmethod
    def check_required(cls, active: bool = False) -> Tuple[List[str], List[str]]:
        """Return (critical_missing, recommended_missing) given a scan mode.

        Caller should bail out on `critical_missing` and only warn about
        `recommended_missing`. This makes failures explicit *before* a scan
        runs for hours and produces empty results.
        """
        critical = list(cls.CRITICAL_PASSIVE)
        recommended = list(cls.RECOMMENDED_PASSIVE)
        if active:
            critical.extend(cls.CRITICAL_ACTIVE)
            recommended.extend(cls.RECOMMENDED_ACTIVE)

        critical_missing = [t for t in critical if not cls.check_tool(t)]
        recommended_missing = [t for t in recommended if not cls.check_tool(t)]
        return critical_missing, recommended_missing


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


# Module-level tool execution log — reset at scan start via reset_tool_log().
# Multiple worker threads write here concurrently (subdomain enum, URL collection,
# JS analyzer, etc.). The lock prevents lost updates and torn reads.
_tool_log: Dict[str, dict] = {}
_tool_log_lock = threading.Lock()


def reset_tool_log():
    """Clear the tool log for a new scan."""
    global _tool_log
    with _tool_log_lock:
        _tool_log = {}


def record_tool_log(name: str, entry: dict) -> None:
    """Thread-safe write to the global tool log."""
    with _tool_log_lock:
        _tool_log[name] = entry


def snapshot_tool_log() -> Dict[str, dict]:
    """Return a thread-safe shallow copy of the current tool log."""
    with _tool_log_lock:
        return dict(_tool_log)


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


_STDOUT_LOG_LIMIT = 8_000  # chars — cap stdout in log files to avoid huge blobs


def _track_captured(name: str, result: subprocess.CompletedProcess, t0: float, log_dir: Path):
    """Record status and save stderr+stdout for a capture_output=True subprocess call."""
    elapsed = round(time.time() - t0, 1)
    _tool_log[name] = {
        'status': 'ok' if result.returncode == 0 else 'fail',
        'rc': result.returncode,
        'elapsed': elapsed,
    }
    parts: list[str] = []
    if result.stderr:
        parts.append(f"=== stderr ===\n{result.stderr}")
    if result.stdout:
        out = result.stdout
        truncated = len(out) > _STDOUT_LOG_LIMIT
        if truncated:
            out = out[:_STDOUT_LOG_LIMIT]
        parts.append(f"=== stdout{'  (truncated)' if truncated else ''} ===\n{out}")
    if parts:
        (log_dir / f"{name}.log").write_text('\n'.join(parts))


class OutputManager:
    """Manages output directories and files"""

    # Restrict the domain segment to characters legal in DNS/hostnames so
    # an attacker can't craft `../../../etc` and escape the results dir.
    # Allowed: letters, digits, dot, hyphen, underscore, colon (for ports),
    # asterisk (wildcard subs). The lookahead also requires at least one
    # alphanumeric character so meaningless inputs like `..` or `***` don't
    # produce gibberish output directories.
    _SAFE_DOMAIN_RE = re.compile(r'^(?=.*[A-Za-z0-9])[A-Za-z0-9._\-:*]{1,253}$')

    def __init__(self, base_dir: str, domain: str):
        if not self._SAFE_DOMAIN_RE.match(domain or ''):
            raise ValueError(
                f"Refusing to create output directory: domain {domain!r} contains "
                f"unsafe characters (path traversal attempt?)"
            )
        # Defense-in-depth: ensure the resolved path stays inside base_dir.
        self.domain = domain
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(base_dir).resolve()
        candidate = (base / f"{domain}_{self.timestamp}").resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Refusing to create output directory outside {base}: {candidate}"
            )
        self.base_dir = candidate

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
            'fuzzing': self.base_dir / 'fuzzing',
        }

        self._create_structure()

    def _create_structure(self):
        """Create directory structure"""
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        Logger.success(f"Structure created at: {self.base_dir}")

    def get_path(self, category: str, filename: str) -> Path:
        """Return full path for a file, validating that it stays inside its category dir."""
        category_dir = self.dirs[category].resolve()
        candidate = (category_dir / filename).resolve()
        try:
            candidate.relative_to(category_dir)
        except ValueError:
            raise ValueError(
                f"Refusing to write outside {category_dir}: {candidate}"
            )
        return candidate


class CertificateTransparency:
    """Certificate Transparency Log Enumeration"""
    
    def __init__(self, domain: str, output_mgr: OutputManager):
        self.domain = domain
        self.output_mgr = output_mgr
    
    def query_crtsh(self) -> Set[str]:
        """Query crt.sh for subdomains"""
        Logger.info("Querying crt.sh...")
        _t0 = time.time()
        try:
            url = f"https://crt.sh/?q=%.{self.domain}&output=json"
            # crt.sh frequently returns transient 404/502 when its Postgres
            # backend is overloaded. Retry the request a few times with a
            # longer wait before giving up.
            response = _api_request(url, timeout=30)
            if response is not None and response.status_code in (404, 502, 503):
                for wait in (15, 30, 60):
                    Logger.warning(f"crt.sh HTTP {response.status_code} — retrying in {wait}s")
                    time.sleep(wait)
                    response = _api_request(url, timeout=30)
                    if response is not None and response.status_code == 200:
                        break

            if response and response.status_code == 200:
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

                _tool_log['crtsh'] = {'status': 'ok', 'rc': 0, 'elapsed': round(time.time() - _t0, 1), 'found': len(domains)}
                Logger.success(f"crt.sh: {len(domains)} domains")
                return domains
            else:
                if response is None:
                    _tool_log['crtsh'] = {'status': 'fail', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': 'connection failed'}
                    Logger.warning("crt.sh: connection failed (all retries exhausted)")
                else:
                    _tool_log['crtsh'] = {'status': 'fail', 'rc': response.status_code, 'elapsed': round(time.time() - _t0, 1), 'msg': f'HTTP {response.status_code}'}
                    Logger.warning(f"crt.sh returned HTTP {response.status_code}")

        except Exception as e:
            _tool_log['crtsh'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
            Logger.error(f"Error querying crt.sh: {e}")

        return set()
    
    def query_certspotter(self, api_key: Optional[str] = None) -> Set[str]:
        """Query CertSpotter API"""
        Logger.info("Querying CertSpotter...")
        _t0 = time.time()
        try:
            url = f"https://api.certspotter.com/v1/issuances?domain={self.domain}&include_subdomains=true&expand=dns_names"
            headers = {}

            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'

            response = _api_request(url, headers=headers, timeout=30)

            if response and response.status_code == 200:
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

                _tool_log['certspotter'] = {'status': 'ok', 'rc': 0, 'elapsed': round(time.time() - _t0, 1), 'found': len(domains)}
                Logger.success(f"CertSpotter: {len(domains)} domains")
                return domains
            else:
                if response is None:
                    _tool_log['certspotter'] = {'status': 'fail', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': 'connection failed'}
                    Logger.warning("CertSpotter: connection failed (all retries exhausted)")
                else:
                    _tool_log['certspotter'] = {'status': 'fail', 'rc': response.status_code, 'elapsed': round(time.time() - _t0, 1), 'msg': f'HTTP {response.status_code}'}
                    Logger.warning(f"CertSpotter returned HTTP {response.status_code}")

        except Exception as e:
            _tool_log['certspotter'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
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
            _tool_log['virustotal'] = {'status': 'not_found', 'rc': -1, 'elapsed': 0, 'msg': 'No API key configured'}
            return set()

        Logger.info("Querying VirusTotal...")
        _t0 = time.time()
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
                if page_count > 0:
                    time.sleep(15)  # VT free-tier: 4 req/min
                response = _api_request(url, headers=headers, timeout=30)
                if not response or response.status_code != 200:
                    Logger.warning(f"VirusTotal returned status {response.status_code if response else 'no response'}")
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

            _tool_log['virustotal'] = {'status': 'ok', 'rc': 0, 'elapsed': round(time.time() - _t0, 1), 'found': len(domains)}
            Logger.success(f"VirusTotal: {len(domains)} domains")
            return domains

        except Exception as e:
            _tool_log['virustotal'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
            Logger.error(f"Error querying VirusTotal: {e}")

        return set()
    
    def query_alienvault(self) -> Set[str]:
        """Query AlienVault OTX"""
        Logger.info("Querying AlienVault OTX...")
        _t0 = time.time()
        try:
            url = f"https://otx.alienvault.com/api/v1/indicators/domain/{self.domain}/passive_dns"
            # OTX free tier rate-limits unauthenticated clients aggressively.
            # Cap retries at 2 with 15s base (waits: 15s+30s+60s ≈ 105s worst case).
            # If OTX is truly saturating our IP, longer waits (previously 465s)
            # don't help — better to fail fast and let other sources fill the gap.
            response = _api_request(url, timeout=30, max_retries=2, backoff=15.0)

            if response and response.status_code == 200:
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

                _tool_log['alienvault'] = {'status': 'ok', 'rc': 0, 'elapsed': round(time.time() - _t0, 1), 'found': len(domains)}
                Logger.success(f"AlienVault: {len(domains)} domains")
                return domains
            else:
                if response is None:
                    _tool_log['alienvault'] = {'status': 'fail', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': 'connection failed or rate-limited'}
                    Logger.warning("AlienVault: connection failed or rate-limited (all retries exhausted)")
                else:
                    _tool_log['alienvault'] = {'status': 'fail', 'rc': response.status_code, 'elapsed': round(time.time() - _t0, 1), 'msg': f'HTTP {response.status_code}'}
                    Logger.warning(f"AlienVault returned HTTP {response.status_code}")

        except Exception as e:
            _tool_log['alienvault'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
            Logger.error(f"Error querying AlienVault: {e}")

        return set()
    
    def query_securitytrails(self) -> Set[str]:
        """Query SecurityTrails API"""
        api_key = self.api_config.get_key('securitytrails')
        if not api_key:
            Logger.warning("SecurityTrails API key not configured")
            _tool_log['securitytrails'] = {'status': 'not_found', 'rc': -1, 'elapsed': 0, 'msg': 'No API key configured'}
            return set()

        Logger.info("Querying SecurityTrails...")
        _t0 = time.time()
        try:
            url = f"https://api.securitytrails.com/v1/domain/{self.domain}/subdomains"
            headers = {'APIKEY': api_key}
            response = _api_request(url, headers=headers, timeout=30)

            if response and response.status_code == 200:
                data = response.json()
                domains = set()

                for subdomain in data.get('subdomains', []):
                    full_domain = f"{subdomain}.{self.domain}"
                    domains.add(full_domain)

                output_file = self.output_mgr.get_path('api_data', 'securitytrails.txt')
                with open(output_file, 'w') as f:
                    f.write('\n'.join(sorted(domains)) + '\n')

                _tool_log['securitytrails'] = {'status': 'ok', 'rc': 0, 'elapsed': round(time.time() - _t0, 1), 'found': len(domains)}
                Logger.success(f"SecurityTrails: {len(domains)} domains")
                return domains
            else:
                status_code = response.status_code if response else 0
                _tool_log['securitytrails'] = {'status': 'fail', 'rc': status_code, 'elapsed': round(time.time() - _t0, 1), 'msg': f'HTTP {status_code}'}

        except Exception as e:
            _tool_log['securitytrails'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
            Logger.error(f"Error querying SecurityTrails: {e}")

        return set()


class SubdomainEnum:
    """Comprehensive subdomain enumeration"""

    def __init__(self, domain: str, output_mgr: OutputManager, api_config: APIConfig):
        self.domain = domain
        self.output_mgr = output_mgr
        self.api_config = api_config
        _sf_threads = min(20, max(10, _CPU_COUNT * 2))
        _proxy_flag = _get_proxy_flag()
        # Feed UI-configured API keys into subfinder via an auto-generated
        # provider-config.yaml (keeps user-owned ~/.config/subfinder untouched).
        _sf_pc_flag: List[str] = []
        try:
            _sf_pc = self.api_config.sync_subfinder_config()
            if _sf_pc:
                _sf_pc_flag = ['-pc', str(_sf_pc)]
        except Exception as e:
            Logger.warning(f"Could not sync subfinder provider-config: {e}")
        self.tools = {
            'subfinder': ['subfinder', '-d', domain, '-all', '-silent', '-t', str(_sf_threads)] + _sf_pc_flag + _proxy_flag,
            'assetfinder': ['assetfinder', '--subs-only', domain],
            'findomain': ['findomain', '-t', domain, '-q'],
            # amass has a slow startup and different output conventions per version —
            # it runs in its own dedicated slot after the parallel pool (see run_amass()).
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

            # Patch found count into existing log entry set by _track_captured
            if tool_name in _tool_log:
                _tool_log[tool_name]['found'] = len(subs)
                # Non-zero exit with results → partial (not fail).
                # amass/findomain often exit rc=1 on network timeouts yet still return data.
                if result.returncode != 0 and subs:
                    _tool_log[tool_name]['status'] = 'partial'
            if result.returncode == 0:
                Logger.success(f"{tool_name}: {len(subs)} subdomains")
            else:
                Logger.warning(f"{tool_name}: rc={result.returncode}, recovered {len(subs)} subdomains")
            return subs

        except subprocess.TimeoutExpired:
            _tool_log[tool_name] = {'status': 'timeout', 'rc': -1, 'elapsed': round(time.time() - _t0, 1)}
            Logger.warning(f"{tool_name} timeout")
        except Exception as e:
            Logger.error(f"Error running {tool_name}: {e}")

        return set()

    def run_amass(self) -> Set[str]:
        """Run amass in its own dedicated slot after the parallel pool.

        amass has two quirks that make it unsuitable for the shared pool:
          1. Slow startup — it initialises a local DB and multiple data sources
             before emitting any output, so it always "finishes" last, blocking
             faster tools from starting.
          2. Version variance — amass v3 writes to stdout; amass v4 may write
             only to the local DB or to a `-o` file.  We force `-o` so we always
             read results from a file rather than stdout.

        Skip-fast contract (TASK #25):
          Without API keys (Shodan / Censys / VirusTotal / etc.), amass
          falls back to the same free sources that subfinder/assetfinder/
          crt.sh already cover. On the bscash.com.br scan it burned
          617 seconds for ZERO new subdomains. We now check for at least
          one configured datasource key and skip the run entirely if none
          exist, saving ~10 min per scan.
        """
        if not ToolChecker.check_tool('amass'):
            _tool_log['amass'] = {'status': 'not_found', 'rc': -1, 'elapsed': 0}
            return set()

        # Pre-check: is there at least one API key configured for amass?
        # sync_amass_config() returns None when zero applicable keys are set.
        try:
            _amass_cfg = self.api_config.sync_amass_config()
        except Exception as e:
            Logger.warning(f"Could not sync amass config: {e}")
            _amass_cfg = None

        if _amass_cfg is None:
            Logger.warning(
                "amass: skipping — no API keys configured (Shodan/Censys/VirusTotal "
                "etc.). Without keys, amass duplicates subfinder/assetfinder/crt.sh "
                "and burns ~10 min for no extra coverage. Run --configure-api or use "
                "the dashboard /settings/apis to enable."
            )
            _tool_log['amass'] = {
                'status':  'skipped',
                'rc':      0,
                'elapsed': 0,
                'msg':     'no datasource API keys configured',
            }
            return set()

        Logger.info("Running amass (passive, dedicated slot — up to 10 min)...")
        output_file = self.output_mgr.get_path('subdomains', 'amass.txt')
        _t0 = time.time()

        try:
            _proxy_args = _get_proxy_flag()
            # API key config already validated above — pass it to amass.
            _amass_config_flag: List[str] = ['-config', str(_amass_cfg)]
            result = subprocess.run(
                [
                    'amass', 'enum', '-passive',
                    '-d', self.domain,
                    '-o', str(output_file),   # force file output — reliable across all versions
                    '-timeout', '10',          # amass-internal cap in minutes
                ] + _amass_config_flag + _proxy_args,
                capture_output=True,
                text=True,
                timeout=660,  # hard cap: 11 min (1 min headroom over internal timeout)
            )
            _track_captured('amass', result, _t0, self.output_mgr.dirs['logs'])

            # Collect from -o file (primary) + stdout fallback
            subs: Set[str] = set()
            if output_file.exists():
                for line in output_file.read_text().splitlines():
                    sub = line.strip()
                    if sub and matches_domain(sub, self.domain):
                        subs.add(sub)
            for line in result.stdout.splitlines():
                sub = line.strip()
                if sub and matches_domain(sub, self.domain):
                    subs.add(sub)

            if 'amass' in _tool_log:
                _tool_log['amass']['found'] = len(subs)
                if result.returncode != 0 and subs:
                    _tool_log['amass']['status'] = 'partial'
                elif not subs:
                    # rc=0 with 0 subs usually means missing data-source keys
                    # (~/.config/amass/config.yaml) — report as partial so the
                    # summary surfaces the miss instead of a misleading ✓.
                    _tool_log['amass']['status'] = 'partial'

            if subs:
                Logger.success(f"amass: {len(subs)} subdomains (rc={result.returncode})")
            else:
                Logger.warning(f"amass: 0 subdomains (rc={result.returncode}) — check logs/amass.log (often missing data-source API keys)")

            return subs

        except subprocess.TimeoutExpired:
            _tool_log['amass'] = {'status': 'timeout', 'rc': -1, 'elapsed': round(time.time() - _t0, 1)}
            Logger.warning("amass: timeout (10-min budget exhausted)")
            return set()
        except Exception as e:
            _tool_log['amass'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
            Logger.error(f"amass error: {e}")
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
            _tool_log['uncover'] = {'status': 'timeout', 'rc': -1, 'elapsed': round(time.time() - _t0, 1)}
            Logger.warning("uncover timeout")
            return set()
        except Exception as e:
            _tool_log['uncover'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
            Logger.error(f"Error in uncover: {e}")
            return set()

    def run_all(self) -> Path:
        """Run all enumeration tools including APIs and CT logs"""
        Logger.header("SUBDOMAIN ENUMERATION")


        all_subs = set()

        # Traditional tools + CT + passive APIs all in parallel
        ct = CertificateTransparency(self.domain, self.output_mgr)
        apis = PassiveAPIs(self.domain, self.output_mgr, self.api_config)

        # AlienVault is rate-limited aggressively — run it after the parallel pool to
        # avoid 429s from concurrent HTTP traffic across all other sources firing at once.
        enum_tasks: list[tuple[str, any]] = [
            *[(name, (self.run_tool, name, cmd)) for name, cmd in self.tools.items() if cmd],
            ('crtsh',         (ct.query_crtsh,)),
            ('certspotter',   (ct.query_certspotter, self.api_config.get_key('certspotter'))),
            ('virustotal',    (apis.query_virustotal,)),
            ('securitytrails',(apis.query_securitytrails,)),
        ]

        _workers = min(len(enum_tasks), max(5, _CPU_COUNT))
        Logger.info(f"Subdomain enumeration: {len(enum_tasks)} sources in parallel (workers={_workers})")

        def _run_task(task):
            fn, *args = task
            return fn(*args)

        with ThreadPoolExecutor(max_workers=_workers) as executor:
            futures = {executor.submit(_run_task, t): name for name, t in enum_tasks}
            for future in as_completed(futures):
                try:
                    subs = future.result()
                    if subs:
                        all_subs.update(subs)
                except Exception as e:
                    Logger.warning(f"Enum task {futures[future]} error: {e}")

        # AlienVault — run sequentially after the pool so it doesn't compete for rate limits
        all_subs.update(apis.query_alienvault())

        # amass — dedicated slot after pool: slow startup + version-variant output
        all_subs.update(self.run_amass())

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

            # sdlookup reads IPs from stdin and writes JSON to stdout.
            # -json: emit Shodan InternetDB JSON per IP.
            # The old flag combo (-i/-json/-o) caused exit code 2 due to the -o
            # flag; stdin+stdout works universally across sdlookup versions.
            _sdl_t0 = time.time()
            with open(ip_file, 'r') as stdin_f:
                result = subprocess.run(
                    ['sdlookup', '-c', '50', '-json'],
                    stdin=stdin_f,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            _track_captured('sdlookup', result, _sdl_t0, self.output_mgr.dirs['logs'])

            # Write raw output so the parse step can read it
            raw_out = result.stdout.strip()
            if raw_out:
                output_file.write_text(result.stdout)

            # Parse results robustly: sdlookup may emit objects concatenated on
            # one line without separating newlines.  Use raw_decode to walk the
            # stream and extract every valid JSON object regardless of spacing.
            def _iter_json_objects(text: str):
                decoder = json.JSONDecoder()
                pos = 0
                text = text.strip()
                while pos < len(text):
                    try:
                        obj, end = decoder.raw_decode(text, pos)
                        yield obj
                        pos = end
                        while pos < len(text) and text[pos] in ' \t\r\n':
                            pos += 1
                    except json.JSONDecodeError:
                        pos += 1

            if output_file.exists():
                raw_text = output_file.read_text()
                data = list(_iter_json_objects(raw_text))

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

    def scan_with_naabu(self, input_file: Path):
        """Fast active port scan with naabu — runs on resolved subdomains."""
        if not ToolChecker.check_tool('naabu'):
            Logger.warning("naabu not found, skipping active port scan")
            return

        # naabu exits rc=1 when it can't resolve anything in the input — common
        # when DNS resolution is CDN-masked (Akamai/Cloudflare) and puredns+dnsx
        # return 0. Short-circuit with a clear 'skipped' status instead of a
        # misleading 'fail'.
        try:
            host_count = sum(1 for ln in input_file.read_text().splitlines() if ln.strip())
        except Exception:
            host_count = 0
        if host_count == 0:
            _tool_log['naabu'] = {'status': 'skipped', 'rc': 0, 'elapsed': 0,
                                  'msg': 'no hosts to scan (empty input)'}
            Logger.info("naabu: skipped — no hosts to scan")
            return

        Logger.info("Scanning ports with naabu (active)...")
        output_file = self.output_mgr.get_path('ports', 'naabu_results.txt')

        # naabu should always connect directly — proxy adds too much noise
        _direct_env = {k: v for k, v in os.environ.items()
                       if k.upper() not in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
                                            'http_proxy', 'https_proxy', 'all_proxy')}
        try:
            cmd = [
                'naabu',
                '-l', str(input_file),
                # Common web, API, DB, cache, and non-standard ports
                '-p', ','.join([
                    '80,443,8080,8443,8000,8888,3000,5000,9090,9443',
                    '8081,8082,8083,8084,8085,8086,8887,9000,9001,9002',
                    '6443,4443,3128,8181,10443,8899,7070,7443',
                    '22,21,25,110,143,993,995,389,636',   # infra
                    '3306,5432,1433,1521,27017,6379,9200,9300,2181',  # DBs
                ]),
                '-silent',
                '-o', str(output_file),
                '-rate', '1000',
                '-timeout', '5',
                '-retries', '2',
                '-c', str(min(50, _CPU_COUNT * 4)),
            ]
            # stdout=DEVNULL: naabu prints every open port to stdout in addition to
            # the -o file, which doubles every line in the scan log.  Discard stdout
            # here — the -o file is the authoritative result set.
            # check=False: naabu exits rc=1 when every input host is unresolvable
            # (common with CDN-masked DNS). We handle that gracefully below.
            result = run_logged('naabu', cmd, self.output_mgr.dirs['logs'],
                                timeout=600, check=False, env=_direct_env,
                                stdout=subprocess.DEVNULL)

            if output_file.exists():
                count = count_nonempty_lines(output_file)
                if count:
                    Logger.success(f"naabu: {count} open ports found")
                    _tool_log['naabu']['found'] = count
                elif result.returncode != 0:
                    # rc!=0 + no output = all inputs unresolvable — skipped, not fail.
                    _tool_log['naabu']['status'] = 'skipped'
                    _tool_log['naabu']['msg'] = f'rc={result.returncode}, likely all hosts unresolvable'
                    Logger.info("naabu: skipped — no resolvable hosts")
                else:
                    Logger.info("naabu: no open ports found")
            elif result.returncode != 0:
                _tool_log['naabu']['status'] = 'skipped'
                _tool_log['naabu']['msg'] = f'rc={result.returncode}, no output file'
                Logger.info("naabu: skipped — no resolvable hosts")
        except Exception as e:
            Logger.error(f"Error in naabu: {e}")


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
            _httpx_threads = min(100, max(50, _CPU_COUNT * 8))
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
                '-rate-limit', str(min(300, _CPU_COUNT * 25)),
                '-threads', str(_httpx_threads),
                '-retries', '1',
                '-json',
                '-o', str(json_file)
            ]
            # httpx must connect directly — routing through a proxy (even a fast one)
            # causes false-negative results because free proxies can't reach all IPs.
            _direct_env = {k: v for k, v in os.environ.items()
                           if k.upper() not in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
                                                'http_proxy', 'https_proxy', 'all_proxy')}

            run_logged('httpx', cmd, self.output_mgr.dirs['logs'], timeout=600, check=True,
                       stdout=subprocess.DEVNULL, env=_direct_env)

            # Extract URLs
            urls = []
            with open(json_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        urls.append(data.get('url', ''))
                    except (json.JSONDecodeError, AttributeError):
                        # Malformed line in httpx JSON output — skip silently,
                        # this is expected for partial reads / mixed output.
                        continue

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
            _proxy = _get_proxy_flag()
            # gowitness uses --proxy <url> syntax
            _gowitness_proxy = ['--proxy', _proxy[1]] if _proxy else []
            cmd = [
                'gowitness', 'scan', 'file',
                '-f', str(input_file),
                '--screenshot-path', str(screenshots_dir),
                '--write-db',
                '--write-db-uri', f'sqlite://{db_file}',
            ] + _gowitness_proxy

            run_logged('gowitness', cmd, self.output_mgr.dirs['logs'], timeout=1800, check=True)
            Logger.success(f"Screenshots saved to {screenshots_dir}")

        except Exception as e:
            Logger.error(f"Error in gowitness: {e}")


class URLCollector:
    """Advanced URL collection with modern tools"""

    def __init__(self, output_mgr: OutputManager, domain: str = ''):
        self.output_mgr = output_mgr
        # `domain` is the target root used by zone-level archive collectors
        # (currently urlfinder; see collect_with_urlfinder). Defaults to ''
        # for backward compat with any caller that doesn't pass it — those
        # paths simply skip domain-aware collectors with a clear log msg.
        self.domain = domain

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

    def _archive_targets(self, input_file: Path, cap: int = 12) -> List[str]:
        """Build target list for archive lookups (gau).

        Always includes apex + www; then fills remaining slots with unique
        active hosts from httpx output. Archive sources are domain-level, so
        feeding sibling subdomains surfaces URLs the apex alone misses.
        """
        root = self.output_mgr.domain
        seen: List[str] = []
        seen_set: Set[str] = set()

        for candidate in (root, f'www.{root}'):
            if candidate not in seen_set:
                seen.append(candidate); seen_set.add(candidate)

        try:
            for host in self._load_hosts(input_file):
                if host not in seen_set and matches_domain(host, root):
                    seen.append(host); seen_set.add(host)
                    if len(seen) >= cap:
                        break
        except Exception:
            pass
        return seen[:cap]

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
        bad = failures + timeouts
        if bad == 0:
            return 'ok', 0
        if bad >= total:
            # Everything failed
            if timeouts and failures == 0:
                return 'timeout', -1
            return 'fail', 1
        # Some succeeded — report partial when >30% failed/timed out
        if bad / total > 0.30:
            return 'partial', 0
        return 'ok', 0

    @staticmethod
    def _parse_meg_urls(content: str) -> Set[str]:
        urls = set()
        for line in content.splitlines():
            match = re.search(r'(https?://\S+)\s+\((\d{3})\b', line.strip())
            if match and match.group(2) == '200':
                urls.add(match.group(1))
        return urls

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

            _KATANA_BUDGET = 480  # total wall-clock budget (was 600s — reduced after
                                  # katana routinely consumed 50% of total scan time)
            _katana_rl = min(500, max(200, _CPU_COUNT * 30))
            all_urls = set()
            katana_timeouts = 0
            katana_failures = 0
            katana_skipped = 0
            _kt0 = time.time()

            for idx, host in enumerate(hosts[:50], start=1):
                if time.time() - _kt0 > _KATANA_BUDGET:
                    katana_skipped = len(hosts[:50]) - idx + 1
                    Logger.warning(f"katana: budget {_KATANA_BUDGET}s reached at host {idx} — skipping {katana_skipped}")
                    break
                try:
                    # Katana needs direct connections — proxy adds unreliability
                    # (free proxies frequently fail → 0 URLs from all hosts)
                    _katana_env = {k: v for k, v in os.environ.items()
                                   if k.upper() not in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
                                                        'http_proxy', 'https_proxy', 'all_proxy')}
                    # Bail per-host earlier if remaining budget is tight; keeps
                    # one slow host from eating the entire remaining budget.
                    _remaining = max(10, _KATANA_BUDGET - int(time.time() - _kt0))
                    _per_host = min(45, _remaining)
                    result = subprocess.run(
                        ['katana', '-u', host, '-silent', '-depth', '2', '-jc',
                         '-timeout', '10', '-rate-limit', str(_katana_rl), '-c', str(min(20, _CPU_COUNT * 2))],
                        capture_output=True,
                        text=True,
                        timeout=_per_host,
                        env=_katana_env,
                    )
                    self._append_log(log_file, f"{host} (rc={result.returncode})", result.stderr)
                    if result.returncode != 0:
                        katana_failures += 1
                    batch_urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                    all_urls.update(batch_urls)
                    if idx == 1 or idx % 10 == 0 or idx == len(hosts):
                        Logger.info(f"katana progress: {idx}/{min(len(hosts), 50)} hosts, {len(all_urls)} URLs")
                except subprocess.TimeoutExpired:
                    katana_timeouts += 1
                    self._append_log(log_file, f"{host} (timeout)", '')
                    Logger.warning(f"katana timeout on {host}")
                except Exception as e:
                    katana_failures += 1
                    self._append_log(log_file, f"{host} (error)", str(e))

            total = min(len(hosts), 50) - katana_skipped
            status, rc = self._summarize_batch_status(total, katana_failures, katana_timeouts)
            if katana_skipped > 0:
                status = 'partial'
            _tool_log['katana'] = {
                'status': status, 'rc': rc,
                'elapsed': round(time.time() - _t0, 1),
                'urls': len(all_urls), 'timeouts': katana_timeouts,
                'failures': katana_failures, 'skipped': katana_skipped,
            }

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(all_urls)) + '\n')

            Logger.success(f"katana: {len(all_urls)} URLs")
            return all_urls

        except Exception as e:
            _tool_log['katana'] = {'status': 'error', 'rc': -1, 'elapsed': 0, 'msg': str(e)}
            Logger.error(f"Error in katana: {e}")
            return set()

    def _collect_with_gau(self, input_file: Path) -> Set[str]:
        """Fetch archived URLs with gau — runs on the *full* subdomain list
        (all_subdomains.txt when available, falling back to the passed file).

        Rationale: archive sources may have URLs for subdomains that probed as
        inactive. Running gau on every known subdomain with --subs surfaces
        URLs that mention sub-sub-domains we hadn't discovered. Parallelised
        with a small pool to keep total wall-clock within budget.

        Key fix: always pass --providers explicitly so behaviour is identical
        whether or not ~/.gau.toml exists (Docker vs macOS vs CI).
        --timeout here is the HTTP request timeout *to each archive source*,
        not a total wall-clock cap (the subprocess timeout handles that).
        """
        if not ToolChecker.check_tool('gau'):
            return set()

        gau_file = self.output_mgr.get_path('urls', 'gau.txt')
        gau_log  = self.output_mgr.get_path('logs', 'gau.log')

        # Prefer the full subdomain list so gau covers inactive/unresolvable hosts
        # whose URLs might still live in archive sources. Fall back to whatever
        # the caller passed (typically alive.txt).
        all_subs_file = self.output_mgr.get_path('subdomains', 'all_subdomains.txt')
        source_file = all_subs_file if all_subs_file.exists() else input_file
        targets = self._archive_targets(source_file, cap=200)

        # gau must bypass proxy — routing archive fetches through free proxies
        # turns Wayback/OTX requests into timeouts and returns 0 URLs even when
        # live sources have data.
        _direct_env = {k: v for k, v in os.environ.items()
                       if k.upper() not in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
                                            'http_proxy', 'https_proxy', 'all_proxy')}

        urls: set[str] = set()
        timeouts = failures = skipped = 0
        _BUDGET = 600
        _t0 = time.time()
        _lock = threading.Lock()
        _log_lock = threading.Lock()

        def _run_one(domain: str) -> Tuple[str, int, str]:
            """Returns (domain, batch_size, status) where status ∈ ok/timeout/fail."""
            remaining = _BUDGET - (time.time() - _t0)
            if remaining < 20:
                return domain, 0, 'skipped'
            try:
                result = subprocess.run(
                    [
                        'gau',
                        '--threads', '5',
                        '--timeout', '20',
                        '--retries', '2',
                        '--providers', 'otx,urlscan,wayback',
                        '--blacklist', 'ttf,woff,woff2,svg,png,jpg,jpeg,gif,ico,css,eot,mp4,mp3',
                        '--subs',
                    ],
                    input=domain + '\n',
                    capture_output=True,
                    text=True,
                    timeout=min(90, int(remaining)),
                    env=_direct_env,
                )
                with _log_lock:
                    self._append_log(gau_log, f"{domain} (rc={result.returncode})", result.stderr)
                if result.returncode != 0:
                    return domain, 0, 'fail'
                batch = {l.strip() for l in result.stdout.splitlines() if l.strip()}
                with _lock:
                    before = len(urls)
                    urls.update(batch)
                    delta = len(urls) - before
                if batch:
                    Logger.info(f"gau: {domain} → {len(batch)} URLs (+{delta} new, total {len(urls)})")
                return domain, len(batch), 'ok'
            except subprocess.TimeoutExpired:
                with _log_lock:
                    self._append_log(gau_log, f"{domain} (timeout)", '')
                return domain, 0, 'timeout'
            except Exception as e:
                with _log_lock:
                    self._append_log(gau_log, f"{domain} (error)", str(e))
                return domain, 0, 'fail'

        # Small pool: gau itself opens 5 internal threads per call → 3 workers
        # ≈ 15 concurrent archive HTTP reqs, high enough to finish in budget
        # without tripping OTX/Wayback rate-limits.
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(_run_one, d): d for d in targets}
            for fut in as_completed(futures):
                domain, _, st = fut.result()
                if st == 'skipped':
                    skipped += 1
                elif st == 'timeout':
                    timeouts += 1
                    Logger.warning(f"gau timeout on {domain}")
                elif st == 'fail':
                    failures += 1
                    Logger.warning(f"gau failed on {domain}")

        status, rc = self._summarize_batch_status(len(targets), failures, timeouts)
        if skipped > 0:
            status = 'partial'
        _tool_log['gau'] = {'status': status, 'rc': rc,
                            'elapsed': round(time.time() - _t0, 1),
                            'timeouts': timeouts, 'failures': failures,
                            'skipped': skipped, 'urls': len(urls)}
        gau_file.write_text('\n'.join(sorted(urls)) + '\n')
        Logger.success(
            f"gau: {len(urls)} URLs (hosts={len(targets)}, "
            f"timeouts={timeouts}, failures={failures}, skipped={skipped})"
        )

        # Harvest new subdomains from the URL corpus — a host may appear in
        # archived URLs even when it probed as inactive.
        self._harvest_subs_from_urls(urls)

        return urls

    def _harvest_subs_from_urls(self, urls: Set[str]) -> None:
        """Extract hostnames from URLs that match the target domain and merge
        them into all_subdomains.txt (dedup). Writes harvested-only set to
        subdomains/gau_harvested.txt for visibility."""
        root = self.output_mgr.domain
        harvested: Set[str] = set()
        for u in urls:
            try:
                host = urlparse(u).hostname or ''
            except Exception:
                continue
            host = host.lower().rstrip('.')
            if host and matches_domain(host, root):
                harvested.add(host)
        if not harvested:
            return

        all_subs_file = self.output_mgr.get_path('subdomains', 'all_subdomains.txt')
        existing: Set[str] = set()
        if all_subs_file.exists():
            for line in all_subs_file.read_text().splitlines():
                s = line.strip().lower()
                if s:
                    existing.add(s)
        new_subs = harvested - existing
        harvested_file = self.output_mgr.get_path('subdomains', 'gau_harvested.txt')
        harvested_file.write_text('\n'.join(sorted(harvested)) + '\n')
        if new_subs:
            merged = sorted(existing | new_subs)
            all_subs_file.write_text('\n'.join(merged) + '\n')
            Logger.success(f"gau harvested {len(new_subs)} new subdomains from archived URLs")

    def collect_with_urlfinder(self, input_file: Path) -> Set[str]:
        """Collect URLs with urlfinder (ProjectDiscovery's high-speed passive collector).

        urlfinder unifies multiple archive sources (Wayback, Common Crawl,
        AlienVault OTX, etc.) behind PD's retryable HTTP client and rate-limiter.

        Why -d (root domain) instead of -list (host list)?
        urlfinder's archive sources are *zone-level*: querying `tesla.com` already
        returns URLs from every subdomain found in Wayback/CC/etc. The first
        integration used `-list` on the host file, which made urlfinder do
        N redundant zone queries (one per host) — and apparently triggered
        provider-side throttling, returning 0 URLs in 600 s on both bscash and
        tesla. The official upstream example (`urlfinder -d tesla.com`)
        finishes in ~2.5 min with ~200k URLs.

        Why -all? Without it urlfinder only enables the small subset of
        providers that don't need a key — usually nothing useful comes back.
        `-all` enables every source the binary knows about; the ones that
        require keys silently skip if no provider-config.yaml is present.

        We still filter results to the configured domain just in case a
        provider returns out-of-scope URLs, since the orchestrator hands the
        whole URL set to downstream tools (gf, nuclei, dalfox).
        """
        if not ToolChecker.check_tool('urlfinder'):
            Logger.warning("urlfinder not found, skipping (install via /settings/tools)")
            record_tool_log('urlfinder', {
                'status': 'not_found', 'rc': -1, 'elapsed': 0,
            })
            return set()

        if not self.domain:
            Logger.warning(
                "urlfinder skipped — URLCollector was instantiated without a "
                "domain (caller bug). Pass URLCollector(output_mgr, domain)."
            )
            record_tool_log('urlfinder', {
                'status': 'skipped', 'rc': 0, 'elapsed': 0,
                'msg': 'no domain passed to URLCollector',
            })
            return set()

        Logger.info(f"Collecting URLs with urlfinder (PD) for -d {self.domain} -all ...")
        output_file = self.output_mgr.get_path('urls', 'urlfinder.txt')
        log_file    = self.output_mgr.get_path('logs', 'urlfinder.log')
        budget_s    = 600  # 10-minute hard cap

        # input_file is unused — kept in the signature for parity with the
        # other collectors so the orchestrator's `_crawlers` dict stays uniform.
        _ = input_file

        t0 = time.time()
        try:
            with open(log_file, 'w') as lf:
                result = subprocess.run(
                    ['urlfinder',
                     '-d',      self.domain,
                     '-all',
                     '-o',      str(output_file),
                     '-silent'],
                    stderr=lf,
                    stdout=subprocess.DEVNULL,
                    timeout=budget_s,
                )
            elapsed = round(time.time() - t0, 1)

            # Parse + filter to scope. Some providers (especially OTX) leak
            # cross-zone URLs; trust matches_domain() as the gatekeeper.
            urls: Set[str] = set()
            in_scope_count = 0
            out_of_scope_count = 0
            if output_file.exists():
                with open(output_file, 'r') as f:
                    for raw in f:
                        line = raw.strip()
                        if not line:
                            continue
                        try:
                            host = urlparse(line).hostname or ''
                        except Exception:
                            host = ''
                        if host and matches_domain(host, self.domain):
                            urls.add(line)
                            in_scope_count += 1
                        else:
                            out_of_scope_count += 1

            status = 'ok' if result.returncode == 0 else 'partial'
            record_tool_log('urlfinder', {
                'status':       status,
                'rc':           result.returncode,
                'elapsed':      elapsed,
                'urls':         len(urls),
                'in_scope':     in_scope_count,
                'out_of_scope': out_of_scope_count,
            })
            if out_of_scope_count:
                Logger.success(
                    f"urlfinder: {len(urls)} in-scope URLs in {elapsed}s "
                    f"({out_of_scope_count} out-of-scope filtered)"
                )
            else:
                Logger.success(f"urlfinder: {len(urls)} URLs in {elapsed}s")
            return urls

        except subprocess.TimeoutExpired:
            elapsed = round(time.time() - t0, 1)
            record_tool_log('urlfinder', {
                'status': 'timeout', 'rc': -1, 'elapsed': elapsed,
                'msg': f'budget {budget_s}s exhausted',
            })
            Logger.warning(f"urlfinder: budget {budget_s}s reached")
            return set()
        except Exception as e:
            elapsed = round(time.time() - t0, 1)
            record_tool_log('urlfinder', {
                'status': 'error', 'rc': -1, 'elapsed': elapsed, 'msg': str(e),
            })
            Logger.error(f"urlfinder error: {e}")
            return set()

    def collect_from_archives(self, input_file: Path) -> Set[str]:
        """Collect URLs — ALL crawlers and archive tools run fully in parallel."""
        Logger.header("URL COLLECTION")

        all_urls: set[str] = set()
        _lock = threading.Lock()

        # All sources run concurrently — each has its own internal budget/timeout.
        # Archive collectors: urlfinder (PD) is primary, gau is healthy backup.
        # Live crawlers: katana + hakrawler crawl the host list directly.
        #
        # waybackurls and xurlfind3r were removed (TASK #23/#24) after returning
        # 0 URLs in 4/4 real scans (bscash, tesla x2, paypal). urlfinder + gau
        # already cover Wayback/OTX/CommonCrawl. To resurrect either, see
        # `git log --diff-filter=D --name-only -- GivEnum.py`.
        _crawlers = [
            ('urlfinder',    self.collect_with_urlfinder,     input_file),
            ('gau',          self._collect_with_gau,          input_file),
            ('katana',       self.collect_with_katana,        input_file),
            ('hakrawler',    self.collect_with_hakrawler,     input_file),
        ]

        Logger.info(f"Launching {len(_crawlers)} URL sources in parallel "
                    f"(urlfinder/gau: archive  |  katana/hakrawler: live crawl)…")

        with ThreadPoolExecutor(max_workers=len(_crawlers)) as executor:
            futures = {executor.submit(fn, arg): name for name, fn, arg in _crawlers}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    urls = future.result()
                    with _lock:
                        all_urls.update(urls)
                    Logger.info(f"  [{name}] finished → {len(urls)} URLs  (running total: {len(all_urls)})")
                except Exception as e:
                    Logger.warning(f"  [{name}] crashed: {e}")

        return all_urls

    def collect_with_hakrawler(self, input_file: Path) -> Set[str]:
        """Crawl URLs with hakrawler"""
        if not ToolChecker.check_tool('hakrawler'):
            Logger.warning("hakrawler not found")
            return set()

        Logger.info("Crawling with hakrawler...")
        output_file = self.output_mgr.get_path('urls', 'hakrawler.txt')
        _t0 = time.time()
        try:
            # Collect hosts from file, then pass as stdin to hakrawler.
            # -d 2 = crawl depth; -u = output only URLs; -t 5 = thread limit
            # Note: hakrawler has no domain-scope flag — scoping is implicit since
            # the stdin lines are the target URLs.  The old -h flag is for HTTP
            # headers, NOT domain filtering — using it caused immediate failure.
            # Direct env — proxy breaks live crawling same as httpx/katana
            _hak_env = {k: v for k, v in os.environ.items()
                        if k.upper() not in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
                                             'http_proxy', 'https_proxy', 'all_proxy')}
            with open(input_file, 'r') as f:
                result = subprocess.run(
                    ['hakrawler', '-d', '2', '-u', '-t', '5', '-timeout', '10'],
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=_hak_env,
                )
            _track_captured('hakrawler', result, _t0, self.output_mgr.dirs['logs'])

            urls = set(line.strip() for line in result.stdout.split('\n') if line.strip())

            # rc=0 with zero URLs is ambiguous: could be API-only target (no HTML
            # to crawl) or a silent failure (proxy 502, DNS, etc.). Surface as
            # 'partial' when hosts were present so the issue is not hidden.
            if result.returncode == 0 and not urls:
                try:
                    host_count = sum(1 for ln in input_file.read_text().splitlines() if ln.strip())
                except Exception:
                    host_count = 0
                if host_count > 0:
                    _tool_log['hakrawler']['status'] = 'partial'

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(urls)) + '\n')

            Logger.success(f"hakrawler: {len(urls)} URLs")
            return urls

        except subprocess.TimeoutExpired:
            _tool_log['hakrawler'] = {'status': 'timeout', 'rc': -1, 'elapsed': round(time.time() - _t0, 1)}
            Logger.warning("hakrawler timed out")
            return set()
        except Exception as e:
            _tool_log['hakrawler'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
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

        # Paths probed on every host — biased towards findings that appear in real reports
        interesting_paths = [
            # Discovery & metadata
            '/robots.txt', '/sitemap.xml', '/sitemap_index.xml',
            '/.well-known/security.txt', '/security.txt',
            '/crossdomain.xml', '/clientaccesspolicy.xml',
            '/humans.txt', '/ads.txt', '/app-ads.txt',
            # API surface
            '/api', '/api/', '/api/v1', '/api/v2', '/api/v3',
            '/v1', '/v2', '/v3', '/rest', '/rest/v1',
            '/swagger.json', '/swagger.yaml', '/openapi.json', '/openapi.yaml',
            '/swagger-ui.html', '/swagger-ui/', '/api-docs', '/api/docs',
            '/redoc', '/api/swagger', '/docs',
            '/graphql', '/graphiql', '/api/graphql', '/graphql/console',
            # Config / secrets
            '/.env', '/.env.production', '/.env.local', '/.env.backup',
            '/.env.example', '/.env.staging', '/.env.test',
            '/config.json', '/config.php', '/configuration.php',
            '/wp-config.php', '/wp-config.php.bak', '/wp-config.php.old',
            '/config/database.yml', '/config/secrets.yml', '/config/settings.yml',
            '/settings.py', '/local_settings.py',
            '/app/config/parameters.yml', '/app/config/parameters.yml.dist',
            '/package.json', '/composer.json', '/composer.lock',
            '/Gemfile', '/requirements.txt', '/Pipfile',
            # Admin panels
            '/admin', '/admin/', '/admin.php', '/admin/login',
            '/administrator', '/administrator/', '/administrator/index.php',
            '/wp-admin/', '/wp-login.php',
            '/phpmyadmin', '/phpmyadmin/', '/pma', '/pma/',
            '/adminer.php', '/adminer',
            '/_admin', '/cpanel', '/panel', '/backend',
            '/management', '/manage', '/dashboard/login',
            # Sensitive / debug files
            '/phpinfo.php', '/info.php', '/test.php', '/phptest.php',
            '/server-status', '/server-info', '/nginx_status',
            '/web.config', '/.htaccess', '/.htpasswd',
            '/WEB-INF/web.xml', '/WEB-INF/applicationContext.xml',
            '/.DS_Store',
            # VCS exposure
            '/.git/config', '/.git/HEAD', '/.gitignore',
            '/.svn/entries', '/.hg/hgrc',
            # Backup / archive
            '/backup.zip', '/backup.tar.gz', '/backup.sql',
            '/dump.sql', '/db.sql', '/database.sql',
            '/site.zip', '/www.zip', '/html.zip',
            # Debug / monitoring endpoints
            '/debug', '/console',
            '/_profiler', '/telescope', '/horizon',
            '/health', '/healthz', '/ping', '/status',
            '/metrics', '/actuator', '/actuator/health',
            '/actuator/env', '/actuator/beans', '/actuator/mappings',
            # Auth
            '/login', '/signin', '/auth', '/auth/login',
            '/user/login', '/account/login', '/sso/login',
            # Misc
            '/upload', '/uploads', '/files', '/static/files',
            '/favicon.ico',
        ]

        paths_file = self.output_mgr.get_path('urls', 'meg_paths.txt')
        with open(paths_file, 'w') as f:
            f.write('\n'.join(interesting_paths) + '\n')

        # Sample hosts to keep meg runtime bounded (80+ paths × many hosts = slow)
        _MEG_HOST_LIMIT = 20
        sampled_file = self.output_mgr.get_path('urls', 'meg_hosts_sample.txt')
        try:
            all_hosts = [l.strip() for l in input_file.read_text().splitlines() if l.strip()]
            with open(sampled_file, 'w') as f:
                f.write('\n'.join(all_hosts[:_MEG_HOST_LIMIT]) + '\n')
            if len(all_hosts) > _MEG_HOST_LIMIT:
                Logger.info(f"meg: sampling {_MEG_HOST_LIMIT}/{len(all_hosts)} hosts to stay within time budget")
        except Exception:
            sampled_file = input_file  # fallback

        _t0 = time.time()
        try:
            result = subprocess.run(
                ['meg', '-d', '1000', '-s', '200', '-v', str(paths_file), str(sampled_file), str(meg_dir)],
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

        except subprocess.TimeoutExpired:
            elapsed = round(time.time() - _t0, 1)
            _tool_log['meg'] = {'status': 'timeout', 'rc': -1, 'elapsed': elapsed,
                                'msg': f'Timed out after {elapsed}s'}
            Logger.warning(f"meg: timed out after {elapsed}s")
            return set()
        except Exception as e:
            _tool_log['meg'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
            Logger.error(f"Error in meg: {e}")
            return set()

    def parse_robots_sitemap(self, alive_file: Path) -> Set[str]:
        """Parse robots.txt Disallow paths and sitemap.xml URLs from live hosts."""
        if not alive_file.exists():
            _tool_log['robots_sitemap'] = {'status': 'ok', 'rc': 0, 'elapsed': 0, 'discovered': 0}
            return set()

        with open(alive_file) as f:
            hosts = [l.strip() for l in f if l.strip()]

        # Cap hosts to avoid unbounded runtime (8s × N hosts × sitemaps can blow up)
        _HOST_LIMIT = 20
        _SITEMAP_LIMIT = 3   # max sitemaps to fetch per host
        if len(hosts) > _HOST_LIMIT:
            Logger.info(f"robots_sitemap: sampling {_HOST_LIMIT}/{len(hosts)} hosts")
            hosts = hosts[:_HOST_LIMIT]

        discovered: Set[str] = set()
        robots_paths: Set[str] = set()
        session = requests.Session()
        session.headers['User-Agent'] = USER_AGENT
        _t0 = time.time()

        for host in hosts:
            host_sitemaps: list[str] = []

            # robots.txt — collect paths and sitemap references
            try:
                r = session.get(f"{host.rstrip('/')}/robots.txt", timeout=8, allow_redirects=True)
                if r.status_code == 200 and 'text/plain' in r.headers.get('Content-Type', ''):
                    for line in r.text.splitlines():
                        line = line.strip()
                        if line.lower().startswith(('disallow:', 'allow:')):
                            path_val = line.split(':', 1)[1].strip().split('?')[0]
                            if path_val and path_val != '/':
                                robots_paths.add(path_val)
                                discovered.add(f"{host.rstrip('/')}{path_val}")
                        elif line.lower().startswith('sitemap:'):
                            sm_url = line.split(':', 1)[1].strip()
                            if sm_url and len(host_sitemaps) < _SITEMAP_LIMIT:
                                host_sitemaps.append(sm_url)
            except Exception:
                pass

            # Default sitemap if no robots.txt references found
            if not host_sitemaps:
                host_sitemaps = [f"{host.rstrip('/')}/sitemap.xml"]

            # Fetch sitemaps (scoped to this host, capped at _SITEMAP_LIMIT)
            for sm_url in host_sitemaps[:_SITEMAP_LIMIT]:
                try:
                    r = session.get(sm_url, timeout=8, allow_redirects=True)
                    if r.status_code == 200:
                        for url_match in re.findall(r'<loc>\s*(https?://[^<\s]+)\s*</loc>', r.text):
                            discovered.add(url_match.strip())
                except Exception:
                    pass

        elapsed = round(time.time() - _t0, 1)
        _tool_log['robots_sitemap'] = {
            'status': 'ok', 'rc': 0, 'elapsed': elapsed, 'discovered': len(discovered)
        }

        # Persist discovered paths
        if robots_paths:
            out = self.output_mgr.get_path('urls', 'robots_paths.txt')
            with open(out, 'w') as f:
                f.write('\n'.join(sorted(robots_paths)) + '\n')

        if discovered:
            Logger.info(f"robots.txt/sitemap: {len(discovered)} paths/URLs discovered")

        return discovered

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
            # subjs -i <file> is silently broken in v1.0.1; pipe via stdin instead
            with open(input_file, 'r') as fh:
                stdin_data = fh.read()
            _t0 = time.time()
            result = subprocess.run(
                ['subjs'],
                input=stdin_data,
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

        except subprocess.TimeoutExpired:
            _tool_log['subjs'] = {'status': 'timeout', 'rc': -1, 'elapsed': round(time.time() - _t0, 1)}
            Logger.warning("subjs timed out")
            return set()
        except Exception as e:
            _tool_log['subjs'] = {'status': 'error', 'rc': -1, 'elapsed': round(time.time() - _t0, 1), 'msg': str(e)}
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
            last_result = None
            for url in urls[:100]:  # Limit to prevent excessive scanning
                last_result = subprocess.run(
                    ['jsubfinder', '-u', url, '-silent'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                findings = set(line.strip() for line in last_result.stdout.split('\n') if line.strip())
                all_findings.update(findings)
            if urls and last_result is not None:
                _track_captured('jsubfinder', last_result, _t0, self.output_mgr.dirs['logs'])

            with open(output_file, 'w') as f:
                f.write('\n'.join(sorted(all_findings)) + '\n')

            Logger.success(f"jsubfinder: {len(all_findings)} findings")
            return all_findings
            
        except Exception as e:
            Logger.error(f"Error in jsubfinder: {e}")
            return set()

    def _extract_js_from_urls(self, urls_file: Path) -> Set[str]:
        """Extract .js file URLs directly from a URL corpus (no HTTP request needed).

        This is the fallback path for API-heavy targets where subjs/getJS find
        nothing because alive hosts serve JSON instead of HTML.  Any URL in the
        collected corpus whose path ends with a JS extension is a real JS asset.
        """
        if not urls_file.exists():
            return set()
        _JS_EXTS = re.compile(r'\.(js|mjs|jsx|ts|tsx|min\.js)(\?|$)', re.IGNORECASE)
        js_urls: Set[str] = set()
        try:
            for line in urls_file.read_text(errors='ignore').splitlines():
                url = line.strip()
                if url and _JS_EXTS.search(url):
                    js_urls.add(url)
        except Exception:
            pass
        return js_urls

    def analyze_all(self, alive_file: Path) -> Set[str]:
        """Complete JS analysis"""
        Logger.header("JAVASCRIPT ANALYSIS")

        all_js = set()

        # ── 1. subjs: crawls HTML pages for <script src=...> references ─────
        # Works best on HTML-serving hosts; returns 0 on pure API/JSON targets
        all_js.update(self.collect_with_subjs(alive_file))

        # ── 2. getJS: similar HTML crawler ───────────────────────────────────
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

        # ── 3. URL-corpus extraction (zero HTTP; works for API-heavy targets) ─
        # Extracts .js URLs directly from urls_clean.txt — any URL whose path
        # ends in .js/.mjs/.jsx/etc is a JS asset regardless of the page type.
        urls_clean = self.output_mgr.get_path('urls', 'urls_clean.txt')
        corpus_js = self._extract_js_from_urls(urls_clean)
        if corpus_js:
            corpus_file = self.output_mgr.get_path('js', 'from_urls.txt')
            corpus_file.write_text('\n'.join(sorted(corpus_js)) + '\n')
            Logger.success(f"JS from URL corpus: {len(corpus_js)} files")
        all_js.update(corpus_js)

        # ── Save consolidated JS file list ───────────────────────────────────
        all_js_file = self.output_mgr.get_path('js', 'all_js_files.txt')
        with open(all_js_file, 'w') as f:
            f.write('\n'.join(sorted(all_js)) + '\n')

        Logger.info(f"Total JS files: {len(all_js)} (subjs/getJS crawl + URL corpus extraction)")

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

        # Disable SSL warnings — scanned hosts often have self-signed / expired certs.
        # verify=False is intentional in this recon context.
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = requests.Session()
        session.verify = False
        headers = {'User-Agent': USER_AGENT}

        # Pre-filter obviously malformed URLs (escaped backslashes from bad
        # URL extraction, duplicate path segments from WordPress relative-
        # path bugs). These always 404 and waste request budget.
        def _looks_malformed(u: str) -> bool:
            low = u.lower()
            if '%5c' in low or '\\' in u:
                return True
            # Heuristic: same path segment duplicated consecutively
            # (e.g. /wp-includes/js/wp-includes/js/).
            parsed = urlparse(u).path.lower()
            segments = [s for s in parsed.split('/') if s]
            for i in range(len(segments) - 3):
                if segments[i] == segments[i + 2] and segments[i + 1] == segments[i + 3]:
                    return True
            return False

        malformed_skipped = 0
        candidates: List[str] = []
        for u in sorted(js_urls):
            if _looks_malformed(u):
                malformed_skipped += 1
                continue
            candidates.append(u)
            if len(candidates) >= limit:
                break
        if malformed_skipped:
            Logger.info(f"JS download: skipped {malformed_skipped} malformed URL(s) before requesting")

        for url in candidates:
            try:
                response = session.get(url, headers=headers, timeout=15, stream=True)
                if response.status_code != 200:
                    failures += 1
                    Logger.warning(f"JS download HTTP {response.status_code}: {url}")
                    continue

                content_type = response.headers.get('content-type', '').lower()
                url_path = urlparse(url).path.lower()
                if 'javascript' not in content_type and not url_path.endswith(('.js', '.mjs', '.cjs')):
                    failures += 1
                    Logger.warning(f"JS download skipped (not JS, content-type={content_type or 'none'}): {url}")
                    continue

                chunks = bytearray()
                truncated = False
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    chunks.extend(chunk)
                    if len(chunks) > max_bytes:
                        chunks = bytearray()
                        truncated = True
                        break

                if not chunks:
                    failures += 1
                    reason = f"exceeded {max_bytes} bytes" if truncated else "empty response body"
                    Logger.warning(f"JS download skipped ({reason}): {url}")
                    continue

                name = Path(urlparse(url).path).name or 'script.js'
                safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', name)[:80] or 'script.js'
                digest = hashlib.sha1(url.encode('utf-8')).hexdigest()[:12]
                output_file = download_dir / f"{digest}_{safe_name}"
                with open(output_file, 'wb') as f:
                    f.write(chunks)
                downloaded += 1

            except Exception as e:
                failures += 1
                Logger.warning(f"JS download error on {url}: {e}")

        if downloaded == 0 and failures == 0:
            js_status = 'ok'
        elif downloaded == 0:
            js_status = 'fail'
        elif failures == 0:
            js_status = 'ok'
        else:
            js_status = 'partial'
        _tool_log['js_download'] = {
            'status': js_status,
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
                except Exception as e:
                    Logger.warning(f"Git dump failed for {url}: {e}")
            
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

            _nuclei_c = min(100, max(25, _CPU_COUNT * 8))
            _nuclei_rl = min(500, max(150, _CPU_COUNT * 20))
            cmd = [
                'nuclei',
                '-l', str(input_file),
                '-severity', severity,
                '-silent',
                '-c', str(_nuclei_c),         # parallel template execution
                '-rate-limit', str(_nuclei_rl),
                '-bulk-size', str(min(50, _CPU_COUNT * 4)),
                '-jsonl-export', str(json_file)
            ] + _get_proxy_flag()

            run_logged('nuclei', cmd, self.output_mgr.dirs['logs'], timeout=3600, check=True)
            
            # Parse results
            vulns = []
            if json_file.exists():
                with open(json_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            vulns.append(f"[{data.get('info', {}).get('severity', 'unknown')}] {data.get('template-id', '')} - {data.get('matched-at', '')}")
                        except (json.JSONDecodeError, AttributeError):
                            # Skip malformed nuclei JSONL line.
                            continue
            
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

            _proxy = _get_proxy_flag()
            _dalfox_proxy = ['--proxy', _proxy[1]] if _proxy else []
            run_logged('dalfox',
                       ['dalfox', 'file', str(targets_file), '--silence', '--no-color', '--output', str(output_file)]
                       + _dalfox_proxy,
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

    def scan_with_sqlmap(self, url_file: Path):
        """Run sqlmap on gf-categorized SQLi URLs (active mode only).

        Expects url_file to be the output of `gf sqli` — URLs already pre-filtered
        to those with SQL-injectable parameters.  Capped at 50 URLs to keep
        scan time reasonable; sqlmap runs in batch/non-interactive mode.
        """
        if not ToolChecker.check_tool('sqlmap'):
            Logger.warning("sqlmap not found, skipping SQL injection scan")
            return

        if not url_file.exists() or count_nonempty_lines(url_file) == 0:
            Logger.info("No gf-sqli URLs to test with sqlmap")
            return

        Logger.header("SQL INJECTION SCAN")

        # Read and cap targets
        with open(url_file, 'r') as f:
            targets = [l.strip() for l in f if l.strip() and '?' in l][:50]

        if not targets:
            Logger.info("No parameterized SQLi targets found")
            return

        Logger.info(f"Running sqlmap on {len(targets)} SQLi-candidate URLs...")
        targets_file = self.output_mgr.get_path('vulnerabilities', 'sqlmap_targets.txt')
        output_dir   = self.output_mgr.get_path('vulnerabilities', 'sqlmap')
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(targets_file, 'w') as f:
            f.write('\n'.join(targets) + '\n')

        try:
            cmd = [
                'sqlmap',
                '-m', str(targets_file),
                '--batch',
                '--level', '2',
                '--risk', '1',
                '--timeout', '10',
                '--retries', '2',
                '--threads', '5',
                '--output-dir', str(output_dir),
                '--no-logging',
                '--answers', 'crack=N,dict=N,continue=Y,quit=N',
            ] + _get_proxy_flag()

            run_logged('sqlmap', cmd, self.output_mgr.dirs['logs'], timeout=2400)

            # Collect any confirmed injections from sqlmap output dirs
            found = []
            for sub in output_dir.iterdir():
                log = sub / 'log'
                if log.exists():
                    text = log.read_text(errors='replace')
                    if 'injectable' in text.lower() or 'sqlmap identified' in text.lower():
                        found.append(sub.name)

            if found:
                Logger.warning(f"sqlmap: potential SQLi in {len(found)} target(s): {', '.join(found)}")
            else:
                Logger.success("sqlmap: no SQL injection found")

        except Exception as e:
            Logger.error(f"Error in sqlmap: {e}")


class FuzzScanner:
    """Directory and endpoint fuzzing with ffuf."""

    # Ordered list of candidate wordlists — first one that exists wins
    _WORDLISTS = [
        '/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt',
        '/usr/share/seclists/Discovery/Web-Content/common.txt',
        '/usr/share/wordlists/dirb/common.txt',
        '/usr/share/dirb/wordlists/common.txt',
    ]

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def fuzz_with_ffuf(self, alive_file: Path):
        """Fuzz each live host for hidden paths, admin panels, config files, etc.

        Caps at 20 hosts to keep total scan time bounded.  Results are saved
        per-host as JSON and summarised to fuzzing/ffuf_summary.txt.
        """
        if not ToolChecker.check_tool('ffuf'):
            Logger.warning("ffuf not found, skipping directory fuzzing")
            return

        wordlist = next((w for w in self._WORDLISTS if os.path.exists(w)), None)
        if not wordlist:
            Logger.warning("No wordlist found for ffuf "
                           "(install seclists or dirb — apt-get install seclists)")
            return

        try:
            with open(alive_file, 'r') as f:
                targets = [l.strip() for l in f if l.strip()][:20]
        except Exception:
            return

        if not targets:
            return

        Logger.header("DIRECTORY FUZZING")
        Logger.info(f"Fuzzing {len(targets)} hosts with ffuf ({os.path.basename(wordlist)})...")

        for target in targets:
            base = target.rstrip('/')
            safe_name = base.replace('://', '_').replace('/', '_').replace(':', '_')
            out_file = self.output_mgr.get_path('fuzzing', f'ffuf_{safe_name}.json')

            cmd = [
                'ffuf',
                '-u', f'{base}/FUZZ',
                '-w', wordlist,
                '-mc', 'all',
                '-fc', '404,429,400',
                '-fs', '0',
                '-t', '50',
                '-timeout', '10',
                '-rate', '150',
                '-o', str(out_file),
                '-of', 'json',
                '-s',                    # silent — no progress bar
            ]
            try:
                run_logged(f'ffuf_{safe_name[-30:]}', cmd,
                           self.output_mgr.dirs['logs'], timeout=300)
            except Exception as e:
                Logger.error(f"ffuf error on {base}: {e}")

        # Aggregate results
        found_paths: list[str] = []
        for jf in self.output_mgr.dirs['fuzzing'].glob('ffuf_*.json'):
            try:
                data = json.loads(jf.read_text())
                for r in data.get('results', []):
                    status = r.get('status', 0)
                    url    = r.get('url', '')
                    length = r.get('length', 0)
                    found_paths.append(f"[{status}] {url} (size={length})")
            except Exception:
                continue

        if found_paths:
            summary = self.output_mgr.get_path('fuzzing', 'ffuf_summary.txt')
            summary.write_text('\n'.join(sorted(set(found_paths))) + '\n')
            Logger.warning(f"ffuf: {len(found_paths)} paths discovered → {summary}")
        else:
            Logger.success("ffuf: no interesting paths found")


class JWTScanner:
    """JWT vulnerability testing with jwt_tool.

    Extracts JWT tokens (eyJ…) from httpx JSON responses (headers + body where
    available) and runs jwt_tool's playbook mode to detect:
      - none-algorithm attacks
      - weak-secret brute-force (using a compact built-in list)
      - alg confusion (RS256→HS256)
      - kid injection
    """

    _JWT_RE = re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*')

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def scan_from_httpx(self, httpx_json_file: Path):
        if not ToolChecker.check_tool('jwt_tool'):
            Logger.warning("jwt_tool not found, skipping JWT testing")
            return
        if not httpx_json_file.exists():
            return

        # Harvest JWTs from all field values in every httpx JSON line
        raw_text = httpx_json_file.read_text(errors='replace')
        tokens: set[str] = set(self._JWT_RE.findall(raw_text))
        if not tokens:
            Logger.info("jwt_tool: no JWT tokens found in HTTP responses")
            return

        Logger.header("JWT TESTING")
        Logger.info(f"Found {len(tokens)} unique JWT(s) — running jwt_tool playbook...")

        out_dir = self.output_mgr.get_path('vulnerabilities', 'jwt')
        out_dir.mkdir(parents=True, exist_ok=True)
        summary_file = self.output_mgr.get_path('vulnerabilities', 'jwt_summary.txt')
        findings: list[str] = []

        for i, token in enumerate(tokens):
            out_file = out_dir / f'jwt_{i}.txt'
            try:
                result = subprocess.run(
                    ['jwt_tool', token, '-M', 'pb', '-np'],   # playbook, no progress bar
                    capture_output=True, text=True, timeout=90,
                )
                combined = result.stdout + result.stderr
                out_file.write_text(combined)
                # Flag tokens where jwt_tool found something exploitable
                if any(kw in combined.lower() for kw in
                       ('vulnerable', 'none algorithm', 'rs/hs confusion',
                        'weak secret', 'kid inject', 'found!')):
                    short = token[:60] + ('…' if len(token) > 60 else '')
                    findings.append(f"[VULN] {short}\n  → {out_file}")
            except subprocess.TimeoutExpired:
                continue
            except Exception as e:
                Logger.error(f"jwt_tool error: {e}")
                continue

        if findings:
            summary_file.write_text('\n'.join(findings) + '\n')
            Logger.warning(f"jwt_tool: {len(findings)} vulnerable JWT(s)! → {summary_file}")
        else:
            Logger.success("jwt_tool: no JWT vulnerabilities found")


class S3Scanner:
    """Cloud storage bucket exposure detection using s3scanner.

    Generates domain-derived bucket name variations (common naming patterns
    used by developers) and checks them for public-read/public-write access
    on AWS S3, GCS, and Azure Blob.
    """

    _SUFFIXES = [
        '', '-backup', '-bkp', '-assets', '-static', '-media',
        '-uploads', '-prod', '-staging', '-dev', '-development',
        '-test', '-qa', '-data', '-files', '-store', '-cdn',
        '-logs', '-images', '-public', '-private', '-internal',
        '-api', '-app', '-web', '-db', '-database',
    ]

    def __init__(self, domain: str, output_mgr: OutputManager):
        self.domain   = domain
        self.output_mgr = output_mgr

    def _generate_names(self) -> list[str]:
        base   = self.domain.split('.')[0]          # bnb.gov.br → bnb
        dashed = self.domain.replace('.', '-')      # bnb-gov-br
        names: list[str] = []
        for pfx in (base, dashed):
            for sfx in self._SUFFIXES:
                names.append(f'{pfx}{sfx}')
        return list(dict.fromkeys(names))           # deduplicate, preserve order

    def scan(self):
        if not ToolChecker.check_tool('s3scanner'):
            Logger.warning("s3scanner not found, skipping bucket scan")
            return

        Logger.header("CLOUD BUCKET SCAN")
        names = self._generate_names()
        Logger.info(f"Checking {len(names)} bucket name variations for {self.domain}…")

        buckets_file = self.output_mgr.get_path('cloud', 's3_targets.txt')
        results_file = self.output_mgr.get_path('cloud', 's3_results.txt')
        buckets_file.write_text('\n'.join(names) + '\n')

        try:
            # s3scanner v3+ outputs to stdout only — there is no --out-file flag.
            # Capture stdout ourselves and write to the results file.
            _s3_t0 = time.time()
            result = subprocess.run(
                ['s3scanner', 'scan', '--buckets-file', str(buckets_file)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            _track_captured('s3scanner', result, _s3_t0, self.output_mgr.dirs['logs'])

            output = result.stdout.strip()
            if output:
                results_file.write_text(output + '\n')

            if output:
                # A bucket with AuthUsers: [], AllUsers: [] is PRIVATE — no
                # public access configured.  Only flag lines where at least one
                # permission (READ, WRITE, FULL_CONTROL) appears in AllUsers or
                # AuthUsers, OR where s3scanner explicitly says "open" / "public".
                def _is_exposed(line: str) -> bool:
                    lo = line.lower()
                    # Explicit open/public markers from s3scanner
                    if 'open' in lo:
                        return True
                    # AllUsers or AuthUsers with actual permissions (non-empty)
                    import re as _re
                    for group in ('allusers', 'authusers'):
                        m = _re.search(rf'{group}:\s*\[([^\]]*)\]', lo)
                        if m and m.group(1).strip():
                            return True
                    return False

                exposed = [l.strip() for l in output.splitlines() if _is_exposed(l)]
                exists  = [l.strip() for l in output.splitlines()
                           if 'bucket_exists' in l.lower() and not _is_exposed(l)]

                if exposed:
                    Logger.warning(f"s3scanner: {len(exposed)} publicly accessible bucket(s)!")
                    for line in exposed:
                        Logger.warning(f"  {line}")
                elif exists:
                    Logger.info(f"s3scanner: {len(exists)} bucket(s) exist (all private — no public access)")
                else:
                    Logger.success("s3scanner: no exposed buckets found")
            else:
                Logger.success("s3scanner: no exposed buckets found")
        except Exception as e:
            Logger.error(f"Error in s3scanner: {e}")


class BypassScanner:
    """HTTP 403/401 bypass testing with byp4xx.

    Parses httpx JSON output for forbidden responses, then runs byp4xx against
    each URL using common bypass techniques (path normalisation, header injection,
    verb tampering).  Caps at 40 targets to keep scan time reasonable.
    """

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def bypass_403(self, httpx_json_file: Path):
        if not ToolChecker.check_tool('byp4xx'):
            Logger.warning("byp4xx not found, skipping 403 bypass testing")
            return
        if not httpx_json_file.exists():
            return

        # Collect 403/401 URLs from httpx JSON
        forbidden: list[str] = []
        with open(httpx_json_file, 'r', errors='replace') as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get('status-code') in (401, 403):
                        url = obj.get('url', '')
                        if url:
                            forbidden.append(url)
                except Exception:
                    continue

        if not forbidden:
            Logger.info("byp4xx: no 403/401 responses to test")
            return

        targets = forbidden[:40]
        Logger.header("403 BYPASS TESTING")
        Logger.info(f"Testing {len(targets)} forbidden URL(s) with byp4xx…")

        findings: list[str] = []
        out_dir = self.output_mgr.get_path('vulnerabilities', 'bypass')
        out_dir.mkdir(parents=True, exist_ok=True)

        for url in targets:
            safe = url.replace('://', '_').replace('/', '_').replace(':', '_')
            out_file = out_dir / f'byp4xx_{safe[:60]}.txt'
            try:
                result = subprocess.run(
                    ['byp4xx', url],
                    capture_output=True, text=True, timeout=30,
                )
                output = result.stdout + result.stderr
                out_file.write_text(output)
                # byp4xx prints bypassed URLs with their real status codes
                bypassed = [l for l in output.splitlines()
                            if any(c in l for c in ('200', '301', '302', '307')) and url[:20] in l]
                if bypassed:
                    findings.extend([f"{url} → {b.strip()}" for b in bypassed])
            except subprocess.TimeoutExpired:
                continue
            except Exception as e:
                Logger.error(f"byp4xx error on {url}: {e}")
                continue

        if findings:
            summary = self.output_mgr.get_path('vulnerabilities', 'bypass_summary.txt')
            summary.write_text('\n'.join(findings) + '\n')
            Logger.warning(f"byp4xx: {len(findings)} bypass(es) found! → {summary}")
        else:
            Logger.success("byp4xx: no bypasses found")


class APIDiscovery:
    """API endpoint discovery with kiterunner.

    Uses kiterunner's routes-small.kite wordlist to brute-force common API
    paths across all live hosts.  Output is deduplicated and saved to
    urls/kiterunner_apis.txt for inclusion in the scan report.
    """

    _WORDLISTS = [
        '/root/.kiterunner/routes-small.kite',
        os.path.expanduser('~/.kiterunner/routes-small.kite'),
    ]

    def __init__(self, output_mgr: OutputManager):
        self.output_mgr = output_mgr

    def discover(self, alive_file: Path):
        if not ToolChecker.check_tool('kr'):
            Logger.warning("kiterunner (kr) not found, skipping API discovery")
            return

        wordlist = next((w for w in self._WORDLISTS if os.path.exists(w)), None)
        if not wordlist:
            Logger.warning("kiterunner: routes-small.kite wordlist not found "
                           "(run: kr wordlist download routes-small)")
            return

        try:
            with open(alive_file, 'r') as f:
                targets = [l.strip() for l in f if l.strip()][:25]
        except Exception:
            return

        if not targets:
            return

        Logger.header("API DISCOVERY")
        Logger.info(f"Scanning {len(targets)} hosts for API endpoints with kiterunner…")

        out_file    = self.output_mgr.get_path('urls', 'kiterunner_apis.txt')
        hosts_file  = self.output_mgr.get_path('urls', 'kr_targets.txt')
        hosts_file.write_text('\n'.join(targets) + '\n')

        try:
            cmd = [
                'kr', 'brute', str(hosts_file),
                '-w', wordlist,
                '--fail-status-codes', '400,401,404,501,502,503',
                '-o', str(out_file),
                '--timeout', '3',
                '-x', '5',
                '--max-connection-per-host', '3',
                '-q',
            ]
            run_logged('kiterunner', cmd, self.output_mgr.dirs['logs'], timeout=600)

            if out_file.exists():
                count = count_nonempty_lines(out_file)
                if count:
                    Logger.success(f"kiterunner: {count} API endpoint(s) found → {out_file}")
                else:
                    Logger.info("kiterunner: no API endpoints found")
        except Exception as e:
            Logger.error(f"Error in kiterunner: {e}")


class ReconEnricher:
    """Post-enumeration enrichment: zone transfers, CORS misconfig, WAF detection."""

    def __init__(self, domain: str, output_mgr: OutputManager):
        self.domain = domain
        self.output_mgr = output_mgr

    def check_zone_transfer(self) -> list[str]:
        """Attempt AXFR zone transfer on all NS servers for the domain."""
        Logger.info(f"Checking zone transfer for {self.domain}...")
        results = []
        try:
            ns_answers = dns.resolver.resolve(self.domain, 'NS')
            for ns in ns_answers:
                ns_host = str(ns).rstrip('.')
                try:
                    xfr = dns.query.xfr(ns_host, self.domain, timeout=10)
                    records = []
                    for msg in xfr:
                        for rrset in msg.answer:
                            records.append(str(rrset))
                    if records:
                        Logger.warning(f"Zone transfer OPEN on {ns_host}!")
                        results.extend(records)
                except Exception:
                    pass  # Transfer refused — expected
        except Exception as e:
            Logger.warning(f"Could not resolve NS for {self.domain}: {e}")

        if results:
            out = self.output_mgr.get_path('dns', 'zone_transfer.txt')
            with open(out, 'w') as f:
                f.write('\n'.join(results) + '\n')
        return results

    def detect_cors_misconfig(self, alive_file: Path, sample: int = 30):
        """Check for CORS misconfigurations on a sample of live hosts.

        Severity:
          [high]   Origin reflected back AND Access-Control-Allow-Credentials: true
          [medium] Origin reflected back (no credentials header)
          [info]   ACAO: * (wildcard — not exploitable unless used with credentialled APIs)
        """
        Logger.info("Checking CORS misconfigurations...")
        if not alive_file.exists():
            _tool_log['cors'] = {'status': 'ok', 'rc': 0, 'elapsed': 0, 'findings': 0}
            return
        with open(alive_file) as f:
            hosts = [l.strip() for l in f if l.strip()][:sample]

        findings = []
        _t0 = time.time()
        for host in hosts:
            try:
                resp = requests.get(
                    host,
                    headers={'User-Agent': USER_AGENT, 'Origin': 'https://evil.com'},
                    timeout=8,
                    allow_redirects=False,
                )
                acao = resp.headers.get('Access-Control-Allow-Origin', '')
                acac = resp.headers.get('Access-Control-Allow-Credentials', '').lower()

                if acao == 'https://evil.com':
                    # Origin was reflected
                    if acac == 'true':
                        findings.append(f"[high] {host} → Origin reflected + ACAC:true (credentialled CORS)")
                    else:
                        findings.append(f"[medium] {host} → Origin reflected (no credentials)")
                elif acao == '*':
                    # Wildcard — not directly exploitable with credentials (browsers block it)
                    findings.append(f"[info] {host} → ACAO: * (wildcard, review if used by credentialled clients)")
            except Exception:
                pass

        elapsed = round(time.time() - _t0, 1)
        _tool_log['cors'] = {'status': 'ok', 'rc': 0, 'elapsed': elapsed, 'findings': len(findings)}

        if findings:
            high_count = sum(1 for f in findings if f.startswith('[high]'))
            Logger.warning(f"CORS: {len(findings)} finding(s) ({high_count} high)")
            out = self.output_mgr.get_path('vulnerabilities', 'cors_misconfig.txt')
            with open(out, 'w') as f:
                f.write('\n'.join(findings) + '\n')
        else:
            Logger.success("No CORS misconfigurations detected")

    def detect_waf(self, alive_file: Path, sample: int = 10):
        """Detect WAF presence via server headers on a sample of hosts."""
        Logger.info("Detecting WAF presence...")
        if not alive_file.exists():
            return
        with open(alive_file) as f:
            hosts = [l.strip() for l in f if l.strip()][:sample]

        waf_signatures = {
            'cloudflare': 'Cloudflare',
            'akamai': 'Akamai',
            'sucuri': 'Sucuri',
            'imperva': 'Imperva',
            'barracuda': 'Barracuda',
            'f5 big-ip': 'F5 BIG-IP',
            'aws': 'AWS WAF',
            'ddos-guard': 'DDoS-Guard',
        }

        findings = []
        for host in hosts:
            try:
                resp = requests.head(host, headers={'User-Agent': USER_AGENT}, timeout=8, allow_redirects=True)
                server = resp.headers.get('Server', '').lower()
                via = resp.headers.get('Via', '').lower()
                combined = f"{server} {via} {' '.join(str(v) for v in resp.headers.values()).lower()}"
                for sig, name in waf_signatures.items():
                    if sig in combined:
                        findings.append(f"{host} → {name}")
                        break
            except Exception:
                pass

        if findings:
            Logger.info(f"WAF detected on {len(findings)} hosts")
            out = self.output_mgr.get_path('http', 'waf_detection.txt')
            with open(out, 'w') as f:
                f.write('\n'.join(findings) + '\n')

    # ── Email Security ────────────────────────────────────────────────────────

    def check_email_security(self) -> list[str]:
        """Check SPF, DMARC and common DKIM selectors for email spoofing vectors."""
        Logger.info(f"Checking email security (SPF/DMARC/DKIM) for {self.domain}...")
        issues: list[str] = []

        # ── SPF ──────────────────────────────────────────────────────────────
        try:
            spf_records: list[str] = []
            for rdata in dns.resolver.resolve(self.domain, 'TXT'):
                txt = str(rdata).strip('"')
                if txt.startswith('v=spf1'):
                    spf_records.append(txt)

            if not spf_records:
                issues.append(f"[high] SPF missing → anyone can spoof @{self.domain}")
            elif len(spf_records) > 1:
                issues.append(f"[medium] Multiple SPF records (RFC-invalid, mail may be rejected)")
            else:
                spf = spf_records[0]
                if '+all' in spf:
                    issues.append(f"[high] SPF uses '+all' → any server is authorised to send as {self.domain}")
                elif '?all' in spf:
                    issues.append(f"[medium] SPF uses '?all' (neutral) → policy is not enforced")
                elif '-all' not in spf and '~all' not in spf:
                    issues.append(f"[low] SPF has no 'all' mechanism → incomplete policy")
        except dns.resolver.NXDOMAIN:
            issues.append(f"[high] SPF missing (NXDOMAIN for TXT on {self.domain})")
        except Exception:
            pass

        # ── DMARC ────────────────────────────────────────────────────────────
        try:
            dmarc_records: list[str] = []
            for rdata in dns.resolver.resolve(f'_dmarc.{self.domain}', 'TXT'):
                txt = str(rdata).strip('"')
                if txt.startswith('v=DMARC1'):
                    dmarc_records.append(txt)

            if not dmarc_records:
                issues.append(f"[high] DMARC missing → no enforcement for email spoofing")
            else:
                dmarc = dmarc_records[0]
                if 'p=none' in dmarc:
                    issues.append(f"[medium] DMARC policy p=none → monitoring only, spoofed emails still delivered")
                if 'rua=' not in dmarc and 'ruf=' not in dmarc:
                    issues.append(f"[low] DMARC has no reporting address (rua=/ruf=) → no spoofing visibility")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            issues.append(f"[high] DMARC missing (_dmarc.{self.domain} does not exist)")
        except Exception:
            pass

        # ── DKIM selectors ───────────────────────────────────────────────────
        common_selectors = [
            'default', 'google', 'mail', 'dkim', 'k1', 'k2',
            'selector1', 'selector2', 'email', 's1', 's2',
            'mandrill', 'sendgrid', 'mailchimp', 'amazonses',
        ]
        found_selectors: list[str] = []
        for sel in common_selectors:
            try:
                dns.resolver.resolve(f'{sel}._domainkey.{self.domain}', 'TXT')
                found_selectors.append(sel)
            except Exception:
                pass

        if not found_selectors:
            issues.append(f"[info] No common DKIM selectors found (checked: {', '.join(common_selectors[:6])}...)")

        # ── Save ─────────────────────────────────────────────────────────────
        lines: list[str] = [
            f"=== Email Security: {self.domain} ===",
            f"DKIM selectors found: {', '.join(found_selectors) or 'none'}",
            "",
        ]
        if issues:
            Logger.warning(f"Email security: {len(issues)} issue(s) found")
            lines += [f"  {i}" for i in issues]
            out = self.output_mgr.get_path('vulnerabilities', 'email_security.txt')
            with open(out, 'w') as f:
                f.write('\n'.join(lines) + '\n')
        else:
            Logger.success("Email security: SPF/DMARC/DKIM look good")

        return issues

    # ── HTTP Security Headers ─────────────────────────────────────────────────

    def check_security_headers(self, alive_file: Path, sample: int = 30) -> list[str]:
        """Audit HTTP security headers and cookie flags on live hosts."""
        Logger.info("Checking HTTP security headers...")
        if not alive_file.exists():
            return []

        with open(alive_file) as f:
            hosts = [l.strip() for l in f if l.strip()][:sample]

        # (header, friendly-name, severity, html_only)
        # html_only=True → only flag for HTML pages; API/JSON responses don't need these browser headers
        REQUIRED_HEADERS = [
            ('Strict-Transport-Security',  'HSTS',                   'high',   False),
            ('Content-Security-Policy',    'Content-Security-Policy','medium', True),
            ('X-Frame-Options',            'X-Frame-Options',        'medium', True),
            ('X-Content-Type-Options',     'X-Content-Type-Options', 'low',    False),
            ('Referrer-Policy',            'Referrer-Policy',        'low',    True),
            ('Permissions-Policy',         'Permissions-Policy',     'low',    True),
        ]

        all_findings: list[str] = []
        session = requests.Session()
        session.headers['User-Agent'] = USER_AGENT

        for host in hosts:
            try:
                resp = session.get(host, timeout=10, allow_redirects=True)
                resp_headers_lower = {k.lower() for k in resp.headers}

                # Determine if this is an HTML response (browser-only headers only apply here)
                content_type = resp.headers.get('Content-Type', '').lower()
                is_html = 'text/html' in content_type

                # Missing headers
                for header, name, severity, html_only in REQUIRED_HEADERS:
                    # HSTS only matters on HTTPS
                    if header == 'Strict-Transport-Security' and not host.startswith('https://'):
                        continue
                    # Browser-only headers (CSP, X-Frame-Options, etc.) don't apply to API/JSON endpoints
                    if html_only and not is_html:
                        continue
                    if header.lower() not in resp_headers_lower:
                        all_findings.append(f"[{severity}] {host} → Missing {header}")

                # HSTS max-age too short
                hsts_val = resp.headers.get('Strict-Transport-Security', '')
                if hsts_val:
                    m = re.search(r'max-age=(\d+)', hsts_val)
                    if m and int(m.group(1)) < 31_536_000:
                        all_findings.append(
                            f"[low] {host} → HSTS max-age {m.group(1)}s < 1 year (recommended ≥31536000)"
                        )

                # Version disclosure via Server / X-Powered-By
                server_hdr = resp.headers.get('Server', '')
                if server_hdr and any(c.isdigit() for c in server_hdr):
                    all_findings.append(f"[low] {host} → Server header exposes version: {server_hdr}")
                xpb = resp.headers.get('X-Powered-By', '')
                if xpb:
                    all_findings.append(f"[low] {host} → X-Powered-By exposes stack: {xpb}")

                # Cookie flags (urllib3 gives us all Set-Cookie lines)
                try:
                    cookie_lines = resp.raw.headers.getlist('set-cookie')
                except Exception:
                    raw_ck = resp.headers.get('Set-Cookie', '')
                    cookie_lines = [raw_ck] if raw_ck else []

                for cookie_line in cookie_lines:
                    name_part = cookie_line.split('=')[0].strip()
                    flags_lower = cookie_line.lower()
                    missing_flags: list[str] = []
                    if host.startswith('https://') and 'secure' not in flags_lower:
                        missing_flags.append('Secure')
                    if 'httponly' not in flags_lower:
                        missing_flags.append('HttpOnly')
                    if 'samesite' not in flags_lower:
                        missing_flags.append('SameSite')
                    if missing_flags:
                        all_findings.append(
                            f"[low] {host} → Cookie '{name_part}' missing flags: {', '.join(missing_flags)}"
                        )

            except Exception:
                pass

        if all_findings:
            Logger.warning(f"Security headers: {len(all_findings)} issue(s) across {len(hosts)} hosts")
            out = self.output_mgr.get_path('vulnerabilities', 'security_headers.txt')
            with open(out, 'w') as f:
                f.write('\n'.join(all_findings) + '\n')
        else:
            Logger.success("Security headers: no issues found")

        return all_findings


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
    
    # Parameter vulnerability categories — used for tagging and prioritised output
    _PARAM_CATEGORIES: dict[str, list[str]] = {
        'open_redirect': [
            'redirect', 'return', 'next', 'callback', 'continue', 'goto',
            'dest', 'destination', 'target', 'redir', 'url', 'link', 'returnurl',
            'returnto', 'backurl', 'forward', 'location',
        ],
        'ssrf': [
            'url', 'uri', 'endpoint', 'server', 'host', 'site', 'webhook',
            'fetch', 'load', 'proxy', 'remote', 'src', 'source', 'api',
            'feed', 'import', 'connect',
        ],
        'lfi_rfi': [
            'file', 'filename', 'path', 'dir', 'folder', 'document', 'root',
            'include', 'page', 'template', 'view', 'layout', 'load',
            'config', 'resource', 'module', 'action',
        ],
        'sqli': [
            'id', 'uid', 'user_id', 'item', 'order', 'sort', 'category',
            'product', 'search', 'query', 'q', 'filter', 'limit', 'offset',
            'page', 'num', 'start', 'from', 'to', 'by',
        ],
        'auth_tokens': [
            'token', 'key', 'apikey', 'api_key', 'access_token', 'auth',
            'secret', 'password', 'passwd', 'pass', 'pwd', 'hash',
            'session', 'csrf', 'nonce', 'signature', 'sig',
        ],
        'user_data': [
            'user', 'username', 'email', 'name', 'login', 'account',
            'admin', 'role', 'group', 'uid', 'userid', 'profile',
        ],
        'debug': [
            'debug', 'test', 'dev', 'beta', 'staging', 'verbose',
            'trace', 'log', 'mode',
        ],
    }

    def analyze_parameters(self, url_file: Path):
        """Analyze URL parameters and categorise by likely vulnerability class."""
        Logger.info("Analyzing URL parameters...")

        params: dict[str, int] = {}
        interesting_params: set[str] = set()
        categorized: dict[str, set[str]] = {cat: set() for cat in self._PARAM_CATEGORIES}
        # Sample URLs per interesting parameter for context
        param_examples: dict[str, str] = {}

        # Flatten interesting patterns for quick membership test
        all_interesting = {p for plist in self._PARAM_CATEGORIES.values() for p in plist}

        try:
            with open(url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]

            for url in urls:
                if '?' not in url:
                    continue
                query_params = parse_qs(urlparse(url).query)
                for param in query_params:
                    params[param] = params.get(param, 0) + 1
                    param_lower = param.lower()

                    if param_lower in all_interesting or any(p in param_lower for p in all_interesting):
                        interesting_params.add(param)
                        if param not in param_examples:
                            param_examples[param] = url

                    for cat, patterns in self._PARAM_CATEGORIES.items():
                        if param_lower in patterns or any(p in param_lower for p in patterns):
                            categorized[cat].add(param)

            # ── Save raw parameter list ───────────────────────────────────────
            all_params_file = self.output_mgr.get_path('parameters', 'all_parameters.txt')
            with open(all_params_file, 'w') as f:
                for p, cnt in sorted(params.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"{p}: {cnt}\n")

            # ── Save interesting parameters ───────────────────────────────────
            interesting_file = self.output_mgr.get_path('parameters', 'interesting_parameters.txt')
            with open(interesting_file, 'w') as f:
                f.write('\n'.join(sorted(interesting_params)))

            # ── Save categorized parameters ───────────────────────────────────
            cat_file = self.output_mgr.get_path('parameters', 'categorized_parameters.txt')
            with open(cat_file, 'w') as f:
                for cat, pset in categorized.items():
                    if pset:
                        f.write(f"[{cat}] {', '.join(sorted(pset))}\n")
                        for p in sorted(pset):
                            if p in param_examples:
                                f.write(f"  example: {param_examples[p]}\n")

            total_cats = sum(1 for v in categorized.values() if v)
            Logger.success(
                f"Found {len(params)} unique parameters, {len(interesting_params)} interesting "
                f"({total_cats} vuln categories)"
            )

        except Exception as e:
            Logger.error(f"Error analyzing parameters: {e}")


    # gf pattern → short label used in filenames and log messages
    _GF_PATTERNS: list[str] = [
        'ssrf', 'sqli', 'lfi', 'xss', 'idor', 'rce',
        'redirect', 'ssti', 'debug_logic', 'interestingparams',
    ]

    def categorize_with_gf(self, url_file: Path) -> dict[str, int]:
        """Pipe collected URLs through gf patterns to surface likely-vulnerable targets.

        Saves one file per matching pattern to the parameters directory:
          parameters/gf_ssrf.txt, gf_sqli.txt, gf_lfi.txt …

        Returns a dict of {pattern: match_count} so callers know what was found.
        """
        if not ToolChecker.check_tool('gf'):
            return {}

        Logger.info("Categorizing URLs with gf patterns...")
        hits: dict[str, int] = {}

        for pattern in self._GF_PATTERNS:
            out_file = self.output_mgr.get_path('parameters', f'gf_{pattern}.txt')
            try:
                with open(url_file, 'r') as stdin_f:
                    result = subprocess.run(
                        ['gf', pattern],
                        stdin=stdin_f,
                        capture_output=True, text=True, timeout=60,
                    )
                if result.stdout.strip():
                    lines = [l for l in result.stdout.splitlines() if l.strip()]
                    with open(out_file, 'w') as f:
                        f.write('\n'.join(lines) + '\n')
                    hits[pattern] = len(lines)
            except FileNotFoundError:
                break   # gf binary missing — abort
            except Exception:
                continue

        if hits:
            parts = '  '.join(f'{p}:{n}' for p, n in hits.items())
            Logger.success(f"gf: {parts}")
        else:
            Logger.info("gf: no pattern matches in collected URLs")

        return hits


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
            )

            with open(output_file, 'w') as f:
                f.write(result.stdout)

            findings = []
            if json_file.exists():
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        findings = data
                    elif isinstance(data, dict):
                        findings = [data]
                except (json.JSONDecodeError, OSError):
                    pass

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
        # Try without hardcoded fingerprints first (works on most installs)
        try:
            run_logged(
                'subjack',
                ['subjack', '-w', str(input_file), '-o', str(output_file), '-ssl', '-timeout', '30'],
                log_dir,
                timeout=600,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            # Fallback: try with explicit fingerprints path
            fp_path = Path.home() / 'go' / 'pkg' / 'mod' / 'github.com' / 'haccer' / 'subjack@v0.0.0-20201112041112-049c369c6946' / 'fingerprints.json'
            if fp_path.exists():
                try:
                    run_logged(
                        'subjack',
                        ['subjack', '-w', str(input_file), '-o', str(output_file), '-ssl', '-timeout', '30', '-c', str(fp_path)],
                        log_dir,
                        timeout=600,
                    )
                except Exception as e:
                    Logger.error(f"Error in subjack: {e}")
                    return
            else:
                Logger.warning("subjack fingerprints.json not found, skipping")
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
        # Guard: if the stored value is a masked sentinel, skip
        if '••' in webhook_url or not webhook_url.startswith('http'):
            Logger.warning("Discord webhook URL looks invalid — check settings")
            return

        domain    = summary.get('domain', 'unknown')
        timestamp = summary.get('timestamp', '')
        changes   = summary.get('changes', {})
        is_first  = summary.get('first_scan', False)

        fields = []
        for category, data in changes.items():
            new_count     = len(data.get('new', []))
            removed_count = len(data.get('removed', []))
            if new_count or removed_count:
                value = f"+{new_count} new" if new_count else ""
                if removed_count:
                    value += f"  -{removed_count} removed" if value else f"-{removed_count} removed"
                fields.append({
                    "name": category.replace('_', ' ').title(),
                    "value": value or "—",
                    "inline": True,
                })

        if not fields:
            status_text = "First scan completed — no baseline to diff" if is_first else "No changes since last scan"
            fields.append({"name": "Status", "value": status_text, "inline": False})

        embed = {
            "title": f"❯ givenum — {domain}",
            "description": f"Scan completed at {timestamp}",
            "color": self._discord_color(summary),
            "fields": fields,
            "footer": {"text": "GivEnum • github.com/6bat66/Givenum"},
        }

        try:
            import urllib.request, urllib.error
            payload = json.dumps({"embeds": [embed]}).encode('utf-8')
            req = urllib.request.Request(
                webhook_url.strip(),
                data=payload,
                headers={'Content-Type': 'application/json', 'User-Agent': 'GivEnum/1.0'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                status_code = resp.getcode()
                Logger.success(f"Discord notification sent (HTTP {status_code})")
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:200]
            Logger.warning(f"Discord notification failed: HTTP {e.code} — {body}")
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
            Logger.info("No previous scan found — diff skipped, sending scan-complete notification")
            # Still notify so the first scan doesn't go silent
            if self.notifier:
                self.notifier.notify({
                    'domain': self.domain,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'previous_scan': None,
                    'changes': {},
                    'new_vulns': [],
                    'first_scan': True,
                })
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

        def _section(title: str, items: list[str], emoji: str = '⚠️', cap: int = 30):
            if not items:
                return
            lines.append(f"## {emoji} {title}\n")
            for item in items[:cap]:
                lines.append(f"- `{item}`")
            if len(items) > cap:
                lines.append(f"\n_…and {len(items) - cap} more (see output files)_")
            lines.append("\n---\n")

        def _read(category: str, filename: str) -> list[str]:
            p = self.output_mgr.get_path(category, filename)
            if not p.exists():
                return []
            with open(p) as f:
                return [l.strip() for l in f if l.strip()]

        # Email security
        email_issues = _read('vulnerabilities', 'email_security.txt')
        email_issues = [l for l in email_issues if l.startswith('[')]
        _section('Email Security Issues (SPF/DMARC/DKIM)', email_issues, '📧')

        # Security headers
        header_issues = _read('vulnerabilities', 'security_headers.txt')
        _section('HTTP Security Header Issues', header_issues, '🔒')

        # CORS
        cors_issues = _read('vulnerabilities', 'cors_misconfig.txt')
        _section('CORS Misconfigurations', cors_issues, '🌐')

        # Nuclei
        _section('Vulnerabilities (Nuclei)', _read('vulnerabilities', 'nuclei_results.txt'), '🚨')

        # Dalfox
        _section('XSS Findings (Dalfox)', _read('vulnerabilities', 'dalfox_results.txt'), '💉')

        # Takeover
        _section('Subdomain Takeover Candidates', _read('takeover', 'subzy_results.txt'), '🎯')

        # Git exposure
        _section('Exposed Git Repositories', _read('git', 'exposed_git.txt'), '📁')

        # Zone transfer
        _section('Zone Transfer Results', _read('dns', 'zone_transfer.txt'), '🔓')

        # Categorized parameters
        cat_params = _read('parameters', 'categorized_parameters.txt')
        if cat_params:
            lines.append("## 🧩 Interesting Parameters by Category\n")
            for item in cat_params[:50]:
                lines.append(f"  {item}")
            lines.append("\n---\n")

        # Save report
        with open(report_file, 'w') as f:
            f.write('\n'.join(lines))

        Logger.success(f"Report: {report_file}")
    
    def generate_json_report(self, scan_mode: str = 'passive'):
        """Generate JSON report"""
        def _rl(cat: str, fname: str) -> list[str]:
            return self._read_lines(cat, fname)

        statistics = {
            'subdomains':             len(_rl('subdomains', 'all_subdomains.txt')),
            'bruteforce_subdomains':  len(_rl('subdomains', 'bruteforce.txt')),
            'resolved':               len(_rl('dns', 'resolved.txt')),
            'active_http':            len(_rl('http', 'alive.txt')),
            'urls':                   len(_rl('urls', 'urls_clean.txt')),
            'js_files':               len(_rl('js', 'all_js_files.txt')),
            'interesting_parameters': len(_rl('parameters', 'interesting_parameters.txt')),
            'open_ports':             len(_rl('ports', 'open_ports.txt')),
            'nuclei_findings':        len(_rl('vulnerabilities', 'nuclei_results.txt')),
            'dalfox_findings':        len(_rl('vulnerabilities', 'dalfox_results.txt')),
            'security_header_issues': len(_rl('vulnerabilities', 'security_headers.txt')),
            'email_security_issues':  len([l for l in _rl('vulnerabilities', 'email_security.txt') if l.startswith('[')]),
            'cors_findings':          len(_rl('vulnerabilities', 'cors_misconfig.txt')),
            'zone_transfer_records':  len(_rl('dns', 'zone_transfer.txt')),
            'subzy_findings':         len(_rl('takeover', 'subzy_results.txt')),
            'subjack_findings':       len(_rl('takeover', 'subjack_results.txt')),
            'git_exposures':          len(_rl('git', 'exposed_git.txt')),
            'cloud_aws':              len(_rl('cloud', 'aws_services.txt')),
            'cloud_azure':            len(_rl('cloud', 'azure_services.txt')),
            'cloud_gcp':              len(_rl('cloud', 'gcp_services.txt')),
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
                'nuclei':           _rl('vulnerabilities', 'nuclei_results.txt'),
                'dalfox':           _rl('vulnerabilities', 'dalfox_results.txt'),
                'security_headers': _rl('vulnerabilities', 'security_headers.txt'),
                'email_security':   [l for l in _rl('vulnerabilities', 'email_security.txt') if l.startswith('[')],
                'cors':             _rl('vulnerabilities', 'cors_misconfig.txt'),
                'zone_transfer':    _rl('dns', 'zone_transfer.txt'),
                'takeover': {
                    'subzy':   _rl('takeover', 'subzy_results.txt'),
                    'subjack': _rl('takeover', 'subjack_results.txt'),
                },
                'git_exposure': _rl('git', 'exposed_git.txt'),
                'parameters': {
                    'interesting':  _rl('parameters', 'interesting_parameters.txt'),
                    'categorized':  _rl('parameters', 'categorized_parameters.txt'),
                },
                'cloud': {
                    'aws':   _rl('cloud', 'aws_services.txt'),
                    'azure': _rl('cloud', 'azure_services.txt'),
                    'gcp':   _rl('cloud', 'gcp_services.txt'),
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
        # Apply proxy env-vars so all child processes inherit them
        _apply_proxy_env()

        # Components
        self.subdomain_enum = SubdomainEnum(domain, self.output_mgr, self.api_config)
        self.dns_resolver = DNSResolver(self.output_mgr)
        self.port_scanner = PortScanner(self.output_mgr)
        self.http_prober = HTTPProber(self.output_mgr)
        self.url_collector = URLCollector(self.output_mgr, self.domain)
        self.js_analyzer = JSAnalyzer(self.output_mgr)
        self.git_dumper = GitDumper(self.output_mgr)
        self.vuln_scanner    = VulnScanner(self.output_mgr)
        self.fuzz_scanner    = FuzzScanner(self.output_mgr)
        self.jwt_scanner     = JWTScanner(self.output_mgr)
        self.s3_scanner      = S3Scanner(domain, self.output_mgr)
        self.bypass_scanner  = BypassScanner(self.output_mgr)
        self.api_discovery   = APIDiscovery(self.output_mgr)
        self.cloud_detector  = CloudDetector(self.output_mgr)
        self.recon_enricher  = ReconEnricher(domain, self.output_mgr)
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
            Logger.info("Tip: use --active to enable brute-force, ffuf, nuclei, dalfox, sqlmap, arjun")

        # 1. Subdomain enumeration (passive sources)
        subs_file = self.subdomain_enum.run_all()

        # 1a. Zone transfer + email security (DNS-only, runs early)
        self.recon_enricher.check_zone_transfer()
        self.recon_enricher.check_email_security()

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

        # 3. Cloud detection + S3 bucket scan
        self.cloud_detector.detect(resolved_file)
        self.s3_scanner.scan()

        # 4. sdlookup — queries Shodan InternetDB, zero direct packets, always safe
        # Run this BEFORE httpx so Shodan data is available early.
        if not skip_portscan:
            self.port_scanner.scan_with_sdlookup(resolved_file)

        # 5. HTTP Probing — must run BEFORE naabu.
        # naabu does active TCP scanning across 40+ ports; government/WAF targets
        # detect the port sweep and block the scanner's IP.  Running httpx first
        # while the IP is still clean ensures we get real HTTP responses.
        alive_file = self.http_prober.probe_with_httpx(resolved_file)

        if not alive_file or count_nonempty_lines(alive_file) == 0:
            Logger.warning("No active hosts found, stopping after HTTP probing")
            self._finalize_run(start_time, active=active)
            return

        self.http_prober.check_urls_with_hakcheckurl(alive_file)

        # 5a. naabu active port scan — runs HERE, AFTER httpx, so the IP sweep
        # does not trigger WAF/firewall blocks before we get HTTP responses.
        if not skip_portscan:
            self.port_scanner.scan_with_naabu(resolved_file)

        # 5b. CORS misconfig + WAF detection + security headers
        self.recon_enricher.detect_cors_misconfig(alive_file)
        self.recon_enricher.detect_waf(alive_file)
        self.recon_enricher.check_security_headers(alive_file)

        # 5c. JWT testing (passive — reads httpx response headers)
        httpx_json = self.output_mgr.get_path('http', 'httpx_full.json')
        self.jwt_scanner.scan_from_httpx(httpx_json)

        # 5d. 403/401 bypass (active only)
        if active:
            self.bypass_scanner.bypass_403(httpx_json)

        # 6. Screenshots
        if not skip_screenshots:
            self.http_prober.screenshot_with_gowitness(alive_file)

        # 7. URL Collection
        all_urls = self.url_collector.collect_from_archives(alive_file)

        # 8. Probe common paths with meg + parse robots.txt / sitemap.xml
        all_urls.update(self.url_collector.probe_paths_with_meg(alive_file))
        all_urls.update(self.url_collector.parse_robots_sitemap(alive_file))

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
                # 12b. gf pattern categorization (passive — pure regex, no network)
                gf_hits = self.param_discovery.categorize_with_gf(clean_urls)
                if active:
                    self.param_discovery.discover_with_arjun(clean_urls)

        # 13. JavaScript Analysis
        self.js_analyzer.analyze_all(alive_file)

        # 14. Git exposure
        self.git_dumper.check_and_dump(alive_file)

        # 14b. API discovery — kiterunner sends only HTTP GETs to known route patterns,
        # no payloads, purely discovery-oriented → runs in passive mode too
        self.api_discovery.discover(alive_file)

        # 15. Vulnerability scanning (active only)
        if active and not skip_vuln_scan:
            # 15b. Directory fuzzing — finds admin panels, backups, hidden APIs
            self.fuzz_scanner.fuzz_with_ffuf(alive_file)

            self.vuln_scanner.scan_with_nuclei(alive_file)

            # 15b. XSS scanning with dalfox (active only)
            clean_urls = self.output_mgr.get_path('urls', 'urls_clean.txt')
            if clean_urls.exists():
                self.vuln_scanner.scan_with_dalfox(clean_urls)

            # 15c. SQL injection on gf-sqli categorized URLs
            gf_sqli_file = self.output_mgr.get_path('parameters', 'gf_sqli.txt')
            self.vuln_scanner.scan_with_sqlmap(gf_sqli_file)

        # 16. Takeover check
        self.takeover_checker.check_with_subzy(resolved_file)
        if active:
            self.takeover_checker.check_with_subjack(resolved_file)

        # 17. Diff tracking
        self.diff_manager.diff_results()

        # 18. Generate reports
        self.report_generator.generate_markdown_report(scan_mode='active' if active else 'passive')
        self.report_generator.generate_json_report(scan_mode='active' if active else 'passive')
        # _generate_analysis_report() removed with analyze_results.py (TASK #20).

        # Summary
        self._print_summary(time.time() - start_time)

    def _finalize_run(self, start_time: float, active: bool = False):
        """Write partial results and print a summary before exiting early"""
        self.diff_manager.diff_results()
        self.report_generator.generate_markdown_report(scan_mode='active' if active else 'passive')
        self.report_generator.generate_json_report(scan_mode='active' if active else 'passive')
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
                    Logger.info(f"{name}: {count_nonempty_lines(path)}")
                except OSError as e:
                    Logger.warning(f"Could not count {name} ({path}): {e}")

        Logger.success(f"\nTime: {elapsed_time/60:.2f} minutes")
        Logger.success(f"Results: {self.output_mgr.base_dir}")
        Logger.info(f"Report: {self.output_mgr.get_path('reports', 'report.md')}")
        analysis_file = self.output_mgr.get_path('reports', 'analysis.md')
        if analysis_file.exists():
            Logger.info(f"Analysis: {analysis_file}")

        # Tool execution summary
        if _tool_log:
            Logger.header("TOOL EXECUTION SUMMARY")
            ok = partial = fail = timeout = error = skip = skipped = 0
            for tool, info in sorted(_tool_log.items()):
                st = info['status']
                if st == 'ok':
                    icon = Colors.OKGREEN + '✓' + Colors.ENDC
                    ok += 1
                elif st == 'partial':
                    icon = Colors.WARNING + '~' + Colors.ENDC
                    partial += 1
                elif st == 'timeout':
                    icon = Colors.FAIL + '⏱' + Colors.ENDC
                    timeout += 1
                elif st == 'error':
                    icon = Colors.FAIL + '!' + Colors.ENDC
                    error += 1
                elif st == 'not_found':
                    icon = Colors.WARNING + '—' + Colors.ENDC
                    skip += 1
                elif st == 'skipped':
                    icon = Colors.WARNING + '⊘' + Colors.ENDC
                    skipped += 1
                else:  # 'fail' or any other
                    icon = Colors.FAIL + '✗' + Colors.ENDC
                    fail += 1
                Logger.info(f"  {icon} {tool:<22} {st:<10} {info['elapsed']}s")
            Logger.info(
                f"\n  ok={ok}  partial={partial}  fail={fail}  "
                f"timeout={timeout}  error={error}  skipped={skipped}  not_found={skip}"
            )
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
    _I  = Logger._C_INF
    _G  = Logger._C_FND
    _D  = Logger._C_DIM
    _B  = Logger._C_BOLD
    _R  = Logger._C_RST

    banner = (
        f"\n"
        f"{_I}{_B}"
        f"  _____ _       ______\n"
        f" / ___/(_)   __/ ____/___  __  ______ ___\n"
        f"/ (_ / / /| |/ / __/ / _ \\/ / / / __ `__ \\\n"
        f"\\___/_/_/ |___/____/_//_/\\__,_/_/ /_/ /_/\n"
        f"{_R}"
        f"{_D}                                        v2.0{_R}\n"
        f"\n"
        f"  {_G}passive recon · active exploitation · asset discovery{_R}\n"
        f"  {_D}givenum.io{_R}\n"
    )

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

    # Check critical tools — fail fast so the user doesn't wait hours for an
    # empty scan when a P0 tool isn't on PATH.
    critical_missing, recommended_missing = ToolChecker.check_required(active=args.active)
    if critical_missing:
        Logger.error(f"Missing critical tools: {', '.join(critical_missing)}")
        Logger.error("Install them with: ./install_tools.sh   (or: docker compose build app)")
        sys.exit(1)
    if recommended_missing:
        Logger.warning(
            f"Missing recommended tools (scan will continue but lose capability): "
            f"{', '.join(recommended_missing)}"
        )

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
