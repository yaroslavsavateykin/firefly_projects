#!/bin/bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)

write_run_sh() {
  local dir="$1"
  local inp="$2"
  local out="$3"
  local depth="$4"
  mkdir -p "$dir"
  cat > "$dir/run.sh" <<EOF_RUN
#!/bin/bash
set -e

NP=\${NP:-6}
FF=\$PWD/${depth}/shared/firefly/8.2.0/firefly820
EX=\$PWD/${depth}/shared/firefly/8.2.0
BASIS=\$PWD/${depth}/shared/basis_sets/benzo_aug-cc-pVDZ.lib
INP=${inp}
OUT=${out}
TMP=/tmp/firefly_\${USER}_\${INP%.inp}_\$\$
PROCGRP=/tmp/firefly_\${USER}_\${INP%.inp}_procgrp_\$\$

printf "local %d\n" "\$((NP - 1))" > "\$PROCGRP"
rm -f "\$OUT"
echo "Running input \$INP on \$NP ranks"
"\$FF" -r -f -i "\$INP" -o "\$OUT" -p -stdext -ex "\$EX" -b "\$BASIS" -t "\$TMP" -p4pg "\$PROCGRP"
STATUS=\$?
rm -f "\$PROCGRP"
[ "\$STATUS" -eq 0 ] || exit "\$STATUS"
EOF_RUN
  chmod +x "$dir/run.sh"
}

write_mp2() {
  local iso="$1"
  local dir="$ROOT/$iso/01_mp2_opt"
  local inp="$dir/${iso}_mp2_opt.inp"
  mkdir -p "$dir"
  if [ "$iso" = "p_bq" ]; then
    local title="p-benzoquinone MP2/aug-cc-pVDZ geometry optimization"
    local atoms='C     6.0     0.0000000000     1.4000000000     0.0000000000
C     6.0     1.2124355650     0.7000000000     0.0000000000
C     6.0     1.2124355650    -0.7000000000     0.0000000000
C     6.0     0.0000000000    -1.4000000000     0.0000000000
C     6.0    -1.2124355650    -0.7000000000     0.0000000000
C     6.0    -1.2124355650     0.7000000000     0.0000000000
O     8.0     0.0000000000     2.6200000000     0.0000000000
O     8.0     0.0000000000    -2.6200000000     0.0000000000
H     1.0     2.1500000000     1.2410000000     0.0000000000
H     1.0     2.1500000000    -1.2410000000     0.0000000000
H     1.0    -2.1500000000    -1.2410000000     0.0000000000
H     1.0    -2.1500000000     1.2410000000     0.0000000000'
  else
    local title="o-benzoquinone MP2/aug-cc-pVDZ geometry optimization"
    local atoms='C     6.0     0.0000000000     1.4000000000     0.0000000000
C     6.0     1.2124355650     0.7000000000     0.0000000000
C     6.0     1.2124355650    -0.7000000000     0.0000000000
C     6.0     0.0000000000    -1.4000000000     0.0000000000
C     6.0    -1.2124355650    -0.7000000000     0.0000000000
C     6.0    -1.2124355650     0.7000000000     0.0000000000
O     8.0     0.0000000000     2.6200000000     0.0000000000
O     8.0     2.2685000000     1.3100000000     0.0000000000
H     1.0     2.1500000000    -1.2410000000     0.0000000000
H     1.0     0.0000000000    -2.4800000000     0.0000000000
H     1.0    -2.1500000000    -1.2410000000     0.0000000000
H     1.0    -2.1500000000     1.2410000000     0.0000000000'
  fi
  local maxit=100
  local trmax=0.5
  if [ "$iso" = "o_bq" ]; then
    maxit=200
    trmax=0.05
  fi
  cat > "$inp" <<EOF_INP
 \$CONTRL D5=.T. EXETYP=RUN FSTINT=.T. GENCON=.F. ICHARG=0 ICUT=13 INTTYP=HONDO
      ITOL=30 MAXIT=${maxit} MULT=1 RUNTYP=OPTIMIZE SCFTYP=RHF MPLEVL=2 WIDE=1 \$END
 \$MOORTH NOSTF=.T. NOZERO=.T. SYMDEN=.T. SYMS=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 \$END
 \$GUESS GUESS=HUCKEL \$END
 \$BASIS EXTFIL=.T. GBASIS=acc-pvdz \$END
 \$SYSTEM KDIAG=0 MASMEM=200000000 MWORDS=200 MXBCST=-1 NOJAC=1 TIMLIM=60000 \$END
 \$STATPT HSSEND=.F. ITBMAT=300 METHOD=GDIIS NSTEP=100 OPTTOL=1E-04
      TRMAX=${trmax} UPHESS=BFGS \$END
 \$SCF DAMP=.T. DIIS=.T. DIRSCF=.T. FDIFF=.F. SHIFT=.T. SOSCF=.F. \$END
 \$MP2 METHOD=1 \$END
 \$DATA
${title}
C1
${atoms}
 \$END
EOF_INP
  write_run_sh "$dir" "${iso}_mp2_opt.inp" "${iso}_mp2_opt.out" "../../../../"
}

