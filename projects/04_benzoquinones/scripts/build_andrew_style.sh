#!/bin/bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SOURCE_ANDREW="$ROOT/basis_templates/quinone_MP2.inp"
SOURCE_XMC="$ROOT/basis_templates/quinone_XMCQDPT2.inp"

[ "$#" -ge 1 ] || { echo "Usage: $0 p_bq|o_bq [--from-mp2]" >&2; exit 2; }
ISO=$1
[ "$ISO" = "p_bq" ] || [ "$ISO" = "o_bq" ] || { echo "Unknown isomer: $ISO" >&2; exit 2; }
FROM_MP2=0
[ "${2:-}" = "--from-mp2" ] && FROM_MP2=1

extract_basis() {
  awk -v element="$1" -v z="$2" '
    $1 == element && $2 == z { take=1; next }
    take && NF == 0 { exit }
    take { print }
  ' "$SOURCE_ANDREW"
}

C_BASIS=$(extract_basis C 6.0)
O_BASIS=$(extract_basis O 8.0)
H_BASIS=$(extract_basis H 1.0)

initial_geometry() {
  if [ "$ISO" = "p_bq" ]; then
    cat <<'EOF'
C 6.0 0.0000000000 1.4000000000 0.0000000000
C 6.0 1.2124355650 0.7000000000 0.0000000000
C 6.0 1.2124355650 -0.7000000000 0.0000000000
C 6.0 0.0000000000 -1.4000000000 0.0000000000
C 6.0 -1.2124355650 -0.7000000000 0.0000000000
C 6.0 -1.2124355650 0.7000000000 0.0000000000
O 8.0 0.0000000000 2.6200000000 0.0000000000
O 8.0 0.0000000000 -2.6200000000 0.0000000000
H 1.0 2.1500000000 1.2410000000 0.0000000000
H 1.0 2.1500000000 -1.2410000000 0.0000000000
H 1.0 -2.1500000000 -1.2410000000 0.0000000000
H 1.0 -2.1500000000 1.2410000000 0.0000000000
EOF
  else
    cat <<'EOF'
C 6.0 0.0000000000 1.4000000000 0.0000000000
C 6.0 1.2124355650 0.7000000000 0.0000000000
C 6.0 1.2124355650 -0.7000000000 0.0000000000
C 6.0 0.0000000000 -1.4000000000 0.0000000000
C 6.0 -1.2124355650 -0.7000000000 0.0000000000
C 6.0 -1.2124355650 0.7000000000 0.0000000000
O 8.0 0.0000000000 2.6200000000 0.0000000000
O 8.0 2.2685000000 1.3100000000 0.0000000000
H 1.0 2.1500000000 -1.2410000000 0.0000000000
H 1.0 0.0000000000 -2.4800000000 0.0000000000
H 1.0 -2.1500000000 -1.2410000000 0.0000000000
H 1.0 -2.1500000000 1.2410000000 0.0000000000
EOF
  fi
}

mp2_geometry() {
  local out="$ROOT/$ISO/01_mp2_opt/${ISO}_mp2_opt.out"
  grep -q "EQUILIBRIUM GEOMETRY LOCATED" "$out" || {
    echo "ERROR: $out has no converged MP2 geometry" >&2
    exit 1
  }
  awk '
    /COORDINATES OF ALL ATOMS ARE \(ANGS\)/ { count=0; active=1; next }
    active && /^[[:space:]]*[A-Z][a-z]?[[:space:]]+[0-9]+\./ {
      count++
      line[count]=sprintf("%s %.1f %.10f %.10f %.10f", $1, $2, $3, $4, $5)
    }
    END {
      if (count == 0) exit 2
      for (i=1; i<=count; i++) print line[i]
    }
  ' "$out"
}

