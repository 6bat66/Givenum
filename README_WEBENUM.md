# WebEnum - Comprehensive Web Enumeration Tool

🎯 **Ferramenta completa de enumeração web automatizada** que coleta MÁXIMO de informações sobre um domínio sem fazer scan invasivo.

## 📋 Índice

- [Características](#-características)
- [Instalação](#-instalação)
- [Uso Básico](#-uso-básico)
- [Pipeline de Enumeração](#-pipeline-de-enumeração)
- [Estrutura de Output](#-estrutura-de-output)
- [Troubleshooting](#-troubleshooting)
- [Customização](#-customização)

---

## ✨ Características

### O que o script FAZ:
- ✅ **Enumeração massiva de subdomínios** (subfinder, assetfinder, findomain, amass)
- ✅ **Resolução DNS inteligente** (puredns, dnsx)
- ✅ **HTTP probing completo** (httpx com tech detection)
- ✅ **Coleta de URLs históricas** (wayback, gau)
- ✅ **Crawling de sites ativos** (hakrawler)
- ✅ **Análise de arquivos JavaScript** (getJS, subjs)
- ✅ **Screenshots automatizados** (gowitness - opcional)
- ✅ **Verificação de subdomain takeover** (subzy)
- ✅ **Deduplicação e normalização** (anew, uro)
- ✅ **Execução paralela** para velocidade máxima
- ✅ **Output organizado** em diretórios estruturados

### O que o script NÃO faz:
- ❌ Não faz scan de vulnerabilidades (nuclei, nmap)
- ❌ Não faz bruteforce de diretórios (isso é scanning)
- ❌ Não faz fuzzing de parâmetros
- ❌ **Apenas coleta informação existente/pública**

---

## 🔧 Instalação

### 1. Requisitos

- **Python 3.6+**
- **Go 1.19+** (para instalar as ferramentas Go)
- Linux/macOS (Windows via WSL)

### 2. Instalar Ferramentas

#### Ferramentas OBRIGATÓRIAS (críticas):

```bash
# Subfinder
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# HTTPx
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
```

#### Ferramentas RECOMENDADAS (alta prioridade):

```bash
# Assetfinder
go install github.com/tomnomnom/assetfinder@latest

# Findomain
wget https://github.com/Findomain/Findomain/releases/latest/download/findomain-linux
chmod +x findomain-linux
sudo mv findomain-linux /usr/local/bin/findomain

# Puredns
go install github.com/d3mondev/puredns/v2@latest

# Dnsx
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest

# Gau
go install github.com/lc/gau/v2/cmd/gau@latest

# Waybackurls
go install github.com/tomnomnom/waybackurls@latest

# Hakrawler
go install github.com/hakluke/hakrawler@latest

# Anew
go install -v github.com/tomnomnom/anew@latest

# Uro
pip3 install uro
```

#### Ferramentas OPCIONAIS (melhoram resultado):

```bash
# Amass (pesado mas muito bom)
go install -v github.com/owasp-amass/amass/v4/...@master

# Gowitness (screenshots)
go install github.com/sensepost/gowitness@latest

# GetJS
go install github.com/003random/getJS@latest

# Subjs
go install -v github.com/lc/subjs@latest

# Subzy (takeover)
go install -v github.com/LukaSikic/subzy@latest
```

### 3. Verificar Instalação

```bash
chmod +x webenum.py
./webenum.py --check-tools
```

Isso mostra quais ferramentas estão instaladas e quais faltam.

---

## 🚀 Uso Básico

### Modo simples (sem screenshots):

```bash
./webenum.py -d example.com --skip-screenshots
```

### Modo completo (com screenshots):

```bash
./webenum.py -d example.com
```

### Especificar diretório de output:

```bash
./webenum.py -d example.com -o /caminho/para/results
```

### Apenas verificar ferramentas:

```bash
./webenum.py --check-tools
```

---

## 🔄 Pipeline de Enumeração

O script executa automaticamente estas etapas:

### 1️⃣ **Descoberta de Subdomínios**
```
subfinder + assetfinder + findomain (paralelo)
   ↓
all_subdomains.txt (deduplicated)
```

### 2️⃣ **Resolução DNS**
```
puredns resolve (valida DNS)
   ↓
dnsx (enriquece com A, AAAA, CNAME)
   ↓
resolved.txt
```

### 3️⃣ **HTTP Probing**
```
httpx (múltiplas portas)
   ↓
- Status codes
- Títulos
- Tecnologias
- Redirects
   ↓
alive.txt + httpx_full.json
```

### 4️⃣ **Screenshots** (opcional)
```
gowitness
   ↓
screenshots/*.png
```

### 5️⃣ **Coleta de URLs**
```
┌─ gau (wayback + common crawl)
├─ waybackurls (wayback machine)
├─ hakrawler (crawl sites ativos)
└─ getJS → subjs (extrai de JS)
   ↓
urls_raw.txt
   ↓
uro (normaliza/deduplica)
   ↓
urls_clean.txt
```

### 6️⃣ **Takeover Check**
```
subzy (verifica CNAMEs vulneráveis)
   ↓
subzy_results.txt
```

---

## 📁 Estrutura de Output

Após a execução, você terá:

```
results/
└── example.com_20250121_143022/
    ├── subdomains/
    │   ├── subfinder.txt
    │   ├── assetfinder.txt
    │   ├── findomain.txt
    │   └── all_subdomains.txt          # ⭐ Use este
    │
    ├── dns/
    │   ├── resolved.txt                # ⭐ Use este
    │   └── dnsx_full.json
    │
    ├── http/
    │   ├── alive.txt                   # ⭐ Use este
    │   └── httpx_full.json             # ⭐ JSON com tudo
    │
    ├── urls/
    │   ├── urls_raw.txt
    │   └── urls_clean.txt              # ⭐ Use este
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

### Arquivos mais importantes:

| Arquivo | Descrição |
|---------|-----------|
| `all_subdomains.txt` | Todos os subdomínios encontrados |
| `resolved.txt` | Subdomínios que resolvem DNS |
| `alive.txt` | URLs com HTTP/HTTPS respondendo |
| `httpx_full.json` | Dados completos (tech, status, etc) |
| `urls_clean.txt` | URLs coletadas e normalizadas |

---

## 🎯 Exemplos de Uso

### Exemplo 1: Bug Bounty - Reconhecimento Inicial

```bash
./webenum.py -d target.com -o ~/bugbounty/target/
```

Depois analise:
- `http/httpx_full.json` → buscar tecnologias conhecidas
- `urls_clean.txt` → procurar endpoints interessantes
- `screenshots/` → revisar visualmente

### Exemplo 2: Apenas Subdomínios Rápido

```bash
# Rode só a parte de subdomínios manualmente:
subfinder -d target.com -all -silent > subs.txt
assetfinder --subs-only target.com >> subs.txt
findomain -t target.com -q >> subs.txt
cat subs.txt | sort -u > subs_uniq.txt
```

### Exemplo 3: Continuação Manual

Use os outputs do WebEnum para continuar manualmente:

```bash
# Pegar os hosts ativos e fazer bruteforce de diretórios
cat results/target.com_*/http/alive.txt | \
  ffuf -u FUZZ/admin -w - -mc 200,403,401

# Pegar URLs e testar XSS
cat results/target.com_*/urls/urls_clean.txt | \
  kxss | tee possible_xss.txt

# Pegar subdomínios e fazer mais DNS recon
cat results/target.com_*/dns/resolved.txt | \
  dnsx -resp -cname -ptr -recon
```

---

## ⚡ Dicas de Performance

### Script lento?

1. **Pule screenshots** (economiza muito tempo):
   ```bash
   ./webenum.py -d target.com --skip-screenshots
   ```

2. **Use amass apenas se necessário**:
   - Amass é muito completo mas LENTO
   - Para recon rápido: só subfinder + assetfinder + findomain

3. **Timeout de ferramentas**:
   - O script tem timeouts padrão (5-15 min por ferramenta)
   - Se quiser mais controle, edite os valores no código

### Quer MÁXIMO resultado?

Rode DEPOIS do script básico:

```bash
# Amass profundo (pode levar horas)
amass enum -active -brute -d target.com -o amass_deep.txt

# Adicione ao resultado anterior
cat amass_deep.txt >> results/target.com_*/subdomains/all_subdomains.txt
cat results/target.com_*/subdomains/all_subdomains.txt | sort -u > all.txt
```

---

## 🐛 Troubleshooting

### Erro: "httpx é obrigatório!"

```bash
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

# Certifique-se que $GOPATH/bin está no PATH
export PATH=$PATH:$(go env GOPATH)/bin
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
```

### Erro: "puredns não encontrado"

- O script continua mesmo sem puredns
- Mas INSTALE puredns para melhores resultados:
  ```bash
  go install github.com/d3mondev/puredns/v2@latest
  ```

### Nenhum host ativo encontrado

Pode ser:
1. Domínio realmente não tem hosts web
2. Proteções anti-scan (Cloudflare, rate limit)
3. Resolução DNS falhando

Tente:
```bash
# Teste manual
echo "www.target.com" | httpx -silent
```

### Timeout errors

- Normal em domínios grandes (ex: google.com)
- Aumente timeouts editando os valores no código:
  ```python
  timeout=600  # Para 900 ou 1200
  ```

---

## 🔨 Customização

### Adicionar nova ferramenta de subdomínios

Edite a classe `SubdomainEnum`:

```python
self.tools = {
    'subfinder': ['subfinder', '-d', domain, '-all', '-silent'],
    'assetfinder': ['assetfinder', '--subs-only', domain],
    'findomain': ['findomain', '-t', domain, '-q'],
    'novatool': ['novatool', '--domain', domain],  # ← Adicione aqui
}
```

### Mudar portas HTTP

Edite o método `probe_with_httpx`:

```python
'-ports', '80,443,8080,8443,8000,8888,9000,3000,5000',  # Adicione suas portas
```

### Desabilitar alguma etapa

Comente a chamada no método `run_full_enum()`:

```python
# Não quer screenshots? Já tem o --skip-screenshots
# Não quer takeover? Comente esta linha:
# self.takeover_checker.check_with_subzy(resolved_file)
```

---

## 📊 Comparação com Outros Tools

| Ferramenta | WebEnum | Amass | Subfinder | Recon-ng |
|------------|---------|-------|-----------|----------|
| Subdomínios | ✅ (3+ tools) | ✅ | ✅ | ✅ |
| DNS recon | ✅ | ✅ | ⚠️ | ⚠️ |
| HTTP probing | ✅ | ⚠️ | ❌ | ❌ |
| URL collect | ✅ | ❌ | ❌ | ⚠️ |
| Screenshots | ✅ | ❌ | ❌ | ❌ |
| JS analysis | ✅ | ❌ | ❌ | ❌ |
| Takeover | ✅ | ⚠️ | ❌ | ❌ |
| Output organizado | ✅ | ⚠️ | ⚠️ | ✅ |
| Velocidade | ⚡⚡ | 🐢 | ⚡⚡⚡ | ⚡ |

**WebEnum** = Pipeline completo automatizado
**Amass** = Subdomínios profundos (lento)
**Subfinder** = Subdomínios rápidos (especializado)
**Recon-ng** = Framework completo (curva de aprendizado)

---

## 🎓 Próximos Passos

Depois de usar o WebEnum, você pode:

1. **Análise Manual**:
   - Revisar `httpx_full.json` buscando tech interessantes
   - Ver screenshots para UI/funcionalidades
   - Procurar padrões em `urls_clean.txt`

2. **Scanning** (cuidado!):
   ```bash
   # Nuclei (templates de vulnerabilidades)
   cat results/*/http/alive.txt | \
     nuclei -t cves/ -t exposures/ -severity high,critical

   # Bruteforce de diretórios
   cat results/*/http/alive.txt | \
     while read url; do
       ffuf -u $url/FUZZ -w wordlist.txt -mc 200,403
     done
   ```

3. **Focused Recon**:
   - APIs? → Arjun, ParamSpider
   - JS? → LinkFinder, SecretFinder
   - Git exposed? → git-dumper

---

## 📝 Notas Importantes

### ⚠️ Legal

- Use APENAS em alvos autorizados
- Bug bounty? Leia as regras do programa
- Pentesting? Tenha contrato assinado
- Recon passivo é OK, mas respeite rate limits

### 💡 Boas Práticas

1. **Organize por projeto**:
   ```bash
   mkdir -p ~/recon/target1
   ./webenum.py -d target1.com -o ~/recon/target1/
   ```

2. **Versione seus achados**:
   ```bash
   cd ~/recon/target1
   git init
   git add results/
   git commit -m "Recon inicial $(date)"
   ```

3. **Compare runs**:
   ```bash
   # Rode novamente após 1 semana
   ./webenum.py -d target.com -o ~/recon/target/week2

   # Compare subdomínios novos
   comm -13 \
     <(sort week1/target.com_*/subdomains/all_subdomains.txt) \
     <(sort week2/target.com_*/subdomains/all_subdomains.txt)
   ```

---

## 🤝 Contribuindo

Quer adicionar features? Ideias:

- [ ] Integração com APIs (SecurityTrails, Shodan)
- [ ] Modo "stealth" com delays
- [ ] Dashboard HTML dos resultados
- [ ] Integração com notificações (Discord, Telegram)
- [ ] Suporte a múltiplos domínios (lista)
- [ ] Resume de runs anteriores

---

## 📚 Referências

- [ProjectDiscovery Tools](https://github.com/projectdiscovery)
- [TomNomNom Tools](https://github.com/tomnomnom)
- [OWASP Amass](https://github.com/owasp-amass/amass)
- [HakLuke Tools](https://github.com/hakluke)

---

## 👨‍💻 Autor

**@6bat66**

Se tiver dúvidas ou sugestões, abre uma issue! 🚀

---

## ⭐ Gostou?

Se o WebEnum te ajudou, dá uma estrela no repo! ⭐
