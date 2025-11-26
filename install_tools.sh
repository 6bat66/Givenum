#!/bin/bash

# ============================================================================
# WebEnum - Tools Installation Script
# Cross-platform support for macOS and Debian/Kali Linux
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
info() { echo -e "${BLUE}[*]${NC} $1"; }
success() { echo -e "${GREEN}[+]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[-]${NC} $1"; }
header() { echo -e "\n${BLUE}========================================${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}========================================${NC}\n"; }

# Detect OS
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

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
        if [ "$OS" = "darwin" ]; then
            echo "  brew install go"
        else
            echo "  Ubuntu/Debian: sudo apt install golang-go"
            echo "  Or: https://go.dev/dl/"
        fi
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
        warning "$name already installed"
        return 0
    fi

    info "Installing $name..."
    if go install -v "$package@latest" 2>/dev/null; then
        success "$name installed"
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
        warning "$name already installed"
        return 0
    fi

    info "Installing $name via pip..."
    
    if command_exists pipx && pipx install "$package" 2>/dev/null; then
        success "$name installed via pipx"
        return 0
    elif python3 -m pip install --user "$package" 2>/dev/null; then
        success "$name installed"
        return 0
    else
        error "Failed to install $name"
        return 1
    fi
}

# Install massdns
install_massdns() {
    if command_exists massdns; then
        warning "massdns already installed"
        return 0
    fi

    info "Installing massdns..."

    if [ "$OS" = "darwin" ]; then
        if command_exists brew; then
            if brew install massdns 2>/dev/null; then
                success "massdns installed via Homebrew"
                return 0
            fi
        fi
    fi

    # Compile from source
    info "Compiling from source..."
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"

    if git clone https://github.com/blechschmidt/massdns 2>/dev/null; then
        cd massdns
        if make 2>/dev/null; then
            if sudo make install 2>/dev/null; then
                success "massdns installed to /usr/local/bin"
            elif cp bin/massdns "$GOPATH/bin/" 2>/dev/null; then
                success "massdns installed to $GOPATH/bin"
            else
                warning "Could not move massdns to PATH"
            fi
        fi
    fi
    cd - >/dev/null
}

# Install system packages
install_system_packages() {
    header "SYSTEM PACKAGES"
    
    if [ "$OS" = "darwin" ]; then
        if command_exists brew; then
            info "Installing via Homebrew..."
            brew install git curl wget jq 2>/dev/null || true
        fi
    else
        info "Installing system packages..."
        if command_exists apt; then
            sudo apt update && sudo apt install -y git curl wget jq python3-pip 2>/dev/null || true
        elif command_exists dnf; then
            sudo dnf install -y git curl wget jq python3-pip 2>/dev/null || true
        fi
    fi
}

# ============================================================================
# MAIN
# ============================================================================

header "WEBENUM - TOOLS INSTALLATION"

info "OS: $OS ($ARCH)"

# Check dependencies
info "Checking dependencies..."
check_go
check_python

# Configure GOPATH
if [ -z "$GOPATH" ]; then
    export GOPATH="$HOME/go"
    warning "GOPATH not set, using: $GOPATH"
fi

export PATH="$PATH:$GOPATH/bin"

# Shell config
SHELL_CONFIG="$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_CONFIG="$HOME/.bash_profile"
fi

# Add Go bin to PATH
if ! grep -q 'export PATH=$PATH:$(go env GOPATH)/bin' "$SHELL_CONFIG" 2>/dev/null; then
    info "Adding Go bin to PATH..."
    echo '' >> "$SHELL_CONFIG"
    echo '# Go binaries' >> "$SHELL_CONFIG"
    echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> "$SHELL_CONFIG"
    success "PATH configured in $SHELL_CONFIG"
fi

# Python user bin
PYTHON_USER_BIN=$(python3 -m site --user-base)/bin
if [ -d "$PYTHON_USER_BIN" ]; then
    export PATH="$PATH:$PYTHON_USER_BIN"
    
    if ! grep -q "$(python3 -m site --user-base)/bin" "$SHELL_CONFIG" 2>/dev/null; then
        echo '' >> "$SHELL_CONFIG"
        echo '# Python user binaries' >> "$SHELL_CONFIG"
        echo 'export PATH=$PATH:'"$(python3 -m site --user-base)/bin" >> "$SHELL_CONFIG"
    fi
fi

# Install system packages
install_system_packages

# ============================================================================
# CORE SUBDOMAIN ENUMERATION
# ============================================================================

header "SUBDOMAIN ENUMERATION TOOLS"

install_go_tool "github.com/projectdiscovery/subfinder/v2/cmd/subfinder" "subfinder"
install_go_tool "github.com/tomnomnom/assetfinder" "assetfinder"
install_go_tool "github.com/owasp-amass/amass/v4/...@master" "amass"

