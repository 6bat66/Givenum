# Security policy

GivEnum is itself a security tool, so it's a meatier target than a
typical OSS project — config files, proxy URLs, and target domains all
flow through subprocess calls. Take this policy seriously.

---

## Reporting a vulnerability

**Do NOT open a public GitHub issue for security problems.** Instead:

1. Email `davidalmeida8414@gmail.com` with the subject line starting with
   `[GIVENUM SECURITY]`.
2. Include:
   - a clear description of the vulnerability
   - reproduction steps (commands, config, payloads)
   - the version / commit hash you tested against
   - whether you've shared it with anyone else

Expect an acknowledgement within **5 business days**. A fix or
mitigation timeline follows after triage. We'll credit you in the
release notes unless you ask us not to.

If you believe the issue is being actively exploited, mark the email as
urgent and we'll prioritise.

---

## Supported versions

The audit + hardening work happens on the `organize-web-enum-tools`
branch (current default). Only that branch receives security fixes —
older tags / branches are unmaintained.

---

## What counts as a vulnerability

| Category | Severity | Example |
|---|---|---|
| Path traversal | High | A `--domain` value that escapes `results/` |
| Command injection | High | A proxy URL or config field that runs an arbitrary shell command |
| Credential disclosure | High | API keys leaking into a log or report file |
| SSRF | Medium | The proxy fetcher being tricked into hitting an internal address |
| Denial of service | Low–Medium | A malformed target that hangs a scan indefinitely |
| Code execution via crafted target response | High | A scan target's HTML/JS payload triggering arbitrary code in our parser |

What does **not** count as a vulnerability:

- Running GivEnum against a target you don't own (that's a *you* problem)
- Tools that hang because the target rate-limits them
- Subprocess output with junk (we can't sanitise everything)

---

## Hardening already applied

These are the security fixes done during the audit. If you find a
regression in any of them, please report it.

| Fix | Where | Why |
|---|---|---|
| `OutputManager` domain validation | `GivEnum.py` | Prevent `--domain "../etc"` writing outside results dir |
| `OutputManager.get_path` containment check | `GivEnum.py` | Same protection for individual file writes |
| `proxy-fetcher` `exec` → `execFile` | `web/src/lib/proxy-fetcher.ts` | Stop shell-meta in proxy URLs from running commands (supply-chain risk: proxy lists come from public GitHub repos) |
| Screenshot route MIME whitelist | `web/src/app/api/scan/[id]/screenshot/[file]/route.ts` | Block `.env` / `.log` from being served as if they were images |
| Tool installer registry, not shell script generation | `web/src/app/api/tools/update/route.ts` | Replaces a generated shell script with `execFile` invocations of validated tool argv arrays |
| `_tool_log` thread-safe lock | `GivEnum.py` | Prevent torn reads when a reader iterates while writers append |
| Force IPv4 for Python HTTP | `GivEnum.py` (`urllib3.util.connection.HAS_IPV6 = False`) | Side-effect of fixing the Network unreachable bug — also prevents some IPv6-routing surprises |

---

## Threat model

GivEnum is **not** designed to be hardened against:

- A **malicious user with shell access to the host** running the scanner.
  Anyone who can run `python3 GivEnum.py` can already do everything the
  scanner can do.
- A **compromised target** that returns crafted HTTP responses *intended*
  to abuse a parser bug. We do basic defensive parsing but rely on the
  underlying tools (subfinder, httpx, nuclei) for safety against this.
- A **malicious tool binary** dropped into `$PATH`. We assume the system
  binaries (`subfinder`, `httpx`, etc.) come from the install script /
  Dockerfile and haven't been tampered with.

GivEnum **is** designed to be hardened against:

- **Untrusted target domains** passed via `--domain` or the dashboard form
- **Proxy URLs** loaded from public GitHub repos (treated as adversarial
  input — see proxy-fetcher hardening above)
- **API keys** stored in `~/.config/givenum/api.json` (file is masked when
  shown in the UI; never logged in plain text)

---

## Disclaimer

GivEnum is for **authorized** security testing. Use only against systems
you own or have explicit, written permission to test. The author does
not accept liability for misuse.
