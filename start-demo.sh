#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${BRIGHTCLEAN_PYTHON:-python3}"
mkdir -p "$ROOT/.run" "$ROOT/data"

# Never reuse an old unrestricted chatbot or repository-wide static server.
# Stop only processes recorded as belonging to this demo.
"$ROOT/stop-demo.sh"
for port in 8188 8199 8200; do
  if "$PYTHON" - "$port" <<'PY'
import socket,sys
with socket.socket() as s:
    sys.exit(0 if s.connect_ex(('127.0.0.1',int(sys.argv[1]))) == 0 else 1)
PY
  then
    echo "Port $port is already in use. Stop its owner before starting the secure demo." >&2
    exit 1
  fi
done

cleanup_failure() { "$ROOT/stop-demo.sh"; }
trap cleanup_failure ERR
for service in website chatbot admin; do
  case "$service" in
    website) script=("$ROOT/public_server.py" website);;
    chatbot) script=("$ROOT/public_server.py" chatbot);;
    admin) script=("$ROOT/admin_server.py");;
  esac
  name="$service"
  [ "$service" != website ] || name=site
  [ "$service" != chatbot ] || name=backend
  nohup "$PYTHON" "${script[@]}" >"$ROOT/.run/$name.log" 2>&1 &
  echo $! > "$ROOT/.run/$name.pid"
done
for endpoint in '8188/' '8199/health' '8200/'; do
  ready=false
  for _ in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:$endpoint" >/dev/null 2>&1; then ready=true; break; fi
    sleep 0.25
  done
  if [ "$ready" != true ]; then
    echo "Startup failed at $endpoint; inspect .run/*.log" >&2
    cleanup_failure
    exit 1
  fi
done
trap - ERR
printf '\nClass 3 demo is ready:\n  Website: http://127.0.0.1:8188/\n  Chatbot: http://127.0.0.1:8199/health\n  Admin:   http://127.0.0.1:8200/\n\n'
