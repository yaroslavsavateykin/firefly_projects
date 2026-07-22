#!/usr/bin/env python3
"""Run extended H2 RHF+FCI scan in STO-3G basis."""
import subprocess, os, re
import numpy as np

FF = os.path.expanduser("~/firefly_projects/shared/firefly/8.2.0/firefly820")
EX = os.path.expanduser("~/firefly_projects/shared/firefly/8.2.0")
WORKDIR = os.path.expanduser("~/firefly_projects/projects/02_h2_potential_curves/extended_scan")
os.makedirs(WORKDIR, exist_ok=True)

# Dense near minimum, coarser at large R
R_vals = (list(np.arange(0.4, 1.0, 0.05)) +
          list(np.arange(1.0, 3.0, 0.1)) +
          list(np.arange(3.0, 8.1, 0.2)))
R_vals = sorted(set([round(r, 4) for r in R_vals]))

BOHR = 1.8897259886  # 1 Angstrom in Bohr

def make_inp_rhf(R_bohr):
    return f""" $CONTRL SCFTYP=RHF RUNTYP=ENERGY UNITS=BOHR ICHARG=0 MULT=1 $END
 $BASIS GBASIS=STO NGAUSS=3 $END
 $GUESS GUESS=HUCKEL $END
 $SCF DAMP=.T. DIIS=.T. DIRSCF=.T. $END
 $SYSTEM MWORDS=50 TIMLIM=120 $END
 $DATA
H2 RHF STO-3G R={R_bohr:.6f} bohr
C1
H 1.0 0.0 0.0 {R_bohr/2:.8f}
H 1.0 0.0 0.0 {-R_bohr/2:.8f}
 $END
"""

def make_inp_fci(R_bohr):
    return f""" $CONTRL SCFTYP=RHF RUNTYP=ENERGY UNITS=BOHR ICHARG=0 MULT=1 CITYP=ALDET $END
 $BASIS GBASIS=STO NGAUSS=3 $END
 $GUESS GUESS=HUCKEL $END
 $SCF DAMP=.T. DIIS=.T. DIRSCF=.T. $END
 $SYSTEM MWORDS=50 TIMLIM=120 $END
 $CIDET NACT=2 NCORE=0 NELS=2 NSTATE=1 $END
 $DATA
H2 FCI STO-3G R={R_bohr:.6f} bohr
C1
H 1.0 0.0 0.0 {R_bohr/2:.8f}
H 1.0 0.0 0.0 {-R_bohr/2:.8f}
 $END
"""

def make_inp_h_atom():
    return """ $CONTRL SCFTYP=ROHF RUNTYP=ENERGY UNITS=BOHR ICHARG=0 MULT=2 $END
 $BASIS GBASIS=STO NGAUSS=3 $END
 $GUESS GUESS=HUCKEL $END
 $SCF DAMP=.T. DIIS=.T. DIRSCF=.T. $END
 $SYSTEM MWORDS=50 TIMLIM=60 $END
 $DATA
H atom STO-3G
C1
H 1.0 0.0 0.0 0.0
 $END
"""

def parse_energy(text, is_fci=False):
    """Parse energy from Firefly output."""
    if is_fci:
        # CI eigenstate energy
        m = re.findall(r'CI EIGENSTATE\s+\d+\s+TOTAL ENERGY\s*=\s*(-?\d+\.\d+)', text)
        if m:
            return float(m[-1])
        # Alternative: STATE  1  ENERGY=
        m = re.findall(r'STATE\s+1\s+ENERGY=\s*(-?\d+\.\d+)', text)
        if m:
            return float(m[-1])
    # RHF energy
    m = re.findall(r'FINAL ENERGY IS\s+(-?\d+\.\d+)', text)
    if m:
        return float(m[-1])
    return None

def run_calc(inp_content, tag, is_fci=False):
    inp_file = os.path.join(WORKDIR, f"{tag}.inp")
    out_file = os.path.join(WORKDIR, f"{tag}.out")
    tmp_dir = f"/tmp/ff_{tag}_{os.getpid()}"
    procgrp = f"/tmp/ff_{tag}_pg_{os.getpid()}"

    with open(inp_file, 'w') as f:
        f.write(inp_content)
    # Remove existing output
    if os.path.exists(out_file):
        os.remove(out_file)
    with open(procgrp, 'w') as f:
        f.write("local 1\n")

    result = subprocess.run(
        [FF, '-r', '-f', '-i', inp_file, '-o', out_file, '-p', '-stdext',
         '-ex', EX, '-t', tmp_dir, '-p4pg', procgrp],
        capture_output=True, timeout=120
    )
    try:
        os.remove(procgrp)
    except:
        pass

    E = None
    if os.path.exists(out_file):
        with open(out_file) as f:
            text = f.read()
        E = parse_energy(text, is_fci)
    return E

print("=== Computing H atom energy ===")
E_H = run_calc(make_inp_h_atom(), "h_atom", is_fci=False)
print(f"E(H) = {E_H}")

print("\n=== Running H2 scan ===")
results_rhf = []
results_fci = []

for R_ang in R_vals:
    R_bohr = R_ang * BOHR
    tag_base = f"{R_ang:.4f}".replace('.', '_')

    # RHF
    E_rhf = run_calc(make_inp_rhf(R_bohr), f"h2_rhf_{tag_base}", is_fci=False)
    results_rhf.append((R_ang, E_rhf))

    # FCI
    E_fci = run_calc(make_inp_fci(R_bohr), f"h2_fci_{tag_base}", is_fci=True)
    results_fci.append((R_ang, E_fci))

    print(f"R={R_ang:.3f} A: RHF={E_rhf}, FCI={E_fci}")

# Save results
import json
results = {
    'E_H': E_H,
    'rhf': results_rhf,
    'fci': results_fci
}
with open(os.path.join(WORKDIR, 'results.json'), 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to {WORKDIR}/results.json")
