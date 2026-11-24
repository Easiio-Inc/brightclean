#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"$ROOT/stop-demo.sh" || true
rm -f "$ROOT/data/class3-demo-crm.db" "$ROOT/data/class3-demo-crm.db-shm" "$ROOT/data/class3-demo-crm.db-wal"
rm -f "$ROOT/.run/"*.log "$ROOT/.run/"*.pid 2>/dev/null || true
python3 "$ROOT/scripts/seed_demo.py"
echo "Demo data reset. Run ./start-demo.sh to start with a clean CRM."
