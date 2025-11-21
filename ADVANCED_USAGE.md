# WebEnum - Advanced Usage & One-Liners

Guia avançado com exemplos práticos e one-liners úteis para análise de resultados.

---

## 🎯 One-Liners Úteis

### Análise de Subdomínios

```bash
# Subdomínios únicos por TLD
cat results/*/subdomains/all_subdomains.txt | awk -F. '{print $(NF-1)"."$NF}' | sort | uniq -c | sort -rn

# Subdomínios com 3+ níveis (possíveis dev/staging)
cat results/*/subdomains/all_subdomains.txt | awk -F. '{if(NF>=4) print}' | sort

# Subdomínios com palavras interessantes
cat results/*/subdomains/all_subdomains.txt | grep -iE "(dev|test|stage|staging|uat|admin|vpn|mail|git|jenkins)"

# Comparar 2 enumerações (novos subdomínios)
comm -13 <(sort old/all_subdomains.txt) <(sort new/all_subdomains.txt)
```

### Análise de HTTP/HTTPS

```bash
# Todos os hosts com status 200
cat results/*/http/httpx_full.json | jq -r 'select(.status_code == 200) | .url'

# Hosts com redirect (3xx)
cat results/*/http/httpx_full.json | jq -r 'select(.status_code >= 300 and .status_code < 400) | "\(.url) -> \(.location)"'

# Hosts com autenticação (401/403)
cat results/*/http/httpx_full.json | jq -r 'select(.status_code == 401 or .status_code == 403) | .url'

# Hosts por tecnologia específica
cat results/*/http/httpx_full.json | jq -r 'select(.tech[] | test("WordPress")) | .url'
cat results/*/http/httpx_full.json | jq -r 'select(.tech[] | test("nginx")) | .url'

# Hosts SEM WAF detectado
cat results/*/http/httpx_full.json | jq -r 'select(.tech | length == 0 or (. | tostring | test("Cloudflare|Incapsula|Akamai") | not)) | .url'

# Listar todas tecnologias únicas
cat results/*/http/httpx_full.json | jq -r '.tech[]' | sort -u

# Hosts com títulos específicos
cat results/*/http/httpx_full.json | jq -r 'select(.title | test("Dashboard|Admin|Login"; "i")) | "\(.url) - \(.title)"'

# Extrair apenas domínios (sem path)
cat results/*/http/alive.txt | sed 's|https\?://||' | cut -d/ -f1 | sort -u
```

### Análise de URLs

```bash
# URLs por extensão
cat results/*/urls/urls_clean.txt | grep -oE '\.[a-z0-9]+(\?|$)' | sort | uniq -c | sort -rn

# URLs com parâmetros específicos
cat results/*/urls/urls_clean.txt | grep -E "[?&](id|user|file|path|url|redirect)="

# Extrair todos parâmetros únicos
cat results/*/urls/urls_clean.txt | grep -oE '[?&][^=]+=' | tr -d '?&=' | sort -u

# URLs de API
cat results/*/urls/urls_clean.txt | grep -iE '/api/|/v[0-9]+/'

# URLs com extensões interessantes
cat results/*/urls/urls_clean.txt | grep -E '\.(php|asp|aspx|jsp|do|action)(\?|$)'

# URLs sem query string (endpoints puros)
cat results/*/urls/urls_clean.txt | grep -v '?'

# URLs com query strings (potencial input)
cat results/*/urls/urls_clean.txt | grep '?'

# Paths únicos (sem query)
cat results/*/urls/urls_clean.txt | sed 's/?.*//' | sort -u

# Contar URLs por host
cat results/*/urls/urls_clean.txt | sed 's|^\(https\?://[^/]*\).*|\1|' | sort | uniq -c | sort -rn
```

### Análise de JavaScript

```bash
# Listar todos arquivos JS
cat results/*/js/js_files.txt

# JS por domínio
cat results/*/js/js_files.txt | sed 's|^\(https\?://[^/]*\).*|\1|' | sort | uniq -c | sort -rn

# JS com nomes interessantes
cat results/*/js/js_files.txt | grep -iE "(config|admin|api|auth|secret|key|token)"

# Baixar todos JS para análise offline
mkdir js_downloads
cat results/*/js/js_files.txt | xargs -I{} wget -q {} -P js_downloads/
```

---

## 🔍 Análise Avançada com jq

### Estatísticas Complexas

```bash
# Top 10 tecnologias mais usadas
cat results/*/http/httpx_full.json | jq -r '.tech[]' | sort | uniq -c | sort -rn | head -10

# Distribuição de status codes
cat results/*/http/httpx_full.json | jq -r '.status_code' | sort | uniq -c | sort -rn

# Hosts por tamanho de response
cat results/*/http/httpx_full.json | jq -r 'select(.content_length != null) | "\(.content_length)\t\(.url)"' | sort -rn | head -20

# Tempo de resposta médio
cat results/*/http/httpx_full.json | jq -r '.response_time' | awk '{sum+=$1; count++} END {print "Média:", sum/count, "ms"}'

# Hosts com múltiplas tecnologias
cat results/*/http/httpx_full.json | jq -r 'select(.tech | length > 3) | "\(.url) - \(.tech | length) techs: \(.tech | join(", "))"'
```