write_cis_initial() {
  local iso="$1"
  local dir="$ROOT/$iso/02_cis"
  local mp2="$ROOT/$iso/01_mp2_opt/${iso}_mp2_opt.inp"
  local inp="$dir/${iso}_cis.inp"
  mkdir -p "$dir"
  awk '
    BEGIN { copy=0 }
    /^C1$/ { copy=1; print; next }
    copy && /^ \$END/ { print; exit }
    copy { print }
  ' "$mp2" > "$dir/geometry.tmp"
  cat > "$inp" <<EOF_INP
 \$CONTRL D5=.T. EXETYP=RUN FSTINT=.T. GENCON=.F. ICHARG=0 ICUT=13 INTTYP=HONDO
      ITOL=30 MAXIT=100 MULT=1 RUNTYP=ENERGY SCFTYP=RHF CITYP=CIS WIDE=1 \$END
 \$MOORTH NOSTF=.T. NOZERO=.T. SYMDEN=.T. SYMS=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 \$END
 \$GUESS GUESS=HUCKEL \$END
 \$BASIS EXTFIL=.T. GBASIS=acc-pvdz \$END
 \$SYSTEM KDIAG=0 MASMEM=200000000 MWORDS=200 MXBCST=-1 NOJAC=1 TIMLIM=60000 \$END
 \$SCF DAMP=.T. DIIS=.T. DIRSCF=.T. FDIFF=.F. SHIFT=.T. SOSCF=.F. \$END
 \$CIS ISTATE=1 MULT=1 NSTATE=4 \$END
 \$DATA
${iso} CIS on starting geometry
EOF_INP
  cat "$dir/geometry.tmp" >> "$inp"
  rm -f "$dir/geometry.tmp"
  write_run_sh "$dir" "${iso}_cis.inp" "${iso}_cis.out" "../../../../"
}

write_mp2 "$1"
write_cis_initial "$1"

extract_mp2_geometry() {
  local iso="$1"
  local out="$ROOT/$iso/01_mp2_opt/${iso}_mp2_opt.out"
  if ! grep -q "EQUILIBRIUM GEOMETRY LOCATED" "$out"; then
    echo "ERROR: $out has no converged MP2 geometry" >&2
    exit 1
  fi
  awk '
    /COORDINATES OF ALL ATOMS ARE \(ANGS\)/ { start=NR }
    END { if (!start) exit 2 }
  ' "$out"
  awk '
    /COORDINATES OF ALL ATOMS ARE \(ANGS\)/ { start=NR; next }
    start && NR > start + 2 && /^[[:space:]]*[A-Z][a-z]?[[:space:]]+[0-9]+\./ {
      printf "%-2s %7.1f %16.10f %16.10f %16.10f\n", $1, $2, $3, $4, $5
    }
    start && NR > start + 2 && NF == 0 { if (count > 0) exit }
    start && NR > start + 2 && /^[[:space:]]*[A-Z][a-z]?[[:space:]]+[0-9]+\./ { count++ }
  ' "$out"
}

