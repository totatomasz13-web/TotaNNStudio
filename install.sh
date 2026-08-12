#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${TOTA_STUDIO_REPO_URL:-https://github.com/totatomasz13-web/TotaNNStudio.git}"
if [ "$(id -u)" -eq 0 ]; then
  DEFAULT_INSTALL_DIR=/opt/totannstudio
  DEFAULT_BIN_DIR=/usr/local/bin
else
  DEFAULT_INSTALL_DIR="$HOME/.local/share/totannstudio"
  DEFAULT_BIN_DIR="$HOME/.local/bin"
fi
INSTALL_DIR="${TOTA_STUDIO_INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
BIN_DIR="${TOTA_STUDIO_BIN_DIR:-$DEFAULT_BIN_DIR}"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
if [ "$(id -u)" -eq 0 ]; then
  DEFAULT_EXISTING_UNIT=/etc/systemd/system/totannstudio.service
else
  DEFAULT_EXISTING_UNIT="$SYSTEMD_USER_DIR/totannstudio.service"
fi
EXISTING_UNIT="${TOTA_STUDIO_EXISTING_UNIT:-$DEFAULT_EXISTING_UNIT}"
EXISTING_HOST=""
EXISTING_PORT=""
if [ -f "$EXISTING_UNIT" ] && grep -q 'ExecStart=.*totannstudio' "$EXISTING_UNIT"; then
  EXISTING_HOST="$(grep -E '^Environment=TOTA_STUDIO_HOST=' "$EXISTING_UNIT" | tail -n 1 | cut -d= -f3- || true)"
  EXISTING_PORT="$(grep -E '^Environment=TOTA_STUDIO_PORT=' "$EXISTING_UNIT" | tail -n 1 | cut -d= -f3- || true)"
fi
STUDIO_PORT="${TOTA_STUDIO_PORT:-${EXISTING_PORT:-8080}}"
if ! printf '%s\n' "$STUDIO_PORT" | grep -Eq '^[0-9]+$' || [ "$STUDIO_PORT" -lt 1 ] || [ "$STUDIO_PORT" -gt 65535 ]; then
  echo "Nieprawidłowy TOTA_STUDIO_PORT: $STUDIO_PORT (dozwolone 1-65535)." >&2
  exit 1
fi
DEFAULT_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | grep -oE 'src [0-9.]+' | awk '{print $2}' | head -n 1 || true)"
if printf '%s\n' "$DEFAULT_IP" | grep -Eq '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)'; then
  PRIVATE_IP="$DEFAULT_IP"
else
  PRIVATE_IP=""
fi
if [ -n "${TOTA_STUDIO_HOST:-}" ]; then
  STUDIO_HOST="$TOTA_STUDIO_HOST"
  DISPLAY_HOST="$TOTA_STUDIO_HOST"
  [ "$DISPLAY_HOST" = "0.0.0.0" ] && DISPLAY_HOST="${PRIVATE_IP:-127.0.0.1}"
  STUDIO_URL="http://$DISPLAY_HOST:$STUDIO_PORT/studio/"
elif [ -n "$EXISTING_HOST" ]; then
  STUDIO_HOST="$EXISTING_HOST"
  DISPLAY_HOST="$EXISTING_HOST"
  [ "$DISPLAY_HOST" = "0.0.0.0" ] && DISPLAY_HOST="${PRIVATE_IP:-127.0.0.1}"
  STUDIO_URL="http://$DISPLAY_HOST:$STUDIO_PORT/studio/"
elif [ -n "$PRIVATE_IP" ]; then
  STUDIO_HOST="$PRIVATE_IP"
  STUDIO_URL="http://$PRIVATE_IP:$STUDIO_PORT/studio/"
else
  STUDIO_HOST=127.0.0.1
  STUDIO_URL="http://127.0.0.1:$STUDIO_PORT/studio/"
fi

case "$STUDIO_HOST" in
  ""|*[!A-Za-z0-9.-]*|.*|*.)
    echo "Nieprawidłowy TOTA_STUDIO_HOST: wartość musi być adresem IPv4 lub nazwą hosta." >&2
    exit 1
    ;;
esac

command -v python3 >/dev/null || { echo "Brak python3. Zainstaluj Python 3.10+." >&2; exit 1; }

if ! python3 - "$STUDIO_HOST" <<'PY'
import socket
import sys

host = sys.argv[1]
try:
    with socket.socket() as sock:
        sock.bind((host, 0))
except OSError as exc:
    print(exc, file=sys.stderr)
    raise SystemExit(1)
PY
then
  echo "Do hosta $STUDIO_HOST nie można przypisać usługi. Sprawdź TOTA_STUDIO_HOST lub adres IP komputera." >&2
  exit 1
fi

port_is_busy() {
  python3 - "$STUDIO_HOST" "$1" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
with socket.socket() as sock:
    try:
        sock.bind((host, port))
    except OSError:
        raise SystemExit(0)
raise SystemExit(1)
PY
}

port_has_totannstudio() {
  command -v curl >/dev/null 2>&1 || return 1
  health_host="$STUDIO_HOST"
  [ "$health_host" = "0.0.0.0" ] && health_host=127.0.0.1
  response="$(curl -fsS --max-time 2 "http://$health_host:$1/api/health" 2>/dev/null || true)"
  printf '%s' "$response" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"' &&
    printf '%s' "$response" | grep -Eq '"engine"[[:space:]]*:[[:space:]]*"tota"'
}

