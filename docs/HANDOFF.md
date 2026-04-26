# GivEnum — Handoff para próxima sessão de Claude

Documento gerado ao fim de uma sessão pesada de auditoria + hardening
(2026-04-25 → 2026-04-27). Cole isso na próxima conversa para a
nova instância pegar contexto sem precisar re-descobrir tudo.

---

## TL;DR

GivEnum é uma plataforma de recon (passive + active) com CLI Python
(`GivEnum.py`, ~5k linhas) e dashboard Next.js 15 (`web/`). Roda em
Docker. Branch principal: `organize-web-enum-tools`.

A última sessão fechou **34 tasks** (auditoria, hardening de segurança,
delete de tools mortas, integração de novas tools, governance docs,
mypy CI). Estado:

- **102 testes verdes** (74 Python pytest + 28 web vitest)
- CI no GitHub Actions: pytest + vitest + tsc + mypy (mypy continue-on-error)
- 19 tasks abertas, **todas não-bloqueantes**
- Última vulnerabilidade reportável encontrada num scan: foi falso
  positivo do subzy (`url7672.ihdublin.com` aparentava Cargo Collective
  takeover, era SendGrid tracking — não reportável)

---

## O usuário

- **Username:** dvl (`6bat66` no GitHub, `davidalmeida8414@gmail.com`)
- **Estilo preferido:** "act like a mature debater, question my ideas,
  challenge my views, show me the blind spots". **NÃO valida sem
  questionar.** Empurra de volta quando ele pede excesso de auditoria
  ou refatoração arriscada sem testes.
- **Background:** "curious penetration tester" — foco em recon e bug
  bounty. Português é a língua principal.
- **Padrão observado:** tem instinto de "audit tudo, refactor tudo".
  Combata isso. ROI > volume.

---

## Estado do código (snapshot atual)

### Estrutura
```
/Users/dvl/CODE/Givenum/
├── GivEnum.py             # 5k linhas — orchestrator (god file, será modularizado eventualmente)
├── scan_runner.py         # wrapper usado pelo web pra spawn de scan
├── batch_enum.sh          # CLI multi-domain
├── install_tools.sh       # installer cross-platform com summary counters
├── Dockerfile             # imagem all-in-one (Kali base) com verification stage
├── docker-compose.yml     # services: app (web+tools) e scanner (CLI)
├── pyproject.toml         # mypy config
├── pytest.ini
├── requirements.txt       # runtime Python deps
├── requirements-dev.txt   # pytest + mypy + pytest-timeout
├── .github/workflows/test.yml   # CI matrix: Python 3.11/3.12 + Node 22
├── README.md              # rewritten end-to-end
├── CONTRIBUTING.md        # house rules + how to add a tool
├── SECURITY.md            # disclosure policy + threat model
├── CHANGELOG.md           # Keep a Changelog format
├── LICENSE                # MIT
├── docs/
│   ├── AUDIT.md          # auditoria original detalhada
│   └── HANDOFF.md        # ESTE arquivo
├── tests/
│   ├── test_output_manager.py        # 21 — domain regex, path traversal
│   ├── test_matches_domain.py        # 16 — wildcards, suffix collision
│   ├── test_tool_log.py              # 4 — thread safety
│   ├── test_tool_registry_consistency.py  # 6 — drift check entre Python/TS/Dockerfile
│   ├── test_amass_skip.py            # 12 — skip-fast contract
│   ├── test_givenum_smoke.py         # 3 — orphan self.method() calls
│   ├── test_url_collector_wiring.py  # 3 — orphan self.<attr> access
│   ├── test_force_ipv4.py            # 1 — IPv4 patch regression
│   ├── test_git_dumper_errors.py     # 4 — failure-mode classification
│   └── test_scan_runner.py           # 4 — load_job typed exceptions
└── web/                   # Next.js 15 + React 19 + TS strict
    ├── package.json       # engines: ">=20" (era <23 antes, bumpado)
    ├── vitest.config.ts
    └── src/lib/*.test.ts  # 28 testes vitest
```

### Branches
- **`organize-web-enum-tools`** — único ativo, default
- `fix/bugs-and-cleanup` e `claude/determined-darwin` — DELETADAS

