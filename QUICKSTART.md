# WebEnum - Quick Start Guide

Guia rápido para começar a usar o WebEnum em 5 minutos.

---

## 📦 Instalação Rápida

### 1. Instale as ferramentas automaticamente:

```bash
chmod +x install_tools.sh
./install_tools.sh
```

**Importante:** Depois da instalação, execute:
```bash
source ~/.bashrc
```

### 2. Verifique a instalação:

```bash
./webenum.py --check-tools
```

Você deve ver as ferramentas críticas instaladas (subfinder, httpx).

---

## 🚀 Uso Básico

### Modo mais simples (sem screenshots):

```bash
./webenum.py -d example.com --skip-screenshots
```

### Com screenshots:

```bash
./webenum.py -d example.com
```

---

## 📁 Onde Ficam os Resultados?

Tudo vai para `./results/DOMINIO_TIMESTAMP/`:

```
results/example.com_20250121_143022/
├── subdomains/all_subdomains.txt  ← TODOS os subdomínios
├── dns/resolved.txt               ← Subdomínios que resolvem
├── http/alive.txt                 ← Sites HTTP ativos
├── http/httpx_full.json           ← Dados completos (techs, status)
├── urls/urls_clean.txt            ← URLs coletadas
└── screenshots/*.png              ← Screenshots (se não usou --skip-screenshots)
```

---

## 🔍 Analisando Resultados

Use o script de análise:

```bash
./analyze_results.py results/example.com_*/
```

Isso mostra:
- Sumário geral
- Tecnologias detectadas
- Hosts interessantes (admin, login, APIs)
- Possíveis vulnerabilidades

### Exportar relatório em Markdown:

```bash
./analyze_results.py results/example.com_*/ --export report.md
```

---

## 📊 Processamento em Batch

Para enumerar múltiplos domínios:

### 1. Crie um arquivo com os domínios:

```bash
cat > targets.txt << EOF
example.com
target1.com
target2.com
EOF
```

### 2. Execute o batch:

```bash
./batch_enum.sh targets.txt --skip-screenshots
```

---

## 💡 Próximos Passos

### Depois da enumeração básica, você pode:

#### 1. Buscar endpoints interessantes:

```bash
cd results/example.com_*/

# URLs com parâmetros
cat urls/urls_clean.txt | grep -E "\?(id|user|file|page)="

# APIs
cat http/alive.txt | grep -i api

# Admin panels
cat http/httpx_full.json | jq -r 'select(.title | test("admin|login|dashboard"; "i")) | .url'
```

#### 2. Fazer scan de vulnerabilidades (cuidado!):

```bash
# Nuclei para CVEs e misconfigs
cat results/*/http/alive.txt | nuclei -t cves/ -severity high,critical

# XSS básico
cat results/*/urls/urls_clean.txt | kxss
```

#### 3. Bruteforce de diretórios (mais invasivo):

```bash
# Com ffuf
cat results/*/http/alive.txt | while read url; do
  ffuf -u "$url/FUZZ" -w wordlist.txt -mc 200,403 -o "ffuf_${url//\//_}.txt"
done
```

---

## 🐛 Problemas Comuns

### "httpx é obrigatório!"

```bash
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
export PATH=$PATH:$(go env GOPATH)/bin
```

### "Nenhum host ativo encontrado"

1. Verifique se o domínio é válido:
   ```bash
   dig example.com
   ```

2. Teste httpx manualmente:
   ```bash
   echo "www.example.com" | httpx -silent
   ```

### Scripts não executam

```bash
chmod +x *.py *.sh
```

---

## ⚡ Dicas de Performance

### Para recon rápido:
- Use `--skip-screenshots` (economiza 5-10 min)
- Não instale amass (ou não use) - ele é lento

### Para recon completo:
- Instale TODAS as ferramentas opcionais
- Rode sem `--skip-screenshots`
- Deixe rodar overnight se for domínio grande

### Para domínios grandes (ex: google.com):
- Espere 30+ minutos
- Considere rodar em VPS
- Use `screen` ou `tmux` para não perder sessão

---

## 📚 Comandos Úteis

### Ver apenas subdomínios novos (comparar 2 runs):

```bash
comm -13 \
  <(sort results/example.com_20250121_*/subdomains/all_subdomains.txt) \
  <(sort results/example.com_20250122_*/subdomains/all_subdomains.txt)
```

### Extrair apenas domínios com tech específica:

```bash
cat results/*/http/httpx_full.json | \
  jq -r 'select(.tech[] | test("WordPress")) | .url'
```

### Encontrar todos os status 403:

```bash
cat results/*/http/httpx_full.json | \
  jq -r 'select(.status_code == 403) | .url'
```

---

## 🎯 Workflow Recomendado

```
1. Enumeração rápida inicial
   └─> ./webenum.py -d target.com --skip-screenshots

2. Revisar resultados
   └─> ./analyze_results.py results/target.com_*/

3. Identificar alvos prioritários
   └─> hosts com tech conhecidas, admin panels, APIs

4. Enumeração focada
   └─> rodar ferramentas específicas nos alvos prioritários

5. Scanning (com autorização!)
   └─> nuclei, ffuf, etc. nos endpoints interessantes
```

---

## 🔗 Links Úteis

- **README completo:** `README_WEBENUM.md`
- **Instalação de ferramentas:** `install_tools.sh --help`
- **Batch processing:** `batch_enum.sh <file>`
- **Análise de resultados:** `analyze_results.py <dir>`

---

**Pronto! Agora você pode começar a enumerar. Happy hunting! 🎯**
