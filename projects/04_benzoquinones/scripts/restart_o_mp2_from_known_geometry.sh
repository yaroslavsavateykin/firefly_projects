#!/bin/bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC="$ROOT/o_bq/03_cis_opt_geometry/o_bq_cis_opt_geometry.inp"
DIR="$ROOT/o_bq/01_mp2_opt"
INP="$DIR/o_bq_mp2_opt.inp"

if [ ! -f "$SRC" ]; then
  echo "Missing source geometry input: $SRC" >&2
  exit 1
fi

awk '
  BEGIN { data=0 }
  /^[[:space:]]*\$DATA/ { data=1; print " $DATA"; getline; print "o_bq MP2 custom-basis geometry optimization restart from known MP2 geometry"; next }
  data { print }
' "$SRC" > "$DIR/.data_restart.tmp"

cat > "$INP" <<'EOF'
 $CONTRL SCFTYP=RHF RUNTYP=OPTIMIZE ICHARG=0 MULT=1 MPLEVL=2 EXETYP=RUN
      INTTYP=HONDO ICUT=13 ITOL=30 D5=.T. MAXIT=200 GENCON=.F. WIDE=1 FSTINT=.T.
 $END
 $SYSTEM TIMLIM=60000 MWORDS=200 MASMEM=200000000 MXBCST=-1 KDIAG=0 NOJAC=1 $END
 $MOORTH NOSTF=.T. NOZERO=.T. SYMS=.T. SYMDEN=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 $END
 $GUESS GUESS=HUCKEL $END
 $STATPT METHOD=GDIIS OPTTOL=1D-04 NSTEP=100 HSSEND=.F. UPHESS=BFGS ITBMAT=300
      TRMAX=0.01
 $END
 $SCF DIRSCF=.T. FDIFF=.F. DIIS=.T. DAMP=.T. SHIFT=.T. SOSCF=.F. $END
 $MP2 METHOD=1 $END
EOF

cat "$DIR/.data_restart.tmp" >> "$INP"
rm -f "$DIR/.data_restart.tmp"

