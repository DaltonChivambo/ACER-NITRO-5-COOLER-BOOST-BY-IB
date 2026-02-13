#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_PREFIX:-/usr/local}/lib/nitro-boost"

echo "=== Nitro 5 Cooler Boost - Instalação ==="
[ "$(id -u)" -ne 0 ] && echo "Execute com sudo" && exit 1

mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/nitro_boost" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/nitro-boost" "$INSTALL_DIR/"
[ -f "$SCRIPT_DIR/uninstall.sh" ] && cp "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/" && chmod +x "$INSTALL_DIR/uninstall.sh"
[ -f "$SCRIPT_DIR/nitro-boost-ib.svg" ] && cp "$SCRIPT_DIR/nitro-boost-ib.svg" "$INSTALL_DIR/" && \
  mkdir -p /usr/share/icons/hicolor/scalable/apps && \
  cp "$SCRIPT_DIR/nitro-boost-ib.svg" /usr/share/icons/hicolor/scalable/apps/nitro-boost-ib.svg && \
  gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
[ -f "$SCRIPT_DIR/nitro-boost-ib.png" ] && cp "$SCRIPT_DIR/nitro-boost-ib.png" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/nitro-boost"
ln -sf "$INSTALL_DIR/nitro-boost" /usr/local/bin/nitro-boost

if [ -f "$SCRIPT_DIR/nitro-boost-ib.desktop" ]; then
  sed "s|/usr/local/lib/nitro-boost|$INSTALL_DIR|g" "$SCRIPT_DIR/nitro-boost-ib.desktop" > /tmp/nitro-boost-ib.desktop
  cp /tmp/nitro-boost-ib.desktop /usr/share/applications/nitro-boost-ib.desktop
  echo "App instalado: procure por 'Acer Nitro 5' ou 'Cooler Boost' no menu"
fi

# Polkit: executar sem pedir senha
if [ -f "$SCRIPT_DIR/nitro-boost.polkit.rules" ]; then
  mkdir -p /etc/polkit-1/rules.d
  cp "$SCRIPT_DIR/nitro-boost.polkit.rules" /etc/polkit-1/rules.d/50-nitro-boost.rules
  chmod 644 /etc/polkit-1/rules.d/50-nitro-boost.rules
  echo "Polkit: app configurado para abrir sem senha"
fi

# Sudoers: alternativa (mantém para sudo nitro-boost no terminal)
if [ -f "$SCRIPT_DIR/nitro-boost.sudoers" ]; then
  cp "$SCRIPT_DIR/nitro-boost.sudoers" /etc/sudoers.d/nitro-boost
  chmod 440 /etc/sudoers.d/nitro-boost
fi

echo ""
echo "Instalado! Execute: nitro-boost ou procure 'Acer Nitro 5 Cooler Boost by IB' nos aplicativos"
