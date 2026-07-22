#!/bin/bash

NP=10
FF=$PWD/../../../shared/firefly/8.2.0/firefly820
EX=$PWD/../../../shared/firefly/8.2.0
INP=ch4_canonical_sto3g.inp
OUT=ch4_canonical_sto3g.out
TMP=/tmp/firefly_${USER}_${INP%.inp}_$$
PROCGRP=/tmp/firefly_${USER}_${INP%.inp}_procgrp_$$

printf "local %d\n" "$((NP - 1))" > "$PROCGRP"
rm -f "$OUT"
echo "Running input $INP"
"$FF" -r -f -i "$INP" -o "$OUT" -p -stdext -ex "$EX" -t "$TMP" -p4pg "$PROCGRP" >/dev/null 2>&1
STATUS=$?
rm -f "$PROCGRP"
[ "$STATUS" -eq 0 ] || exit "$STATUS"