### Identidade git
```
git config user.name  "6bat66"
git config user.email "davidalmeida8414@gmail.com"
```

---

## Testes & CI — checklist antes de commitar

```bash
cd /Users/dvl/CODE/Givenum

# Python (74 testes)
python3 -m pytest -v
# OBS: usuário roda Mac com Python 3.14 (Homebrew). pytest deve ser
# instalado lá. Se 'pytest: command not found', use:
#   /opt/homebrew/opt/python@3.14/bin/python3.14 -m pip install --break-system-packages pytest pytest-timeout requests dnspython mypy types-requests
# OU use /usr/bin/python3 -m pytest -v

# Web (28 testes vitest + tsc)
cd web
npm test
npx --no-install tsc --noEmit
cd ..
```

CI roda automaticamente em todo push para `organize-web-enum-tools`.

---

## House rules (do CONTRIBUTING.md, releia antes de mexer)

1. **Tests are mandatory for new behaviour.** A sessão anterior pegou
   2 bugs críticos por causa de tests escritos a posteriori — escreva
   ANTES.
2. **No bare `except:`.** Especifique a exception class.
3. **No `|| echo "X failed"` no Dockerfile** sem entrar no
   verification stage.
4. **Antes de deletar um método, GREP exhaustivo:**
   ```bash
   grep -n "method_name" $(git ls-files '*.py' '*.ts' '*.tsx')
   ```
   Sessão passada: removi `_generate_analysis_report()` mas deixei
   uma call site órfã. Crashou scan de 30 min. Não repita.
5. **Test files vão em `tests/`** (Python) ou `web/src/lib/*.test.ts` (web).
6. **Tools que retornam 0 em 4+ scans = candidato a delete.** Foi
   o caso de `waybackurls` e `xurlfind3r`.

---

## Convenções específicas

### Adicionar uma nova tool de recon

A tool aparece em **4 lugares simultaneamente** (consistency test
falha se um faltar):

1. `Dockerfile` — install step + entry no verification stage
2. `install_tools.sh` — `go_install` ou `pip_install`
3. `GivEnum.py` `ToolChecker.REQUIRED_TOOLS` — categoria certa
4. `web/src/lib/tools.ts` `TOOL_REGISTRY` — entry com `installer` argv

Wire na orchestrator class (`SubdomainEnum`, `URLCollector`, etc.) com:
- `if not ToolChecker.check_tool('X'): return set()`
- `record_tool_log('X', {...})` no fim
- Hard timeout (subprocess.TimeoutExpired tratado)

### Mudar comportamento de um tool já integrado

1. Lê o método da classe relevante em `GivEnum.py`
2. **Roda os tests existentes ANTES** da mudança (estado de baseline)
3. Faz mudança
4. Atualiza/adiciona test que cobre o novo comportamento
5. Roda tests de novo (deve estar verde)
6. **Sempre rebuild do container depois:**
   ```bash
   docker compose build app && docker compose up -d app
   ```

### Padrões de erro que JÁ aprendemos

| Erro | Causa | Como evitar |
|---|---|---|
| `Errno 101 Network is unreachable` | IPv6 sem rota no container | **Já fixado** com `urllib3.util.connection.HAS_IPV6 = False` no top de `GivEnum.py`. Se voltar, NÃO REMOVA o patch. |
| `Errno 111 Connection refused` | Target tem WAF/blocklist do IP do container | Não tem fix nosso. Documente como "target-side defense". |
| `ConnectTimeoutError 15s` em sequência | Tool sem circuit breaker per-host | TASK #57 (js_download). Padrão pra evitar em novas tools. |
| `subzy: VULNERABLE` mas false positive | Fingerprints subzy desatualizados | TASK #60. SEMPRE valide com `dig CNAME` antes de reportar. |
| Container não pega mudanças do código | Esqueceu `docker compose build app` | Sempre rebuild após mudança em GivEnum.py / scan_runner.py / Dockerfile. |

---

## Backlog priorizado (19 tasks abertas)

### 🔴 Próxima sessão (alto ROI)

- **#57** Bug: js_download sequencial sem circuit breaker. Em targets
  HTTP lentos perde 12 min sequencial. Fix: ThreadPoolExecutor +
  circuit breaker per-host (se 2 timeouts no mesmo host, skipa
  resto). ~30 min.