write_input_with_geometry() {
  local iso="$1"
  local kind="$2"
  local dir="$3"
  local inp="$4"
  local geom="$5"
  mkdir -p "$dir"
  case "$kind" in
    cis_opt)
      cat > "$inp" <<EOF_INP
 \$CONTRL D5=.T. EXETYP=RUN FSTINT=.T. GENCON=.F. ICHARG=0 ICUT=13 INTTYP=HONDO
      ITOL=30 MAXIT=100 MULT=1 RUNTYP=ENERGY SCFTYP=RHF CITYP=CIS WIDE=1 \$END
 \$MOORTH NOSTF=.T. NOZERO=.T. SYMDEN=.T. SYMS=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 \$END
 \$GUESS GUESS=HUCKEL \$END
 \$BASIS EXTFIL=.T. GBASIS=acc-pvdz \$END
 \$SYSTEM KDIAG=0 MASMEM=200000000 MWORDS=200 MXBCST=-1 NOJAC=1 TIMLIM=60000 \$END
 \$SCF DAMP=.T. DIIS=.T. DIRSCF=.T. FDIFF=.F. SHIFT=.T. SOSCF=.F. \$END
 \$CIS ISTATE=1 MULT=1 NSTATE=4 \$END
 \$DATA
${iso} CIS on MP2-optimized geometry
C1
${geom}
 \$END
EOF_INP
      ;;
    casscf)
      cat > "$inp" <<EOF_INP
 \$CONTRL D5=.T. EXETYP=RUN FSTINT=.T. GENCON=.F. ICHARG=0 ICUT=13 INTTYP=HONDO
      ITOL=30 MAXIT=100 MULT=1 RUNTYP=ENERGY SCFTYP=MCSCF WIDE=1 \$END
 \$MOORTH NOSTF=.T. NOZERO=.T. SYMDEN=.T. SYMS=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 \$END
 \$GUESS GUESS=HUCKEL \$END
 \$BASIS EXTFIL=.T. GBASIS=acc-pvdz \$END
 \$SYSTEM KDIAG=0 MASMEM=200000000 MWORDS=200 MXBCST=-1 NOJAC=1 TIMLIM=60000 \$END
 \$SCF DAMP=.T. DIIS=.T. DIRSCF=.T. FDIFF=.F. SHIFT=.T. SOSCF=.F. \$END
 \$DET NCORE=22 NACT=10 NELS=12 CVGTOL=1D-8 ITERMX=1000 NSTATE=15
      WSTATE(1)=1,1,1,1,1 \$END
 \$MCSCF MAXIT=70 ACURCY=1D-8 CISTEP=ALDET ENGTOL=1D-12 IFORB=1 ISTATE=1
      SOSCF=.T. \$END
 \$DATA
${iso} ALDET-CASSCF(12,10) on MP2-optimized geometry
C1
${geom}
 \$END
EOF_INP
      ;;
    xmc_template)
      cat > "$inp" <<EOF_INP
 \$CONTRL D5=.T. EXETYP=RUN FSTINT=.T. GENCON=.F. ICHARG=0 ICUT=13 INTTYP=HONDO
      ITOL=30 MAXIT=100 MULT=1 RUNTYP=ENERGY SCFTYP=MCSCF MPLEVL=2 WIDE=1 \$END
 \$MOORTH NOSTF=.T. NOZERO=.T. SYMDEN=.T. SYMS=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 \$END
 \$GUESS GUESS=MOREAD NORB=236 \$END
 \$BASIS EXTFIL=.T. GBASIS=acc-pvdz \$END
 \$SYSTEM KDIAG=0 MASMEM=200000000 MWORDS=200 MXBCST=-1 NOJAC=1 TIMLIM=60000 \$END
 \$SCF DAMP=.T. DIIS=.T. DIRSCF=.T. FDIFF=.F. SHIFT=.T. SOSCF=.F. \$END
 \$DET NCORE=22 NACT=10 NELS=12 CVGTOL=1D-8 ITERMX=1000 NSTATE=15
      WSTATE(1)=1,1,1,1,1 \$END
 \$MCSCF MAXIT=70 ACURCY=1D-8 CISTEP=ALDET ENGTOL=1D-12 IFORB=1 ISTATE=1
      SOSCF=.T. \$END
 \$XMCQDPT NSTATE=5 EDSHFT=2D-2 GENZRO=1D-20 ISTATE(1)=1 THRCON=1D-8 THRERI=1D-20
      THRGEN=1D-20 WSTATE(1)=1,1,1,1,1 \$END
 \$MCQGENS GEN1=3 GEN2=3 GEN3=1 USEGEN1=.T. \$END
 \$DATA
