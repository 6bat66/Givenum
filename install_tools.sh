#!/bin/bash

# ============================================================================
# WebEnum Enhanced - Tools Installation Script
# ============================================================================
# Installs all tools required for WebEnum Enhanced including:
# - API-based subdomain enumeration
# - Vulnerability scanning
# - Fuzzing tools
# - Parameter discovery
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
            echo "  Fedora: sudo dnf install golang"
        fi
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
    
    if command_exists pipx && pipx install "$package" 2>/dev/null; then
        success "$name installed successfully via pipx"
        return 0
    elif python3 -m pip install --user "$package" 2>/dev/null; then
        success "$name installed successfully"
        return 0
    elif pip3 install --user "$package" 2>/dev/null; then
        success "$name installed successfully"
        return 0
    else
        error "Failed to install $name"
        warning "Try manually: python3 -m pip install --user $package"
        return 1
    fi
}

# Install massdns
install_massdns() {
    if command_exists massdns; then
        warning "massdns is already installed, skipping..."
        return 0
    fi

    info "Installing massdns..."

    if [ "$OS" = "darwin" ]; then
        if command_exists brew; then
            info "Trying to install via Homebrew..."
            if brew install massdns 2>/dev/null; then
                success "massdns installed via Homebrew"
                return 0
            fi
        fi
    fi

    # Compile from source
    info "Compiling massdns from source..."
    
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
                warning "Manually copy from: $TMP_DIR/massdns/bin/massdns"
            fi
        else
            error "Failed to compile massdns"
        fi
    else
        error "Failed to clone massdns repository"
    fi

    cd - >/dev/null
}

# Install nuclei templates
install_nuclei_templates() {
    if command_exists nuclei; then
        info "Installing/updating Nuclei templates..."
        nuclei -update-templates 2>/dev/null || true
        success "Nuclei templates updated"
    fi
}

# Install system packages
install_system_packages() {
    header "INSTALLING SYSTEM PACKAGES"
    
    if [ "$OS" = "darwin" ]; then
        if command_exists brew; then
            info "Installing system packages via Homebrew..."
            brew install nmap nikto 2>/dev/null || warning "Some packages failed to install via brew"
        else
            warning "Homebrew not found, skipping system packages"
            info "Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        fi
    else
        info "Installing system packages..."
        if command_exists apt; then
            sudo apt update && sudo apt install -y nmap nikto 2>/dev/null || warning "Some packages failed to install"
        elif command_exists dnf; then
            sudo dnf install -y nmap nikto 2>/dev/null || warning "Some packages failed to install"
        elif command_exists yum; then
            sudo yum install -y nmap nikto 2>/dev/null || warning "Some packages failed to install"
        else
            warning "No supported package manager found, please install nmap and nikto manually"
        fi
    fi
}

# ============================================================================
# MAIN
# ============================================================================

header "WEBENUM ENHANCED - TOOLS INSTALLATION"

info "Detected OS: $OS ($ARCH)"

# Check basic dependencies
info "Checking basic dependencies..."
check_go
check_python

# Configure GOPATH
if [ -z "$GOPATH" ]; then
    export GOPATH="$HOME/go"
    warning "GOPATH not configured, using: $GOPATH"
fi

export PATH="$PATH:$GOPATH/bin"

# Detect shell config
SHELL_CONFIG="$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_CONFIG="$HOME/.bash_profile"
fi

# Check if Go bin is in PATH
if ! grep -q 'export PATH=$PATH:$(go env GOPATH)/bin' "$SHELL_CONFIG" 2>/dev/null; then
    info "Adding Go bin to PATH permanently..."
    echo '' >> "$SHELL_CONFIG"
    echo '# Go binaries' >> "$SHELL_CONFIG"
    echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> "$SHELL_CONFIG"
    success "PATH configured! Run: source $SHELL_CONFIG"
fi

# Python user bin
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
# CORE SUBDOMAIN ENUMERATION
# ============================================================================

header "INSTALLING CORE SUBDOMAIN TOOLS"

install_go_tool "github.com/projectdiscovery/subfinder/v2/cmd/subfinder" "subfinder"
install_go_tool "github.com/tomnomnom/assetfinder" "assetfinder"

# Findomain
if ! command_exists findomain; then
    info "Installing findomain..."

    if [ "$OS" = "darwin" ] && command_exists brew; then
        if brew install findomain 2>/dev/null; then
            success "findomain installed via Homebrew"
        fi
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
                success "findomain installed in /usr/local/bin/"
            elif mv findomain "$GOPATH/bin/" 2>/dev/null; then
                success "findomain installed in $GOPATH/bin/"
            else
                warning "Could not move findomain to PATH"
            fi
        else
            error "Failed to download findomain"
        fi

        cd - >/dev/null
        rm -rf "$TMP_DIR"
    fi
else
    warning "findomain already installed"
fi

