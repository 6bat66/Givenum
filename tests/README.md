# Tests

Minimal pytest + vitest suite covering the highest-risk areas of the codebase.
Targets identified by the audit: `OutputManager` (path traversal), `matches_domain`
(filtering correctness), `_tool_log` (thread safety), `normaliseProxy` (supply-chain
input validation), `buildDiffData` (diff semantics).

This isn't a "100% coverage" suite. It's the **floor below which we don't refactor**
the larger modules — every safe rewrite of `GivEnum.py` should keep these green.

---

## Python (pytest)

### One-time setup

```bash
pip install --break-system-packages -r requirements-dev.txt
# or, in a venv:  pip install -r requirements-dev.txt
```

### Run

```bash
pytest                    # run everything
pytest tests/test_output_manager.py -v
pytest -k "traversal"     # filter by name
```

Configuration lives in `pytest.ini`. Each test has a 30 s timeout (set via
`pytest-timeout`) so a deadlock in the concurrency tests doesn't hang CI.

### What's covered

| File | What it proves |
|---|---|
| `test_output_manager.py` | Domain regex rejects path-traversal/shell-metachar inputs; `get_path` keeps every write inside its category dir; standard subdirs are created. |
| `test_matches_domain.py` | Suffix collisions (`notexample.com` vs `example.com`) don't match; wildcards, case, trailing dots all behave. |
| `test_tool_log.py` | 200 concurrent writes don't lose entries; readers iterating during writes don't raise; `snapshot_tool_log()` returns an independent copy. |

---

## Web (vitest)

### One-time setup

```bash
cd web
npm install   # picks up vitest from devDependencies
```

### Run

```bash
cd web
npm test            # one-shot
npm run test:watch  # interactive
```

Configuration lives in `web/vitest.config.ts`. Tests live next to the code they
exercise: `src/lib/proxy-fetcher.test.ts`, `src/lib/results.test.ts`.

### What's covered

| File | What it proves |
|---|---|
| `proxy-fetcher.test.ts` | `normaliseProxy` accepts well-formed URLs, infers `http://` for `ip:port`, skips comments, rejects malformed input. Regression battery for shell-metachar payloads (`$(…)`, backticks, `;`, `|`, `&&`) — the supply-chain attack surface that motivated the `execFile` switch. |
| `results.test.ts` | `buildDiffData` correctly classifies `new` / `persisted` / `removed` against fresh/empty/identical/duplicate inputs. |

---

## Adding a new test

1. **Pick the smallest unit** — a function or a class method, not a whole pipeline.
2. **Name it after the behaviour, not the implementation.** Good: `test_rejects_unsafe_domains`. Bad: `test_regex_returns_none`.
3. **One concept per test.** If you're using `parametrize`/`it.each`, all rows should test the same property.
4. **Run it locally before committing.** A red test in CI burns more time than a 30 s local check.

---

## CI (not yet wired)

When you add GitHub Actions, the minimum is:

```yaml
# .github/workflows/test.yml (sketch)
on: [push, pull_request]
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements-dev.txt requests dnspython
      - run: pytest
  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - run: cd web && npm ci && npm test
```