### Filtros Específicos

```bash
# Hosts com WordPress + versão
cat results/*/http/httpx_full.json | jq -r 'select(.tech[] | test("WordPress")) | "\(.url) - \(.tech | map(select(test("WordPress"))) | .[0])"'

# Hosts PHP sem framework detectado
cat results/*/http/httpx_full.json | jq -r 'select(.tech[] | test("PHP")) | select(.tech | map(test("Laravel|Symfony|CodeIgniter|Drupal|WordPress")) | any | not) | .url'

# Servidores web por tipo
echo "=== Apache ==="
cat results/*/http/httpx_full.json | jq -r 'select(.tech[] | test("Apache")) | .url' | wc -l
echo "=== Nginx ==="
cat results/*/http/httpx_full.json | jq -r 'select(.tech[] | test("nginx")) | .url' | wc -l
echo "=== IIS ==="
cat results/*/http/httpx_full.json | jq -r 'select(.tech[] | test("IIS")) | .url' | wc -l
```

### Export Customizado

```bash
# CSV com status e tech
cat results/*/http/httpx_full.json | jq -r '[.url, .status_code, (.tech | join(";"))] | @csv' > analysis.csv

# Tabela markdown
cat results/*/http/httpx_full.json | jq -r '["| URL | Status | Title |"], ["|-----|--------|-------|"], (.[] | ["| ", .url, " | ", (.status_code|tostring), " | ", .title, " |"] | join("")) | .[]' > table.md
```

---

## 🛠️ Integração com Outras Ferramentas

### Com Nuclei

```bash
# Scan rápido de CVEs
cat results/*/http/alive.txt | nuclei -t cves/ -severity critical,high -o nuclei_cves.txt

# Scan de exposures
cat results/*/http/alive.txt | nuclei -t exposures/ -o nuclei_exposures.txt

# Scan de misconfigs
cat results/*/http/alive.txt | nuclei -t misconfiguration/ -o nuclei_misconfigs.txt

# Scan focado por tecnologia
cat results/*/http/httpx_full.json | jq -r 'select(.tech[] | test("WordPress")) | .url' | nuclei -t wordpress/ -o nuclei_wp.txt
```

### Com FFuf (Directory Bruteforce)

```bash
# Bruteforce básico
cat results/*/http/alive.txt | while read url; do
    ffuf -u "$url/FUZZ" -w /path/to/wordlist.txt -mc 200,204,301,302,307,401,403 -o "ffuf_$(echo $url | md5sum | cut -d' ' -f1).json" -of json
done

# Bruteforce apenas em hosts específicos (ex: WordPress)
cat results/*/http/httpx_full.json | jq -r 'select(.tech[] | test("WordPress")) | .url' | \
while read url; do
    ffuf -u "$url/FUZZ" -w wordpress-wordlist.txt -mc 200,403
done

# Virtual host fuzzing
cat results/*/dns/resolved.txt | while read sub; do
    ffuf -u https://target.com -H "Host: FUZZ.target.com" -w <(echo $sub) -mc all -fc 404
done
```

### Com Gau/Wayback (mais URLs)

```bash
# Pegar ainda mais URLs históricas
cat results/*/subdomains/all_subdomains.txt | gau --threads 10 --subs > extra_urls.txt

# Merge com URLs existentes
cat results/*/urls/urls_clean.txt extra_urls.txt | uro | anew all_urls_final.txt
```

### Com ParamSpider

```bash
# Encontrar parâmetros GET
cat results/*/http/alive.txt | while read url; do
    paramspider -d $(echo $url | sed 's|https\?://||' | cut -d/ -f1)
done
```

### Com Arjun (API parameter discovery)

```bash
# Descobrir parâmetros ocultos
cat results/*/http/alive.txt | while read url; do
    arjun -u "$url"
done
```

### Com Kxss (XSS hunting)

```bash
# Encontrar parâmetros refletidos
cat results/*/urls/urls_clean.txt | kxss | tee possible_xss.txt

# Com dalfox
cat possible_xss.txt | dalfox pipe --skip-bav
```

### Com SQLMap

```bash
# Testar SQLi em parâmetros
cat results/*/urls/urls_clean.txt | grep '?' | head -10 | while read url; do
    sqlmap -u "$url" --batch --risk 1 --level 1
done
```

---

## 📊 Relatórios Automatizados

### Script de Relatório Simples

```bash
#!/bin/bash
RESULTS_DIR="$1"

echo "# WebEnum Report - $(basename $RESULTS_DIR)"
echo ""
echo "## Summary"
echo "- Subdomains: $(wc -l < $RESULTS_DIR/subdomains/all_subdomains.txt)"
echo "- Alive Hosts: $(wc -l < $RESULTS_DIR/http/alive.txt)"
echo "- URLs Collected: $(wc -l < $RESULTS_DIR/urls/urls_clean.txt)"
echo ""
echo "## Top Technologies"
cat $RESULTS_DIR/http/httpx_full.json | jq -r '.tech[]' | sort | uniq -c | sort -rn | head -10
echo ""
echo "## Interesting Hosts"
cat $RESULTS_DIR/http/httpx_full.json | jq -r 'select(.title | test("admin|login|dashboard"; "i")) | .url'
```

