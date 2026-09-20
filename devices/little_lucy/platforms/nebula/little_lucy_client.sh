#!/bin/sh
# Little Lucy Nebula MVP client. BusyBox/Dropbear friendly; no package installs.
set -u
BASE_URL="${LUCY_BASE_URL:-http://192.168.31.125:18790}"
STATE=/tmp/little_lucy_state.json
FRAME=/tmp/little_lucy_frame.jpg
LAST_STATE=ready
I=0

state_name() {
  sed -n 's/.*"state"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$1" \
    | tr '[:upper:]' '[:lower:]' | tr '_' '-'
}

while :; do
  if wget -q -T 2 -O "$STATE.new" "$BASE_URL/state.json"; then
    mv "$STATE.new" "$STATE"
    S="$(state_name "$STATE")"
    [ -n "$S" ] && LAST_STATE="$S"
  fi
  case "$LAST_STATE" in
    ready|thinking|working|verify|success|needs-you|offline) : ;;
    *) LAST_STATE=ready ;;
  esac
  FOLDER="$LAST_STATE"
  [ "$FOLDER" = "needs-you" ] && FOLDER=needs_you
  N="$(printf '%02d' "$I")"
  if wget -q -T 2 -O "$FRAME.new" "$BASE_URL/frames/$FOLDER/$N.jpg"; then
    mv "$FRAME.new" "$FRAME"
    /usr/bin/cmd_jpeg_display "$FRAME" >/dev/null 2>&1 || true
  fi
  I=$(( (I + 1) % 18 ))
  sleep 0.16
done