# Amass
install_go_tool "github.com/owasp-amass/amass/v4/...@master" "amass"

# ============================================================================
# DNS TOOLS
# ============================================================================

header "INSTALLING DNS TOOLS"

install_go_tool "github.com/projectdiscovery/dnsx/cmd/dnsx" "dnsx"
install_go_tool "github.com/d3mondev/puredns/v2" "puredns"
install_massdns

# ============================================================================
# HTTP PROBING
# ============================================================================

header "INSTALLING HTTP PROBING TOOLS"

install_go_tool "github.com/projectdiscovery/httpx/cmd/httpx" "httpx"
install_go_tool "github.com/sensepost/gowitness" "gowitness"

# ============================================================================
# URL COLLECTION
# ============================================================================

header "INSTALLING URL COLLECTION TOOLS"

install_go_tool "github.com/lc/gau/v2/cmd/gau" "gau"
install_go_tool "github.com/tomnomnom/waybackurls" "waybackurls"
install_go_tool "github.com/hakluke/hakrawler" "hakrawler"
install_go_tool "github.com/003random/getJS" "getJS"
install_go_tool "github.com/lc/subjs" "subjs"

# ============================================================================
# UTILITIES
# ============================================================================

header "INSTALLING UTILITY TOOLS"

install_go_tool "github.com/tomnomnom/anew" "anew"
install_python_tool "uro" "uro"
install_go_tool "github.com/tomnomnom/unfurl" "unfurl"
install_go_tool "github.com/tomnomnom/qsreplace" "qsreplace"

# ============================================================================
# VULNERABILITY SCANNING
# ============================================================================

header "INSTALLING VULNERABILITY SCANNING TOOLS"

install_go_tool "github.com/projectdiscovery/nuclei/v3/cmd/nuclei" "nuclei"
install_nuclei_templates

# System tools
install_system_packages

# ============================================================================
# FUZZING TOOLS
# ============================================================================

header "INSTALLING FUZZING TOOLS"

install_go_tool "github.com/ffuf/ffuf" "ffuf"

# Dirsearch (Python)
if ! command_exists dirsearch; then
    info "Installing dirsearch..."
    
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    if git clone https://github.com/maurosoria/dirsearch.git 2>/dev/null; then
        cd dirsearch
        sudo python3 setup.py install 2>/dev/null || python3 setup.py install --user 2>/dev/null
        success "dirsearch installed"
    else
        error "Failed to clone dirsearch"
    fi
    
    cd - >/dev/null
    rm -rf "$TMP_DIR"
else
    warning "dirsearch already installed"
fi

# ============================================================================
# PARAMETER DISCOVERY
# ============================================================================

header "INSTALLING PARAMETER DISCOVERY TOOLS"

# Arjun
install_python_tool "arjun" "arjun"

# ParamSpider
if ! command_exists paramspider; then
    info "Installing ParamSpider..."
    
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    if git clone https://github.com/devanshbatham/ParamSpider 2>/dev/null; then
        cd ParamSpider
        python3 -m pip install --user -r requirements.txt 2>/dev/null
        chmod +x paramspider.py
        
        # Try to symlink to PATH
        if sudo ln -sf "$(pwd)/paramspider.py" /usr/local/bin/paramspider 2>/dev/null; then
            success "ParamSpider installed"
        elif ln -sf "$(pwd)/paramspider.py" "$GOPATH/bin/paramspider" 2>/dev/null; then
            success "ParamSpider installed"
        else
            warning "ParamSpider installed but not in PATH"
            info "Add to PATH manually: $(pwd)/paramspider.py"
        fi
    else
        error "Failed to clone ParamSpider"
    fi
    
    cd - >/dev/null
else
    warning "paramspider already installed"
fi

# ============================================================================
# TAKEOVER DETECTION
# ============================================================================

header "INSTALLING TAKEOVER DETECTION TOOLS"

install_go_tool "github.com/PentestPad/subzy" "subzy"
install_go_tool "github.com/haccer/subjack" "subjack"

# ============================================================================
# XSS & INJECTION TESTING
# ============================================================================

header "INSTALLING XSS/INJECTION TOOLS"

install_go_tool "github.com/Emoe/kxss" "kxss"
install_go_tool "github.com/hahwul/dalfox/v2" "dalfox"

# SQLMap
if ! command_exists sqlmap; then
    info "Installing SQLMap..."
    
    if [ "$OS" = "darwin" ] && command_exists brew; then
        brew install sqlmap 2>/dev/null && success "sqlmap installed via Homebrew"
    else
        if command_exists apt; then
            sudo apt install -y sqlmap 2>/dev/null && success "sqlmap installed"
        else
            install_python_tool "sqlmap" "sqlmap"
        fi
    fi
else
    warning "sqlmap already installed"
fi

# ============================================================================
# ADDITIONAL TOOLS
# ============================================================================

header "INSTALLING ADDITIONAL TOOLS"