REQUESTED_PORT="$STUDIO_PORT"
while port_is_busy "$STUDIO_PORT"; do
  if port_has_totannstudio "$STUDIO_PORT"; then
    echo "Wykryto istniejące TotaNNStudio na porcie $STUDIO_PORT; port zostaje zachowany."
    break
  fi
  if [ "${TOTA_STUDIO_STRICT_PORT:-0}" = "1" ]; then
    PORT_OWNER="$(ss -H -ltnp "sport = :$STUDIO_PORT" 2>/dev/null | head -n 1 || true)"
    echo "Port $STUDIO_PORT jest zajęty${PORT_OWNER:+ ($PORT_OWNER)}. Ustaw inny TOTA_STUDIO_PORT albo wyłącz TOTA_STUDIO_STRICT_PORT." >&2
    exit 1
  fi
  if [ "$STUDIO_PORT" -ge 65535 ]; then
    echo "Brak wolnego portu od $REQUESTED_PORT do 65535." >&2
    exit 1
  fi
  STUDIO_PORT=$((STUDIO_PORT + 1))
done
if [ "$STUDIO_PORT" != "$REQUESTED_PORT" ]; then
  PORT_OWNER="$(ss -H -ltnp "sport = :$REQUESTED_PORT" 2>/dev/null | head -n 1 || true)"
  echo "Port $REQUESTED_PORT jest zajęty${PORT_OWNER:+ ($PORT_OWNER)}; wybrano wolny port $STUDIO_PORT."
  STUDIO_URL="http://${DISPLAY_HOST:-${PRIVATE_IP:-127.0.0.1}}:$STUDIO_PORT/studio/"
fi

if [ "${TOTA_STUDIO_CHECK_ONLY:-0}" = "1" ]; then
  echo "HOST=$STUDIO_HOST"
  echo "PORT=$STUDIO_PORT"
  echo "URL=$STUDIO_URL"
  exit 0
fi

command -v git >/dev/null || { echo "Brak git. Zainstaluj pakiet git." >&2; exit 1; }

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

if [ "$(id -u)" -eq 0 ] && command -v systemctl >/dev/null; then
  if ! id totannstudio >/dev/null 2>&1; then
    useradd --system --home-dir /var/lib/totannstudio --shell /usr/sbin/nologin totannstudio
  fi
  install -d -o totannstudio -g totannstudio -m 750 /var/lib/totannstudio/models
  chown -R root:root "$INSTALL_DIR"
  chmod -R go-w "$INSTALL_DIR"
  {
    echo "[Unit]"
    echo "Description=TotaNNStudio local neural network studio"
    echo "After=network.target"
    echo ""
    echo "[Service]"
    echo "Type=simple"
    echo "User=totannstudio"
    echo "Group=totannstudio"
    printf 'ExecStart=%q\n' "$INSTALL_DIR/.venv/bin/totannstudio"
    echo "Environment=TOTA_STUDIO_HOST=$STUDIO_HOST"
    echo "Environment=TOTA_STUDIO_PORT=$STUDIO_PORT"
    echo "Environment=TOTA_MODELS_DIR=/var/lib/totannstudio/models"
    echo "Restart=on-failure"
    echo "RestartSec=5"
    echo "NoNewPrivileges=true"
    echo "PrivateTmp=true"
    echo ""
    echo "[Install]"
    echo "WantedBy=multi-user.target"
  } > /etc/systemd/system/totannstudio.service
  systemctl daemon-reload
  systemctl enable totannstudio.service
  systemctl restart totannstudio.service
  AUTOSTART_MESSAGE="Autostart po restarcie systemu włączony."
elif command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1; then
  mkdir -p "$SYSTEMD_USER_DIR"
  {
    echo "[Unit]"
    echo "Description=TotaNNStudio local neural network studio"
    echo "After=network.target"
    echo ""
    echo "[Service]"
    echo "Type=simple"
    printf 'ExecStart=%q\n' "$INSTALL_DIR/.venv/bin/totannstudio"
    echo "Environment=TOTA_STUDIO_HOST=$STUDIO_HOST"
    echo "Environment=TOTA_STUDIO_PORT=$STUDIO_PORT"
    echo "Restart=on-failure"
    echo "RestartSec=5"
    echo "NoNewPrivileges=true"
    echo "PrivateTmp=true"
    echo ""
    echo "[Install]"
    echo "WantedBy=default.target"
  } > "$SYSTEMD_USER_DIR/totannstudio.service"
  systemctl --user daemon-reload
  systemctl --user enable totannstudio.service
  systemctl --user restart totannstudio.service
  AUTOSTART_MESSAGE="Autostart po zalogowaniu włączony. Dla startu bez logowania administrator może wykonać: sudo loginctl enable-linger $USER"
else
  AUTOSTART_MESSAGE="Brak działającego systemd użytkownika — uruchamiaj ręcznie: $BIN_DIR/totannstudio"
fi

echo ""
echo "TotaNNStudio zainstalowane."
echo "$AUTOSTART_MESSAGE"
echo "Otwórz: $STUDIO_URL"