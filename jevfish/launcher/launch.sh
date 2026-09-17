#!/bin/bash
# One-click start for JevFish on a Mac. JevFish.app runs this with the repo folder as $1.
# First start: installs uv (into ~/Library/Application Support/JevFish/bin, no admin
# password) and the Python packages. Every start: reuses a running JevFish or starts one
# on a free port, then opens it in the browser.
#
# Test hooks: JEVFISH_NO_GUI=1 logs instead of showing dialogs, JEVFISH_NO_OPEN=1 skips the
# browser, JEVFISH_UV_INSTALLER replaces the uv install script, JEVFISH_PORTS lists ports,
# JEVFISH_EXTRA_PATH replaces the usual tool folders added to PATH, JEVFISH_RETRY_SLEEP sets
# the pause between install attempts.
set -u -o pipefail

ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
JF="$ROOT/jevfish"
STATE="${JEVFISH_HOME:-$HOME/Library/Application Support/JevFish}"
LOGS="$HOME/Library/Logs/JevFish"
LOG="$LOGS/launcher.log"
PORTS="${JEVFISH_PORTS:-5055 5056 5057 5058 5059 5060 5061 5062 5063 5064}"
# Finder starts apps with a bare PATH, so add the usual places uv lives.
export PATH="$STATE/bin:$PATH${JEVFISH_EXTRA_PATH-:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin}"

mkdir -p "$STATE" "$LOGS"
exec >>"$LOG" 2>&1
echo "== $(date '+%Y-%m-%d %H:%M:%S') start from $ROOT"

gui() { [ "${JEVFISH_NO_GUI:-}" != "1" ]; }

tell() {  # a dialog that closes itself, so setup carries on behind it
  echo "note: $1"
  gui && osascript -e "display dialog \"$1\" with title \"JevFish\" buttons {\"OK\"} default button \"OK\" giving up after 30" >/dev/null 2>&1 &
}

fail() {
  echo "error: $1"
  if gui; then
    choice=$(osascript -e "button returned of (display alert \"JevFish could not start\" message \"$1\" as critical buttons {\"Show log\", \"OK\"} default button \"OK\")" 2>/dev/null)
    [ "$choice" = "Show log" ] && open -a Console "$LOG"
  fi
  exit 1
}

running_port() {  # prints the port of a JevFish already running here
  for p in $PORTS; do
    if curl -fsS --max-time 1 "http://127.0.0.1:$p/api/health" 2>/dev/null | grep -q '"app": *"jevfish"'; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

open_app() {
  echo "ready http://127.0.0.1:$1/"
  printf '%s\n' "$ROOT" >"$STATE/repo-path"
  [ "${JEVFISH_NO_OPEN:-}" = "1" ] || open "http://127.0.0.1:$1/"
  exit 0
}

[ -f "$JF/pyproject.toml" ] || fail "The JevFish files are missing from $ROOT. Download JevFish again."

if port=$(running_port); then
  echo "already running on $port"
  open_app "$port"
fi

# 1. uv, the tool that installs Python and the packages
UV="$(command -v uv || true)"
if [ -z "$UV" ]; then
  tell "Installing uv, a small tool JevFish needs. This happens once."
  curl -LsSf "${JEVFISH_UV_INSTALLER:-https://astral.sh/uv/install.sh}" |
    env UV_INSTALL_DIR="$STATE/bin" UV_NO_MODIFY_PATH=1 sh ||
    fail "Could not install uv. Check the internet connection and open JevFish again."
  UV="$STATE/bin/uv"
  [ -x "$UV" ] || fail "uv did not install. The log has the details."
fi
echo "uv: $UV"

# 2. Python and the packages, again only when the lock file changed
STAMP="$JF/.venv/.jevfish-synced"
if [ ! -x "$JF/.venv/bin/jevfish" ] || [ ! -f "$STAMP" ] || [ "$JF/uv.lock" -nt "$STAMP" ] || [ "$JF/pyproject.toml" -nt "$STAMP" ]; then
  if [ -x "$JF/.venv/bin/jevfish" ]; then
    tell "Updating JevFish. Your browser opens when it is ready."
  else
    tell "Setting up JevFish. The first start downloads about 1 GB and takes around 5 minutes. Your browser opens when it is ready."
  fi
  # About 150 downloads: retry, since uv keeps whatever finished and a blip should not end setup.
  synced=""
  for attempt in 1 2 3; do
    if (cd "$JF" && UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-120}" "$UV" sync --frozen); then
      synced=1
      break
    fi
    echo "package install attempt $attempt failed"
    sleep "${JEVFISH_RETRY_SLEEP:-5}"
  done
  [ -n "$synced" ] || fail "Installing the Python packages failed. Check the internet connection and open JevFish again."
  touch "$STAMP"
fi

# 3. The web app ships built. Rebuild only if someone deleted it and Node is around.
if [ ! -f "$JF/web/dist/index.html" ]; then
  command -v npm >/dev/null || fail "The web app is missing from jevfish/web/dist. Download JevFish again."
  (cd "$JF/web" && npm install && npm run build) || fail "Building the web app failed."
fi

# 4. Start on the first free port and wait for it
port=""
for p in $PORTS; do
  if ! nc -z 127.0.0.1 "$p" >/dev/null 2>&1; then
    port="$p"
    break
  fi
done
[ -n "$port" ] || fail "Ports $PORTS are all in use. Close whatever is using them and open JevFish again."
echo "starting on $port"
(cd "$JF" && nohup "$JF/.venv/bin/jevfish" serve --port "$port" >>"$LOGS/server.log" 2>&1 &)
for _ in $(seq 1 240); do
  if curl -fsS --max-time 1 "http://127.0.0.1:$port/api/health" 2>/dev/null | grep -q '"app": *"jevfish"'; then
    open_app "$port"
  fi
  sleep 0.5
done
fail "JevFish did not start within two minutes. The log has the details."
