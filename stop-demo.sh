#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for name in admin site backend; do
  pidfile="$ROOT/.run/$name.pid"
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    # Guard against a stale PID file pointing at an unrelated process.
    if [[ "$pid" =~ ^[0-9]+$ ]] && [ -r "/proc/$pid/cmdline" ]; then
      command=$(tr '\0' ' ' < "/proc/$pid/cmdline")
      case "$command" in
        *"$ROOT/public_server.py"*|*"$ROOT/admin_server.py"*|*"http.server 8188"*|*"website_chatbot/backend/app.py --host 127.0.0.1 --port 8199"*)
          kill "$pid" 2>/dev/null || true
          for _ in $(seq 1 40); do
            if ! kill -0 "$pid" 2>/dev/null; then break; fi
            if [ -r "/proc/$pid/stat" ] && [ "$(awk '{print $3}' "/proc/$pid/stat")" = Z ]; then break; fi
            sleep 0.05
          done
          ;;
      esac
    fi
    rm -f "$pidfile"
  fi
done
echo "Class 3 demo processes stopped."