# Findomain
if ! command_exists findomain; then
    info "Installing findomain..."
    
    if [ "$OS" = "darwin" ] && command_exists brew; then
        brew install findomain 2>/dev/null && success "findomain installed"
    else
        case "$ARCH" in
            x86_64) FINDOMAIN_ARCH="amd64" ;;
            aarch64|arm64) FINDOMAIN_ARCH="arm64" ;;
            *) FINDOMAIN_ARCH="amd64" ;;
        esac
        
        FINDOMAIN_URL="https://github.com/Findomain/Findomain/releases/latest/download/findomain-${OS}-${FINDOMAIN_ARCH}.zip"
        TMP_DIR=$(mktemp -d)
        cd "$TMP_DIR"
        
        if wget -q "$FINDOMAIN_URL" 2>/dev/null || curl -sL "$FINDOMAIN_URL" -o "findomain.zip"; then
            unzip -q "findomain.zip" 2>/dev/null || unzip "findomain-${OS}-${FINDOMAIN_ARCH}.zip" 2>/dev/null
            chmod +x findomain
            
            if sudo mv findomain /usr/local/bin/ 2>/dev/null; then
                success "findomain installed"
            elif mv findomain "$GOPATH/bin/" 2>/dev/null; then
                success "findomain installed to $GOPATH/bin"
            fi
        fi
        cd - >/dev/null
        rm -rf "$TMP_DIR"
    fi
fi

# Knock
if ! command_exists knockpy; then
    info "Installing knock..."
    python3 -m pip install --user knockpy 2>/dev/null && success "knock installed" || warning "knock install failed"
fi

# ============================================================================
# DNS TOOLS
# ============================================================================

header "DNS TOOLS"

install_go_tool "github.com/projectdiscovery/dnsx/cmd/dnsx" "dnsx"
install_go_tool "github.com/d3mondev/puredns/v2" "puredns"
install_go_tool "github.com/vortexau/dnsvalidator" "dnsvalidator"
install_massdns

# ============================================================================
# HTTP PROBING
# ============================================================================

header "HTTP PROBING TOOLS"

install_go_tool "github.com/projectdiscovery/httpx/cmd/httpx" "httpx"
install_go_tool "github.com/hakluke/hakcheckurl" "hakcheckurl"
install_go_tool "github.com/sensepost/gowitness" "gowitness"

# ============================================================================
# URL COLLECTION
# ============================================================================

header "URL COLLECTION TOOLS"

install_go_tool "github.com/hueristiq/xurlfind3r/cmd/xurlfind3r" "xurlfind3r"
install_go_tool "github.com/lc/gau/v2/cmd/gau" "gau"
install_go_tool "github.com/tomnomnom/waybackurls" "waybackurls"
install_go_tool "github.com/hakluke/hakrawler" "hakrawler"
install_go_tool "github.com/tomnomnom/meg" "meg"

# Photon
if ! command_exists photon; then
    info "Installing Photon..."
    python3 -m pip install --user photon-python 2>/dev/null && success "Photon installed" || warning "Photon install failed"
fi

# ============================================================================
# JAVASCRIPT ANALYSIS
# ============================================================================

header "JAVASCRIPT ANALYSIS TOOLS"

install_go_tool "github.com/lc/subjs" "subjs"
install_go_tool "github.com/003random/getJS" "getJS"

# jsubfinder
if ! command_exists jsubfinder; then
    info "Installing jsubfinder..."
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    if git clone https://github.com/ThreatUnknown/jsubfinder 2>/dev/null; then
        cd jsubfinder
        if go build 2>/dev/null; then
            if sudo mv jsubfinder /usr/local/bin/ 2>/dev/null; then
                success "jsubfinder installed"
            elif mv jsubfinder "$GOPATH/bin/" 2>/dev/null; then
                success "jsubfinder installed to $GOPATH/bin"
            fi
        fi
    fi
    cd - >/dev/null
    rm -rf "$TMP_DIR"
fi

# ============================================================================
# UTILITIES
# ============================================================================

header "UTILITY TOOLS"

install_go_tool "github.com/tomnomnom/anew" "anew"
install_go_tool "github.com/tomnomnom/unfurl" "unfurl"
install_go_tool "github.com/tomnomnom/qsreplace" "qsreplace"
install_go_tool "github.com/takshal/freq" "freq"

# uro
if ! command_exists uro; then
    info "Installing uro..."
    python3 -m pip install --user uro 2>/dev/null && success "uro installed" || warning "uro install failed"
fi

# ============================================================================
# SCANNING TOOLS
# ============================================================================

header "SCANNING TOOLS"

install_go_tool "github.com/projectdiscovery/nuclei/v3/cmd/nuclei" "nuclei"

# Update Nuclei templates
if command_exists nuclei; then
    info "Updating Nuclei templates..."
    nuclei -update-templates 2>/dev/null || true
    success "Nuclei templates updated"
fi

# sdlookup
if ! command_exists sdlookup; then
    info "Installing sdlookup..."
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    if git clone https://github.com/j3ssie/sdlookup 2>/dev/null; then
        cd sdlookup
        if go build 2>/dev/null; then
            if sudo mv sdlookup /usr/local/bin/ 2>/dev/null; then
                success "sdlookup installed"
            elif mv sdlookup "$GOPATH/bin/" 2>/dev/null; then
                success "sdlookup installed to $GOPATH/bin"
            fi
        fi
    fi
    cd - >/dev/null
    rm -rf "$TMP_DIR"