- **#60** TakeoverChecker enriquecer com `dig CNAME` validation.
  Subzy false positive em SendGrid tracking domains. Validação
  pos-subzy: dig CNAME, comparar com fingerprint, marcar
  'requires-manual-review' em vez de VULNERABLE. ~30 min.
- **#58** Subzy output dos hosts vulneráveis no log. Hoje só diz
  "Possible takeovers found!" sem listar. Já há `subzy_results.txt`
  na pasta `takeover/`, falta só ler e printar. ~15 min.

### 🟡 Médio prazo

- **#33** Modularizar `URLCollector` (god class 932 → ~744 linhas
  depois das deleções). Extrair `ArchiveCollector` e `LiveCrawler`.
- **#36** Modularizar `GivEnum.py` em pacote `givenum/`. **NÃO
  começar sem mais testes** — ver plano em `docs/AUDIT.md`.
- **#34** `HostBucket` semaphore (rate limiting global por host).
- **#35** Retry exponencial centralizado.
- **#37** NDJSON job log (substitui ANSI text log).
- **#38** Hook `usePolledFetch` no front (3 lugares duplicam polling).
- **#40** Pre-commit hook (ruff + prettier + eslint).
- **#39** Pinar versões Go no Dockerfile (ainda `@latest`).

### 🟢 Avaliar (não atacar sem motivo)

- **#42** alterx (subdomain wordlist generator)
- **#43** chaos-client (PD Chaos DB, requires PDCP token)
- **#44** pdtm (PD Tool Manager — substituiria parte do install_tools.sh)
- **#45-48** outras tools PD (cloudlist, asnmap, openrisk, vulnx, etc.)

### 🔵 UX & cosmético

- **#28** Decisão de localização UI (PT/EN/i18n) — hoje misturado
- **#55** UI bug: scan header duplica nome quando project=domain
  (`github.comgithub.com`)
- **#51 já fechada** mas verificar se kr wordlist agora carrega de
  fato (paths candidatos foram expandidos, não validado em scan)
- **#59** Cleanup: `=2.0.0` `=2.31.0` etc lixo no /app do container
  (algum `pip install requests>=2.31.0` sem aspas em algum momento)

### 🟣 Ainda mais opcional

- **#56 já fechada** mas investigar SE o subzy fingerprint do Cargo
  Collective vs SendGrid pode ser corrigido upstream (issue no repo do
  subzy)
- **#50 já fechada** mas baseline mypy tem 16 errors — apertar quando
  modularizar `GivEnum.py`. Quando estiver verde, flip
  `continue-on-error: false` no `.github/workflows/test.yml`.

---

## Particularidades operacionais

### Docker
- Build inicial: ~10 min
- Build incremental (sem `--no-cache`): ~1-2 min se só código mudou
- Build `--no-cache`: ~15 min, **só usa se realmente precisar**
- Container roda com volume `./results:/app/results`
- Senha do dashboard via `.env` → `GIVENUM_PASSWORD`
- Porta padrão: 3000 (`docker compose up -d app`, abre `http://localhost:3000`)

### API keys (estado atual do user)
- **Configurado:** `github_token` (pra `github-subdomains` rodar)
- **Não configurado:** Shodan, Censys, VirusTotal, SecurityTrails,
  CertSpotter, Hunter, Netlas, FOFA
