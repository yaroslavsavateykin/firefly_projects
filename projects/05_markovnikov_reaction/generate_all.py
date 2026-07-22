#!/usr/bin/env python3
"""
Generate all Firefly input files for the Markovnikov C3H7F reaction path.

Usage:
  python generate_all.py

Then:
  ./run_all.sh
  python parse_energies.py   # scan energies → find max → generate hessian/sadpoint/irc
"""

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# ── 1. Read geodesic_interpolation.xyz and extract frames ──────────────
with open(os.path.join(BASE, "geodesic_interpolation.xyz")) as f:
    lines = f.readlines()

def parse_frames(raw):
    frames = []
    i = 0
    while i < len(raw):
        line = raw[i].strip()
        if not line:
            i += 1
            continue
        try:
            nat = int(line)
        except ValueError:
            i += 1
            continue
        title = raw[i + 1].strip()
        coords = []
        for j in range(nat):
            parts = raw[i + 2 + j].strip().split()
            if len(parts) >= 4:
                elem = parts[0]
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                coords.append((elem, x, y, z))
        frames.append((title, coords))
        i += 2 + nat
    return frames

frames = parse_frames(lines)
print(f"Parsed {len(frames)} frames from geodesic_interpolation.xyz")

# ── 2. Template for the $DATA block (basis set per atom type) ──────────
# We reuse the basis from the original C3H7F system.
# The template preserves the $DATA header + basis functions, and we just
# replace the coordinates.

# Read the template from the original scan_00.inp
def read_template(path):
    with open(path) as f:
        content = f.read()
    return content

# Build coordinates line for a given atom
def coord_line(atom_type, elem, x, y, z):
    return f"{elem:>5}   {atom_type:<5}  {x:>20.10f}  {y:>20.10f}  {z:>20.10f}"

ATOM_MAP = {"C": 6.0, "H": 1.0, "F": 9.0}

# ── 3. Generate scan directories (c3h7f_scan_00 .. c3h7f_scan_10) ──────

# We need atomic basis templates per atom type.
# Parse the original c3h7f_scan_00.inp to extract basis blocks per atom type.
# Actually, let's just parse the $DATA section and replace coordinates.

def parse_data_section(inp_path):
    """Parse $DATA section from a Firefly input file.
    Returns (system_name, point_group, atom_blocks)
    where atom_blocks is a list of (element, zval, x, y, z, basis_lines)
    """
    with open(inp_path) as f:
        content = f.read()

    data_start = content.find("$DATA")
    data_end = content.find("$END", data_start)
    data_text = content[data_start:data_end]

    lines = data_text.split("\n")
    # Skip $DATA line
    lines = lines[1:]

    system_name = lines[0].strip()
    point_group = lines[1].strip()

    atom_blocks = []
    i = 2
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("!"):
            i += 1
            continue
        parts = line.split()
        if len(parts) < 4:
            i += 1
            continue
        try:
            zval = float(parts[1])
        except ValueError:
            i += 1
            continue
        elem = parts[0]
        x, y, z = float(parts[2]), float(parts[3]), float(parts[4])
        # Collect basis lines until the next atom line or $END
        basis_lines = []
        i += 1
        while i < len(lines):
            l = lines[i]
            stripped = l.strip()
            if stripped == "" or stripped.startswith("$END"):
                break
            # Check if this looks like a new atom line (element + number + 3 numbers)
            parts2 = l.split()
            if len(parts2) >= 5:
                try:
                    _ = float(parts2[1])
                    __ = float(parts2[2])
                    ___ = float(parts2[3])
                    ____ = float(parts2[4])
                    # This is a new atom line
                    break
                except ValueError:
                    pass
            basis_lines.append(l.rstrip())
            i += 1

        atom_blocks.append({
            "elem": elem,
            "zval": zval,
            "x": x, "y": y, "z": z,
            "basis_lines": basis_lines
        })

    return system_name, point_group, atom_blocks

scan_template_path = os.path.join(BASE, "c3h7f_scan_00", "c3h7f_scan_00.inp")
sys_name, pg, atom_blocks_template = parse_data_section(scan_template_path)

print(f"System: {sys_name}, Point group: {pg}, Atoms: {len(atom_blocks_template)}")

# The atom order in the template: C, C, C, H, H, H, H, H, H, H, F
# Map element type to its basis block
elem_to_basis = {}
for ab in atom_blocks_template:
    if ab["elem"] not in elem_to_basis:
        elem_to_basis[ab["elem"]] = ab["basis_lines"]

