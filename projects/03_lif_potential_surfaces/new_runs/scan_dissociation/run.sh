#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

"$ROOT/new_runs/run_new.sh" --one scan_dissociation/lif_dissociation_scan.inp
