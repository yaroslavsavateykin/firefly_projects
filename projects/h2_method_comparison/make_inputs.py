#!/usr/bin/env python3
"""Generate Firefly SURFACE inputs for H2/STO-3G method comparison."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


R_MIN = Decimal("0.40")
R_MAX = Decimal("5.00")
N_POINTS = 93

INPUT_DIR = Path("inputs")


@dataclass(frozen=True)
class MethodSpec:
    filename: str
    title: str
    contrl: str
    guess: str
    extra_groups: tuple[str, ...] = ()
    nsurf: int | None = None


METHODS = (
    MethodSpec(
        filename="h2_rhf_surface.inp",
        title="H2 RHF/STO-3G singlet surface",
        contrl="$CONTRL SCFTYP=RHF RUNTYP=SURFACE MULT=1 ICHARG=0",
        guess="$GUESS GUESS=HUCKEL $END",
    ),
    MethodSpec(
        filename="h2_uhf_plain_surface.inp",
        title="H2 plain UHF/STO-3G singlet symmetric-candidate surface",
        contrl="$CONTRL SCFTYP=UHF RUNTYP=SURFACE MULT=1 ICHARG=0",
        guess="$GUESS GUESS=HUCKEL $END",
    ),
    MethodSpec(
        filename="h2_uhf_mix_surface.inp",
        title="H2 broken-symmetry UHF/STO-3G singlet surface with MIX",
        contrl="$CONTRL SCFTYP=UHF RUNTYP=SURFACE MULT=1 ICHARG=0 NOSYM=1",
        guess="$GUESS GUESS=HUCKEL MIX=.T. $END",
    ),
    MethodSpec(
        filename="h2_mp2_surface.inp",
        title="H2 RHF-MP2/STO-3G singlet surface",
        contrl="$CONTRL SCFTYP=RHF MPLEVL=2 RUNTYP=SURFACE MULT=1 ICHARG=0",
        guess="$GUESS GUESS=HUCKEL $END",
    ),
    MethodSpec(
        filename="h2_ump2_mix_surface.inp",
        title="H2 UMP2/STO-3G singlet surface",
        contrl="$CONTRL SCFTYP=UHF MPLEVL=2 RUNTYP=SURFACE MULT=1 ICHARG=0 NOSYM=1",
        guess="$GUESS GUESS=HUCKEL MIX=.T. $END",
    ),
    MethodSpec(
        filename="h2_ump2_surface.inp",
        title="H2 UMP2/STO-3G broken-symmetry singlet surface",
        contrl="$CONTRL SCFTYP=UHF MPLEVL=2 RUNTYP=SURFACE MULT=1 ICHARG=0 NOSYM=1",
        guess="$GUESS GUESS=HUCKEL $END",
    ),
    MethodSpec(
        filename="h2_fci_surface.inp",
        title="H2 Full CI/ALDET/STO-3G singlet surface",
        contrl="$CONTRL CITYP=ALDET SCFTYP=RHF RUNTYP=SURFACE MULT=1 ICHARG=0",
        guess="$GUESS GUESS=HUCKEL $END",
        extra_groups=("$CIDET NACT=2 NCORE=0 NELS=2 NSTATE=4 $END",),
        nsurf=4,
    ),
)


def fmt(value: Decimal) -> str:
    return f"{float(value):.6f}"


def step_size() -> Decimal:
    if N_POINTS < 2:
        raise ValueError("N_POINTS must be at least 2.")
    if R_MIN <= 0 or R_MAX <= 0:
        raise ValueError("R_MIN and R_MAX must be positive.")
    if R_MAX <= R_MIN:
        raise ValueError("R_MAX must be greater than R_MIN.")
    return ((R_MAX - R_MIN) / Decimal(N_POINTS - 1)).quantize(
        Decimal("0.000001"),
        rounding=ROUND_HALF_UP,
    )


def surf_group(method: MethodSpec, step: Decimal) -> str:
    nsurf_line = "" if method.nsurf is None else f"   NSURF={method.nsurf}\n"
    return f""" $SURF
   IVEC1(1)=1,2
   IGRP1(1)=2
   ORIG1=0.000000
   DISP1=-{fmt(step)}
   NDISP1={N_POINTS}
{nsurf_line} $END"""


def make_text(method: MethodSpec, step: Decimal) -> str:
    extra_groups = "\n".join(f" {group}" for group in method.extra_groups)
    if extra_groups:
        extra_groups = "\n" + extra_groups

    return f"""! {method.title}
! Firefly 8.2.0, one RUNTYP=SURFACE job
! Grid: R(H-H) = {fmt(R_MAX)} down to {fmt(R_MIN)} Angstrom, {N_POINTS} points
! $DATA starts at R={fmt(R_MAX)} Angstrom; $SURF moves atom 2 by DISP1.

 {method.contrl}
      MAXIT=100 UNITS=ANGS $END
 $SYSTEM TIMLIM=600 MEMORY=1000000 $END
 $BASIS GBASIS=STO NGAUSS=3 $END
 {method.guess}
 $SCF DAMP=.T. DIIS=.T. DIRSCF=.T. FDIFF=.F. SHIFT=.T.
      SOSCF=.F. DENTOL=1.0E-4 $END
{surf_group(method, step)}
{extra_groups}
 $DATA
{method.title}; reverse scan R_start={fmt(R_MAX)} A, R_end={fmt(R_MIN)} A
C1
H 1.0 0.000000 0.000000 0.000000
H 1.0 0.000000 0.000000 {fmt(R_MAX)}
 $END
"""


def main() -> None:
    step = step_size()
    expected_end = R_MAX - step * Decimal(N_POINTS - 1)
    if abs(expected_end - R_MIN) > Decimal("0.000001"):
        raise ValueError(
            f"Grid mismatch: R_MAX - STEP*(N_POINTS-1) = {expected_end}, expected {R_MIN}"
        )

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    for method in METHODS:
        path = INPUT_DIR / method.filename
        path.write_text(make_text(method, step), encoding="utf-8")
        print(f"Wrote {path}")

    print(
        f"Generated {len(METHODS)} surface inputs on {fmt(R_MAX)} -> {fmt(R_MIN)} "
        f"Angstrom grid, step -{fmt(step)}, NDISP1={N_POINTS}."
    )


if __name__ == "__main__":
    main()
