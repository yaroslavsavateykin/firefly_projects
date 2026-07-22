#!/bin/bash
set -e

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 input.inp" >&2
  exit 2
fi

NP=${NP:-6}
INP=$1
OUT=${INP%.inp}.out
FF=$PWD/../../../shared/firefly/8.2.0/firefly820
EX=$PWD/../../../shared/firefly/8.2.0
TMP=/tmp/firefly_${USER}_${INP%.inp}_$$
PROCGRP=/tmp/firefly_${USER}_${INP%.inp}_procgrp_$$

printf "local %d\n" "$((NP - 1))" > "$PROCGRP"
rm -f "$OUT"
echo "Running input $INP on $NP ranks"
"$FF" -r -f -i "$INP" -o "$OUT" -p -stdext -ex "$EX" -t "$TMP" -p4pg "$PROCGRP"
STATUS=$?
rm -f "$PROCGRP"
exit "$STATUS"