def make_inp_content(elem_order, coords_list, runtyp="ENERGY", extra=""):
    """Generate a Firefly input file content."""
    lines = []
    lines.append(f" $CONTRL SCFTYP=RHF RUNTYP={runtyp} ICHARG=0 MULT=1 DFTTYP=B3LYP EXETYP=RUN")
    lines.append("       INTTYP=HONDO ICUT=13 ITOL=30 D5=.T. MAXIT=100 GENCON=.F. WIDE=1 FSTINT=.T.")
    lines.append(" $END")
    lines.append(" $SYSTEM TIMLIM=60000 MWORDS=200 MASMEM=200000000 MXBCST=-1 KDIAG=0 NOJAC=1 $END")
    lines.append(" $MOORTH NOSTF=.T. NOZERO=.T. SYMS=.T. SYMDEN=.T. SYMVEC=.T. SYMVX=.T.")
    lines.append("       TOLE=0.0D0 TOLZ=0.0D0 $END")
    lines.append(" $GUESS GUESS=HUCKEL $END")

    if "HESSIAN" in runtyp:
        lines.append(" $FORCE NVIB=2 $END")
    if "SADPOINT" in runtyp:
        lines.append(" $STATPT METHOD=QA OPTTOL=1D-04 NSTEP=100 HSSEND=.T. UPHESS=POWELL IFOLOW=1")
        lines.append("       ITBMAT=300 HESS=READ $END")
        lines.append(f" ! [qphorus:disabled] FORCE")
        lines.append(f" !  $FORCE NVIB=2 $END")
    if "IRC" in runtyp:
        lines.append(" $SCF DIRSCF=.T. FDIFF=.F. DIIS=.T. DAMP=.T. SHIFT=.T. SOSCF=.F. $END")
    else:
        lines.append(" $SCF DIRSCF=.T. FDIFF=.F. DIIS=.T. DAMP=.T. SHIFT=.T. SOSCF=.F. $END")

    # $DATA
    lines.append(" $DATA")
    lines.append(" C3H7F")
    lines.append(" C1")

    for elem, (x, y, z) in zip(elem_order, coords_list):
        zval = ATOM_MAP[elem]
        lines.append(f"{elem:>5}   {zval:<5}  {x:>20.10f}  {y:>20.10f}  {z:>20.10f}")
        for bl in elem_to_basis[elem]:
            lines.append(bl)

    lines.append("")
    lines.append(" $END")

    return "\n".join(lines)

# Element order from template
elem_order = [ab["elem"] for ab in atom_blocks_template]

# Generate scan directories
NUM_SCAN = len(frames)
for idx, (title, coords) in enumerate(frames):
    dirname = f"c3h7f_scan_{idx:02d}"
    scandir = os.path.join(BASE, dirname)
    os.makedirs(scandir, exist_ok=True)

    inp_content = make_inp_content(elem_order, [c[1:] for c in coords], runtyp="ENERGY")
    inp_path = os.path.join(scandir, f"{dirname}.inp")
    with open(inp_path, "w") as f:
        f.write(inp_content)

    # run.sh
    run_sh = os.path.join(BASE, "new_file_opt_00", "run.sh")
    shutil.copy(run_sh, os.path.join(scandir, "run.sh"))

    print(f"  Created {dirname}/")

# ── 4. Fix new_file_opt_01 with Frame 11 (product endpoint) ────────────
prod_frame = frames[-1]  # Frame 11
opt01_dir = os.path.join(BASE, "new_file_opt_01")

# The original new_file_opt_01 was copied from 00, fix the geometry
inp_path_01 = os.path.join(opt01_dir, "new_file_opt_01.inp")
with open(inp_path_01) as f:
    inp01_content = f.read()

# We need to replace the coordinates
# Read the template opt_00.inp to get the structure
opt00_template = os.path.join(BASE, "new_file_opt_00", "new_file_opt_00.inp")
sys_name_opt, pg_opt, atom_blocks_opt = parse_data_section(opt00_template)

elem_order_opt = [ab["elem"] for ab in atom_blocks_opt]

# Generate opt_01 with product geometry
inp01_new = make_inp_content(elem_order_opt, [c[1:] for c in prod_frame[1]], runtyp="OPTIMIZE")
inp01_new = inp01_new.replace(
    " $SCF DIRSCF=.T. FDIFF=.F. DIIS=.T. DAMP=.T. SHIFT=.T. SOSCF=.F. $END",
    " $STATPT METHOD=GDIIS OPTTOL=1D-04 NSTEP=100 HSSEND=.F. UPHESS=BFGS ITBMAT=300\n $END\n $SCF DIRSCF=.T. FDIFF=.F. DIIS=.T. DAMP=.T. SHIFT=.T. SOSCF=.F. $END"
).replace(
    " $GUESS GUESS=HUCKEL $END\n",
    " $GUESS GUESS=HUCKEL $END\n"
)

# Actually simpler: just add the STATPT block
lines = inp01_new.split("\n")
new_lines = []
for line in lines:
    new_lines.append(line)
    if "$GUESS" in line and "STATPT" not in inp01_new:
        new_lines.append(" $STATPT METHOD=GDIIS OPTTOL=1D-04 NSTEP=100 HSSEND=.F. UPHESS=BFGS ITBMAT=300")
        new_lines.append(" $END")

inp01_new = "\n".join(new_lines)

with open(inp_path_01, "w") as f:
    f.write(inp01_new)

# Also update the geometry xyz file
xyz_path_01 = os.path.join(opt01_dir, "new_file_opt_01_geometry.xyz")
with open(xyz_path_01, "w") as f:
    f.write(f"{len(prod_frame[1])}\n")
    f.write("Markovnikov product endpoint (Frame 11)\n")
    for elem, x, y, z in prod_frame[1]:
        f.write(f"{elem:>2}  {x:>20.10f}  {y:>20.10f}  {z:>20.10f}\n")

print(f"  Updated new_file_opt_01/ with Frame 11 geometry")

# ── 5. Generate the Hessian stub (will need to fill coordinates after running scans) ──
print("")
print("Done generating scan directories.")
print("")
print("Next steps:")
print("  1. Run: ./run_all.sh")
print("  2. Run: python parse_energies.py   # to find max and generate hessian/sadpoint/irc")
