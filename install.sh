#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${TOTA_STUDIO_REPO_URL:-https://github.com/totatomasz13-web/TotaNNStudio.git}"
INSTALL_DIR="${TOTA_STUDIO_INSTALL_DIR:-$HOME/.local/share/totannstudio}"
BIN_DIR="${TOTA_STUDIO_BIN_DIR:-$HOME/.local/bin}"

command -v git >/dev/null || { echo "Brak git. Zainstaluj pakiet git." >&2; exit 1; }
command -v python3 >/dev/null || { echo "Brak python3. Zainstaluj Python 3.10+." >&2; exit 1; }

if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  if [ -e "$INSTALL_DIR" ] && [ -n "$(find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
    echo "Katalog instalacji istnieje i nie jest repozytorium Git: $INSTALL_DIR" >&2
    exit 1
  fi
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

python3 -m venv "$INSTALL_DIR/.venv" || {
  echo "Nie można utworzyć venv. Na Debianie/Ubuntu zainstaluj: sudo apt install python3-venv" >&2
  exit 1
}
"$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip
"$INSTALL_DIR/.venv/bin/python" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
"$INSTALL_DIR/.venv/bin/python" -m pip install "$INSTALL_DIR"

mkdir -p "$BIN_DIR"
ln -sfn "$INSTALL_DIR/.venv/bin/totannstudio" "$BIN_DIR/totannstudio"

echo ""
echo "TotaNNStudio zainstalowane. Uruchom:"
echo "  $BIN_DIR/totannstudio"
echo "Potem otwórz: http://127.0.0.1:4173/studio/"