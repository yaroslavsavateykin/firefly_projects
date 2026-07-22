#!/bin/bash
set -euo pipefail

export NP=${NP:-6}

run_step() {
    local dir="$1"
    echo "=== $dir ==="
    (cd "$dir" && bash run.sh)
}

replace_xmc_vec_from_cis_stage() {
    local iso="$1"
    local xmc_dir="$iso/04_xmcqdpt2"
    local cis_dat="../03_cis_opt_geometry/${iso}_cis_opt_geometry.dat"
    (
        cd "$xmc_dir"
        perl -0ne 'while(/(^ *\$VEC.*?^ *\$END.*?$)/msg){$last=$1} END{print $last}' "$cis_dat" > restart_from_cis_stage.vec
        perl -0pi -e 'BEGIN{local $/; open F,"restart_from_cis_stage.vec"; $v=<F>} s/^ *\$VEC.*?^ *\$END.*?$/$v/msg' "${iso}_xmcqdpt2.inp"
    )
}

relax_ortho_xmc_mcscf() {
    local inp="o_bq/04_xmcqdpt2/o_bq_xmcqdpt2.inp"
    perl -0pi -e 's/\$MCSCF MAXIT=70 ACURCY=1D-8 CISTEP=ALDET ENGTOL=1D-12 IFORB=1 ISTATE=1\n      SOSCF=\.T\. \$END/\$MCSCF MAXIT=200 ACURCY=5D-3 CISTEP=ALDET ENGTOL=1D-3 IFORB=1 ISTATE=1\n      SOSCF=.T. \$END/' "$inp"
}

relax_para_xmc_mcscf() {
    local inp="p_bq/04_xmcqdpt2/p_bq_xmcqdpt2.inp"
    perl -0pi -e 's/\$MCSCF MAXIT=70 ACURCY=1D-8 CISTEP=ALDET ENGTOL=1D-12 IFORB=1 ISTATE=1\n      SOSCF=\.T\. \$END/\$MCSCF MAXIT=200 ACURCY=5D-2 CISTEP=ALDET ENGTOL=1D-2 IFORB=1 ISTATE=1\n      SOSCF=.T. \$END/' "$inp"
}

run_isomer() {
    local iso="$1"
    bash scripts/build_andrew_style.sh "$iso"
    run_step "$iso/01_mp2_opt"
    run_step "$iso/02_cis"
    bash scripts/build_andrew_style.sh "$iso" --from-mp2
    run_step "$iso/03_cis_opt_geometry"
    replace_xmc_vec_from_cis_stage "$iso"
    if [ "$iso" = "p_bq" ]; then
      relax_para_xmc_mcscf
    elif [ "$iso" = "o_bq" ]; then
      relax_ortho_xmc_mcscf
    fi
    run_step "$iso/04_xmcqdpt2"
}

run_isomer p_bq &
pid_p=$!

run_isomer o_bq &
pid_o=$!

status=0
wait "$pid_p" || status=$?
wait "$pid_o" || status=$?
[ "$status" -eq 0 ] || exit "$status"

echo "=== All done ==="
