#!/bin/bash

# ============================================================================
# WebEnum - Tools Installation Script
# ============================================================================
# Automatically installs all tools required for WebEnum
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() { echo -e "${BLUE}[*]${NC} $1"; }
success() { echo -e "${GREEN}[+]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[-]${NC} $1"; }
header() { echo -e "\n${BLUE}========================================${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}========================================${NC}\n"; }

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Go
check_go() {
    if ! command_exists go; then
        error "Go is not installed!"
        echo ""
        echo "Install Go first:"
        echo "  Ubuntu/Debian: sudo apt install golang-go"
        echo "  macOS: brew install go"
        echo "  Manual: https://go.dev/dl/"
        echo ""
        exit 1
    fi

    GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
    success "Go $GO_VERSION detected"
}

# Check Python3
check_python() {
    if ! command_exists python3; then
        error "Python3 is not installed!"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    success "Python $PYTHON_VERSION detected"
}

# Install Go tool
install_go_tool() {
    local package=$1
    local name=$2

    if command_exists "$name"; then
        warning "$name is already installed, skipping..."
        return 0
    fi

    info "Installing $name..."
    if go install -v "$package@latest" 2>/dev/null; then
        success "$name installed successfully"
        return 0
    else
        error "Failed to install $name"
        return 1
    fi
}

# Install Python tool
install_python_tool() {
    local package=$1
    local name=$2

    if command_exists "$name" || python3 -c "import $package" 2>/dev/null; then
        warning "$name is already installed, skipping..."
        return 0
    fi

    info "Installing $name via pip..."
    
    # Try pip3 install with user flag first (works without sudo)
    if python3 -m pip install --user "$package" 2>/dev/null; then
        success "$name installed successfully"
        return 0
    # Try pipx if available (recommended for CLI tools)
    elif command_exists pipx && pipx install "$package" 2>/dev/null; then
        success "$name installed successfully via pipx"
        return 0
    # Try regular pip3
    elif pip3 install "$package" 2>/dev/null; then
        success "$name installed successfully"
        return 0
    else
        error "Failed to install $name"
        warning "Try manually: python3 -m pip install --user $package"
        return 1
    fi
}

# ============================================================================
# MAIN
# ============================================================================

header "WEBENUM - TOOLS INSTALLATION"

# Check basic dependencies
info "Checking basic dependencies..."
check_go
check_python

# Configure GOPATH if not set
if [ -z "$GOPATH" ]; then
    export GOPATH="$HOME/go"
    warning "GOPATH not configured, using: $GOPATH"
fi

# Add Go bin to PATH
export PATH="$PATH:$GOPATH/bin"

# Check if Go bin is permanently in PATH
SHELL_CONFIG="$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
fi

if ! grep -q 'export PATH=$PATH:$(go env GOPATH)/bin' "$SHELL_CONFIG" 2>/dev/null; then
    info "Adding Go bin to PATH permanently..."
    echo '' >> "$SHELL_CONFIG"
    echo '# Go binaries' >> "$SHELL_CONFIG"
    echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> "$SHELL_CONFIG"
    success "PATH configured! Run: source $SHELL_CONFIG"
fi

# Ensure Python user bin is in PATH
PYTHON_USER_BIN=$(python3 -m site --user-base)/bin
if [ -d "$PYTHON_USER_BIN" ]; then
    export PATH="$PATH:$PYTHON_USER_BIN"
    
    if ! grep -q "$(python3 -m site --user-base)/bin" "$SHELL_CONFIG" 2>/dev/null; then
        info "Adding Python user bin to PATH..."
        echo '' >> "$SHELL_CONFIG"
        echo '# Python user binaries' >> "$SHELL_CONFIG"
        echo 'export PATH=$PATH:'"$(python3 -m site --user-base)/bin" >> "$SHELL_CONFIG"
    fi
fi

# ============================================================================
# CRITICAL TOOLS (required)
# ============================================================================

header "INSTALLING CRITICAL TOOLS"

install_go_tool "github.com/projectdiscovery/subfinder/v2/cmd/subfinder" "subfinder"
install_go_tool "github.com/projectdiscovery/httpx/cmd/httpx" "httpx"

# ============================================================================
# RECOMMENDED TOOLS (high priority)
# ============================================================================

header "INSTALLING RECOMMENDED TOOLS"

