FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive
ENV GOPATH=/root/go
ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin:/root/.local/bin
ENV NEXT_TELEMETRY_DISABLED=1
ENV RESULTS_DIR=/app/results
ENV GIVENUM_ROOT_DIR=/app
ENV GIVENUM_CONFIG_DIR=/root/.config/givenum
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

WORKDIR /app

RUN apt-get update -q && apt-get install -y -q \
    git curl wget jq unzip ca-certificates gnupg \
    python3 python3-pip python3-venv \
    build-essential libpcap-dev \
    chromium \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y -q nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN printf '#!/bin/sh\nexec /usr/bin/chromium --no-sandbox "$@"\n' \
      > /usr/local/bin/google-chrome && chmod +x /usr/local/bin/google-chrome

RUN mkdir -p /root/.config/puredns && \
    printf "8.8.8.8\n8.8.4.4\n1.1.1.1\n1.0.0.1\n9.9.9.9\n208.67.222.222\n208.67.220.220\n" \
      > /root/.config/puredns/resolvers.txt

# gau default config for VPS/Docker:
# - commoncrawl: blocked (SSL error on all VPS providers)
# - wayback: connection refused from datacenter IPs
# - otx + urlscan: always work
RUN printf 'threads = 2\nverbose = false\nretries = 1\nsubdomains = false\nparameters = false\nproviders = ["otx","urlscan"]\nblacklist = ["ttf","woff","svg","png","jpg","gif","ico","css","woff2"]\njson = false\n\n[filters]\n  filterstatuscodes = []\n  filtermimetypes = ["image/png", "image/jpg", "image/svg+xml", "image/gif"]\n' \
      > /root/.gau.toml

RUN ARCH=$(uname -m) && \
    case "$ARCH" in \
      x86_64)         GOARCH="amd64" ;; \
      aarch64|arm64)  GOARCH="arm64" ;; \
      *) echo "Unsupported arch: $ARCH" && exit 1 ;; \
    esac && \
    GO_VERSION=1.24.2 && \
    curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${GOARCH}.tar.gz" \
      | tar -C /usr/local -xz

# Core Python dependencies (MUST succeed)
RUN python3 -m pip install --break-system-packages -q \
    requests>=2.31.0 \
    beautifulsoup4>=4.12.0 \
    lxml>=4.9.0 \
    urllib3>=2.0.0 \
    dnspython>=2.4.0 \
    flask>=3.0.0

# Optional Python tools (may fail on some platforms)
RUN python3 -m pip install --break-system-packages -q knockpy 2>/dev/null || true
RUN python3 -m pip install --break-system-packages -q uro 2>/dev/null || true
RUN python3 -m pip install --break-system-packages -q git-dumper 2>/dev/null || true
RUN python3 -m pip install --break-system-packages -q arjun 2>/dev/null || true
RUN python3 -m pip install --break-system-packages -q photon-scanner 2>/dev/null || true

RUN go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install github.com/tomnomnom/assetfinder@latest && \
    go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest && \
    go install github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

RUN go install github.com/d3mondev/puredns/v2@latest 2>/dev/null || echo "[!] puredns failed (non-critical)"
RUN go install github.com/hakluke/hakcheckurl@latest 2>/dev/null || echo "[!] hakcheckurl failed (non-critical)"
RUN go install github.com/sensepost/gowitness@latest 2>/dev/null || echo "[!] gowitness failed (non-critical)"
RUN go install github.com/hueristiq/xurlfind3r/cmd/xurlfind3r@latest 2>/dev/null || echo "[!] xurlfind3r failed (non-critical)"
RUN go install github.com/lc/gau/v2/cmd/gau@latest 2>/dev/null || echo "[!] gau failed (non-critical)"
RUN go install github.com/tomnomnom/waybackurls@latest 2>/dev/null || echo "[!] waybackurls failed (non-critical)"
RUN go install github.com/hakluke/hakrawler@latest 2>/dev/null || echo "[!] hakrawler failed (non-critical)"
RUN go install github.com/projectdiscovery/katana/cmd/katana@latest 2>/dev/null || echo "[!] katana failed (non-critical)"
RUN go install github.com/tomnomnom/meg@latest 2>/dev/null || echo "[!] meg failed (non-critical)"
RUN go install github.com/lc/subjs@latest 2>/dev/null || echo "[!] subjs failed (non-critical)"
RUN go install github.com/003random/getJS@latest 2>/dev/null || echo "[!] getJS failed (non-critical)"
RUN go install github.com/tomnomnom/anew@latest 2>/dev/null || echo "[!] anew failed (non-critical)"
RUN go install github.com/tomnomnom/unfurl@latest 2>/dev/null || echo "[!] unfurl failed (non-critical)"
RUN go install github.com/tomnomnom/qsreplace@latest 2>/dev/null || echo "[!] qsreplace failed (non-critical)"
RUN go install github.com/takshal/freq@latest 2>/dev/null || echo "[!] freq failed (non-critical)"
RUN go install github.com/hahwul/dalfox/v2@latest 2>/dev/null || echo "[!] dalfox failed (non-critical)"
RUN go install github.com/PentestPad/subzy@latest 2>/dev/null || echo "[!] subzy failed (non-critical)"
RUN go install github.com/haccer/subjack@latest 2>/dev/null || echo "[!] subjack failed (non-critical)"
RUN go install github.com/owasp-amass/amass/v4/...@latest 2>/dev/null || echo "[!] amass install failed (non-critical)"
RUN go install github.com/gwen001/github-subdomains@latest 2>/dev/null || echo "[!] github-subdomains failed (non-critical)"
RUN go install github.com/projectdiscovery/uncover/cmd/uncover@latest 2>/dev/null || echo "[!] uncover failed (non-critical)"
RUN go install github.com/projectdiscovery/tlsx/cmd/tlsx@latest 2>/dev/null || echo "[!] tlsx failed (non-critical)"
RUN go install github.com/vortexau/dnsvalidator@latest 2>/dev/null || echo "[!] dnsvalidator failed (non-critical)"