write_data_section() {
  local title="$1"
  local geometry="$2"
  echo ' $DATA'
  echo "$title"
  echo "C1"
  while read -r sym z x y zc; do
    [ -n "$sym" ] || continue
    printf "%-2s %7.1f %16.10f %16.10f %16.10f\n" "$sym" "$z" "$x" "$y" "$zc"
    case "$sym" in
      C) printf "%s\n\n" "$C_BASIS" ;;
      O) printf "%s\n\n" "$O_BASIS" ;;
      H) printf "%s\n\n" "$H_BASIS" ;;
      *) echo "Unknown atom: $sym" >&2; exit 3 ;;
    esac
  done <<< "$geometry"
  echo ' $END'
}

write_run_sh() {
  local dir="$1"
  local inp="$2"
  local out="$3"
  mkdir -p "$dir"
  cat > "$dir/run.sh" <<EOF
#!/bin/bash
set -e

NP=\${NP:-6}
FF=\$PWD/../../../../shared/firefly/8.2.0/firefly820
EX=\$PWD/../../../../shared/firefly/8.2.0
INP=$inp
OUT=$out
TMP=/tmp/firefly_\${USER}_\${INP%.inp}_\$\$
PROCGRP=/tmp/firefly_\${USER}_\${INP%.inp}_procgrp_\$\$

printf "local %d\n" "\$((NP - 1))" > "\$PROCGRP"
rm -f "\$OUT"
echo "Running input \$INP on \$NP ranks"
"\$FF" -r -f -i "\$INP" -o "\$OUT" -p -stdext -ex "\$EX" -t "\$TMP" -p4pg "\$PROCGRP"
STATUS=\$?
rm -f "\$PROCGRP"
exit "\$STATUS"
EOF
  chmod +x "$dir/run.sh"
}

write_mp2() {
  local dir="$ROOT/$ISO/01_mp2_opt"
  local inp="$dir/${ISO}_mp2_opt.inp"
  local geom
  local maxit=100
  local statpt_extra=""
  geom=$(initial_geometry)
  if [ "$ISO" = "o_bq" ]; then
    maxit=200
    statpt_extra="      TRMAX=0.05"
  fi
  mkdir -p "$dir"
  {
    cat <<EOF
 \$CONTRL SCFTYP=RHF RUNTYP=OPTIMIZE ICHARG=0 MULT=1 MPLEVL=2 EXETYP=RUN
      INTTYP=HONDO ICUT=13 ITOL=30 D5=.T. MAXIT=$maxit GENCON=.F. WIDE=1 FSTINT=.T.
 \$END
 \$SYSTEM TIMLIM=60000 MWORDS=200 MASMEM=200000000 MXBCST=-1 KDIAG=0 NOJAC=1 \$END
 \$MOORTH NOSTF=.T. NOZERO=.T. SYMS=.T. SYMDEN=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 \$END
 \$GUESS GUESS=HUCKEL \$END
 \$STATPT METHOD=GDIIS OPTTOL=1D-04 NSTEP=100 HSSEND=.F. UPHESS=BFGS ITBMAT=300
$statpt_extra
 \$END
 \$SCF DIRSCF=.T. FDIFF=.F. DIIS=.T. DAMP=.T. SHIFT=.T. SOSCF=.F. \$END
 \$MP2 METHOD=1 \$END
EOF
    write_data_section "$ISO MP2 custom-basis geometry optimization" "$geom"
  } > "$inp"
  write_run_sh "$dir" "${ISO}_mp2_opt.inp" "${ISO}_mp2_opt.out"
}

