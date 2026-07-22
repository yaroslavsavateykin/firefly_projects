#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

"$ROOT/new_runs/run_new.sh" --one scan_crossing/lif_crossing_scan.inp
