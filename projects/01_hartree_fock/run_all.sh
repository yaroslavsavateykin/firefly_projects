#!/bin/bash

for d in \
  h2_rhf_sto3g \
  h2_rhf_631g \
  h2plus_uhf_sto3g \
  h2plus_uhf_631g \
  co_rhf_sto3g \
  co_rhf_631g \
  ch4_canonical_sto3g \
  ch4_boys_sto3g \
  h2o_canonical_sto3g \
  h2o_boys_sto3g \
  c2h4_canonical_sto3g \
  c2h4_boys_sto3g
do
  (cd "$d" && ./run.sh)
done
