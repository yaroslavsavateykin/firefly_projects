# LiF new_runs branch

This directory contains only new LiF calculations. Existing directories `lif_scan/`,
`extended_scan/`, and `fine_crossing/` are treated as source material and are not
modified by the scripts here.

## Geometry regions

The old successful scan in `lif_scan/LiF_CI.out` was parsed before choosing the
new scans:

- ground-state minimum: `R = 1.50 Ang`;
- minimum `E2-E1` gap in the old grid: `R = 7.75 Ang`;
- minimum `E3-E2` gap in the old grid: `R = 5.75 Ang`;
- largest reliable old distance: `R = 7.75 Ang`.

The Firefly inputs in the existing project use the verified `$SURF` uniform scan
syntax. I did not find a local verified example for an arbitrary non-uniform list
of Li-F distances in one input, so the new calculations are grouped as compact
uniform scans instead of one input per point.

## New inputs

- `scan_selected/lif_selected_scan.inp`: minimum-region scan, `R = 1.30-1.70 Ang`,
  step `0.10 Ang`, three roots.
- `scan_crossing/lif_crossing_scan.inp`: dense quasi-crossing scan covering both
  old small-gap regions, `R = 5.25-8.25 Ang`, step `0.10 Ang`, three roots.
- `scan_dissociation/lif_dissociation_scan.inp`: dissociation-limit scan,
  `R = 7.75-9.00 Ang`, step `0.25 Ang`, three roots.

## Properties

Local examples show that `ALDET` single-point calculations can print CI
eigenvectors, natural orbitals, Mulliken/Lowdin populations, and electrostatic
moments. The existing LiF `RUNTYP=SURFACE` output did not include these detailed
per-root property blocks. No unverified Firefly keywords were added to the new
inputs. The analysis script will extract dipoles, charges, CI coefficients, and
spin labels if Firefly prints them; otherwise the missing properties are recorded
in `analysis/properties_audit.md`.

## Extended scan failure

The old `extended_scan` failed with `status=1`. `run_coarse2.log` reports P4
shared-memory allocation failure and says the current `P4_GLOBMEMSIZE` was only
`16777216` bytes. The new runner sets `P4_GLOBMEMSIZE_BYTES=1073741824` by
default and performs a preflight check before launching.

## Running

From the project root:

```bash
new_runs/run_new.sh
```

The runner prints the exact Firefly commands before execution, checks total cores,
configured memory, and output paths, and runs at most two jobs in parallel:

```bash
MAX_PARALLEL=2
NPROC_PER_JOB=8
```

To run one job at a time:

```bash
MAX_PARALLEL=1 new_runs/run_new.sh
```
