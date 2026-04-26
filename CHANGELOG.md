# Changelog

All notable changes to GivEnum follow this file. Format adapted from
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses date-based pre-release versioning until v1.0.

## [Unreleased]

### Added
- `LICENSE` (MIT) — README claimed it for ages; file finally exists.
- `CONTRIBUTING.md`, `SECURITY.md`, this `CHANGELOG.md` (TASK #31).
- `LICENSE`, `requirements.txt` (runtime Python deps split from `-dev`).
- `.github/workflows/test.yml` — pytest + vitest run on every push and PR.
- `tests/` directory:
  - `test_output_manager.py` — domain regex, path traversal, dir layout (21)
  - `test_matches_domain.py` — wildcards, case, suffix collision (16)
  - `test_tool_log.py` — thread safety battery (4)
  - `test_tool_registry_consistency.py` — drift between Dockerfile / Python / TS registries (6)
  - `test_amass_skip.py` — TASK #25 contract (4)
  - `test_givenum_smoke.py` — orphan `self.method()` calls regression (3)
  - `test_url_collector_wiring.py` — orphan `self.<attr>` access regression (3)
  - `test_force_ipv4.py` — TASK #22 regression (1)
  - `test_git_dumper_errors.py` — failure-mode classification (4)
  - `test_scan_runner.py` — `load_job` no longer swallows JSON corruption (4)
  - `web/src/lib/proxy-fetcher.test.ts` (vitest) — `normaliseProxy` + shell-metachar regression battery (22)
  - `web/src/lib/results.test.ts` (vitest) — `buildDiffData` semantics (6)
- `urlfinder` (PD) integrated as the primary archive URL collector; far
  faster than the previous `gau + waybackurls` setup on healthy targets.
- `sqlmap` install in the Dockerfile (was only in `install_tools.sh`).
- Dockerfile **tool installation verification stage** — fails the build
  if any critical tool didn't install, warns on missing recommended.
- Settings hub in the web dashboard: `/settings/{apis,proxy,tools,reports}`
  with sidebar nav.
- Proxy management (single + rotate modes, validated via `curl --proxy`).
- Tools update console (select tools, update from browser, live log tail).
- HTML report generator per scan.
- API keys page: preserves masked values on save, allows clearing via
  empty string.
- Dashboard v2: neon-purple palette, blurred sticky header, responsive
  scan rows, project chip, rescan button.
- `ScanTabs`: alive-only filter for subdomains, extension filter for URLs,
  external-domain filter for screenshots.
- Diff calculation refactored to compute from current/previous scan dirs
  directly, with `current` / `previous` / `persisted` fields added.

### Changed
- README rewritten end-to-end to reflect current state.
- `ToolChecker.check_required(active=False)` — explicit P0 vs P1 lists,
  fail-fast when a critical tool is missing, warn (don't fail) on missing
  recommended.
- `install_tools.sh` — install summary counters, non-zero exit on missing
  P0, `try_run` helper for ad-hoc installs.
- `proxy-fetcher.ts` — `exec(string)` replaced with
  `execFile('curl', argv)` to neutralise supply-chain command injection.
- `OutputManager` — domain regex now requires at least one alphanumeric
  character; resolved path must stay inside `base_dir`.
- `_tool_log` — now thread-safe via lock + `record_tool_log` /
  `snapshot_tool_log` helpers.
- 5 bare `except:` in `GivEnum.py` replaced with typed handlers and
  `Logger.warning`.
- 1 bare `except Exception: pass` in `scan_runner.py` (`load_job`)
  replaced with typed handlers + stderr logging.
- Tools update API now spawns a Node orchestrator that runs each
  installer with `execFile` (no shell script generation).
- Screenshot route now whitelists image extensions and re-validates the
  resolved path stays inside the screenshots directory.
- `JobLogViewer` — overlap-poll guard prevents log line duplication.
- Force IPv4 for all Python HTTP via
  `urllib3.util.connection.HAS_IPV6 = False` — fixes Network unreachable
  errors that killed crt.sh / VirusTotal / AlienVault / JS download / git
  dumper mid-scan in 4 real scans.
- `URLCollector.__init__` now accepts a `domain` parameter (used by
  `urlfinder` zone-level lookup).
- `GitDumper.check_and_dump` failure-mode classification: SSL mismatch
  vs unreachable vs unexpected, with a single summary line instead of
  ~50 individual warnings per scan.
- Kiterunner wordlist: 8 candidate paths in `APIDiscovery._WORDLISTS` +
  Dockerfile downloads once and symlinks to all known kr layouts.
- `_archive_targets` docstring updated to reflect gau-only (after
  waybackurls removal).
- Web `package.json` engines bumped from `>=20 <23` to `>=20`.
- `.gitignore` — `.env*` (any variant) blocked; `.env.example` allowed.
- `CHEAT_SHEET.md` references updated from "WebEnum" → "GivEnum",
  `/opt/webenum` → `/opt/givenum`.

### Removed
- `analyze_results.py` (535-line orphan script confirmed unused).
  Dead references removed from `web/src/app/api/scans/start/route.ts`,
  `GivEnum.py` (`_generate_analysis_report` no-op), `README.md`,
  `CHEAT_SHEET.md`.
- `waybackurls` (TASK #24) — 0 URLs in 4/4 real scans.
- `xurlfind3r` (TASK #23) — same: 0 URLs in 4/4 real scans, 50%+ host
  timeout rate.
- `analyzer-script` argument from `scan_runner.py` and the wrapper that
  invoked the deleted analyzer.
- Branches `fix/bugs-and-cleanup` (already merged via PR #3) and
  `claude/determined-darwin` (stale fork) deleted from origin.

### Fixed
- `proxy-fetcher` supply-chain command injection (HIGH).
- `OutputManager` path traversal via `--domain` (HIGH).
- `_tool_log` torn-read race condition (MEDIUM).
- Dockerfile install silencer for `kr` and `jwt_tool` — both reported as
  "not found" at scan time despite being in the Dockerfile (HIGH for ops).
- `amass` no-op 10-min run when no API keys are configured — now skips
  in 0s with a clear warning (TASK #25).
- `urlfinder` initial integration: switched from `-list <hosts>` to
  `-d <root> -all` matching the upstream usage example. Output is
  filtered through `matches_domain` to drop cross-zone leakage from
  providers like OTX.
- `_generate_analysis_report` orphan call site that crashed
  `run_full_enum` at the very end of every scan after `analyze_results.py`
  was removed.
- `URLCollector` missing `self.domain` attribute crashed `urlfinder`
  immediately. Now passed via constructor with backwards-compat default.
- Dockerfile previously masked `kr` and `jwt_tool` install failures;
  now the verification stage prints PASS/FAIL for every expected tool
  and fails the build on any missing CRITICAL.
- Diff source mapping in `web/src/lib/results.ts` was duplicated TWICE
  in the same function — extracted to a single `DIFF_SOURCES` map.

---

## How to update this file

When you open a PR, append your changes under the appropriate
`Unreleased` subsection (`Added` / `Changed` / `Fixed` / `Removed`).
Keep entries short — link to the commit or task number for context.

When we cut a release, the `[Unreleased]` block is renamed to the
version + date and a fresh `[Unreleased]` is inserted at the top.
