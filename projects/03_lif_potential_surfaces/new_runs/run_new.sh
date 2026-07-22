#!/bin/bash
set -euo pipefail

MAX_PARALLEL=${MAX_PARALLEL:-2}
NPROC_PER_JOB=${NPROC_PER_JOB:-8}
P4_GLOBMEMSIZE_BYTES=${P4_GLOBMEMSIZE_BYTES:-1073741824}
FIREFLY_BIN=${FIREFLY_BIN:-"/home/yaroslav/firefly_projects/shared/firefly/8.2.0/firefly820"}
FIREFLY_EX=${FIREFLY_EX:-"/home/yaroslav/firefly_projects/shared/firefly/8.2.0"}
BASIS_FILE=${BASIS_FILE:-"/home/yaroslav/firefly_projects/shared/basis_sets/lif_aug-cc-pVDZ.lib"}
RUN_ANALYSIS=${RUN_ANALYSIS:-1}
DRY_RUN=0

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
LOG_DIR="$ROOT/new_runs/logs"
mkdir -p "$LOG_DIR"

INPUTS=(
  "scan_selected/lif_selected_scan.inp"
  "scan_crossing/lif_crossing_scan.inp"
  "scan_dissociation/lif_dissociation_scan.inp"
)

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

if [[ "${1:-}" == "--one" ]]; then
  shift
  [[ $# -eq 1 ]] || { echo "Usage: $0 --one relative/input.inp" >&2; exit 2; }
  INPUTS=("$1")
  MAX_PARALLEL=1
fi

mem_words=200000000
mem_bytes=$((mem_words * 8))
mem_gib=$(awk -v b="$mem_bytes" 'BEGIN {printf "%.2f", b/1024/1024/1024}')
p4_gib=$(awk -v b="$P4_GLOBMEMSIZE_BYTES" 'BEGIN {printf "%.2f", b/1024/1024/1024}')
per_job_gib=$(awk -v a="$mem_bytes" -v b="$P4_GLOBMEMSIZE_BYTES" 'BEGIN {printf "%.2f", (a+b)/1024/1024/1024}')
total_cores=$((MAX_PARALLEL * NPROC_PER_JOB))
total_mem_gib=$(awk -v p="$per_job_gib" -v n="$MAX_PARALLEL" 'BEGIN {printf "%.2f", p*n}')
available_cores=$(nproc 2>/dev/null || echo 1)
available_mem_kb=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)
available_mem_gib=$(awk -v kb="$available_mem_kb" 'BEGIN {printf "%.2f", kb/1024/1024}')

echo "Preflight for LiF full CI runs"
echo "  MAX_PARALLEL=$MAX_PARALLEL"
echo "  NPROC_PER_JOB=$NPROC_PER_JOB"
echo "  Total requested cores=$total_cores; available logical cores=$available_cores"
echo "  Firefly MEMORY per job=$mem_words words (~$mem_gib GiB)"
echo "  P4_GLOBMEMSIZE per job=$P4_GLOBMEMSIZE_BYTES bytes (~$p4_gib GiB)"
echo "  Approx configured memory per job=$per_job_gib GiB; for active jobs=$total_mem_gib GiB"
echo "  Available memory from /proc/meminfo=$available_mem_gib GiB"
echo "  FIREFLY_BIN=$FIREFLY_BIN"
echo "  BASIS_FILE=$BASIS_FILE"

[[ -x "$FIREFLY_BIN" ]] || { echo "ERROR: FIREFLY_BIN is not executable: $FIREFLY_BIN" >&2; exit 1; }
[[ -d "$FIREFLY_EX" ]] || { echo "ERROR: FIREFLY_EX does not exist: $FIREFLY_EX" >&2; exit 1; }
[[ -f "$BASIS_FILE" ]] || { echo "ERROR: BASIS_FILE does not exist: $BASIS_FILE" >&2; exit 1; }

if (( total_cores > available_cores )); then
  echo "ERROR: requested $total_cores cores, but only $available_cores logical cores are available." >&2
  echo "Set MAX_PARALLEL=1 or lower NPROC_PER_JOB before launching." >&2
  exit 1
fi

if (( available_mem_kb > 0 )); then
  required_kb=$(awk -v gib="$total_mem_gib" 'BEGIN {printf "%.0f", gib*1024*1024}')
  if (( required_kb > available_mem_kb )); then
    echo "ERROR: configured active-job memory exceeds MemAvailable." >&2
    echo "Set MAX_PARALLEL=1 or lower P4_GLOBMEMSIZE_BYTES before launching." >&2
    exit 1
  fi
fi

declare -a JOB_INPUTS=()
declare -a JOB_OUTPUTS=()
declare -a JOB_LOGS=()

for rel_inp in "${INPUTS[@]}"; do
  inp="$ROOT/new_runs/$rel_inp"
  [[ -f "$inp" ]] || { echo "ERROR: input not found: $inp" >&2; exit 1; }

  out="${inp%.inp}.out"
  log="$LOG_DIR/$(basename "${inp%.inp}").log"

  case "$out" in
    "$ROOT/new_runs/"*) ;;
    *) echo "ERROR: output is outside new_runs: $out" >&2; exit 1 ;;
  esac

  if [[ "$out" == "$ROOT/lif_scan/"* || "$out" == "$ROOT/extended_scan/"* || "$out" == "$ROOT/fine_crossing/"* ]]; then
    echo "ERROR: output overlaps an old calculation directory: $out" >&2
    exit 1
  fi

  JOB_INPUTS+=("$inp")
  JOB_OUTPUTS+=("$out")
  JOB_LOGS+=("$log")