${iso} XMCQDPT2/ALDET-CASSCF(12,10) on MP2-optimized geometry
C1
${geom}
 \$END
EOF_INP
      ;;
  esac
}

write_xmc_run_sh() {
  local iso="$1"
  local dir="$ROOT/$iso/05_xmcqdpt2"
  local casscf_dat="../04_casscf_aldet/${iso}_casscf_aldet.dat"
  mkdir -p "$dir"
  cat > "$dir/run.sh" <<EOF_RUN
#!/bin/bash
set -e

NP=\${NP:-6}
FF=\$PWD/../../../../shared/firefly/8.2.0/firefly820
EX=\$PWD/../../../../shared/firefly/8.2.0
BASIS=\$PWD/../../../../shared/basis_sets/benzo_aug-cc-pVDZ.lib
TEMPLATE=${iso}_xmcqdpt2.template.inp
INP=${iso}_xmcqdpt2.inp
OUT=${iso}_xmcqdpt2.out
CASSCF_DAT=${casscf_dat}
TMP=/tmp/firefly_\${USER}_\${INP%.inp}_\$\$
PROCGRP=/tmp/firefly_\${USER}_\${INP%.inp}_procgrp_\$\$

if [ ! -f "\$CASSCF_DAT" ]; then
  echo "Missing CASSCF dat file: \$CASSCF_DAT" >&2
  exit 2
fi

awk '
  BEGIN { invec=0; block=""; last="" }
  /^[[:space:]]*\\\$VEC/ { invec=1; block=\$0 ORS; next }
  invec {
    block = block \$0 ORS
    if (\$0 ~ /^[[:space:]]*\\\$END/) { last=block; invec=0 }
  }
  END {
    if (last == "") exit 3
    printf "%s", last
  }
' "\$CASSCF_DAT" > .vec.tmp

cat "\$TEMPLATE" .vec.tmp > "\$INP"
rm -f .vec.tmp

printf "local %d\n" "\$((NP - 1))" > "\$PROCGRP"
rm -f "\$OUT"
echo "Running input \$INP on \$NP ranks"
"\$FF" -r -f -i "\$INP" -o "\$OUT" -p -stdext -ex "\$EX" -b "\$BASIS" -t "\$TMP" -p4pg "\$PROCGRP"
STATUS=\$?
rm -f "\$PROCGRP"
[ "\$STATUS" -eq 0 ] || exit "\$STATUS"
EOF_RUN
  chmod +x "$dir/run.sh"
}

build_downstream_from_mp2() {
  local iso="$1"
  local geom
  geom=$(extract_mp2_geometry "$iso")
  write_input_with_geometry "$iso" cis_opt "$ROOT/$iso/03_cis_opt_geometry" "$ROOT/$iso/03_cis_opt_geometry/${iso}_cis_opt_geometry.inp" "$geom"
  write_run_sh "$ROOT/$iso/03_cis_opt_geometry" "${iso}_cis_opt_geometry.inp" "${iso}_cis_opt_geometry.out" "../../../../"

  write_input_with_geometry "$iso" casscf "$ROOT/$iso/04_casscf_aldet" "$ROOT/$iso/04_casscf_aldet/${iso}_casscf_aldet.inp" "$geom"
  write_run_sh "$ROOT/$iso/04_casscf_aldet" "${iso}_casscf_aldet.inp" "${iso}_casscf_aldet.out" "../../../../"

  write_input_with_geometry "$iso" xmc_template "$ROOT/$iso/05_xmcqdpt2" "$ROOT/$iso/05_xmcqdpt2/${iso}_xmcqdpt2.template.inp" "$geom"
  write_xmc_run_sh "$iso"
}

if [ "${2:-}" = "--from-mp2" ]; then
  build_downstream_from_mp2 "$1"
fi
