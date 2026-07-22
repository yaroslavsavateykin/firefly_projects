#!/bin/bash

set -euo pipefail

NP=${NP:-10}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FF="${FF:-${SCRIPT_DIR}/../../../shared/firefly/8.2.0/firefly820}"
EX="${EX:-${SCRIPT_DIR}/../../../shared/firefly/8.2.0}"

inputs=("${SCRIPT_DIR}"/*.inp)
if [ "${#inputs[@]}" -ne 1 ]; then
  echo "Expected exactly one .inp file in ${SCRIPT_DIR}, found ${#inputs[@]}" >&2
  exit 1
fi

INP="$(basename "${inputs[0]}")"
OUT="${INP%.inp}.out"
TMP="/tmp/firefly_${USER}_${INP%.inp}_$$"
PROCGRP="/tmp/firefly_${USER}_${INP%.inp}_procgrp_$$"

cleanup() {
  rm -rf "${TMP}" "${PROCGRP}"
}
trap cleanup EXIT

if [ ! -x "${FF}" ]; then
  echo "Firefly executable not found or not executable: ${FF}" >&2
  exit 1
fi

if [ ! -d "${EX}" ]; then
  echo "Firefly extension directory not found: ${EX}" >&2
  exit 1
fi

printf "local %d\n" "$((NP - 1))" > "${PROCGRP}"

cd "${SCRIPT_DIR}"
rm -f "${OUT}"
echo "Running input ${INP} on ${NP} processes"
"${FF}" -r -f -i "${INP}" -o "${OUT}" -p -stdext -ex "${EX}" -t "${TMP}" -p4pg "${PROCGRP}" >/dev/null 2>&1