- **Implicação:** `amass` skipa em 0s (correto, fix #56). Se ele
  configurar Shodan/Censys/etc, amass passa a rodar de verdade
  (~10 min) e adiciona cobertura.
- **Onde estão:** `~/.config/givenum/api.json` (mascaradas no display
  do dashboard `/settings/apis`)

### Rate-limit observado
- `crt.sh` retorna 502 frequentemente (server-side overload)
- AlienVault OTX rate-limita pesado em targets grandes
- Hackerone WAF bloqueia IPs Docker (Errno 111)
- Tesla bloqueia IP após 1 scan (rate limit por ASN)
- Bancos brasileiros throttle archive sources (Wayback/CC/OTX)

### Tools que rendem bem (validadas)
- subfinder, httpx, dnsx, naabu — sempre OK
- urlfinder (PD) — funciona com `-d <domain> -all`
- gau — funciona em targets sem rate limit
- katana, hakrawler — live crawl, geralmente OK
- meg — interesting paths discovery, funciona

### Tools com comportamento "falso positivo"
- **subzy** — fingerprints às vezes match em SendGrid quando real
  é Cargo (validar SEMPRE com `dig CNAME`)

### Tools deletadas (não reintroduzir sem evidência)
- `waybackurls` — 0 URLs em 4 scans
- `xurlfind3r` — 0 URLs em 4 scans, 50%+ timeout

---

## Comandos úteis (cole pro user fazer)

```bash
# Rodar scan novo
docker compose run --rm scanner -d TARGET --no-notify

# Ver resultado de scan recente
ls -la /Users/dvl/CODE/Givenum/results/<project>/<domain>_<timestamp>/

# Ver findings de takeover (e validar manualmente!)
cat /Users/dvl/CODE/Givenum/results/.../takeover/subzy_results.txt
dig SUBDOMAIN CNAME +short
curl -sI -L https://SUBDOMAIN

# Restartar dashboard
docker compose down && docker compose up -d app
docker compose logs -f app

# Rodar tests local
python3 -m pytest -v       # 74 verdes
cd web && npm test         # 28 verdes
```

---

## Push-back patterns que funcionam

Quando o usuário pede algo que vai dar back-fire, responda assim
(funcionou nas 5 vezes que fiz na sessão passada):

| Pedido do usuário | Push-back recomendado |
|---|---|
| "Analisa todo o código e melhora tudo" | Não. Ranqueie por ROI, foque em 3 itens. Auditar sem agir = procrastinação. |
| "Refatora GivEnum.py em pacote" | Não, sem testes mais robustos primeiro. Risco de regressão alta. |
| "Adiciona mais X tools de recon" | "Você já tem 30+, a maioria não puxa o peso". Mostre evidência de que cada nova tool adiciona cobertura ÚNICA. |
| "Roda outro scan" sem motivo claro | "Para de scanear. O resultado anterior tinha finding pra investigar." |
| "Faz tudo de uma vez" | Quebre em commits menores, valide cada um. |

---

## Lições da sessão (sériamente importantes)

1. **DOIS bugs críticos meus na sessão** (`_generate_analysis_report`
   orphan call e `URLCollector.domain` missing) só foram pegos em
   scan REAL após 30 min de espera. Solução: smoke tests AST
   (`tests/test_givenum_smoke.py`, `tests/test_url_collector_wiring.py`)
   pegariam em <1s. **Sempre escreva smoke test antes de Edit em
   classes.**

2. **Sandbox tem perm-error em `.git/index.lock`** — nunca consigo
   completar `git commit` direto pelo sandbox. Sempre dê comandos
   pro user executar localmente.

3. **`docker compose build` sem `--no-cache`** já pega mudanças no
   código (passos COPY são invalidados). `--no-cache` só pra
   desinstalações de tools.

4. **mypy** está com `continue-on-error: true` (16 baseline errors).
   Não force resolver os 16 agora — eles são "Path | None expected
   Path" que precisa refactor amplo. Resolver junto com modularização.

---

## Próximo movimento sugerido

Quando o user voltar, **peça duas coisas antes de começar a codar**:

1. "Rodou scan novo desde a última vez? Se sim, me cola o
   `TOOL EXECUTION SUMMARY` (não o log inteiro)."
2. "Tem algum bug ou comportamento estranho que você QUER consertar
   agora? Não me deixe escolher por você — seu uso real dirige."

Se ele responder vago tipo "melhora", **não comece a codar**.
Force-o a escolher do backlog acima OU descrever um problema
concreto. **Auditoria adicional sem alvo = sessão queimada.**

---

## Arquivos de contexto
- [docs/AUDIT.md](AUDIT.md) — auditoria original detalhada
- [CONTRIBUTING.md](../CONTRIBUTING.md) — house rules
- [SECURITY.md](../SECURITY.md) — threat model
- [CHANGELOG.md](../CHANGELOG.md) — histórico de mudanças
- [README.md](../README.md) — overview do projeto

Bom trabalho. A base está sólida — não desperdice o trabalho da
última sessão fazendo refactor especulativo.