read -p "$(echo -e ${YELLOW}Install additional/optional tools? [y/N]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then

    # Meg (for path probing)
    install_go_tool "github.com/tomnomnom/meg" "meg"
    
    # Httprobe
    install_go_tool "github.com/tomnomnom/httprobe" "httprobe"
    
    # GF (pattern matching)
    install_go_tool "github.com/tomnomnom/gf" "gf"
    
    # Anti-burl (remove boring URLs)
    install_go_tool "github.com/tomnomnom/hacks/anti-burl" "anti-burl"
    
    # Jaeles (automated testing)
    install_go_tool "github.com/jaeles-project/jaeles" "jaeles"
    
    # Gospider
    install_go_tool "github.com/jaeles-project/gospider" "gospider"

else
    info "Skipping optional tools..."
fi

# ============================================================================
# PYTHON DEPENDENCIES
# ============================================================================

header "INSTALLING PYTHON DEPENDENCIES"

info "Installing Python requirements..."

cat > /tmp/webenum_requirements.txt << 'EOF'
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
urllib3>=2.0.0
dnspython>=2.4.0
EOF

python3 -m pip install --user -r /tmp/webenum_requirements.txt 2>/dev/null || warning "Some Python packages may have failed to install"
rm /tmp/webenum_requirements.txt

# ============================================================================
# WORDLISTS
# ============================================================================

header "WORDLISTS"

WORDLIST_DIR="$HOME/.config/webenum/wordlists"

if [ ! -d "$WORDLIST_DIR" ]; then
    read -p "$(echo -e ${YELLOW}Download useful wordlists? [y/N]: ${NC})" -n 1 -r
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

        # Common web paths
        if [ ! -f "$WORDLIST_DIR/common.txt" ]; then
            wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
                -O "$WORDLIST_DIR/common.txt" 2>/dev/null || \
            curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
                -o "$WORDLIST_DIR/common.txt"
            success "Common web wordlist downloaded"
        fi
        
        # Directory wordlist
        if [ ! -f "$WORDLIST_DIR/raft-small-directories.txt" ]; then
            wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/raft-small-directories.txt \
                -O "$WORDLIST_DIR/raft-small-directories.txt" 2>/dev/null || \
            curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/raft-small-directories.txt \
                -o "$WORDLIST_DIR/raft-small-directories.txt"
            success "Directory wordlist downloaded"
        fi

        # Parameter wordlist
        if [ ! -f "$WORDLIST_DIR/burp-parameter-names.txt" ]; then
            wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/burp-parameter-names.txt \
                -O "$WORDLIST_DIR/burp-parameter-names.txt" 2>/dev/null || \
            curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/burp-parameter-names.txt \
                -o "$WORDLIST_DIR/burp-parameter-names.txt"
            success "Parameter wordlist downloaded"
        fi

        success "Wordlists saved to $WORDLIST_DIR"
    fi
fi

# ============================================================================
# API KEY CONFIGURATION
# ============================================================================

header "API KEY CONFIGURATION"

API_CONFIG_DIR="$HOME/.config/webenum"
mkdir -p "$API_CONFIG_DIR"

info "API keys enable additional data sources:"
echo "  - VirusTotal (subdomain enumeration)"
echo "  - SecurityTrails (subdomain/DNS history)"
echo "  - Shodan (internet-wide scanning)"
echo "  - CertSpotter (certificate transparency)"
echo ""
info "Configure API keys later with: python3 webenum_enhanced.py --configure-api"

# ============================================================================
# FINAL VERIFICATION
# ============================================================================

header "FINAL VERIFICATION"

CRITICAL_TOOLS=("subfinder" "httpx" "dnsx")
DNS_TOOLS=("puredns" "massdns")
URL_TOOLS=("gau" "waybackurls" "hakrawler" "getJS" "anew" "uro")
SCAN_TOOLS=("nuclei" "nmap" "ffuf")
OPTIONAL_TOOLS=("amass" "gowitness" "arjun" "subzy" "dalfox" "sqlmap")

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
echo "DNS Tools:"
for tool in "${DNS_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${YELLOW}✗${NC} $tool ${YELLOW}(Recommended)${NC}"
    fi
done

echo ""
echo "URL Collection Tools:"
for tool in "${URL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${YELLOW}✗${NC} $tool"
    fi
done

echo ""
echo "Scanning Tools:"
for tool in "${SCAN_TOOLS[@]}"; do
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
success "Installation completed!"
echo ""
warning "IMPORTANT: Execute 'source $SHELL_CONFIG' or open a new terminal"
echo ""
info "Next steps:"
echo "  1. Configure API keys: python3 webenum_enhanced.py --configure-api"
echo "  2. Verify tools: python3 webenum_enhanced.py --check-tools"
echo "  3. Run your first scan: python3 webenum_enhanced.py -d example.com"
echo ""
