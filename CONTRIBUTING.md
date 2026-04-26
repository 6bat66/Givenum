# Contributing to GivEnum

Thanks for considering a contribution. This file is the short version of how
to work on GivEnum without breaking the rest of the project.

---

## Quick start for contributors

```bash
git clone https://github.com/6bat66/Givenum
cd Givenum

# Python deps (runtime + dev)
pip install --break-system-packages -r requirements.txt -r requirements-dev.txt

# Web deps
cd web && npm install && cd ..

# Confirm the suite is green before you touch anything
python3 -m pytest -v
cd web && npm test && cd ..
```

If any test is red **before** you start, stop and report it as an issue
instead of layering changes on top.

---

## What to send a PR for

| Want to do | Open an issue first? |
|---|---|
| Fix a clear bug, with a test that reproduces it | No — just send the PR |
| Add support for a new tool | **Yes** — discuss whether it overlaps with existing tools |
| Refactor an existing class without behaviour change | No, but include tests |
| Change the scan pipeline order | **Yes** — affects everyone |
| Add a new dashboard page | No, but follow the patterns in `web/src/app/settings/*` |

---

## House rules

1. **Tests are mandatory for new behaviour.** The suite caught two real bugs
   that would have wasted 30 min of scan time each. Don't remove tests
   without explaining why in the PR description.

2. **No bare `except:`.** The audit removed five of these and they keep
   coming back. Specify the exception class:
   ```python
   try:
       ...
   except (OSError, json.JSONDecodeError) as e:
       Logger.warning(f"context: {e}")
   ```

3. **No `|| echo "X failed"` in the Dockerfile** for new tools. The
   `Dockerfile` has a verification stage near the end — adding a new tool
   means adding it to the `for t in ...` loop too. The CI consistency test
   (`tests/test_tool_registry_consistency.py`) catches drift between the
   Python `ToolChecker`, the `web/src/lib/tools.ts` registry, and the
   Dockerfile.

4. **Don't delete a method without grepping for every call site.**
   Two regressions from the audit came from this. Run:
   ```bash
   grep -n "method_name" $(git ls-files '*.py' '*.ts' '*.tsx')
   ```

5. **Web UI strings:** if you add user-facing text, follow whatever
   Portuguese/English mix already exists on the page. Full localisation is
   a future task (#28); don't half-do it.

6. **Tools that produce "0 results in 4 scans" get deleted.** waybackurls
   and xurlfind3r were removed for this reason. New tools must justify
   their slot — measure yield over at least 2 real scans before merging.

---

## Pipeline for a typical change

```
git checkout -b feat/short-name
# … hack on it …
python3 -m pytest -v             # all green
cd web && npm test && cd ..      # all green
cd web && npx tsc --noEmit       # type-check passes

git add -A
git commit -m "feat|fix|docs|refactor|test: <one-line summary>

<paragraph explaining WHY this change exists, not just WHAT it does>

Tests:
- list new test files / cases
"
git push origin feat/short-name
# open PR — CI runs the suite automatically (.github/workflows/test.yml)
```

Commit messages: lowercase prefix from the conventional-commits list
(`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`). Body should
explain *why*, not just *what* — the diff already shows what changed.

---

## How to add a new recon tool

1. **Pick the right registry.** A tool exists in up to four places:
   - `Dockerfile` (install step + verification stage entry)
   - `install_tools.sh` (`go_install` or `pip_install`)
   - `GivEnum.py` `ToolChecker.REQUIRED_TOOLS` (Python-side check)
   - `web/src/lib/tools.ts` `TOOL_REGISTRY` (UI-side check)

2. **The consistency test** (`tests/test_tool_registry_consistency.py`)
   will fail at PR time if any of the four are missing.

3. **Wire it into the orchestrator class** that owns its category — e.g.
   archive collectors live in `URLCollector._crawlers`. Your collector
   method should:
   - check `ToolChecker.check_tool('toolname')` and return `set()` if missing
   - record status in `_tool_log` via `record_tool_log(...)` so the
     execution summary stays informative
   - have a hard timeout (no tool should hang the scan)

4. **Run it against ≥2 real targets** before merging. If yield is 0/0,
   you're adding noise. Get evidence first.

---

## Reporting bugs

Issues should include:

- the exact command (CLI flags or dashboard action)
- the target type (single domain / wildcard / etc.)
- the relevant chunk of `logs/<tool>.log` if a specific tool failed
- the `TOOL EXECUTION SUMMARY` block from the end of the scan log

If the bug is security-related (e.g. a way to escape the results dir, or
inject a shell command via a config file), **do not file a public issue** —
see [SECURITY.md](SECURITY.md).
