#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
INPUT_DIR = HERE / "inputs"
SELECTED_CSV = HERE / "selected_R_points.csv"
DATA_CSV = ROOT / "analysis" / "lif_all_data.csv"

BASE_POINTS = {
    "minimum": [1.30, 1.40, 1.50, 1.60, 1.70, 1.80],
    "pre_crossing": [4.50, 5.00, 5.30, 5.50],
    "crossing_e3_e2": [5.60, 5.70, 5.80, 5.85, 5.90, 6.00, 6.10, 6.20],
    "post_crossing": [6.50, 7.00, 7.50, 8.00],
    "dissociation": [8.25, 8.50, 8.75, 9.00],
}


def read_gap_minima() -> dict[str, float]:
    if not DATA_CSV.exists():
        return {}
    by_r: dict[float, dict[int, float]] = defaultdict(dict)
    with DATA_CSV.open() as f:
        for row in csv.DictReader(f):
            if row.get("status") != "normal" or not row.get("R_A") or not row.get("energy_Ha"):
                continue
            try:
                by_r[round(float(row["R_A"]), 2)][int(row["state"])] = float(row["energy_Ha"])
            except (ValueError, KeyError):
                continue

    out: dict[str, float] = {}
    gaps_32 = []
    gaps_21 = []
    for r, states in by_r.items():
        if 3 in states and 2 in states:
            gaps_32.append((states[3] - states[2], r))
        if 2 in states and 1 in states:
            gaps_21.append((states[2] - states[1], r))
    if gaps_32:
        out["auto_gap_e3_e2"] = min(gaps_32, key=lambda x: abs(x[0]))[1]
    if gaps_21:
        out["auto_gap_e2_e1"] = min(gaps_21, key=lambda x: abs(x[0]))[1]
    return out


def filename_for_r(r: float) -> str:
    return f"lif_sp_R_{r:0.2f}".replace(".", "_") + ".inp"


def make_input(r: float) -> str:
    return f""" $CONTRL CITYP=ALDET D5=.T. EXETYP=RUN FSTINT=.T. GENCON=.F.
      ICHARG=0 ICUT=13 INTTYP=HONDO ITOL=30 MAXIT=100 MULT=1
      RUNTYP=ENERGY SCFTYP=RHF WIDE=1 NOSYM=0
 $END
 $MOORTH NOSTF=.T. NOZERO=.T. SYMDEN=.T. SYMS=.T. SYMVEC=.T. SYMVX=.T.
      TOLE=0.0D0 TOLZ=0.0D0 $END
 $GUESS GUESS=HUCKEL $END
 $BASIS EXTFIL=.T. GBASIS=acc-pVDZ $END
 $SYSTEM KDIAG=0 MASMEM=200000000 MWORDS=200 MXBCST=-1 NOJAC=1 TIMLIM=60000 $END
 $SCF DAMP=.T. DIIS=.T. DIRSCF=.T. FDIFF=.F. SHIFT=.T. SOSCF=.F. $END
 $CIDET NACT=29 NCORE=3 NELS=6 NSTATE=3 GROUP=c2v CVGTOL=1e-4 $END
 $DATA
 LiF single-point properties R={r:.2f} Ang
 Cnv 2

Li    3.0     0.0000000000     0.0000000000     0.0000000000
F     9.0     0.0000000000     0.0000000000     {r:.10f}
$END
"""


def main() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    points: dict[float, set[str]] = defaultdict(set)
    for reason, vals in BASE_POINTS.items():
        for r in vals:
            points[round(r, 2)].add(reason)

    for reason, center in read_gap_minima().items():
        for delta in [-0.20, -0.10, 0.0, 0.10, 0.20]:
            r = round(center + delta, 2)
            if 0.30 <= r <= 10.00:
                points[r].add(reason)

    with SELECTED_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["R_A", "reasons", "input_file"])
        writer.writeheader()
        for r in sorted(points):
            name = filename_for_r(r)
            writer.writerow({"R_A": f"{r:.2f}", "reasons": ";".join(sorted(points[r])), "input_file": f"inputs/{name}"})
            (INPUT_DIR / name).write_text(make_input(r))

    print(f"Wrote {len(points)} selected R points to {SELECTED_CSV}")
    print(f"Wrote inputs to {INPUT_DIR}")


if __name__ == "__main__":
    main()
