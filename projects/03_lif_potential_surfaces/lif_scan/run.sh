#!/bin/bash

NP=10
FF=$PWD/../../../shared/firefly/8.2.0/firefly820
EX=$PWD/../../../shared/firefly/8.2.0
BASIS=$PWD/../../../shared/basis_sets/lif_aug-cc-pVDZ.lib
INP=LiF_CI.inp
OUT=LiF_CI.out
TMP=/tmp/firefly_${USER}_${INP%.inp}_$$
PROCGRP=/tmp/firefly_${USER}_${INP%.inp}_procgrp_$$

# Increase P4 shared memory for large CI calculations
export P4_GLOBMEMSIZE=$((256 * 1024 * 1024))  # 256 MB

printf "local %d\n" "$((NP - 1))" > "$PROCGRP"
rm -f "$OUT"
echo "Running input $INP"
"$FF" -r -f -i "$INP" -o "$OUT" -p -stdext -ex "$EX" -b "$BASIS" -t "$TMP" -p4pg "$PROCGRP" >/dev/null 2>&1
STATUS=$?
rm -f "$PROCGRP"
[ "$STATUS" -eq 0 ] || exit "$STATUS"
