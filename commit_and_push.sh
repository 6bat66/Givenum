#!/usr/bin/env bash
# Commits + pushes the audit work that was prepared during the Cowork session.
# Safe to re-run — only commits if there are staged changes.

set -euo pipefail

cd "$(dirname "$0")"

# 1. Clear any stale lock from earlier sessions
if [ -f .git/index.lock ]; then
  rm -f .git/index.lock
  echo "[*] removed stale .git/index.lock"
fi

# 2. Ensure identity is set (Cowork sandbox set it but a fresh shell may not have it)
git config user.name  "6bat66"
git config user.email "davidalmeida8414@gmail.com"

# 3. Drop the stray tsbuildinfo if it slipped in before .gitignore was updated
git rm -f --cached web/tsconfig.tsbuildinfo 2>/dev/null || true

# 4. Stage everything except the audit notes (they go in their own commit)
git add -A -- ':!docs'

# 5. Big feature commit
if ! git diff --cached --quiet; then
  git commit -m "feat: settings hub, dashboard v2, security hardening

Settings:
- New /settings/{apis,proxy,tools,reports} sub-pages with sidebar nav
- Proxy management: single mode (Burp) + rotate mode (free list fetch+validate)
- Tools update console: select tools and update from the browser, live log tail
- HTML report generator per scan
- API keys page: preserve masked values on save, allow clearing via empty string

Dashboard:
- Neon-purple palette, blurred sticky header
- Responsive scan rows, project chip, rescan button
- ScanTabs: alive-only filter for subdomains, extension filter for URLs,
  external-domain filter for screenshots
- JobLogViewer: prevent overlapping polls (was duplicating log lines)

Diff & data:
- Diff is now computed from current/previous scan dirs in a single source
  of truth (DIFF_SOURCES map) instead of duplicated ternary chains
- DiffData gains current/previous/persisted fields for richer diff views

Tooling & infra:
- Dockerfile: add naabu, ffuf, byp4xx, kiterunner, jwt-tool, s3scanner, gf,
  shuffledns, notify, interactsh-client + SecLists wordlists + gf-patterns
- install_tools.sh: install summary counters + non-zero exit on missing P0
- Tool registry now carries an installer argv array; the API spawns a Node
  orchestrator that runs each installer with execFile (no shell), eliminating
  the previous generated-shell-script pattern

Security hardening:
- proxy-fetcher.ts: exec(string) -> execFile('curl', argv) prevents command
  injection through proxy URLs sourced from public GitHub repos
- OutputManager (Python): regex-validated domain + Path.resolve()/relative_to()
  guard against path traversal via --domain '../../etc/passwd'
- OutputManager.get_path: same guard for category/filename
- screenshot route: whitelist .png/.jpg/.jpeg/.webp/.gif extensions and
  re-validate the resolved path stays inside the screenshots directory
- _tool_log: thread-safe lock + record_tool_log/snapshot_tool_log helpers
- 5 bare 'except:' replaced with typed handlers (OSError, JSONDecodeError,
  Exception) and Logger.warning where the failure was previously silent
- ToolChecker.check_required(active=False): explicit P0 vs P1 lists, fail-fast
  when a critical tool is missing, warn (don't fail) on missing recommended

README rewritten end-to-end to reflect current state.
"
  echo "[+] feature commit done"
else
  echo "[~] nothing to commit for feature work"
fi

# 6. Audit notes commit (kept separate so it can be reverted/removed cleanly)
git add docs/
if ! git diff --cached --quiet; then
  git commit -m "docs: add audit notes (docs/AUDIT.md)"
  echo "[+] audit-notes commit done"
else
  echo "[~] no audit notes to commit"
fi

# 7. Push to origin (current branch)
BRANCH=$(git symbolic-ref --short HEAD)
echo ""
echo "[*] pushing $BRANCH to origin..."
git push origin "$BRANCH"

# 8. (Optional) Delete the stale branches identified in the audit
echo ""
echo "[?] To delete the stale branches identified in the audit, run:"
echo "    git branch -D fix/bugs-and-cleanup claude/determined-darwin"
echo "    git push origin --delete fix/bugs-and-cleanup claude/determined-darwin"
