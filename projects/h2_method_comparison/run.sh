#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
FF=${FF:-"$ROOT/../../shared/firefly/8.2.0/firefly820"}
EX=${EX:-"$(dirname "$FF")"}
NP=${NP:-8}
TMP_BASE=${TMP_BASE:-"/tmp"}

inputs=(
    "inputs/h2_rhf_surface.inp"
    "inputs/h2_uhf_plain_surface.inp"
    "inputs/h2_uhf_mix_surface.inp"
    "inputs/h2_mp2_surface.inp"
    "inputs/h2_ump2_surface.inp"
    "inputs/h2_fci_surface.inp"
    "inputs/h2_ump2_mix_surface.inp"
)

if [[ ! -x "$FF" ]]; then
    echo "Firefly executable is not executable: $FF" >&2
    echo "Set FF=/path/to/firefly820 if needed." >&2
    exit 1
fi

mkdir -p outputs

for inp in "${inputs[@]}"; do
    if [[ ! -f "$inp" ]]; then
        echo "Missing $inp. Run: python3 make_inputs.py" >&2
        exit 1
    fi

    base=$(basename "$inp" .inp)
    out="outputs/${base}.out"

    if [[ -f "$out" ]] && grep -q "EXECUTION OF FIREFLY TERMINATED NORMALLY" "$out"; then
        echo "Skipping completed $out"
        continue
    fi

    if [[ -f "$out" ]]; then
        echo "Overwriting incomplete $out"
    fi

    tmp="${TMP_BASE}/firefly_${USER:-user}_${base}_$$"
    procgrp="${TMP_BASE}/firefly_${USER:-user}_${base}_procgrp_$$"
    printf "local %d\n" "$((NP - 1))" > "$procgrp"

    echo "Running $inp -> $out on NP=$NP"
    set +e
    "$FF" -r -f -i "$inp" -o "$out" -p -stdext -ex "$EX" -t "$tmp" -p4pg "$procgrp" >/dev/null 2>&1
    status=$?
    set -e

    rm -f "$procgrp"
    rm -f "${base}.dat" "outputs/${base}.dat"

    if [[ $status -ne 0 ]]; then
        echo "Firefly returned non-zero status for $inp: $status" >&2
        exit "$status"
    fi
done

echo "Finished Firefly SURFACE jobs sequentially."
