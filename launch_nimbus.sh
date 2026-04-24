#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${1:-${NIMBUS_BASE_URL:-http://localhost:8000}}"
URL_NO_QUERY="${BASE_URL%%\?*}"
URL_NO_TRAILING_SLASH="${URL_NO_QUERY%/}"
QUERY_GLUE="?"
if [[ "$BASE_URL" == *\?* ]]; then
  QUERY_GLUE="&"
fi
APP_URL="${BASE_URL}${QUERY_GLUE}mode=app&fresh=$(date +%s)"
SERVER_URL="${URL_NO_TRAILING_SLASH}/health"
IS_LOCALHOST=false
if [[ "$URL_NO_TRAILING_SLASH" == "http://localhost:8000" ]] || [[ "$URL_NO_TRAILING_SLASH" == http://localhost:* ]] || [[ "$URL_NO_TRAILING_SLASH" == "http://127.0.0.1:8000" ]] || [[ "$URL_NO_TRAILING_SLASH" == http://127.0.0.1:* ]]; then
  IS_LOCALHOST=true
fi

cd "$ROOT_DIR"

if [[ "$IS_LOCALHOST" == true ]]; then
  if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Nimbus server already running on port 8000."
  else
    echo "Starting Nimbus server on port 8000..."
    if command -v uvicorn >/dev/null 2>&1; then
      nohup uvicorn backend.main:app --port 8000 >/tmp/nimbus-demo.log 2>&1 &
    else
      nohup python -m uvicorn backend.main:app --port 8000 >/tmp/nimbus-demo.log 2>&1 &
    fi
    sleep 3
  fi

fi

if ! curl -fsS "$SERVER_URL" >/dev/null 2>&1; then
  echo "Nimbus launch failed: server did not respond at $SERVER_URL"
  exit 1
fi

OS_NAME="$(uname -s)"

if [[ "$OS_NAME" == "Darwin" ]]; then
  if open -Ra "Google Chrome" >/dev/null 2>&1; then
    osascript <<'APPLESCRIPT' >/dev/null 2>&1
tell application "Google Chrome"
  repeat with w in every window
    try
      if title of w is "Nimbus" then close w
    end try
  end repeat
end tell
APPLESCRIPT
    sleep 0.3
    open -na "Google Chrome" --args \
      --app="$APP_URL" \
      --window-size=130,150 \
      --window-position=1750,100 \
      --no-default-browser-check \
      --disable-features=TranslateUI
    sleep 1
    osascript <<'APPLESCRIPT' >/dev/null 2>&1
tell application "Google Chrome"
  repeat 20 times
    try
      set bounds of (first window whose title is "Nimbus") to {1750, 100, 1880, 250}
      exit repeat
    end try
    delay 0.25
  end repeat
end tell
APPLESCRIPT
  else
    open "$APP_URL"
  fi
else
  if command -v google-chrome >/dev/null 2>&1; then
    google-chrome \
      --app="$APP_URL" \
      --window-size=130,150 \
      --window-position=1750,100 \
      --no-default-browser-check \
      --disable-features=TranslateUI &
  elif command -v chromium >/dev/null 2>&1; then
    chromium \
      --app="$APP_URL" \
      --window-size=130,150 \
      --window-position=1750,100 \
      --no-default-browser-check \
      --disable-features=TranslateUI &
  else
    xdg-open "$APP_URL" >/dev/null 2>&1 &
  fi
fi

echo "✨ Nimbus is floating on your desktop. Drag it anywhere you like."
