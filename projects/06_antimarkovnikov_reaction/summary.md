# HF addition to propene: actual calculation results

## Method and provenance

Firefly 8.2.0 build 10203, RHF-reference B3LYP, explicit aug-cc-pVDZ,
charge zero, singlet. Original numerical controls retained, including
INTTYP=HONDO, ICUT=13, ITOL=30, D5=.T., MAXIT=100, GENCON=.F., FSTINT=.T.;
UNITS=ANGS is explicit. Optimizations use OPTTOL=1D-5.
All new jobs ran serially with NP=8, SMP NP=1, MKLNP=1, TPOOL=1,
one-thread BLAS environment, and affinity limited to eight CPUs.
Observed Firefly processes had two OS threads per rank (one computational
thread plus runtime/helper thread), not 128 computational threads per rank.

Original project 05 files were read but never edited. The shared reactant
coordinates and basis come from its scan_00 input; prior outputs are not
treated as proof that its currently edited inputs work. Both regioisomers
were built with atom-order-preserving RDKit/MMFF seeds and optimized afresh.
The old project 05 saddle is not used or claimed as relevant to either path.

## Completed calculations

| Calculation | Electronic energy, Eh |
| --- | ---: |
| Shared reactant energy | -218.3899264505 |
| Anti-Markovnikov product optimization | -218.4028310574 |
| Markovnikov product optimization | -218.4097557889 |
| Anti geodesic maximum, frame 05 | -218.2820798211 |
| Markovnikov geodesic maximum, frame 06 | -218.1576302565 |
| Fresh anti-path saddle | -218.3121105330 |
| Anti IRC forward point 10 | -218.3834333645 |
| Anti IRC reverse point 10 | -218.3726056211 |
| Optimized forward IRC endpoint | -218.4031578383 |
| Optimized reverse IRC endpoint | -218.3899260973 |

Both 11-image scans completed: `energy_profile.csv` and
`mark_energy_profile.csv`. Paths were generated with real
`geodesic-interpolate==1.0.0`, not Cartesian interpolation. These are
unrelaxed single-point profiles, not minimum-energy paths or activation barriers.
Rigid rotations from path alignment give small DFT quadrature-dependent
endpoint energy differences (approximately 5-8 microhartree).

Both scan-maximum numerical Hessians completed. The fresh anti-path saddle
converged with maximum gradient 0.0000085 Eh/bohr. Its independent numerical
Hessian has exactly one imaginary frequency, 1592.94i cm^-1; six near-zero
modes have magnitudes below 4 cm^-1. The electronic barrier relative to the
shared reactant is **204.31 kJ/mol**, without ZPE or thermal corrections.

Both IRC directions completed all 10 requested points using the native
Firefly punch Hessian. Subsequent unconstrained endpoint optimizations
converged. Forward connectivity: C2-H10 1.1004 A and C3-F11 1.4139 A,
confirming the anti-Markovnikov product. Reverse connectivity: C2-C3
1.3421 A, H10-F11 0.9403 A, recovering propene plus HF. The forward endpoint
is a slightly lower-energy product conformer than the original product seed.
Ten-point IRC segments themselves are not claimed to reach stationary endpoints.

## Remaining scientific limitations

The fresh Markovnikov saddle search exhausted 200 steps, ending at
-218.3855942134 Eh without stationary-point convergence. Its normal-execution
footer does not make it successful; `mark_saddle.json` records failure.
A refreshed Hessian/better path seed is needed before a Markovnikov barrier,
frequency validation, IRC, or regioselectivity comparison can be reported.
Product/reactant endpoint vibrational Hessians and thermochemical corrections
have not been calculated. Endpoint connectivity and optimization convergence
are established, but minima have not yet been independently frequency-tested.

## Repairs and reproduction

The former external-blocker diagnosis was false. Fixed defects include
column-1 `$DATA`, missing (and later duplicated) atom-basis separators,
80-column truncation, dropped numerical controls, overlapping product seed,
import-time input overwrites, final-coordinate parsing, missing scan XYZs,
abnormal-output false success, saddle-specific convergence markers,
stale-output resume, absent punch preservation, and incomplete Hessian parsing.

`launch.py` uses a project-wide calculation lock, isolated scratch, per-attempt
input snapshots/logs/output archives, input and output SHA-256 hashes, and
scientific completion checks. `.dat` and `.irc` are preserved. Failed prior
attempts are retained under each job's `attempts/`. `recover_product.py`
documents the one product run whose supervising tool timed out while Firefly
continued to completion; recovery checks its archived input byte-for-byte.

Run `bash run_pipeline.sh` to resume both scans and the validated anti-path
downstream chain. Markovnikov downstream is explicit:
`python3 downstream.py hessian --mark`, then `saddle --mark`; do not interpret
the existing failed search as a converged TS. Local environment setup:
`python3 -m venv --system-site-packages .venv`, followed by
`.venv/bin/pip install geodesic-interpolate==1.0.0`; numpy, scipy and RDKit
were already installed on this machine.

Run `python3 test_workflow.py` for import safety, idempotent formatting,
card width/separators/settings, abnormal and unconverged output rejection,
actual output geometry parsing, native Hessian round-trip/truncation rejection,
and actual IRC point-count validation.
