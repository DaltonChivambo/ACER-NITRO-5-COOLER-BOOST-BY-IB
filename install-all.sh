#!/bin/bash
# Acer Nitro 5 Cooler Boost by IB - Instalador completo
# Instala dependências, configura GRUB e instala o app

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_info() { echo -e "${YELLOW}[*]${NC} $1"; }
log_err()  { echo -e "${RED}[ERRO]${NC} $1"; }

echo ""
echo "=============================================="
echo "  Acer Nitro 5 Cooler Boost by IB"
echo "  Instalador completo"
echo "=============================================="
echo ""

[ "$(id -u)" -ne 0 ] && log_err "Execute com sudo: sudo ./install-all.sh" && exit 1

# --- 1. Detectar distro e instalar dependências ---
log_info "Detectando distribuição..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID="${ID:-unknown}"
    DISTRO_ID_LIKE="${ID_LIKE:-}"
else
    DISTRO_ID="unknown"
fi

install_deps() {
    case "$DISTRO_ID" in
        ubuntu|debian|pop|linuxmint|elementary)
            log_info "Instalando dependências (apt)..."
            apt-get update -qq
            apt-get install -y python3 python3-tk lm-sensors
            # nvidia-smi vem com driver NVIDIA (opcional)
            if ! command -v nvidia-smi &>/dev/null; then
                log_info "nvidia-smi não encontrado (opcional - instale driver NVIDIA se tiver GPU dedicada)"
            fi
            ;;
        fedora|rhel|centos)
            log_info "Instalando dependências (dnf)..."
            dnf install -y python3 python3-tkinter lm_sensors 2>/dev/null || \
            yum install -y python3 python3-tkinter lm_sensors 2>/dev/null || true
            ;;
        arch|manjaro)
            log_info "Instalando dependências (pacman)..."
            pacman -Sy --noconfirm python tk lm_sensors 2>/dev/null || true
            ;;
        opensuse*|suse)
            log_info "Instalando dependências (zypper)..."
            zypper install -y python3 python3-tk lm_sensors 2>/dev/null || true
            ;;
        *)
            log_info "Distro não reconhecida ($DISTRO_ID). Tentando apt..."
            apt-get update -qq 2>/dev/null && apt-get install -y python3 python3-tk lm-sensors 2>/dev/null || \
            log_err "Instale manualmente: python3, python3-tk, lm-sensors"
            ;;
    esac
}

install_deps
log_ok "Dependências instaladas"

# --- 2. Verificar Python e tkinter ---
log_info "Verificando Python..."
if ! python3 -c "import tkinter" 2>/dev/null; then
    log_err "tkinter não disponível. Instale python3-tk ou python3-tkinter"
    exit 1
fi
log_ok "Python + tkinter OK"

# --- 3. Configurar GRUB (ec_sys.write_support=1) ---
GRUB_FILE="/etc/default/grub"
EC_PARAM="ec_sys.write_support=1"

if [ -f "$GRUB_FILE" ]; then
    if grep -q "ec_sys.write_support" "$GRUB_FILE"; then
        log_ok "GRUB já contém ec_sys.write_support"
    else
        log_info "Configurando GRUB..."
        # Backup
        cp "$GRUB_FILE" "${GRUB_FILE}.bak.nitro-boost"
        # Adicionar parâmetro em GRUB_CMDLINE_LINUX_DEFAULT
        if grep -q 'GRUB_CMDLINE_LINUX_DEFAULT=' "$GRUB_FILE"; then
            sed -i "s/\(GRUB_CMDLINE_LINUX_DEFAULT=\"[^\"]*\)\"/\1 $EC_PARAM\"/" "$GRUB_FILE"
            log_ok "GRUB configurado com $EC_PARAM"
        else
            log_err "Não foi possível alterar GRUB. Adicione manualmente: $EC_PARAM"
        fi
        # Atualizar GRUB
        if command -v update-grub &>/dev/null; then
            update-grub
        elif command -v grub2-mkconfig &>/dev/null; then
            grub2-mkconfig -o /boot/grub2/grub.cfg 2>/dev/null || \
            grub2-mkconfig -o /boot/efi/EFI/*/grub.cfg 2>/dev/null || true
        elif command -v grub-mkconfig &>/dev/null; then
            grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null || true
        fi
        log_info "Reinicie o sistema para ativar o módulo ec_sys"
    fi
else
    log_err "Arquivo GRUB não encontrado: $GRUB_FILE"
fi

# --- 4. Instalar o app ---
log_info "Instalando aplicativo..."
"$SCRIPT_DIR/install.sh"
log_ok "Aplicativo instalado"

# --- 5. Resumo ---
echo ""
echo "=============================================="
echo -e "  ${GREEN}Instalação concluída com sucesso!${NC}"
echo "=============================================="
echo ""
echo "Próximos passos:"
echo "  1. Se o GRUB foi alterado agora: REINICIE o sistema"
echo "  2. Depois, execute: sudo nitro-boost"
echo "  3. Ou procure 'Acer Nitro 5 Cooler Boost by IB' no menu"
echo ""
echo "Modelos suportados: AN515-44, 46, 56, 57, 58"
echo ""
