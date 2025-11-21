#!/bin/bash

# ============================================================================
# WebEnum Batch Processor
# Processa múltiplos domínios de uma lista
# ============================================================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[*]${NC} $1"; }
success() { echo -e "${GREEN}[+]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[-]${NC} $1"; }

# Verifica argumentos
if [ $# -lt 1 ]; then
    echo "Uso: $0 <arquivo_com_dominios> [opcoes_webenum]"
    echo ""
    echo "Exemplo:"
    echo "  $0 targets.txt --skip-screenshots"
    echo "  $0 domains.txt -o /caminho/output"
    echo ""
    exit 1
fi

DOMAINS_FILE="$1"
shift  # Remove primeiro argumento
EXTRA_ARGS="$@"

# Verifica se arquivo existe
if [ ! -f "$DOMAINS_FILE" ]; then
    error "Arquivo não encontrado: $DOMAINS_FILE"
    exit 1
fi

# Verifica se webenum.py existe
if [ ! -f "./webenum.py" ]; then
    error "webenum.py não encontrado no diretório atual"
    exit 1
fi

# Conta domínios
TOTAL=$(grep -v '^#' "$DOMAINS_FILE" | grep -v '^[[:space:]]*$' | wc -l)

if [ $TOTAL -eq 0 ]; then
    error "Nenhum domínio encontrado em $DOMAINS_FILE"
    exit 1
fi

info "Encontrados $TOTAL domínios para processar"
info "Argumentos extras: ${EXTRA_ARGS:-nenhum}"
echo ""

# Confirma
read -p "$(echo -e ${YELLOW}Iniciar processamento? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    warning "Cancelado pelo usuário"
    exit 0
fi

# Processa cada domínio
COUNTER=0
SUCCESS=0
FAILED=0

while IFS= read -r domain; do
    # Pula linhas vazias e comentários
    [[ "$domain" =~ ^[[:space:]]*$ ]] && continue
    [[ "$domain" =~ ^# ]] && continue

    COUNTER=$((COUNTER + 1))

    echo ""
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}Processando [$COUNTER/$TOTAL]: $domain${NC}"
    echo -e "${BLUE}================================================${NC}"

    # Executa webenum
    if ./webenum.py -d "$domain" $EXTRA_ARGS; then
        SUCCESS=$((SUCCESS + 1))
        success "Domínio $domain concluído com sucesso"
    else
        FAILED=$((FAILED + 1))
        error "Falha ao processar $domain"

        # Pergunta se quer continuar
        read -p "$(echo -e ${YELLOW}Continuar com próximo domínio? [Y/n]: ${NC})" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            warning "Processamento interrompido pelo usuário"
            break
        fi
    fi

done < "$DOMAINS_FILE"

# Sumário final
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}SUMÁRIO FINAL${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}Sucessos:${NC} $SUCCESS"
echo -e "${RED}Falhas:${NC}   $FAILED"
echo -e "${BLUE}Total:${NC}    $COUNTER"
echo ""

if [ $SUCCESS -gt 0 ]; then
    success "Processamento concluído!"
    info "Analise os resultados em: ./results/"
fi
