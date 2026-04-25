#!/usr/bin/env bash

# ============================================================================
# GivEnum - Tools Installation Script
# Cross-platform: macOS (Homebrew + Go) and Debian/Ubuntu/Kali Linux
# ============================================================================

# No set -e: handle errors per-command so one failure doesn't kill everything

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${BLUE}[*]${NC} $1"; }
success() { echo -e "${GREEN}[+]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[-]${NC} $1"; }
skip()    { echo -e "${CYAN}[~]${NC} $1 (already installed)"; }
header()  {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# ============================================================================
# DETECT ENVIRONMENT
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS=$(uname -s | tr '[:upper:]' '[:lower:]')   # darwin | linux
ARCH=$(uname -m)                               # x86_64 | arm64 | aarch64

command_exists() { command -v "$1" >/dev/null 2>&1; }

# Detect whether we're inside a Python virtualenv
in_venv() {
    [ -n "$VIRTUAL_ENV" ] || python3 -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" 2>/dev/null
}

# pip_install <package> [<import_name>]
# Works in venv (no --user) and outside venv (--user or --break-system-packages)
pip_install() {
    local pkg="$1"
    local import_name="${2:-$1}"

    # Already importable?
    if python3 -c "import $import_name" 2>/dev/null; then
        skip "$pkg"
        return 0
    fi
    # Or already on PATH?
    if command_exists "$pkg"; then
        skip "$pkg"
        return 0
    fi

    info "Installing $pkg via pip..."

    if in_venv; then
        # Inside a venv: install directly (no --user)
        python3 -m pip install -q "$pkg" && { success "$pkg installed"; return 0; }
    else
        # Outside venv: prefer --user, fall back to --break-system-packages
        python3 -m pip install -q --user "$pkg" 2>/dev/null && { success "$pkg installed"; return 0; }
        python3 -m pip install -q --break-system-packages "$pkg" 2>/dev/null && { success "$pkg installed"; return 0; }
    fi

    # Last resort: pipx
    if command_exists pipx; then
        pipx install "$pkg" 2>/dev/null && { success "$pkg installed via pipx"; return 0; }
    fi

    warning "Could not install $pkg"
    return 1
}

# Aggregate counters used by the final summary
INSTALL_OK=0
INSTALL_SKIP=0
INSTALL_FAIL=0
FAILED_NAMES=()

# go_install <module@version> <binary_name>
go_install() {
    local module="$1"
    local bin="$2"

    if command_exists "$bin"; then
        skip "$bin"
        INSTALL_SKIP=$((INSTALL_SKIP + 1))
        return 0
    fi

    info "Installing $bin..."
    if go install -v "$module" 2>/dev/null; then
        success "$bin installed"
        INSTALL_OK=$((INSTALL_OK + 1))
    else
        warning "Failed to install $bin (continuing)"
        INSTALL_FAIL=$((INSTALL_FAIL + 1))
        FAILED_NAMES+=("$bin")
    fi
}

# try_run <label> <cmd...>
# Standardised wrapper for ad-hoc installers that don't fit go_install / pip_install
# (curl downloads, git clone + make, etc.). Updates the install counters.
try_run() {
    local label="$1"
    shift
    info "Installing $label..."
    if "$@"; then
        success "$label installed"
        INSTALL_OK=$((INSTALL_OK + 1))
        return 0
    else
        warning "Failed to install $label (continuing)"
        INSTALL_FAIL=$((INSTALL_FAIL + 1))
        FAILED_NAMES+=("$label")
        return 1
    fi
}

# brew_install <formula>
brew_install() {
    local formula="$1"
    if command_exists "$formula"; then
        skip "$formula"
        return 0
    fi
    info "Installing $formula via Homebrew..."
    brew install "$formula" 2>/dev/null && success "$formula installed" || warning "brew install $formula failed"
}

# ============================================================================
# CHECKS
# ============================================================================

header "GIVENUM - TOOLS INSTALLATION"

info "OS: $OS ($ARCH)"
info "Checking dependencies..."

# Go
if ! command_exists go; then
    error "Go is not installed!"
    if [ "$OS" = "darwin" ]; then
        echo "  → brew install go"
    else
        echo "  → sudo apt install golang-go   OR   https://go.dev/dl/"
    fi
    exit 1
fi
success "Go $(go version | awk '{print $3}' | sed 's/go//') detected"

# Python3
if ! command_exists python3; then
    error "Python3 is not installed!"
    exit 1
fi
success "Python $(python3 --version | awk '{print $2}') detected"

# venv warning
if in_venv; then
    info "Virtual environment detected — pip packages will install into the venv"
fi

# GOPATH
if [ -z "$GOPATH" ]; then
    export GOPATH="$HOME/go"
    warning "GOPATH not set, using: $GOPATH"
fi
export PATH="$PATH:$GOPATH/bin"

# ============================================================================
# SHELL PATH CONFIGURATION
# ============================================================================

# Detect active shell config
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_CONFIG="$HOME/.bash_profile"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
else
    SHELL_CONFIG="$HOME/.profile"
fi

GOBIN_LINE='export PATH=$PATH:$(go env GOPATH)/bin'
if ! grep -qF 'GOPATH)/bin' "$SHELL_CONFIG" 2>/dev/null; then
    info "Adding Go bin to PATH in $SHELL_CONFIG..."
    printf '\n# Go binaries\n%s\n' "$GOBIN_LINE" >> "$SHELL_CONFIG"
    success "PATH configured"
fi

# Python user bin (only relevant outside venv)
if ! in_venv; then
    PYTHON_USER_BIN="$(python3 -m site --user-base 2>/dev/null)/bin"
    if [ -d "$PYTHON_USER_BIN" ] && ! grep -qF "$PYTHON_USER_BIN" "$SHELL_CONFIG" 2>/dev/null; then
        printf '\n# Python user binaries\nexport PATH=$PATH:%s\n' "$PYTHON_USER_BIN" >> "$SHELL_CONFIG"
    fi
    export PATH="$PATH:$PYTHON_USER_BIN"
fi

# ============================================================================
# SYSTEM PACKAGES
# ============================================================================

header "SYSTEM PACKAGES"

if [ "$OS" = "darwin" ]; then
    if command_exists brew; then
        info "Updating Homebrew and installing base packages..."
        brew install git curl wget jq 2>/dev/null || true
    else
        warning "Homebrew not found — install it from https://brew.sh for best results"
    fi
else
    # Linux
    if command_exists apt-get; then
        info "Installing base packages via apt..."
        sudo apt-get update -q 2>/dev/null
        sudo apt-get install -y -q git curl wget jq python3-pip build-essential libpcap-dev 2>/dev/null || true
    elif command_exists dnf; then
        sudo dnf install -y git curl wget jq python3-pip gcc libpcap-devel 2>/dev/null || true
    elif command_exists yum; then
        sudo yum install -y git curl wget jq python3-pip gcc libpcap-devel 2>/dev/null || true
    elif command_exists pacman; then
        sudo pacman -Sy --noconfirm git curl wget jq python-pip libpcap 2>/dev/null || true
    fi
fi

# ============================================================================
# SUBDOMAIN ENUMERATION
# ============================================================================

header "SUBDOMAIN ENUMERATION TOOLS"

go_install "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest" "subfinder"
go_install "github.com/tomnomnom/assetfinder@latest" "assetfinder"
go_install "github.com/gwen001/github-subdomains@latest" "github-subdomains"
go_install "github.com/projectdiscovery/uncover/cmd/uncover@latest" "uncover"

# amass v4
if ! command_exists amass; then
    info "Installing amass..."
    go install -v "github.com/owasp-amass/amass/v4/...@latest" 2>/dev/null \
        && success "amass installed" \
        || warning "amass install failed (continuing)"
fi

# findomain
if ! command_exists findomain; then
    info "Installing findomain..."
    if [ "$OS" = "darwin" ] && command_exists brew; then
        brew install findomain 2>/dev/null && success "findomain installed" || warning "findomain brew install failed"
    else
        case "$ARCH" in
            x86_64)          FDA="amd64" ;;
            aarch64|arm64)   FDA="arm64" ;;
            *)               FDA="amd64" ;;
        esac
        FDOS="$OS"
        [ "$FDOS" = "linux" ] && FDOS="linux"
        FD_URL="https://github.com/Findomain/Findomain/releases/latest/download/findomain-${FDOS}-${FDA}.zip"
        TMP=$(mktemp -d)
        (
            cd "$TMP"
            curl -sL "$FD_URL" -o findomain.zip 2>/dev/null \
                && unzip -q findomain.zip 2>/dev/null \
                && chmod +x findomain \
                && (sudo mv findomain /usr/local/bin/ 2>/dev/null || mv findomain "$GOPATH/bin/") \
                && success "findomain installed"
        ) || warning "findomain install failed"
        rm -rf "$TMP"
    fi
