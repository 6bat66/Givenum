#!/bin/bash

# ============================================================================
# WebEnum Tool Installation Script
# Cross-platform support: macOS and Debian/Kali
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[*]${NC} $1"; }
success() { echo -e "${GREEN}[+]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[-]${NC} $1"; }
header() { echo -e "\n${BLUE}========================================${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}========================================${NC}\n"; }

# Detect OS
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Go
check_go() {
    if ! command_exists go; then
        error "Go not installed!"
        echo ""
        if [ "$OS" = "darwin" ]; then
            echo "Install: brew install go"
        else
            echo "Install: sudo apt install golang-go"
        fi
        echo "Or download from: https://go.dev/dl/"
        exit 1
    fi
    
    GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
    success "Go $GO_VERSION detected"
}

# Check Python
check_python() {
    if ! command_exists python3; then
        error "Python3 not installed!"
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
    
    if python3 -m pip install --user "$package" 2>/dev/null || pip3 install --user "$package" 2>/dev/null; then
        success "$name installed"
        return 0
    else
        error "Failed to install $name"
        return 1
    fi
}

# Install system packages
install_system_packages() {
    header "SYSTEM PACKAGES"
    
    if [ "$OS" = "darwin" ]; then
        if command_exists brew; then
            info "Installing via Homebrew..."
            brew install git wget curl jq 2>/dev/null || warning "Some packages may have failed"
        else
            warning "Homebrew not found"
            info "Install: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        fi
    else
        info "Installing system packages..."
        if command_exists apt; then
            sudo apt update && sudo apt install -y git wget curl jq build-essential 2>/dev/null || warning "Some packages may have failed"
        elif command_exists dnf; then
            sudo dnf install -y git wget curl jq gcc make 2>/dev/null || warning "Some packages may have failed"
        elif command_exists yum; then
            sudo yum install -y git wget curl jq gcc make 2>/dev/null || warning "Some packages may have failed"
        fi
    fi
}

# Main
header "WEBENUM TOOL INSTALLER"

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
    success "PATH configured"
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
# SUBDOMAIN ENUMERATION
# ============================================================================

header "SUBDOMAIN TOOLS"

install_go_tool "github.com/projectdiscovery/subfinder/v2/cmd/subfinder" "subfinder"
install_go_tool "github.com/tomnomnom/assetfinder" "assetfinder"
install_go_tool "github.com/projectdiscovery/chaos-client/cmd/chaos" "chaos"

# Findomain
if ! command_exists findomain; then
    info "Installing findomain..."
    
    if [ "$OS" = "darwin" ] && command_exists brew; then
        brew install findomain 2>/dev/null && success "findomain installed via Homebrew"
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
                success "findomain installed"
            fi
        fi
        
        cd - >/dev/null
        rm -rf "$TMP_DIR"
    fi
fi

# Amass
install_go_tool "github.com/owasp-amass/amass/v4/...@master" "amass"

# ============================================================================
# DNS TOOLS
# ============================================================================

header "DNS TOOLS"

install_go_tool "github.com/projectdiscovery/dnsx/cmd/dnsx" "dnsx"
install_go_tool "github.com/d3mondev/puredns/v2" "puredns"
install_go_tool "github.com/projectdiscovery/shuffledns/cmd/shuffledns" "shuffledns"

# massdns
if ! command_exists massdns; then
    info "Installing massdns..."
    
    if [ "$OS" = "darwin" ] && command_exists brew; then
        brew install massdns 2>/dev/null && success "massdns installed"
    else
        TMP_DIR=$(mktemp -d)
        cd "$TMP_DIR"
        
        if git clone https://github.com/blechschmidt/massdns 2>/dev/null; then
            cd massdns
            make 2>/dev/null && sudo make install 2>/dev/null && success "massdns installed"
        fi
        
        cd - >/dev/null
        rm -rf "$TMP_DIR"
    fi
fi

# ============================================================================
# HTTP PROBING
# ============================================================================

header "HTTP PROBING"

install_go_tool "github.com/projectdiscovery/httpx/cmd/httpx" "httpx"
install_go_tool "github.com/hakluke/hakcheckurl" "hakcheckurl"
install_go_tool "github.com/sensepost/gowitness" "gowitness"

