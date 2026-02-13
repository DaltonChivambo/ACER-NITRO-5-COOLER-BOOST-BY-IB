#!/bin/bash
# Acer Nitro 5 Cooler Boost by IB - Desinstalação

set -e
INSTALL_DIR="${INSTALL_DIR:-${INSTALL_PREFIX:-/usr/local}/lib/nitro-boost}"

echo "=== Acer Nitro 5 Cooler Boost - Desinstalação ==="
[ "$(id -u)" -ne 0 ] && echo "Execute com sudo: sudo ./uninstall.sh" && exit 1

echo "Removendo arquivos de $INSTALL_DIR..."
rm -rf "$INSTALL_DIR"
rm -f /usr/local/bin/nitro-boost
rm -f /usr/share/applications/nitro-boost-ib.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/nitro-boost-ib.svg
rm -f /etc/polkit-1/rules.d/50-nitro-boost.rules
rm -f /etc/sudoers.d/nitro-boost

# Atualizar cache de ícones
[ -d /usr/share/icons/hicolor ] && gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true

echo ""
echo "Desinstalação concluída."
echo "Nota: O parâmetro ec_sys.write_support=1 no GRUB não foi removido."
echo "      Para removê-lo, edite /etc/default/grub manualmente."
echo ""