fi

# knockpy
pip_install "knockpy" "knockpy"

# ============================================================================
# DNS TOOLS
# ============================================================================

header "DNS TOOLS"

go_install "github.com/projectdiscovery/dnsx/cmd/dnsx@latest" "dnsx"
go_install "github.com/d3mondev/puredns/v2@latest" "puredns"
go_install "github.com/vortexau/dnsvalidator@latest" "dnsvalidator"
go_install "github.com/projectdiscovery/tlsx/cmd/tlsx@latest" "tlsx"

# massdns
if ! command_exists massdns; then
    info "Installing massdns..."
    if [ "$OS" = "darwin" ] && command_exists brew; then
        brew install massdns 2>/dev/null && success "massdns installed" || _build_massdns=1
    else
        _build_massdns=1
    fi

    if [ "${_build_massdns:-0}" = "1" ]; then
        info "Compiling massdns from source..."
        TMP=$(mktemp -d)
        (
            cd "$TMP"
            git clone -q https://github.com/blechschmidt/massdns \
                && cd massdns \
                && make -s 2>/dev/null \
                && (sudo make install 2>/dev/null || cp bin/massdns "$GOPATH/bin/") \
                && success "massdns installed"
        ) || warning "massdns compile failed"
        rm -rf "$TMP"
    fi
