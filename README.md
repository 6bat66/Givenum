# WebEnum - Índice de Arquivos

Guia de navegação para todos os arquivos do projeto WebEnum.

---

## 📖 Documentação

### 🚀 [QUICKSTART.md](QUICKSTART.md) - **COMECE AQUI!**
Guia rápido de 5 minutos para instalar e começar a usar o WebEnum.
- Instalação express
- Primeiros comandos
- Exemplos básicos
- Troubleshooting rápido

### 📚 [README_WEBENUM.md](README_WEBENUM.md) - Documentação Completa
Documentação detalhada do projeto:
- Características completas
- Instalação passo-a-passo de todas as ferramentas
- Pipeline de enumeração explicado
- Estrutura de outputs
- Comparação com outras ferramentas
- FAQs e troubleshooting completo

### ⚡ [ADVANCED_USAGE.md](ADVANCED_USAGE.md) - Para Usuários Avançados
One-liners, scripts e técnicas avançadas:
- One-liners para análise de resultados
- Integração com Nuclei, FFuf, SQLMap
- Automação e monitoramento contínuo
- Relatórios customizados
- Visualização de dados

---

## 🛠️ Scripts Principais

### 🎯 [webenum.py](webenum.py) - **Script Principal**
Ferramenta principal de enumeração web automatizada.

**Uso:**
```bash
./webenum.py -d example.com --skip-screenshots
./webenum.py -d example.com -o /path/output
./webenum.py --check-tools
```

**O que faz:**
- Enumeração de subdomínios (subfinder, assetfinder, findomain)
- Resolução DNS (puredns, dnsx)
- HTTP probing (httpx)
- Coleta de URLs (gau, waybackurls, hakrawler)
- Análise de JavaScript (getJS, subjs)
- Screenshots (gowitness)
- Verificação de takeover (subzy)

### 📊 [analyze_results.py](analyze_results.py) - Análise de Resultados
Analisa outputs do WebEnum e gera relatórios.

**Uso:**
```bash
./analyze_results.py results/example.com_20250121_*/
./analyze_results.py results/example.com_*/ --export report.md
./analyze_results.py results/example.com_*/ --summary-only
```

**O que faz:**
- Sumário geral de estatísticas
- Análise de tecnologias detectadas
- Identificação de hosts interessantes
- Busca de padrões de vulnerabilidades
- Análise de URLs e parâmetros
- Export para Markdown

---

## 🔧 Scripts de Suporte

### 📦 [install_tools.sh](install_tools.sh) - Instalação Automatizada
Instala todas as ferramentas necessárias automaticamente.

**Uso:**
```bash
chmod +x install_tools.sh
./install_tools.sh
source ~/.bashrc
```

**O que faz:**
- Verifica Go e Python
- Instala ferramentas Go (subfinder, httpx, etc.)
- Instala Findomain
- Instala ferramentas Python (uro)
- Configura PATH
- Baixa wordlists (opcional)
- Verifica instalação final

### 🔄 [batch_enum.sh](batch_enum.sh) - Processamento em Lote
Processa múltiplos domínios de um arquivo.

**Uso:**
```bash
./batch_enum.sh domains.txt --skip-screenshots
./batch_enum.sh targets.txt -o /output/dir
```

**O que faz:**
- Lê lista de domínios de arquivo
- Processa cada um sequencialmente
- Reporta sucessos/falhas
- Permite continuar em caso de erro

---

## 📝 Arquivos de Exemplo

### [domains_example.txt](domains_example.txt)
Arquivo de exemplo para uso com `batch_enum.sh`.

**Formato:**
```
# Comentários começam com #
example.com
target1.com
target2.com
```

---

## 🗂️ Estrutura de Output

Quando você roda o WebEnum, ele cria esta estrutura:

```
results/
└── example.com_20250121_143022/
    ├── subdomains/
    │   ├── subfinder.txt
    │   ├── assetfinder.txt
    │   ├── findomain.txt
    │   └── all_subdomains.txt     ⭐ USE ESTE
    │
    ├── dns/
    │   ├── resolved.txt            ⭐ USE ESTE
    │   └── dnsx_full.json
    │
    ├── http/
    │   ├── alive.txt               ⭐ USE ESTE
    │   └── httpx_full.json         ⭐ JSON COMPLETO
    │
    ├── urls/
    │   ├── urls_raw.txt
    │   └── urls_clean.txt          ⭐ USE ESTE
    │
    ├── js/
    │   └── js_files.txt
    │
    ├── screenshots/
    │   └── *.png
    │
    ├── takeover/
    │   └── subzy_results.txt
    │
    └── logs/
```

---

## 🎓 Workflow Recomendado

