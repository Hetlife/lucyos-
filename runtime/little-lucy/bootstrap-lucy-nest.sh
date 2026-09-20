#!/bin/sh
# Lucy-Nest MVP bootstrap for Creality Nebula N-Pad 01.
# Reversible: no firmware flash and no boot-script modification.
set -eu
BASE_URL="http://192.168.31.125:18790"
ROOT_DIR="/root/lucy-nest"
AUTH_DIR="/root/.ssh"
AUTH_FILE="$AUTH_DIR/authorized_keys"

mkdir -p "$ROOT_DIR" "$AUTH_DIR"
chmod 700 "$AUTH_DIR"
[ -f "$AUTH_FILE" ] || : > "$AUTH_FILE"
chmod 600 "$AUTH_FILE"

wget -q -T 5 -O /tmp/lucy-nest-rsa.pub "$BASE_URL/lucy-nest-rsa.pub"
KEY="$(cat /tmp/lucy-nest-rsa.pub)"
grep -qxF "$KEY" "$AUTH_FILE" 2>/dev/null || printf '%s\n' "$KEY" >> "$AUTH_FILE"
chmod 600 "$AUTH_FILE"

wget -q -T 5 -O "$ROOT_DIR/client.sh.new" "$BASE_URL/lucy-nest-client.sh"
mv "$ROOT_DIR/client.sh.new" "$ROOT_DIR/client.sh"
chmod 700 "$ROOT_DIR/client.sh"

# Take framebuffer ownership without touching Wi-Fi/SSH/services needed for recovery.
killall Monitor >/dev/null 2>&1 || true
killall display-server >/dev/null 2>&1 || true

# Stop any older Lucy-Nest client, then start this candidate.
if [ -f "$ROOT_DIR/client.pid" ]; then
  OLD_PID="$(cat "$ROOT_DIR/client.pid" 2>/dev/null || true)"
  [ -n "$OLD_PID" ] && kill "$OLD_PID" >/dev/null 2>&1 || true
fi
nohup "$ROOT_DIR/client.sh" >"$ROOT_DIR/client.log" 2>&1 &
echo $! > "$ROOT_DIR/client.pid"
sleep 2

PID="$(cat "$ROOT_DIR/client.pid")"
if kill -0 "$PID" 2>/dev/null; then
  echo "LUCY_NEST_MVP_STARTED pid=$PID"
else
  echo "LUCY_NEST_MVP_FAILED"
  tail -20 "$ROOT_DIR/client.log" 2>/dev/null || true
  exit 1
fi