fi

# ============================================================================
# HTTP PROBING
# ============================================================================

header "HTTP PROBING TOOLS"

go_install "github.com/projectdiscovery/httpx/cmd/httpx@latest" "httpx"
go_install "github.com/hakluke/hakcheckurl@latest" "hakcheckurl"
go_install "github.com/sensepost/gowitness@latest" "gowitness"

# ============================================================================
# URL COLLECTION
# ============================================================================

header "URL COLLECTION TOOLS"

go_install "github.com/hueristiq/xurlfind3r/cmd/xurlfind3r@latest" "xurlfind3r"
go_install "github.com/lc/gau/v2/cmd/gau@latest" "gau"
go_install "github.com/tomnomnom/waybackurls@latest" "waybackurls"
go_install "github.com/hakluke/hakrawler@latest" "hakrawler"
go_install "github.com/projectdiscovery/katana/cmd/katana@latest" "katana"
go_install "github.com/tomnomnom/meg@latest" "meg"

# Photon
if ! command_exists photon && ! python3 -c "import photon" 2>/dev/null; then
    warning "Photon auto-install skipped: upstream package name is not reliable. Install manually if needed."
fi

# ============================================================================
# JAVASCRIPT ANALYSIS
# ============================================================================

header "JAVASCRIPT ANALYSIS TOOLS"

go_install "github.com/lc/subjs@latest" "subjs"
go_install "github.com/003random/getJS@latest" "getJS"

# trufflehog (secret scanner — official install script)
if ! command_exists trufflehog; then
    info "Installing trufflehog..."
    if curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh \
        | sh -s -- -b "$GOPATH/bin" 2>/dev/null; then
        success "trufflehog installed"
    else
        warning "trufflehog install failed (continuing)"
    fi
fi

# jsubfinder (no go install path; build from source)
if ! command_exists jsubfinder; then
    info "Installing jsubfinder..."
    TMP=$(mktemp -d)
    (
        cd "$TMP"
        git clone -q https://github.com/ThreatUnknown/jsubfinder \
            && cd jsubfinder \
            && go build -o jsubfinder . 2>/dev/null \
            && (sudo mv jsubfinder /usr/local/bin/ 2>/dev/null || mv jsubfinder "$GOPATH/bin/") \
            && success "jsubfinder installed"
    ) || warning "jsubfinder build failed"
    rm -rf "$TMP"
