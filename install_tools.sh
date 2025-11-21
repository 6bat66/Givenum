#!/bin/bash

# ============================================================================
# WebEnum - Script de Instalação de Ferramentas
# ============================================================================
# Instala automaticamente todas as ferramentas necessárias para o WebEnum
# ============================================================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções auxiliares
info() { echo -e "${BLUE}[*]${NC} $1"; }
success() { echo -e "${GREEN}[+]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[-]${NC} $1"; }
header() { echo -e "\n${BLUE}========================================${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}========================================${NC}\n"; }

# Verifica se comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verifica Go
check_go() {
    if ! command_exists go; then
        error "Go não está instalado!"
        echo ""
        echo "Instale Go primeiro:"
        echo "  Ubuntu/Debian: sudo apt install golang-go"
        echo "  macOS: brew install go"
        echo "  Manual: https://go.dev/dl/"
        echo ""
        exit 1
    fi

    GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
    success "Go $GO_VERSION detectado"
}

# Verifica Python3
check_python() {
    if ! command_exists python3; then
        error "Python3 não está instalado!"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    success "Python $PYTHON_VERSION detectado"
}

# Instala ferramenta Go
install_go_tool() {
    local package=$1
    local name=$2

    if command_exists "$name"; then
        warning "$name já está instalado, pulando..."
        return 0
    fi

    info "Instalando $name..."
    if go install -v "$package@latest" 2>/dev/null; then
        success "$name instalado com sucesso"
        return 0
    else
        error "Falha ao instalar $name"
        return 1
    fi
}

# Instala ferramenta Python
install_python_tool() {
    local package=$1
    local name=$2

    if command_exists "$name"; then
        warning "$name já está instalado, pulando..."
        return 0
    fi

    info "Instalando $name via pip..."
    if pip3 install "$package" --quiet 2>/dev/null; then
        success "$name instalado com sucesso"
        return 0
    else
        error "Falha ao instalar $name"
        return 1
    fi
}

# ============================================================================
# MAIN
# ============================================================================

header "WEBENUM - INSTALAÇÃO DE FERRAMENTAS"

# Verifica dependências
info "Verificando dependências básicas..."
check_go
check_python

# Configura GOPATH se não estiver configurado
if [ -z "$GOPATH" ]; then
    export GOPATH="$HOME/go"
    warning "GOPATH não configurado, usando: $GOPATH"
fi

# Adiciona Go bin ao PATH
export PATH="$PATH:$GOPATH/bin"

# Verifica se Go bin está no PATH permanentemente
if ! grep -q 'export PATH=$PATH:$(go env GOPATH)/bin' ~/.bashrc 2>/dev/null; then
    info "Adicionando Go bin ao PATH permanentemente..."
    echo '' >> ~/.bashrc
    echo '# Go binaries' >> ~/.bashrc
    echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
    success "PATH configurado! Execute: source ~/.bashrc"
fi

# ============================================================================
# FERRAMENTAS CRÍTICAS (obrigatórias)
# ============================================================================

header "INSTALANDO FERRAMENTAS CRÍTICAS"

install_go_tool "github.com/projectdiscovery/subfinder/v2/cmd/subfinder" "subfinder"
install_go_tool "github.com/projectdiscovery/httpx/cmd/httpx" "httpx"

# ============================================================================
# FERRAMENTAS RECOMENDADAS (alta prioridade)
# ============================================================================

header "INSTALANDO FERRAMENTAS RECOMENDADAS"

install_go_tool "github.com/tomnomnom/assetfinder" "assetfinder"
install_go_tool "github.com/projectdiscovery/dnsx/cmd/dnsx" "dnsx"
install_go_tool "github.com/d3mondev/puredns/v2" "puredns"
install_go_tool "github.com/lc/gau/v2/cmd/gau" "gau"
install_go_tool "github.com/tomnomnom/waybackurls" "waybackurls"
install_go_tool "github.com/hakluke/hakrawler" "hakrawler"
install_go_tool "github.com/tomnomnom/anew" "anew"

# Uro (Python)
install_python_tool "uro" "uro"

