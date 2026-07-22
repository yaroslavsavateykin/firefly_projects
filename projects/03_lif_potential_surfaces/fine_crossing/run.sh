#!/bin/bash
# Run LiF fine crossing scan: 24 individual single-point CI/aug-cc-pVDZ calculations
# R = 5.5 to 7.8 Ang, 0.1 Ang steps, NSTATE=3 (S0, S1, S2)

NP=10
FF=$PWD/../../../shared/firefly/8.2.0/firefly820
EX=$PWD/../../../shared/firefly/8.2.0
BASIS=$PWD/../../../shared/basis_sets/lif_aug-cc-pVDZ.lib

export P4_GLOBMEMSIZE=$((256 * 1024 * 1024))  # 256 MB shared memory

TOTAL=0
DONE=0
FAILED=0

for INP in lif_fine_*.inp; do
    OUT="${INP%.inp}.out"
    TMP="/tmp/firefly_${USER}_${INP%.inp}_$$"
    PROCGRP="/tmp/firefly_${USER}_${INP%.inp}_pg_$$"

    TOTAL=$((TOTAL + 1))

    if [ -f "$OUT" ] && grep -q "ALDET CI" "$OUT" 2>/dev/null; then
        echo "SKIP  $INP  (already done)"
        DONE=$((DONE + 1))
        continue
    fi

    printf "local %d\n" "$((NP - 1))" > "$PROCGRP"
    echo "RUN   $INP"
    "$FF" -r -f -i "$INP" -o "$OUT" -p -stdext -ex "$EX" -b "$BASIS" -t "$TMP" -p4pg "$PROCGRP" >/dev/null 2>&1
    STATUS=$?
    rm -f "$PROCGRP"

    if [ "$STATUS" -eq 0 ]; then
        DONE=$((DONE + 1))
        echo "      done (status=0)"
    else
        FAILED=$((FAILED + 1))
        echo "      FAILED (status=$STATUS)"
    fi
done

echo ""
echo "Summary: $DONE/$TOTAL done, $FAILED failed"