fi

# ============================================================================
# UTILITIES
# ============================================================================

header "UTILITY TOOLS"

go_install "github.com/tomnomnom/anew@latest" "anew"
go_install "github.com/tomnomnom/unfurl@latest" "unfurl"
go_install "github.com/tomnomnom/qsreplace@latest" "qsreplace"
go_install "github.com/takshal/freq@latest" "freq"

pip_install "uro" "uro"

# ============================================================================
# SCANNING TOOLS
# ============================================================================

header "SCANNING TOOLS"

go_install "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest" "nuclei"
go_install "github.com/hahwul/dalfox/v2@latest" "dalfox"

if command_exists nuclei; then
    info "Updating Nuclei templates..."
    nuclei -update-templates 2>/dev/null || true
    success "Nuclei templates updated"
fi

# sdlookup (build from source)
if ! command_exists sdlookup; then
    info "Installing sdlookup..."
    TMP=$(mktemp -d)
    (
        cd "$TMP"
        git clone -q https://github.com/j3ssie/sdlookup \
            && cd sdlookup \
            && go build -o sdlookup . 2>/dev/null \
            && (sudo mv sdlookup /usr/local/bin/ 2>/dev/null || mv sdlookup "$GOPATH/bin/") \
            && success "sdlookup installed"
    ) || warning "sdlookup build failed"
    rm -rf "$TMP"
fi

# ============================================================================
# GIT DUMPING
# ============================================================================

header "GIT DUMPING TOOLS"

# goop (build from source)
if ! command_exists goop; then
    info "Installing goop..."
    TMP=$(mktemp -d)
    (
        cd "$TMP"
        git clone -q https://github.com/nyancrimew/goop \
            && cd goop \
            && go build -o goop . 2>/dev/null \
            && (sudo mv goop /usr/local/bin/ 2>/dev/null || mv goop "$GOPATH/bin/") \
            && success "goop installed"
    ) || warning "goop build failed"
    rm -rf "$TMP"
fi

pip_install "git-dumper" "git_dumper"

# ============================================================================
# PARAMETER DISCOVERY
# ============================================================================

header "PARAMETER DISCOVERY TOOLS"

pip_install "arjun" "arjun"

# ============================================================================
# TAKEOVER DETECTION
# ============================================================================

header "TAKEOVER DETECTION TOOLS"

go_install "github.com/PentestPad/subzy@latest" "subzy"
go_install "github.com/haccer/subjack@latest" "subjack"

# ============================================================================
# OPTIONAL TOOLS
# ============================================================================

header "OPTIONAL TOOLS"

echo -n "Install optional tools (sqlmap)? [y/N]: "
read -r REPLY
if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    if ! command_exists sqlmap; then
        if [ "$OS" = "darwin" ] && command_exists brew; then
            brew install sqlmap 2>/dev/null && success "sqlmap installed" || pip_install "sqlmap" "sqlmap"
        else
            pip_install "sqlmap" "sqlmap"
        fi
    else
        skip "sqlmap"
    fi
fi

# ============================================================================
# WORDLISTS
# ============================================================================

header "WORDLISTS"

WORDLIST_DIR="$HOME/.config/givenum/wordlists"

if [ ! -d "$WORDLIST_DIR" ]; then
    echo -n "Download wordlists (SecLists subdomains + common paths)? [y/N]: "
    read -r REPLY
    if [[ "$REPLY" =~ ^[Yy]$ ]]; then
        mkdir -p "$WORDLIST_DIR"

        SECLISTS_BASE="https://raw.githubusercontent.com/danielmiessler/SecLists/master"

        _download() {
            local url="$1" dest="$2"
            [ -f "$dest" ] && { skip "$(basename "$dest")"; return; }
            info "Downloading $(basename "$dest")..."
            curl -sL "$url" -o "$dest" 2>/dev/null \
                || wget -q "$url" -O "$dest" 2>/dev/null \
                || warning "Failed to download $(basename "$dest")"
            [ -s "$dest" ] && success "$(basename "$dest") saved"
        }

        _download "$SECLISTS_BASE/Discovery/DNS/subdomains-top1million-110000.txt" \
                  "$WORDLIST_DIR/subdomains-top1m.txt"
        _download "$SECLISTS_BASE/Discovery/Web-Content/common.txt" \
                  "$WORDLIST_DIR/common.txt"
        _download "$SECLISTS_BASE/Discovery/Web-Content/raft-medium-words.txt" \
                  "$WORDLIST_DIR/raft-medium.txt"

        success "Wordlists saved to $WORDLIST_DIR"
    fi
