#!/bin/sh
set -u

BASE_URL="http://192.168.31.125:18790"
NEXT="/tmp/little-lucy.next.jpg"
CURRENT="/tmp/little-lucy.current.jpg"
LAST="/tmp/little-lucy.last.md5"
LOG="/tmp/little-lucy-client.log"
FAILS=0

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG"
}

fetch_frame() {
  wget -q -T 2 -O "$NEXT" "$BASE_URL/current.jpg" || return 1
  [ -s "$NEXT" ] || return 1
  return 0
}

show_frame() {
  NEW_SUM="$(md5sum "$NEXT" | awk '{print $1}')"
  OLD_SUM="$(cat "$LAST" 2>/dev/null || true)"
  [ "$NEW_SUM" = "$OLD_SUM" ] && return 0
  mv "$NEXT" "$CURRENT"
  printf '%s' "$NEW_SUM" > "$LAST"
  /usr/bin/cmd_jpeg_display "$CURRENT" >/dev/null 2>&1 || return 1
  return 0
}

log "Little Lucy client starting"
while :; do
  if fetch_frame; then
    if show_frame; then
      FAILS=0
    else
      FAILS=$((FAILS + 1))
      log "display failed count=$FAILS"
    fi
  else
    FAILS=$((FAILS + 1))
    rm -f "$NEXT"
    [ "$FAILS" -eq 1 ] && log "frame fetch failed"
    [ "$FAILS" -eq 15 ] && log "Lucy-den unavailable; keeping last good frame"
  fi
  sleep 0.20
done