### Exportar para HTML

```bash
# Usa pandoc para converter markdown em HTML
./analyze_results.py results/example.com_*/ --export report.md
pandoc report.md -o report.html --standalone --toc
```

---

## 🔄 Monitoramento Contínuo

### Script de Diff

```bash
#!/bin/bash
# compare_runs.sh - Compara 2 runs de enumeração

OLD_RUN="$1"
NEW_RUN="$2"

echo "=== Novos Subdomínios ==="
comm -13 <(sort $OLD_RUN/subdomains/all_subdomains.txt) <(sort $NEW_RUN/subdomains/all_subdomains.txt)

echo ""
echo "=== Novos Hosts Ativos ==="
comm -13 <(sort $OLD_RUN/http/alive.txt) <(sort $NEW_RUN/http/alive.txt)

echo ""
echo "=== Mudanças de Status ==="
diff <(cat $OLD_RUN/http/httpx_full.json | jq -r '"\(.url) \(.status_code)"' | sort) \
     <(cat $NEW_RUN/http/httpx_full.json | jq -r '"\(.url) \(.status_code)"' | sort)
```

### Cron Job para Monitoramento

```bash
# Adicionar ao crontab: crontab -e

# Rodar enumeração toda segunda às 2h
0 2 * * 1 cd /path/to/webenum && ./webenum.py -d target.com --skip-screenshots && ./analyze_results.py results/target.com_*/ --export ~/reports/weekly_$(date +\%Y\%m\%d).md
```

---

## 🎨 Visualização de Dados

### Gerar Grafo de Subdomínios

```python
#!/usr/bin/env python3
# subdomain_graph.py - Visualiza hierarquia de subdomínios

import sys
from collections import defaultdict

subdomains = []
with open(sys.argv[1]) as f:
    subdomains = [line.strip() for line in f]

tree = defaultdict(list)
for sub in subdomains:
    parts = sub.split('.')
    if len(parts) > 2:
        parent = '.'.join(parts[1:])
        child = parts[0]
        tree[parent].append(child)

# Imprime em formato tree
for parent, children in sorted(tree.items()):
    print(f"{parent}")
    for child in children:
        print(f"  └── {child}")
```

---

## 🚀 Automação Avançada

### Pipeline Completo

```bash
#!/bin/bash
# full_pipeline.sh - Pipeline completo de recon

DOMAIN="$1"
OUTPUT_DIR="~/recon/$DOMAIN"

# 1. Enumeração inicial
./webenum.py -d "$DOMAIN" -o "$OUTPUT_DIR"

# 2. Análise
./analyze_results.py "$OUTPUT_DIR/$DOMAIN"_*/ --export "$OUTPUT_DIR/report.md"

# 3. Nuclei scan
cat "$OUTPUT_DIR/$DOMAIN"_*/http/alive.txt | nuclei -t cves/ -severity high,critical -o "$OUTPUT_DIR/nuclei.txt"

# 4. Screenshots organizados
mkdir -p "$OUTPUT_DIR/screenshots_sorted"
# (organizar por status code, tech, etc.)

# 5. Notificação
curl -X POST "https://discord.webhook.url" -H "Content-Type: application/json" \
  -d "{\"content\": \"Recon completo para $DOMAIN finalizado!\"}"
```

---

## 💾 Backup e Organização

### Estrutura Recomendada

```
~/recon/
├── target1.com/
│   ├── 2025-01-15_initial/
│   ├── 2025-01-22_weekly/
│   ├── 2025-01-29_weekly/
│   └── reports/
├── target2.com/
│   └── ...
└── scripts/
    ├── webenum.py
    └── ...
```

### Backup Automatizado

```bash
#!/bin/bash
# backup_recon.sh

RECON_DIR="$HOME/recon"
BACKUP_DIR="$HOME/recon_backups"
DATE=$(date +%Y%m%d)

tar -czf "$BACKUP_DIR/recon_$DATE.tar.gz" "$RECON_DIR"

# Manter apenas últimos 30 dias
find "$BACKUP_DIR" -name "recon_*.tar.gz" -mtime +30 -delete
```

---

## 🔐 Melhores Práticas

### 1. Rate Limiting

```bash
# Adicionar delay entre requisições
cat hosts.txt | while read host; do
    httpx -u "$host"
    sleep 1  # 1 segundo de delay
done
```

### 2. Usar Proxies

```bash
# Com proxychains
proxychains4 ./webenum.py -d target.com
```

### 3. User-Agent Rotation

```bash
# httpx já tem -random-agent
# Para outros:
curl -A "Mozilla/5.0 ..." "$URL"
```

---

## 📚 Recursos Adicionais

- [ProjectDiscovery Blog](https://blog.projectdiscovery.io/)
- [HakLuke's Guide to Amass](https://hakluke.medium.com/)
- [TomNomNom's Tools](https://github.com/tomnomnom)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

---

**Happy Hunting! 🎯**
