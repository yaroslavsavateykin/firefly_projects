#!/bin/bash
NP=4
FF=$HOME/firefly_projects/shared/firefly/8.2.0/firefly820
EX=$HOME/firefly_projects/shared/firefly/8.2.0
BASIS=$HOME/firefly_projects/shared/basis_sets/lif_aug-cc-pVDZ.lib
WORKDIR=$HOME/firefly_projects/projects/03_lif_potential_surfaces/extended_scan

INP=$WORKDIR/lif_coarse.inp
OUT=$WORKDIR/lif_coarse.out
TMP=/tmp/firefly_lif_coarse_$$
PROCGRP=/tmp/firefly_lif_coarse_pg_$$

# Increase shared memory for CI
export P4_GLOBMEMSIZE=$((512 * 1024 * 1024))  # 512 MB

printf "local %d\n" "$((NP - 1))" > "$PROCGRP"
rm -f "$OUT"
echo "Running LiF coarse scan (4 states, R=1.0-9.0 A)..."
"$FF" -r -f -i "$INP" -o "$OUT" -p -stdext -ex "$EX" -b "$BASIS" -t "$TMP" -p4pg "$PROCGRP"
STATUS=$?
rm -f "$PROCGRP"
echo "Done, status=$STATUS"
