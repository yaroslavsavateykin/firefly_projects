#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$here"
py="$here/.venv/bin/python"
"$py" generate.py
python3 launch.py reactant/reactant.inp
python3 launch.py product/product.inp
"$py" workflow.py prepare-scan
for input in scan_*/*.inp; do python3 launch.py "$input"; done
"$py" workflow.py analyse-scan
python3 launch.py mark_product/mark_product.inp
"$py" workflow.py prepare-scan --mark
for input in mark_scan_*/*.inp; do python3 launch.py "$input"; done
"$py" workflow.py analyse-scan --mark
for stage in hessian saddle ts-hessian irc-forward irc-reverse endpoint-forward endpoint-reverse; do
    python3 downstream.py "$stage"
done
# ponytail: the Markovnikov search needs a better seed after its 200-step failure;
# run downstream.py stages with --mark explicitly rather than silently retrying.
