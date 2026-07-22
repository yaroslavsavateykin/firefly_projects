#!/bin/bash
set -euo pipefail

MAX_PARALLEL=${MAX_PARALLEL:-2}
NPROC_PER_JOB=${NPROC_PER_JOB:-8}
P4_GLOBMEMSIZE_BYTES=${P4_GLOBMEMSIZE_BYTES:-1073741824}
FIREFLY_BIN=${FIREFLY_BIN:-"/home/yaroslav/firefly_projects/shared/firefly/8.2.0/firefly820"}
FIREFLY_EX=${FIREFLY_EX:-"/home/yaroslav/firefly_projects/shared/firefly/8.2.0"}
BASIS_FILE=${BASIS_FILE:-"/home/yaroslav/firefly_projects/shared/basis_sets/lif_aug-cc-pVDZ.lib"}
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
LOG_DIR="$ROOT/new_runs/logs"
mkdir -p "$LOG_DIR"

INPUTS=(
  "$SCRIPT_DIR/lif_ci_R5_50.inp"
  "$SCRIPT_DIR/lif_ci_R5_85.inp"
  "$SCRIPT_DIR/lif_ci_R6_50.inp"
)

mem_words=200000000
mem_bytes=$((mem_words * 8))
mem_gib=$(awk -v b="$mem_bytes" 'BEGIN {printf "%.2f", b/1024/1024/1024}')
p4_gib=$(awk -v b="$P4_GLOBMEMSIZE_BYTES" 'BEGIN {printf "%.2f", b/1024/1024/1024}')
per_job_gib=$(awk -v a="$mem_bytes" -v b="$P4_GLOBMEMSIZE_BYTES" 'BEGIN {printf "%.2f", (a+b)/1024/1024/1024}')
total_cores=$((MAX_PARALLEL * NPROC_PER_JOB))
available_cores=$(nproc 2>/dev/null || echo 1)
available_mem_kb=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)
available_mem_gib=$(awk -v kb="$available_mem_kb" 'BEGIN {printf "%.2f", kb/1024/1024}')

echo "Preflight for LiF CI-coefficient single-point runs"
echo "  MAX_PARALLEL=$MAX_PARALLEL"
echo "  NPROC_PER_JOB=$NPROC_PER_JOB"
echo "  Total requested cores=$total_cores; available logical cores=$available_cores"
echo "  Firefly MEMORY per job=$mem_words words (~$mem_gib GiB)"
echo "  P4_GLOBMEMSIZE per job=$P4_GLOBMEMSIZE_BYTES bytes (~$p4_gib GiB)"
echo "  Approx configured memory per job=$per_job_gib GiB"
echo "  Available memory from /proc/meminfo=$available_mem_gib GiB"
echo "  FIREFLY_BIN=$FIREFLY_BIN"
echo "  BASIS_FILE=$BASIS_FILE"

[[ -x "$FIREFLY_BIN" ]] || { echo "ERROR: FIREFLY_BIN is not executable: $FIREFLY_BIN" >&2; exit 1; }
[[ -d "$FIREFLY_EX" ]] || { echo "ERROR: FIREFLY_EX does not exist: $FIREFLY_EX" >&2; exit 1; }
[[ -f "$BASIS_FILE" ]] || { echo "ERROR: BASIS_FILE does not exist: $BASIS_FILE" >&2; exit 1; }
(( total_cores <= available_cores )) || { echo "ERROR: requested more cores than available." >&2; exit 1; }

echo ""
echo "Commands to run:"
for inp in "${INPUTS[@]}"; do
  out="${inp%.inp}.out"
  log="$LOG_DIR/$(basename "${inp%.inp}").log"
  case "$out" in
    "$ROOT/new_runs/"*) ;;
    *) echo "ERROR: output is outside new_runs: $out" >&2; exit 1 ;;
  esac
  echo "  cd $SCRIPT_DIR && P4_GLOBMEMSIZE=$P4_GLOBMEMSIZE_BYTES \"$FIREFLY_BIN\" -r -f -i \"$(basename "$inp")\" -o \"$out\" -p -stdext -ex \"$FIREFLY_EX\" -b \"$BASIS_FILE\" -t \"/tmp/firefly_${USER}_$(basename "${inp%.inp}")_\\$\\$\" -p4pg \"/tmp/firefly_${USER}_$(basename "${inp%.inp}")_pg_\\$\\$\" > \"$log\" 2>&1"
done
echo ""

if (( DRY_RUN == 1 )); then
  echo "Dry run only; no Firefly calculations were launched."
  exit 0
fi

run_one() {
  local inp=$1
  local name out log procgrp tmp status
  name=$(basename "${inp%.inp}")
  out="${inp%.inp}.out"
  log="$LOG_DIR/${name}.log"
  procgrp="/tmp/firefly_${USER}_${name}_pg_$$"
  tmp="/tmp/firefly_${USER}_${name}_$$"

  if [[ -f "$out" ]] && grep -q "EXECUTION OF FIREFLY TERMINATED NORMALLY" "$out"; then
    echo "SKIP $inp (already terminated normally)"
    return 0
  fi

  printf "local %d\n" "$((NPROC_PER_JOB - 1))" > "$procgrp"
  echo "RUN  $inp"
  (
    cd "$SCRIPT_DIR"
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
for inp in "${INPUTS[@]}"; do
  run_one "$inp" &
  active=$((active + 1))
  if (( active >= MAX_PARALLEL )); then
    if ! wait -n; then fail=1; fi
    active=$((active - 1))
  fi
done
while (( active > 0 )); do
  if ! wait -n; then fail=1; fi
  active=$((active - 1))
done

python3 "$ROOT/analysis/process_lif_outputs.py"
exit "$fail"