# Findomain (download direto)
if ! command_exists findomain; then
    info "Instalando findomain..."

    ARCH=$(uname -m)
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')

    case "$ARCH" in
        x86_64) ARCH="amd64" ;;
        aarch64) ARCH="arm64" ;;
    esac

    FINDOMAIN_URL="https://github.com/Findomain/Findomain/releases/latest/download/findomain-${OS}-${ARCH}.zip"

    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"

    if wget -q "$FINDOMAIN_URL" 2>/dev/null || curl -sL "$FINDOMAIN_URL" -o "findomain-${OS}-${ARCH}.zip"; then
        unzip -q "findomain-${OS}-${ARCH}.zip" 2>/dev/null
        chmod +x findomain

        # Tenta instalar em /usr/local/bin, senão em $GOPATH/bin
        if sudo mv findomain /usr/local/bin/ 2>/dev/null; then
            success "findomain instalado em /usr/local/bin/"
        elif mv findomain "$GOPATH/bin/" 2>/dev/null; then
            success "findomain instalado em $GOPATH/bin/"
        else
            warning "Não foi possível mover findomain para PATH, copie manualmente de $TMP_DIR"
        fi
    else
        error "Falha ao baixar findomain"
    fi

    cd - >/dev/null
    rm -rf "$TMP_DIR"
else
    warning "findomain já está instalado, pulando..."
fi

# ============================================================================
# FERRAMENTAS OPCIONAIS (melhoram resultado)
# ============================================================================

header "INSTALANDO FERRAMENTAS OPCIONAIS"

read -p "$(echo -e ${YELLOW}Instalar ferramentas opcionais? Isso pode levar mais tempo. [y/N]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then

    # Amass (pesado)
    info "Amass pode levar vários minutos para compilar..."
    install_go_tool "github.com/owasp-amass/amass/v4/...@master" "amass"

    # Gowitness
    install_go_tool "github.com/sensepost/gowitness" "gowitness"

    # GetJS
    install_go_tool "github.com/003random/getJS" "getJS"

    # Subjs
    install_go_tool "github.com/lc/subjs" "subjs"

    # Subzy
    install_go_tool "github.com/LukaSikic/subzy" "subzy"

    # Subjack
    install_go_tool "github.com/haccer/subjack" "subjack"

    # Kxss
    install_go_tool "github.com/Emoe/kxss" "kxss"

    # Qsreplace
    install_go_tool "github.com/tomnomnom/qsreplace" "qsreplace"

    # Unfurl
    install_go_tool "github.com/tomnomnom/unfurl" "unfurl"

else
    info "Pulando ferramentas opcionais..."
fi

# ============================================================================
# WORDLISTS (opcional)
# ============================================================================

header "WORDLISTS"

WORDLIST_DIR="$HOME/.config/webenum/wordlists"

if [ ! -d "$WORDLIST_DIR" ]; then
    read -p "$(echo -e ${YELLOW}Baixar wordlists úteis? [y/N]: ${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p "$WORDLIST_DIR"

        info "Baixando wordlists..."

        # SecLists DNS
        if [ ! -f "$WORDLIST_DIR/subdomains.txt" ]; then
            wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt \
                -O "$WORDLIST_DIR/subdomains.txt" 2>/dev/null || \
            curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt \
                -o "$WORDLIST_DIR/subdomains.txt"
            success "Wordlist de subdomínios baixada"
        fi

        # SecLists Web
        if [ ! -f "$WORDLIST_DIR/common.txt" ]; then
            wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
                -O "$WORDLIST_DIR/common.txt" 2>/dev/null || \
            curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
                -o "$WORDLIST_DIR/common.txt"
            success "Wordlist web comum baixada"
        fi

        success "Wordlists salvas em $WORDLIST_DIR"
    fi
fi

# ============================================================================
# VERIFICAÇÃO FINAL
# ============================================================================

header "VERIFICAÇÃO FINAL"

CRITICAL_TOOLS=("subfinder" "httpx")
RECOMMENDED_TOOLS=("assetfinder" "findomain" "dnsx" "puredns" "gau" "waybackurls" "hakrawler" "anew" "uro")
OPTIONAL_TOOLS=("amass" "gowitness" "getJS" "subjs" "subzy")

info "Verificando instalação..."
echo ""

echo "Críticas:"
for tool in "${CRITICAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${RED}✗${NC} $tool ${RED}(FALTANDO!)${NC}"
    fi
done

echo ""
echo "Recomendadas:"
for tool in "${RECOMMENDED_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${YELLOW}✗${NC} $tool"
    fi
done

echo ""
echo "Opcionais:"
for tool in "${OPTIONAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${YELLOW}○${NC} $tool (não instalado)"
    fi
done

echo ""
success "Instalação concluída!"
echo ""
warning "IMPORTANTE: Execute 'source ~/.bashrc' ou abra um novo terminal"
echo ""
info "Para testar, execute: ./webenum.py --check-tools"