RUN git clone --depth=1 -q https://github.com/blechschmidt/massdns /tmp/massdns && \
    cd /tmp/massdns && make -s 2>/dev/null && \
    cp bin/massdns /usr/local/bin/ && \
    rm -rf /tmp/massdns || echo "[!] massdns build failed (non-critical)"

RUN git clone --depth=1 -q https://github.com/j3ssie/sdlookup /tmp/sdlookup && \
    cd /tmp/sdlookup && go build -o /root/go/bin/sdlookup . 2>/dev/null && \
    rm -rf /tmp/sdlookup || echo "[!] sdlookup build failed (non-critical)"

RUN git clone --depth=1 -q https://github.com/nyancrimew/goop /tmp/goop && \
    cd /tmp/goop && go build -o /root/go/bin/goop . 2>/dev/null && \
    rm -rf /tmp/goop || echo "[!] goop build failed (non-critical)"

RUN git clone --depth=1 -q https://github.com/ThreatUnknown/jsubfinder /tmp/jsubfinder && \
    cd /tmp/jsubfinder && go build -o /root/go/bin/jsubfinder . 2>/dev/null && \
    rm -rf /tmp/jsubfinder || echo "[!] jsubfinder build failed (non-critical)"

RUN curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh \
    | sh -s -- -b /root/go/bin 2>/dev/null || echo "[!] trufflehog install failed (non-critical)"

RUN nuclei -update-templates 2>/dev/null || true

COPY web/package.json web/package-lock.json /app/web/
RUN npm --prefix /app/web ci

COPY GivEnum.py scan_runner.py install_tools.sh batch_enum.sh docker-entrypoint.sh /app/
COPY web /app/web

# postcss.config.mjs must exist for Tailwind to process @tailwind directives.
# Build is run from /app/web so Next.js resolves postcss config relative to CWD.
# WEB_BUILD_REV bumps the cache so `docker compose build` always re-runs npm build.
ARG WEB_BUILD_REV=1
RUN printf 'const config={plugins:{tailwindcss:{},autoprefixer:{}}};export default config;\n' \
    > /app/web/postcss.config.mjs

RUN chmod +x /app/install_tools.sh /app/batch_enum.sh /app/scan_runner.py /app/docker-entrypoint.sh && \
    echo "=== web build rev: ${WEB_BUILD_REV} ===" && \
    echo "=== postcss.config.mjs ===" && cat /app/web/postcss.config.mjs && \
    echo "=== tailwindcss present: $(ls /app/web/node_modules/tailwindcss/package.json 2>/dev/null && echo YES || echo NO) ===" && \
    cd /app/web && npm run build && \
    echo "=== CSS output sample ===" && head -c 80 /app/web/.next/static/css/*.css && echo "" && \
    cd /app && rm -rf /app/web-runtime && \
    mkdir -p /app/web-runtime/.next && \
    cp -R /app/web/.next/standalone/. /app/web-runtime/ && \
    cp -R /app/web/.next/static /app/web-runtime/.next/static && \
    if [ -d /app/web/public ]; then cp -R /app/web/public /app/web-runtime/public; fi

EXPOSE 3000
VOLUME ["/app/results", "/root/.config/givenum"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["web"]