write_cis() {
  local stage="$1"
  local dir="$ROOT/$ISO/$stage"
  local inp out title geom
  mkdir -p "$dir"
  if [ "$stage" = "02_cis" ]; then
    inp="$dir/${ISO}_cis.inp"
    out="${ISO}_cis.out"
    title="$ISO CIS on starting geometry"
    geom=$(initial_geometry)
  else
    inp="$dir/${ISO}_cis_opt_geometry.inp"
    out="${ISO}_cis_opt_geometry.out"
    title="$ISO CIS single-point on MP2-optimized geometry"
    geom=$(mp2_geometry)
  fi
  {
    cat <<'EOF'
 $CONTRL SCFTYP=RHF RUNTYP=ENERGY ICHARG=0 MULT=1 CITYP=CIS EXETYP=RUN
      INTTYP=HONDO ICUT=13 ITOL=30 D5=.T. MAXIT=100 GENCON=.F. WIDE=1 FSTINT=.T.
 $END
 $SYSTEM TIMLIM=60000 MWORDS=200 MASMEM=200000000 MXBCST=-1 KDIAG=0 NOJAC=1 $END
 $MOORTH NOSTF=.T. NOZERO=.T. SYMS=.T. SYMDEN=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 $END
 $GUESS GUESS=HUCKEL $END
 $SCF DIRSCF=.T. FDIFF=.F. DIIS=.T. DAMP=.T. SHIFT=.T. SOSCF=.F. $END
 $CIS ISTATE=1 MULT=1 NSTATE=4 $END
EOF
    write_data_section "$title" "$geom"
  } > "$inp"
  write_run_sh "$dir" "$(basename "$inp")" "$out"
}

write_xmc() {
  local dir="$ROOT/$ISO/04_xmcqdpt2"
  local inp="$dir/${ISO}_xmcqdpt2.inp"
  local geom vec
  mkdir -p "$dir"
  if [ "$FROM_MP2" -eq 1 ]; then
    geom=$(mp2_geometry)
  else
    geom=$(initial_geometry)
  fi
  vec=$(awk '
    BEGIN { invec=0; block=""; last="" }
    /^[[:space:]]*\$VEC/ { invec=1; block=$0 ORS; next }
    invec {
      block = block $0 ORS
      if ($0 ~ /^[[:space:]]*\$END/) { last=block; invec=0 }
    }
    END {
      if (last == "") exit 3
      printf "%s", last
    }
  ' "$SOURCE_XMC")
  {
    cat <<'EOF'
 $CONTRL SCFTYP=MCSCF RUNTYP=ENERGY ICHARG=0 MULT=1 MPLEVL=2 EXETYP=RUN
      INTTYP=HONDO ICUT=13 ITOL=30 D5=.T. MAXIT=100 GENCON=.F. WIDE=1 FSTINT=.T.
 $END
 $SYSTEM TIMLIM=60000 MWORDS=200 MASMEM=200000000 MXBCST=-1 KDIAG=0 NOJAC=1 $END
 $MOORTH NOSTF=.T. NOZERO=.T. SYMS=.T. SYMDEN=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 $END
 $GUESS GUESS=MOREAD NORB=160 IORDER(22)=-23 IORDER(32)=-45 NORDER=1 $END
 $DET NCORE=22 NACT=10 NELS=12 CVGTOL=1D-8 ITERMX=1000 NSTATE=15
      WSTATE(1)=1,1,1,1,1 $END
 $MCSCF MAXIT=70 ACURCY=1D-8 CISTEP=ALDET ENGTOL=1D-12 IFORB=1 ISTATE=1
      SOSCF=.T. $END
 $XMCQDPT NSTATE=5 EDSHFT=2D-2 GENZRO=1D-20 ISTATE(1)=1 THRCON=1D-8 THRERI=1D-20
      THRGEN=1D-20 WSTATE(1)=1,1,1,1,1 $END
 $MCQGENS GEN1=3 GEN2=3 GEN3=1 USEGEN1=.T. $END
EOF
    write_data_section "$ISO XMCQDPT2/ALDET-CASSCF(12,10) Andrew-style geometry" "$geom"
    printf "%s" "$vec"
  } > "$inp"
  write_run_sh "$dir" "${ISO}_xmcqdpt2.inp" "${ISO}_xmcqdpt2.out"
}

write_mp2
write_cis 02_cis
if [ "$FROM_MP2" -eq 1 ]; then
  write_cis 03_cis_opt_geometry
  write_xmc
fi
