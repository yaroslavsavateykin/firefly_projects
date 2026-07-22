# H2/STO-3G Surface Methods Comparison

This project compares six H2 dissociation curves in the minimal STO-3G basis. Every calculation is a single Firefly `RUNTYP=SURFACE` job, not a set of many single-point input files.

The common grid is `R(H-H) = 5.00 -> 0.40 Angstrom`, step `-0.05 Angstrom`, 93 surface geometries. The CSV and plots are sorted as `0.40 -> 5.00 Angstrom`.

## Methods

RHF is a restricted closed-shell singlet. It preserves the pure singlet spin symmetry, but it dissociates H2 poorly because both electrons remain constrained to the same spatial orbital.

UHF is a singlet UHF calculation without `MIX`. The UHF ansatz allows different alpha and beta orbitals, but without an intentional perturbation it can remain RHF-like: `E_UHF ~= E_RHF` and `<S^2> ~= 0`.

UHF + MIX is broken-symmetry UHF. `$GUESS GUESS=HUCKEL MIX=.T. $END` intentionally separates the alpha and beta initial orbitals, and `NOSYM=1` prevents symmetry from restoring the RHF-like branch. The stretched-branch energy is better than RHF, but `<S^2>` grows toward 1, so the determinant is spin-contaminated and not a pure singlet.

MP2 is a perturbative correlation correction to the closed-shell RHF reference:

```text
$CONTRL SCFTYP=RHF MPLEVL=2 RUNTYP=SURFACE MULT=1 ICHARG=0 $END
```

The CSV stores the MP2 total energy printed by Firefly as `E(MP2)= ...`, not the preceding SCF energy. `S2_MP2_ref` is written as 0.0 because the reference is a closed-shell RHF singlet. This is a reference-wavefunction spin value; MP2 is not a separate variational wavefunction with an independently optimized `<S^2>`.

MP2 can improve the energy near equilibrium by adding dynamic correlation. For stretched H2, RHF-reference MP2 can behave poorly because bond breaking requires static correlation, not only dynamic correlation.

UMP2 is second-order perturbation theory on a broken-symmetry UHF reference:

```text
$CONTRL SCFTYP=UHF MPLEVL=2 RUNTYP=SURFACE MULT=1 ICHARG=0 NOSYM=1 $END
$GUESS GUESS=HUCKEL MIX=.T. $END
```

UMP2 uses the same kind of broken-symmetry UHF reference as `UHF + MIX`. The CSV stores Firefly's final MP2 total energy from the UHF-MP2 section. `S2_UMP2_ref` is the spin value of the UHF reference printed before the perturbative correction. Because MP2 uses an RHF reference and UMP2 uses a UHF reference, their dissociation behavior can differ strongly.

Full CI uses determinant ALDET:

```text
$CONTRL CITYP=ALDET SCFTYP=RHF RUNTYP=SURFACE MULT=1 ICHARG=0 $END
$CIDET NACT=2 NCORE=0 NELS=2 NSTATE=4 $END
```

In STO-3G H2, the active space is 2 electrons in 2 molecular orbitals. Full CI is the benchmark within this minimal basis and describes the static correlation of H2 dissociation without artificial broken-symmetry UHF. The main CSV stores only the ground-state root `E_FCI0_hartree`. If available, all four CI root energies are also written to `results/h2_fci_roots.csv`.

## Inputs

The six generated inputs are:

- `inputs/h2_rhf_surface.inp`
- `inputs/h2_uhf_plain_surface.inp`
- `inputs/h2_uhf_mix_surface.inp`
- `inputs/h2_mp2_surface.inp`
- `inputs/h2_ump2_surface.inp`
- `inputs/h2_fci_surface.inp`

All use:

- `RUNTYP=SURFACE`
- `GBASIS=STO NGAUSS=3`
- `C1`
- `ICHARG=0`
- `MULT=1`
- the same reverse scan grid

## Run

```bash
cd h2_surface_methods_comparison
python3 make_inputs.py
bash run.sh
python3 parse_outputs.py
python3 plot_comparison.py
```

`run.sh` runs the surface jobs sequentially. It uses Firefly's `-p4pg` procgrp launch scheme and defaults to:

```bash
NP=8
```

Override if needed:

```bash
NP=6 bash run.sh
```

The Firefly executable path is controlled by `FF`:

```bash
FF=/path/to/firefly820 bash run.sh
```

## Results

Main CSV:

- `results/h2_surface_methods_comparison.csv`

Columns:

```text
R_angstrom,
E_RHF_hartree,
E_UHF_plain_hartree,
E_UHF_mix_hartree,
E_MP2_hartree,
E_UMP2_hartree,
E_FCI0_hartree,
S2_RHF,
S2_UHF_plain,
S2_UHF_mix,
S2_MP2_ref,
S2_UMP2_ref,
S2_FCI0
```

Optional FCI-root CSV:

- `results/h2_fci_roots.csv`

Columns:

```text
R_angstrom,
E_root0,
E_root1,
E_root2,
E_root3,
S2_root0,
S2_root1,
S2_root2,
S2_root3
```

Figures:

- `results/h2_surface_methods_energy_spin.png`
- `results/h2_surface_methods_energy_spin.pdf`
- `results/h2_fci_spin_roots.png`
- `results/h2_fci_spin_roots.pdf`
- `results/h2_all_spin_states.png`
- `results/h2_all_spin_states.pdf`

The main figure's left panel shows total energies for RHF, UHF, UHF + MIX, MP2, UMP2, and FCI. The right panel shows `<S^2>` for RHF, UHF, UHF + MIX, MP2 reference, UMP2 reference, and FCI root 0 if Firefly prints enough spin information for CI roots.

`h2_fci_spin_roots.*` plots all available FCI root spin curves. `h2_all_spin_states.*` collects every available spin diagnostic in one panel.

## Checks

- There are exactly six input files.
- All six inputs use `RUNTYP=SURFACE`.
- The MP2 input contains `MPLEVL=2`.
- The UMP2 input contains `SCFTYP=UHF`, `MPLEVL=2`, `MIX=.T.`, and `NOSYM=1`.
- The FCI input contains `CITYP=ALDET` and `$CIDET`.
- UHF + MIX contains `MIX=.T.` and `NOSYM=1`.
- Plain UHF does not contain `MIX=.T.`.
- The main CSV contains only the required columns.
- The main figure has two panels: energy and `<S^2>`.
- Separate spin figures are written for FCI roots and for all spin states.
- The jobs are launched sequentially on `NP=8` by default.
- The parser prints point counts for RHF, UHF, UHF + MIX, MP2, UMP2, and FCI, the maximum `<S^2>` for UHF + MIX and UMP2 reference, and whether S2 was parsed for FCI roots.

## Completed Run Summary

For the generated 93-point surface grid:

- RHF points: 93.
- UHF points: 93.
- UHF + MIX points: 93.
- MP2 points: 93.
- UMP2 points: 93.
- FCI points: 93.
- `max <S^2>` for UHF + MIX: `1.000000`.
- `max <S^2>` for UMP2 reference: `1.000000`.
- FCI root energies were parsed for four roots and written to `results/h2_fci_roots.csv`.
- S2 for FCI roots was not printed in this Firefly surface output, so `S2_FCI0` and `S2_root*` are `NaN`, FCI is omitted from spin panels, and zero FCI roots are plotted on the dedicated FCI spin graph.
