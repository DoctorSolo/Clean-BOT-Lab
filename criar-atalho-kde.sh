#!/usr/bin/env bash
# Gera um atalho real no menu de aplicativos KDE/GNOME, ajustado ao caminho local da pasta.
set -e
cd "$(dirname "$0")"
ROOT="$(pwd -P)"
TARGET="$HOME/.local/share/applications/clean-bot-lab.desktop"
mkdir -p "$(dirname "$TARGET")"
cat > "$TARGET" <<DESKTOP
[Desktop Entry]
Type=Application
Version=1.0
Name=Clean BOT Lab
Comment=Laboratório visual de memórias para agentes de IA
Exec=/usr/bin/env bash "$ROOT/iniciar-linux.sh"
Path=$ROOT
Icon=$ROOT/app/static/clean-bot.jpg
Terminal=false
Categories=Development;Education;
StartupNotify=true
DESKTOP
chmod +x "$TARGET"
echo "Atalho criado em $TARGET. Procure 'Clean BOT Lab' no menu de aplicativos."