# ============================================================================
# PORT SCANNING
# ============================================================================

header "PORT SCANNING"

# sdlookup (uses Shodan internetdb)
install_go_tool "github.com/j3ssie/sdlookup" "sdlookup"

# ============================================================================
# URL COLLECTION
# ============================================================================

header "URL COLLECTION"

# xurlfind3r (modern URL finder)
install_go_tool "github.com/hueristiq/xurlfind3r/cmd/xurlfind3r" "xurlfind3r"

# katana (modern web crawler)
install_go_tool "github.com/projectdiscovery/katana/cmd/katana" "katana"

# gospider
install_go_tool "github.com/jaeles-project/gospider" "gospider"

# Traditional tools
install_go_tool "github.com/lc/gau/v2/cmd/gau" "gau"
install_go_tool "github.com/tomnomnom/waybackurls" "waybackurls"

# ============================================================================
# JAVASCRIPT ANALYSIS
# ============================================================================

header "JAVASCRIPT TOOLS"

# jsubfinder (finds subdomains in JS)
if ! command_exists jsubfinder; then
    info "Installing jsubfinder..."
    
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    if git clone https://github.com/ThreatUnkn0wn/jsubfinder 2>/dev/null; then
        cd jsubfinder
        
        if [ "$OS" = "darwin" ]; then
            chmod +x install_darwin.sh
            ./install_darwin.sh 2>/dev/null && success "jsubfinder installed"
        else
            chmod +x install.sh
            ./install.sh 2>/dev/null && success "jsubfinder installed"
        fi
    fi
    
    cd - >/dev/null
    rm -rf "$TMP_DIR"
fi

# subjs
install_go_tool "github.com/lc/subjs" "subjs"

# getallurls
install_go_tool "github.com/lc/gau/v2/cmd/gau" "getallurls"

# LinkFinder
if ! command_exists linkfinder; then
    info "Installing LinkFinder..."
    
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    if git clone https://github.com/GerbenJavado/LinkFinder 2>/dev/null; then
        cd LinkFinder
        python3 setup.py install --user 2>/dev/null && success "LinkFinder installed"
    fi
    
    cd - >/dev/null
    rm -rf "$TMP_DIR"
fi

# ============================================================================
# UTILITIES
# ============================================================================

header "UTILITIES"

install_go_tool "github.com/tomnomnom/anew" "anew"
install_python_tool "uro" "uro"
install_go_tool "github.com/tomnomnom/unfurl" "unfurl"
install_go_tool "github.com/tomnomnom/qsreplace" "qsreplace"
install_go_tool "github.com/takshal/freq" "freq"

# ============================================================================
# GIT TOOLS
# ============================================================================

header "GIT TOOLS"

# goop (git dumper)
install_go_tool "github.com/deletescape/goop" "goop"

# trufflehog (secret scanner)
if ! command_exists trufflehog; then
    info "Installing trufflehog..."
    
    if [ "$OS" = "darwin" ] && command_exists brew; then
        brew install trufflehog 2>/dev/null && success "trufflehog installed"
    else
        # Install from GitHub releases
        TMP_DIR=$(mktemp -d)
        cd "$TMP_DIR"
        
        case "$OS" in
            linux)
                if [ "$ARCH" = "x86_64" ]; then
                    TRUFFLEHOG_URL="https://github.com/trufflesecurity/trufflehog/releases/latest/download/trufflehog_3.63.7_linux_amd64.tar.gz"
                fi
                ;;
        esac
        
        if [ -n "$TRUFFLEHOG_URL" ]; then
            wget -q "$TRUFFLEHOG_URL" -O trufflehog.tar.gz 2>/dev/null || curl -sL "$TRUFFLEHOG_URL" -o trufflehog.tar.gz
            tar -xzf trufflehog.tar.gz
            chmod +x trufflehog
            sudo mv trufflehog /usr/local/bin/ 2>/dev/null || mv trufflehog "$GOPATH/bin/"
            success "trufflehog installed"
        fi
        
        cd - >/dev/null
        rm -rf "$TMP_DIR"
    fi
