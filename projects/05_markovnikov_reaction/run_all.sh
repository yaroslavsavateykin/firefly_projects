#!/bin/bash

set -euo pipefail

# Generate all input files
echo "=== Generating input files ==="
python3 generate_all.py

# Create list of directories to run
dirs=()
for d in new_file_opt_00 new_file_opt_01; do
  dirs+=("$d")
done

for i in $(seq -w 0 10); do
  dirs+=("c3h7f_scan_${i}")
done

# Run each directory
for d in "${dirs[@]}"; do
  echo "== ${d} =="
  (cd "${d}" && ./run.sh)
done

# Post-process: find max energy and generate hessian
echo ""
echo "=== Post-processing scans ==="
python3 parse_energies.py --stage 1

# Check if .max_frame_config was created
if [ -f .max_frame_config ]; then
  echo ""
  echo "=== Stage 2: Hessian ==="
  python3 parse_energies.py --stage 2
  (cd c3h7f_hessian && ./run.sh)

  echo ""
  echo "=== Stage 3: Sadpoint ==="
  python3 parse_energies.py --stage 3
  (cd c3h7f_sadpoint && ./run.sh)

  echo ""
  echo "=== Stage 4: IRC forward + reverse ==="
  python3 parse_energies.py --stage 4
  (cd c3h7f_irc_step_19 && ./run.sh)
  (cd c3h7f_irc_reverse_step_19 && ./run.sh)
else
  echo ""
  echo "WARNING: No scan results found. Run scans first, then:"
  echo "  python3 parse_energies.py --stage all"
fi

echo ""
echo "=== Done ==="