done

echo ""
echo "Commands to run:"
for i in "${!JOB_INPUTS[@]}"; do
  inp="${JOB_INPUTS[$i]}"
  out="${JOB_OUTPUTS[$i]}"
  log="${JOB_LOGS[$i]}"
  tmp="/tmp/firefly_${USER}_$(basename "${inp%.inp}")_\$\$"
  pg="/tmp/firefly_${USER}_$(basename "${inp%.inp}")_pg_\$\$"
  echo "  cd $(dirname "$inp") && P4_GLOBMEMSIZE=$P4_GLOBMEMSIZE_BYTES \"$FIREFLY_BIN\" -r -f -i \"$(basename "$inp")\" -o \"$out\" -p -stdext -ex \"$FIREFLY_EX\" -b \"$BASIS_FILE\" -t \"$tmp\" -p4pg \"$pg\" > \"$log\" 2>&1"
done
echo ""

if (( DRY_RUN == 1 )); then
  echo "Dry run only; no Firefly calculations were launched."
  exit 0
fi

run_one() {
  local inp=$1
  local out=$2
  local log=$3
  local name procgrp tmp status

  name=$(basename "${inp%.inp}")
  procgrp="/tmp/firefly_${USER}_${name}_pg_$$"
  tmp="/tmp/firefly_${USER}_${name}_$$"

  if [[ -f "$out" ]] && grep -q "EXECUTION OF FIREFLY TERMINATED NORMALLY" "$out"; then
    echo "SKIP $inp (already terminated normally)"
    return 0
  fi

  printf "local %d\n" "$((NPROC_PER_JOB - 1))" > "$procgrp"
  echo "RUN  $inp"
  (
    cd "$(dirname "$inp")"
    export P4_GLOBMEMSIZE="$P4_GLOBMEMSIZE_BYTES"
    "$FIREFLY_BIN" -r -f -i "$(basename "$inp")" -o "$out" -p -stdext -ex "$FIREFLY_EX" -b "$BASIS_FILE" -t "$tmp" -p4pg "$procgrp"
  ) > "$log" 2>&1
  status=$?
  rm -f "$procgrp"
  echo "DONE $inp status=$status log=$log"
  return "$status"
}

active=0
fail=0
for i in "${!JOB_INPUTS[@]}"; do
  run_one "${JOB_INPUTS[$i]}" "${JOB_OUTPUTS[$i]}" "${JOB_LOGS[$i]}" &
  active=$((active + 1))
  if (( active >= MAX_PARALLEL )); then
    if ! wait -n; then
      fail=1
    fi
    active=$((active - 1))
  fi
done

while (( active > 0 )); do
  if ! wait -n; then
    fail=1
  fi
  active=$((active - 1))
done

if (( RUN_ANALYSIS == 1 )); then
  echo "Running analysis/process_lif_outputs.py"
  python3 "$ROOT/analysis/process_lif_outputs.py"
fi

exit "$fail"
