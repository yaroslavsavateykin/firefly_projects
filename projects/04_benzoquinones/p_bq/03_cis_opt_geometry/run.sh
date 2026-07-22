#!/bin/bash
set -e

NP=${NP:-6}
FF=$PWD/../../../../shared/firefly/8.2.0/firefly820
EX=$PWD/../../../../shared/firefly/8.2.0
INP=p_bq_cis_opt_geometry.inp
OUT=p_bq_cis_opt_geometry.out
TMP=/tmp/firefly_${USER}_${INP%.inp}_$$
PROCGRP=/tmp/firefly_${USER}_${INP%.inp}_procgrp_$$

printf "local %d\n" "$((NP - 1))" > "$PROCGRP"
rm -f "$OUT"
echo "Running input $INP on $NP ranks"
"$FF" -r -f -i "$INP" -o "$OUT" -p -stdext -ex "$EX" -t "$TMP" -p4pg "$PROCGRP"
STATUS=$?
rm -f "$PROCGRP"
exit "$STATUS"