```
1. Leia o QUICKSTART.md
   └─> Entenda o básico

2. Rode install_tools.sh
   └─> Instale as ferramentas

3. Teste com um domínio
   └─> ./webenum.py -d example.com --skip-screenshots

4. Analise os resultados
   └─> ./analyze_results.py results/example.com_*/

5. Use one-liners do ADVANCED_USAGE.md
   └─> Análise profunda

6. Integre com outras ferramentas
   └─> Nuclei, FFuf, etc. (veja README)
```

---

## 🔍 Busca Rápida

**Quero fazer...** → **Veja...**

- Instalar tudo rapidamente → `QUICKSTART.md`
- Entender como funciona → `README_WEBENUM.md` seção "Pipeline"
- Instalar ferramentas manualmente → `README_WEBENUM.md` seção "Instalação"
- Rodar em múltiplos domínios → `batch_enum.sh` + `domains_example.txt`
- Analisar resultados → `analyze_results.py` ou `ADVANCED_USAGE.md`
- One-liners para análise → `ADVANCED_USAGE.md` seção "One-Liners"
- Integrar com Nuclei/FFuf → `ADVANCED_USAGE.md` seção "Integração"
- Troubleshooting → `README_WEBENUM.md` seção "Troubleshooting"
- Customizar o script → `README_WEBENUM.md` seção "Customização"
- Automatizar com cron → `ADVANCED_USAGE.md` seção "Monitoramento"

---

## 📊 Comparação de Arquivos

| Arquivo | Tamanho | Propósito | Nível |
|---------|---------|-----------|-------|
| `QUICKSTART.md` | ~5KB | Início rápido | Iniciante |
| `README_WEBENUM.md` | ~13KB | Docs completas | Todos |
| `ADVANCED_USAGE.md` | ~10KB | Técnicas avançadas | Avançado |
| `INDEX.md` | Este arquivo | Navegação | Todos |
| `webenum.py` | ~25KB | Script principal | - |
| `analyze_results.py` | ~14KB | Análise | - |
| `install_tools.sh` | ~10KB | Instalação | - |
| `batch_enum.sh` | ~3KB | Batch | - |

---

## 🚦 Status das Ferramentas

### Críticas (obrigatórias):
- `subfinder` - Enumeração de subdomínios
- `httpx` - HTTP probing

### Recomendadas (alta prioridade):
- `assetfinder` - Mais subdomínios
- `findomain` - Mais subdomínios
- `puredns` - Resolução DNS
- `dnsx` - Enriquecimento DNS
- `gau` - URLs históricas
- `waybackurls` - Wayback Machine
- `hakrawler` - Crawling live
- `anew` - Deduplicação
- `uro` - Normalização de URLs

### Opcionais (melhoram resultado):
- `amass` - Subdomínios profundos (lento)
- `gowitness` - Screenshots
- `getJS` - Coleta de JS
- `subjs` - Análise de JS
- `subzy` - Takeover check

Verifique status: `./webenum.py --check-tools`

---

## 📞 Suporte

### Problemas Comuns

1. **"Ferramenta não encontrada"**
   - Rode `./install_tools.sh`
   - Verifique `./webenum.py --check-tools`
   - Adicione Go bin ao PATH: `export PATH=$PATH:$(go env GOPATH)/bin`

2. **"Nenhum host ativo"**
   - Teste DNS: `dig example.com`
   - Teste httpx: `echo "www.example.com" | httpx`
   - Domínio pode não ter hosts web

3. **"Script não executa"**
   - Torne executável: `chmod +x *.py *.sh`
   - Verifique Python3: `python3 --version`

4. **"Timeout errors"**
   - Normal em domínios grandes
   - Use `--skip-screenshots` para acelerar

### Recursos

- **Documentação completa:** `README_WEBENUM.md`
- **Início rápido:** `QUICKSTART.md`
- **Técnicas avançadas:** `ADVANCED_USAGE.md`

---

## 🎯 Checklist de Primeiro Uso

- [ ] Li o `QUICKSTART.md`
- [ ] Instalei as ferramentas (`./install_tools.sh`)
- [ ] Verifiquei ferramentas (`./webenum.py --check-tools`)
- [ ] Testei em um domínio (`./webenum.py -d example.com --skip-screenshots`)
- [ ] Analisei resultados (`./analyze_results.py results/example.com_*/`)
- [ ] Explorei one-liners (`ADVANCED_USAGE.md`)

---

## 🏆 Próximos Passos

Depois de dominar o WebEnum:

1. **Aprofundar em ferramentas específicas:**
   - Amass para recon profundo
   - Nuclei para vulnerability scanning
   - FFuf para directory bruteforce

2. **Integrar em workflow maior:**
   - Criar pipeline personalizado
   - Adicionar notificações (Discord, Slack)
   - Automatizar com cron jobs

3. **Contribuir:**
   - Adicionar novas ferramentas
   - Melhorar análise de resultados
   - Criar templates de reports

---

**WebEnum v1.0 - Enumere. Analise. Conquiste. 🎯**

*Criado com ❤️ para a comunidade de Bug Bounty e Pentest*