fi

# ============================================================================
# GIT TOOLS
# ============================================================================

header "GIT DUMPING TOOLS"

# goop
if ! command_exists goop; then
    info "Installing goop..."
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    if git clone https://github.com/nyancrimew/goop 2>/dev/null; then
        cd goop
        if go build 2>/dev/null; then
            if sudo mv goop /usr/local/bin/ 2>/dev/null; then
                success "goop installed"
            elif mv goop "$GOPATH/bin/" 2>/dev/null; then
                success "goop installed to $GOPATH/bin"
            fi
        fi
    fi
    cd - >/dev/null
    rm -rf "$TMP_DIR"
fi

# git-dumper
if ! command_exists git-dumper; then
    info "Installing git-dumper..."
    python3 -m pip install --user git-dumper 2>/dev/null && success "git-dumper installed" || warning "git-dumper install failed"
fi

# ============================================================================
# PARAMETER DISCOVERY
# ============================================================================

header "PARAMETER DISCOVERY TOOLS"

# Arjun
if ! command_exists arjun; then
    info "Installing arjun..."
    python3 -m pip install --user arjun 2>/dev/null && success "arjun installed" || warning "arjun install failed"
fi

# ============================================================================
# TAKEOVER DETECTION
# ============================================================================

header "TAKEOVER DETECTION TOOLS"

install_go_tool "github.com/PentestPad/subzy" "subzy"
install_go_tool "github.com/haccer/subjack" "subjack"

# ============================================================================
# OPTIONAL TOOLS
# ============================================================================

header "OPTIONAL TOOLS"

read -p "$(echo -e ${YELLOW}Install optional tools? [y/N]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    install_go_tool "github.com/hahwul/dalfox/v2" "dalfox"
    
    if ! command_exists sqlmap; then
        if [ "$OS" = "darwin" ] && command_exists brew; then
            brew install sqlmap 2>/dev/null
        else
            python3 -m pip install --user sqlmap 2>/dev/null
        fi
    fi
fi

# ============================================================================
# WORDLISTS
# ============================================================================

header "WORDLISTS"

WORDLIST_DIR="$HOME/.config/webenum/wordlists"

if [ ! -d "$WORDLIST_DIR" ]; then
    read -p "$(echo -e ${YELLOW}Download wordlists? [y/N]: ${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p "$WORDLIST_DIR"
        
        info "Downloading wordlists..."
        
        # Subdomain wordlist
        if [ ! -f "$WORDLIST_DIR/subdomains-top1m.txt" ]; then
            wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt \
                -O "$WORDLIST_DIR/subdomains-top1m.txt" 2>/dev/null || \
            curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt \
                -o "$WORDLIST_DIR/subdomains-top1m.txt"
            success "Subdomain wordlist downloaded"
        fi
        
        # Common paths
        if [ ! -f "$WORDLIST_DIR/common.txt" ]; then
            wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
                -O "$WORDLIST_DIR/common.txt" 2>/dev/null || \
            curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
                -o "$WORDLIST_DIR/common.txt"
            success "Common wordlist downloaded"
        fi
        
        success "Wordlists saved to $WORDLIST_DIR"
    fi
fi

# ============================================================================
# PYTHON DEPENDENCIES
# ============================================================================

header "PYTHON DEPENDENCIES"

info "Installing Python requirements..."

cat > /tmp/webenum_requirements.txt << 'EOF'
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
urllib3>=2.0.0
dnspython>=2.4.0
EOF

python3 -m pip install --user -r /tmp/webenum_requirements.txt 2>/dev/null || warning "Some packages may have failed"
rm /tmp/webenum_requirements.txt

# ============================================================================
# FINAL VERIFICATION
# ============================================================================

header "VERIFICATION"

CRITICAL_TOOLS=("subfinder" "httpx" "dnsx")
RECOMMENDED_TOOLS=("puredns" "massdns" "xurlfind3r" "nuclei" "sdlookup")
OPTIONAL_TOOLS=("gowitness" "arjun" "subzy" "dalfox")

info "Verifying installation..."
echo ""

echo "Critical Tools:"
for tool in "${CRITICAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${RED}✗${NC} $tool ${RED}(MISSING!)${NC}"
    fi
done

echo ""
echo "Recommended Tools:"
for tool in "${RECOMMENDED_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${YELLOW}✗${NC} $tool"
    fi
done

echo ""
echo "Optional Tools:"
for tool in "${OPTIONAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${YELLOW}○${NC} $tool (not installed)"
    fi
done

echo ""
success "Installation complete!"
echo ""
warning "IMPORTANT: Run 'source $SHELL_CONFIG' or open a new terminal"
echo ""
info "Next steps:"
echo "  1. Configure API keys: python3 webenum.py --configure-api"
echo "  2. Verify tools: python3 webenum.py --check-tools"
echo "  3. Run first scan: python3 webenum.py -d example.com"
echo ""