fi

# git-dumper
if ! command_exists git-dumper; then
    info "Installing git-dumper..."
    install_python_tool "git-dumper" "git-dumper"
fi

# ============================================================================
# VULNERABILITY SCANNING
# ============================================================================

header "VULNERABILITY SCANNING"

# nuclei
install_go_tool "github.com/projectdiscovery/nuclei/v3/cmd/nuclei" "nuclei"

if command_exists nuclei; then
    info "Updating Nuclei templates..."
    nuclei -update-templates 2>/dev/null || true
fi

# jaeles
install_go_tool "github.com/jaeles-project/jaeles" "jaeles"

# nikto
if ! command_exists nikto; then
    info "Installing nikto..."
    
    if [ "$OS" = "darwin" ] && command_exists brew; then
        brew install nikto 2>/dev/null
    elif command_exists apt; then
        sudo apt install -y nikto 2>/dev/null
    fi
fi

# ============================================================================
# FUZZING TOOLS
# ============================================================================

header "FUZZING TOOLS"

install_go_tool "github.com/ffuf/ffuf/v2" "ffuf"
install_go_tool "github.com/epi052/feroxbuster" "feroxbuster"
install_go_tool "github.com/OJ/gobuster/v3" "gobuster"

# ============================================================================
# PARAMETER DISCOVERY
# ============================================================================

header "PARAMETER DISCOVERY"

install_python_tool "arjun" "arjun"

# x8 (hidden parameter discovery)
if ! command_exists x8; then
    info "Installing x8..."
    
    if command_exists cargo; then
        cargo install x8 2>/dev/null && success "x8 installed"
    else
        warning "Rust/cargo not found, skipping x8"
    fi
fi

# ============================================================================
# TECHNOLOGY DETECTION
# ============================================================================

header "TECHNOLOGY DETECTION"

# webanalyze
install_go_tool "github.com/rverton/webanalyze/cmd/webanalyze" "webanalyze"

# retire.js
if ! command_exists retire; then
    info "Installing retire.js..."
    
    if command_exists npm; then
        npm install -g retire 2>/dev/null && success "retire.js installed"
    else
        warning "npm not found, skipping retire.js"
    fi
fi

# ============================================================================
# OPTIONAL TOOLS
# ============================================================================

header "OPTIONAL TOOLS"

read -p "$(echo -e ${YELLOW}Install optional tools? [y/N]: ${NC})" -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    install_go_tool "github.com/projectdiscovery/naabu/v2/cmd/naabu" "naabu"
    install_go_tool "github.com/PentestPad/subzy" "subzy"
    install_go_tool "github.com/haccer/subjack" "subjack"
    install_go_tool "github.com/hahwul/dalfox/v2" "dalfox"
    install_go_tool "github.com/projectdiscovery/notify/cmd/notify" "notify"
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
        wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt \
            -O "$WORDLIST_DIR/subdomains.txt" 2>/dev/null || \
        curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt \
            -o "$WORDLIST_DIR/subdomains.txt"
        
        # Directory wordlist
        wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
            -O "$WORDLIST_DIR/common.txt" 2>/dev/null || \
        curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt \
            -o "$WORDLIST_DIR/common.txt"
        
        success "Wordlists: $WORDLIST_DIR"
    fi
fi

# ============================================================================
# VERIFICATION
# ============================================================================

header "VERIFICATION"

CRITICAL_TOOLS=("subfinder" "httpx" "dnsx")
RECOMMENDED_TOOLS=("xurlfind3r" "katana" "sdlookup" "jsubfinder" "nuclei")

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
        echo -e "  ${YELLOW}○${NC} $tool (optional)"
    fi
done

echo ""
success "Installation complete!"
echo ""
warning "IMPORTANT: Run 'source $SHELL_CONFIG' or open a new terminal"
echo ""
info "Next steps:"
echo "  1. Configure API keys: python3 webenum.py --configure-api"
echo "  2. Check tools: python3 webenum.py --check-tools"
echo "  3. Run scan: python3 webenum.py -d example.com"
echo ""