install_go_tool "github.com/tomnomnom/assetfinder" "assetfinder"
install_go_tool "github.com/projectdiscovery/dnsx/cmd/dnsx" "dnsx"
install_go_tool "github.com/d3mondev/puredns/v2" "puredns"
install_go_tool "github.com/lc/gau/v2/cmd/gau" "gau"
install_go_tool "github.com/tomnomnom/waybackurls" "waybackurls"
install_go_tool "github.com/hakluke/hakrawler" "hakrawler"
install_go_tool "github.com/tomnomnom/anew" "anew"

# Uro (Python)
install_python_tool "uro" "uro"

# Findomain (direct download)
if ! command_exists findomain; then
    info "Installing findomain..."

    ARCH=$(uname -m)
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')

    case "$ARCH" in
        x86_64) ARCH="amd64" ;;
        aarch64|arm64) ARCH="arm64" ;;
    esac

    FINDOMAIN_URL="https://github.com/Findomain/Findomain/releases/latest/download/findomain-${OS}-${ARCH}.zip"

    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"

    if wget -q "$FINDOMAIN_URL" 2>/dev/null || curl -sL "$FINDOMAIN_URL" -o "findomain-${OS}-${ARCH}.zip"; then
        unzip -q "findomain-${OS}-${ARCH}.zip" 2>/dev/null
        chmod +x findomain

        # Try to install in /usr/local/bin, otherwise in $GOPATH/bin
        if sudo mv findomain /usr/local/bin/ 2>/dev/null; then
            success "findomain installed in /usr/local/bin/"
        elif mv findomain "$GOPATH/bin/" 2>/dev/null; then
            success "findomain installed in $GOPATH/bin/"
        else
            warning "Could not move findomain to PATH, manually copy from $TMP_DIR"
        fi
    else
        error "Failed to download findomain"
    fi

    cd - >/dev/null
    rm -rf "$TMP_DIR"
else
    warning "findomain is already installed, skipping..."
fi

# ============================================================================
# OPTIONAL TOOLS (improve results)
# ============================================================================

header "INSTALLING OPTIONAL TOOLS"

read -p "$(echo -e ${YELLOW}Install optional tools? This may take longer. [y/N]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then

    # Amass (heavy)
    info "Amass may take several minutes to compile..."
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
    info "Skipping optional tools..."
fi

# ============================================================================
# WORDLISTS (optional)
# ============================================================================

header "WORDLISTS"

WORDLIST_DIR="$HOME/.config/webenum/wordlists"

if [ ! -d "$WORDLIST_DIR" ]; then
    read -p "$(echo -e ${YELLOW}Download useful wordlists? [y/N]: ${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p "$WORDLIST_DIR"

        info "Downloading wordlists..."

        # SecLists DNS
        if [ ! -f "$WORDLIST_DIR/subdomains.txt" ]; then
            wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt \
                -O "$WORDLIST_DIR/subdomains.txt" 2>/dev/null || \
            curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt \
                -o "$WORDLIST_DIR/subdomains.txt"
            success "Subdomain wordlist downloaded"
        fi

        # SecLists Web
        if [ ! -f "$WORDLIST_DIR/common.txt" ]; then
            wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
                -O "$WORDLIST_DIR/common.txt" 2>/dev/null || \
            curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
                -o "$WORDLIST_DIR/common.txt"
            success "Common web wordlist downloaded"
        fi

        success "Wordlists saved to $WORDLIST_DIR"
    fi
fi

# ============================================================================
# FINAL VERIFICATION
# ============================================================================

header "FINAL VERIFICATION"

CRITICAL_TOOLS=("subfinder" "httpx")
RECOMMENDED_TOOLS=("assetfinder" "findomain" "dnsx" "puredns" "gau" "waybackurls" "hakrawler" "anew" "uro")
OPTIONAL_TOOLS=("amass" "gowitness" "getJS" "subjs" "subzy")

info "Verifying installation..."
echo ""

echo "Critical:"
for tool in "${CRITICAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${RED}✗${NC} $tool ${RED}(MISSING!)${NC}"
    fi
done

echo ""
echo "Recommended:"
for tool in "${RECOMMENDED_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${YELLOW}✗${NC} $tool"
    fi
done

echo ""
echo "Optional:"
for tool in "${OPTIONAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${YELLOW}○${NC} $tool (not installed)"
    fi
done

echo ""
success "Installation completed!"
echo ""
warning "IMPORTANT: Run 'source $SHELL_CONFIG' or open a new terminal"
echo ""
info "To test, run: ./webenum.py --check-tools"