fi

# ============================================================================
# PYTHON DEPENDENCIES FOR GIVENUM
# ============================================================================

header "PYTHON DEPENDENCIES"

info "Installing GivEnum Python requirements..."

REQS="${SCRIPT_DIR:-$(pwd)}/requirements.txt"
if [ ! -f "$REQS" ]; then
    warning "requirements.txt not found, using built-in fallback"
    REQS_TMP=$(mktemp)
    cat > "$REQS_TMP" << 'EOF'
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
urllib3>=2.0.0
dnspython>=2.4.0
flask>=3.0.0
EOF
    REQS="$REQS_TMP"
fi

if in_venv; then
    python3 -m pip install -q -r "$REQS" && success "Python dependencies installed"
else
    python3 -m pip install -q --user -r "$REQS" 2>/dev/null \
        || python3 -m pip install -q --break-system-packages -r "$REQS" 2>/dev/null \
        || warning "Some Python packages may have failed"
fi
[ -n "${REQS_TMP:-}" ] && rm -f "$REQS_TMP"

# ============================================================================
# FINAL VERIFICATION
# ============================================================================

header "VERIFICATION"

CRITICAL=("subfinder" "httpx" "dnsx")
RECOMMENDED=("puredns" "massdns" "xurlfind3r" "gau" "waybackurls" "hakrawler" "meg" "nuclei" "dalfox" "sdlookup" "anew" "uro")
OPTIONAL_LIST=("gowitness" "arjun" "subzy" "goop" "git-dumper" "amass" "findomain")

MISSING_CRITICAL=()

echo "Critical Tools:"
for t in "${CRITICAL[@]}"; do
    if command_exists "$t"; then
        echo -e "  ${GREEN}✓${NC} $t"
    else
        echo -e "  ${RED}✗${NC} $t  ${RED}(MISSING — required)${NC}"
        MISSING_CRITICAL+=("$t")
    fi
done

echo ""
echo "Recommended Tools:"
for t in "${RECOMMENDED[@]}"; do
    if command_exists "$t"; then
        echo -e "  ${GREEN}✓${NC} $t"
    else
        echo -e "  ${YELLOW}✗${NC} $t"
    fi
done

echo ""
echo "Optional Tools:"
for t in "${OPTIONAL_LIST[@]}"; do
    if command_exists "$t"; then
        echo -e "  ${GREEN}✓${NC} $t"
    else
        echo -e "  ${CYAN}○${NC} $t"
    fi
done

echo ""
success "Installation complete!"
echo ""

# ── Per-tool install summary ────────────────────────────────────────────────
echo "Install summary:"
echo -e "  ${GREEN}✓ installed:${NC} $INSTALL_OK"
echo -e "  ${CYAN}~ skipped:${NC}   $INSTALL_SKIP  (already on PATH)"
if [ "$INSTALL_FAIL" -gt 0 ]; then
    echo -e "  ${YELLOW}! failed:${NC}    $INSTALL_FAIL"
    echo "    → ${FAILED_NAMES[*]}"
fi
echo ""

if [ "${#MISSING_CRITICAL[@]}" -gt 0 ]; then
    warning "Missing critical tools: ${MISSING_CRITICAL[*]}"
    echo "  Run 'source $SHELL_CONFIG' and try again, or install manually."
    echo ""
fi

warning "Run 'source $SHELL_CONFIG' (or open a new terminal) to update PATH"
echo ""
info "Next steps:"
echo "  1. python3 GivEnum.py --configure-api   # configure API keys"
echo "  2. python3 GivEnum.py --check-tools      # verify everything"
echo "  3. python3 GivEnum.py -d example.com     # first scan"

# Exit non-zero if any critical tool is still missing — useful for CI.
if [ "${#MISSING_CRITICAL[@]}" -gt 0 ]; then
    exit 2
fi
exit 0
echo ""
