#!/usr/bin/env python3
"""
Post-processing script for Markovnikov C3H7F reaction path.

Stages (run with --stage N):
  1. Parse all scan outputs → find max energy frame
  2. Generate hessian input for max frame
  3. Parse hessian output → generate sadpoint input
  4. Parse sadpoint output → generate IRC forward/reverse inputs
  5. Print summary

Usage:
  # After running all scans:
  python parse_energies.py --stage 1
  # After hessian completes:
  python parse_energies.py --stage 2   (or --stage 3 to do both)
  # After sadpoint completes:
  python parse_energies.py --stage 4
  # Full pipeline:
  python parse_energies.py --stage all
"""

import os
import re
import sys
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))

ATOM_MAP = {"C": 6.0, "H": 1.0, "F": 9.0}

# ── Parsing helpers ──────────────────────────────────────────────────────

def parse_energy_from_out(out_path):
    """Return total energy from a Firefly output file."""
    if not os.path.exists(out_path):
        return None
    with open(out_path) as f:
        text = f.read()
    # Look for "TOTAL ENERGY = " pattern
    m = re.search(r"TOTAL ENERGY\s*=\s*([-\d.]+)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"TOTAL ENERGY\s+=\s+([-\d.]+)", text)
    if m:
        return float(m.group(1))
    return None

def parse_geometry_from_out(out_path):
    """Extract final geometry from a Firefly output file.
    Returns list of (elem, x, y, z) or None.
    Looks for the last 'CARTESIAN COORDINATES' block's atomic coordinates.
    """
    if not os.path.exists(out_path):
        return None
    with open(out_path) as f:
        text = f.read()

    # Find all CARTESIAN COORDINATES blocks
    blocks = re.split(r"CARTESIAN COORDINATES\s*\n\s*ATOM\s+CHARGE\s+X\s+Y\s+Z\s*\n-+\s*\n?", text)

    coords = None
    for block in blocks:
        if not block.strip():
            continue
        lines = block.strip().split("\n")
        atoms = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("-") or line.startswith("ATOM") or line.startswith("THE"):
                continue
            parts = line.split()
            if len(parts) >= 5 and "TOTAL" not in line and "NUCLEAR" not in line:
                try:
                    elem = parts[0]
                    # Remove trailing digits if any (e.g., "C1" → "C")
                    elem_clean = re.sub(r'\d+$', '', elem)
                    x = float(parts[2])
                    y = float(parts[3])
                    z = float(parts[4])
                    atoms.append((elem_clean, x, y, z))
                except (ValueError, IndexError):
                    pass
        if len(atoms) == 11:  # C3H7F
            coords = atoms
    return coords

def parse_hessian_from_out(out_path):
    """Extract Hessian matrix from a Firefly output file.
    Returns energy and list of hessian lines.
    """
    if not os.path.exists(out_path):
        return None, None

    with open(out_path) as f:
        text = f.read()

    # Find TOTAL ENERGY
    energy = parse_energy_from_out(out_path)

    # Find $HESS block (should be at the end)
    hess_start = text.find("$HESS")
    if hess_start == -1:
        return None, None

    hess_text = text[hess_start:]
    hess_end = hess_text.find("$END")
    if hess_end == -1:
        hess_end = len(hess_text)

    block = hess_text[:hess_end]

    # Parse the energy line
    energy_line = ""
    m = re.search(r"ENERGY IS\s+([-\d.]+)\s+E\(NUC\)", block)
    if m:
        energy_line = f"ENERGY IS     {m.group(1)} E(NUC) IS      0.0"

    hess_lines = [energy_line]
    # Get data lines
    for line in block.split("\n"):
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("$"):
            continue
        if "ENERGY" in line_stripped and "E(NUC)" in line_stripped:
            continue
        hess_lines.append(line_stripped)

    return energy, [l for l in hess_lines if l]

def frame_coords_from_xyz(idx):
    """Return coordinates for frame idx from geodesic_interpolation.xyz"""
    xyz_path = os.path.join(BASE, "geodesic_interpolation.xyz")
    with open(xyz_path) as f:
        lines = f.readlines()

    i = 0
    frame = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        try:
            nat = int(line)
        except ValueError:
            i += 1
            continue
        if frame == idx:
            coords = []
            for j in range(nat):
                parts = lines[i + 2 + j].strip().split()
                if len(parts) >= 4:
                    coords.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
            return coords
        frame += 1
        i += 2 + nat
    return None

# ── Template operations ──────────────────────────────────────────────────

def read_elem_basis_from_scan(inp_path):
    """Read an ENERGY input file and return (system_name, point_group, elem_order, elem_to_basis)."""
    with open(inp_path) as f:
        content = f.read()

    data_start = content.find("$DATA")
    data_end = content.find("$END", data_start)
    data_text = content[data_start:data_end]

    lines = data_text.split("\n")[1:]
    system = lines[0].strip()
    pg = lines[1].strip()

    elem_to_basis = {}
    elem_order = []
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
            _ = float(parts[1])
        except ValueError:
            i += 1
            continue
        elem = parts[0]
        basis_lines = []
        elem_order.append(elem)
        i += 1
        while i < len(lines):
            l = lines[i].rstrip()
            stripped = l.strip()
            if stripped == "" or stripped.startswith("$END"):
                break
            parts2 = l.split()
            if len(parts2) >= 5:
                try:
                    _ = float(parts2[1])
                    _ = float(parts2[2])
                    _ = float(parts2[3])
                    _ = float(parts2[4])
                    break
                except ValueError:
                    pass
            basis_lines.append(l)
            i += 1
        if elem not in elem_to_basis:
            elem_to_basis[elem] = basis_lines
    return system, pg, elem_order, elem_to_basis

REF_SCAN = os.path.join(BASE, "c3h7f_scan_00", "c3h7f_scan_00.inp")
system, pg, elem_order, elem_to_basis = read_elem_basis_from_scan(REF_SCAN)

def make_inp(geom, runtyp="ENERGY", extra_blocks="", hess_block=""):
    """Generate a Firefly input file with given geometry and run type."""
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
        lines.append(" ! [qphorus:disabled] FORCE")
        lines.append(" !  $FORCE NVIB=2 $END")
    if "IRC" in runtyp:
        # Keep IRC block
        pass
    lines.append(" $SCF DIRSCF=.T. FDIFF=.F. DIIS=.T. DAMP=.T. SHIFT=.T. SOSCF=.F. $END")
    if extra_blocks:
        lines.append(extra_blocks)
    lines.append(" $DATA")
    lines.append(" C3H7F")
    lines.append(" C1")

    for elem, x, y, z in geom:
        zval = ATOM_MAP[elem]
        lines.append(f"{elem:>5}   {zval:<5}  {x:>20.10f}  {y:>20.10f}  {z:>20.10f}")
        for bl in elem_to_basis[elem]:
            lines.append(bl)

    lines.append("")
    lines.append(" $END")
    if hess_block:
        lines.append(hess_block)

    return "\n".join(lines)

# ── Stages ────────────────────────────────────────────────────────────────

def stage1_find_max():
    """Parse all scan outputs, print energy table, return (max_idx, max_energy, max_coords)."""
    print("=" * 60)
    print("Stage 1: Parsing scan energies")
    print("=" * 60)

    energies = []
    for idx in range(11):
        dirname = f"c3h7f_scan_{idx:02d}"
        out_path = os.path.join(BASE, dirname, f"{dirname}.out")
        energy = parse_energy_from_out(out_path)
        energies.append(energy)

    # Print table
    print(f"\n{'Frame':<8} {'Energy (hartree)':<22} {'dE (kJ/mol)':<15} {'File exists':<12}")
    print("-" * 60)
    ref_e = energies[0] if energies[0] is not None else 0.0
    max_idx = 0
    max_energy = energies[0]
    for i, e in enumerate(energies):
        exists = "YES" if e is not None else "NO"
        de = (e - ref_e) * 2625.5 if e is not None else 0.0
        e_str = f"{e:.10f}" if e is not None else "N/A"
        print(f"scan_{i:02d}   {e_str:<22} {de:<15.2f} {exists:<12}")
        if e is not None and (max_energy is None or e > max_energy):
            max_energy = e
            max_idx = i

    if max_energy is None:
        print("\nNo scan outputs found. Run scans first!")
        return None, None, None

    print(f"\nMaximum energy: scan_{max_idx:02d} = {max_energy:.10f} hartree")
    max_coords = frame_coords_from_xyz(max_idx)
    if max_coords:
        print(f"Max frame coordinates: {len(max_coords)} atoms loaded from geodesic_interpolation.xyz")
    return max_idx, max_energy, max_coords

def stage2_generate_hessian(max_idx, max_energy, max_coords):
    """Generate hessian input for the max frame."""
    print("\n" + "=" * 60)
    print("Stage 2: Generating hessian input")
    print("=" * 60)

    hess_dir = os.path.join(BASE, "c3h7f_hessian")
    os.makedirs(hess_dir, exist_ok=True)

    inp = make_inp(max_coords, runtyp="HESSIAN")

    inp_path = os.path.join(hess_dir, "c3h7f_hessian.inp")
    with open(inp_path, "w") as f:
        f.write(inp)

    # Copy run.sh
    shutil.copy(
        os.path.join(BASE, "new_file_opt_00", "run.sh"),
        os.path.join(hess_dir, "run.sh")
    )

    print(f"  Created: {inp_path}")
    print(f"  Next: run ./run_all.sh or cd c3h7f_hessian && ./run.sh")

def stage3_generate_sadpoint():
    """Parse hessian output and generate sadpoint input."""
    print("\n" + "=" * 60)
    print("Stage 3: Generating sadpoint input from hessian output")
    print("=" * 60)

    hess_dir = os.path.join(BASE, "c3h7f_hessian")
    hess_out = os.path.join(hess_dir, "c3h7f_hessian.out")

    if not os.path.exists(hess_out):
        print(f"  ERROR: {hess_out} not found. Run hessian first!")
        return False

    # Get geometry from hessian output
    geom = parse_geometry_from_out(hess_out)
    if geom is None:
        # Fall back to max frame geometry
        print("  Could not parse geometry from hessian output, using scan max frame")
        # Read max frame number
        # We'll get it from the config
        return False

    # Get Hessian matrix
    energy, hess_lines = parse_hessian_from_out(hess_out)
    if hess_lines is None or len(hess_lines) < 2:
        print(f"  Could not parse Hessian from {hess_out}")
        return False

    # Get energy
    e_hess = parse_energy_from_out(hess_out)
    if e_hess is None:
        print(f"  Could not parse energy from {hess_out}")
        return False

    print(f"  Hessian energy: {e_hess:.10f} hartree")
    print(f"  Geometry: {len(geom)} atoms")
    print(f"  Hessian lines: {len(hess_lines)}")

    # Build $HESS block
    hess_block_lines = [" $HESS"]
    hess_block_lines.append(f"ENERGY IS     {e_hess:.10f} E(NUC) IS      0.0")
    for hl in hess_lines:
        if "ENERGY" in hl and "E(NUC)" in hl:
            continue
        hess_block_lines.append(hl)
    hess_block_lines.append(" $END")
    hess_block = "\n".join(hess_block_lines)

    inp = make_inp(geom, runtyp="SADPOINT", hess_block=hess_block)

    sad_dir = os.path.join(BASE, "c3h7f_sadpoint")
    os.makedirs(sad_dir, exist_ok=True)

    inp_path = os.path.join(sad_dir, "c3h7f_sadpoint.inp")
    with open(inp_path, "w") as f:
        f.write(inp)

    # Copy run.sh
    import shutil
    shutil.copy(
        os.path.join(BASE, "new_file_opt_00", "run.sh"),
        os.path.join(sad_dir, "run.sh")
    )

    print(f"  Created: {inp_path}")
    return True

def stage4_generate_irc():
    """Parse sadpoint output and generate IRC forward/reverse inputs."""
    print("\n" + "=" * 60)
    print("Stage 4: Generating IRC inputs from sadpoint output")
    print("=" * 60)

    sad_dir = os.path.join(BASE, "c3h7f_sadpoint")
    sad_out = os.path.join(sad_dir, "c3h7f_sadpoint.out")

    if not os.path.exists(sad_out):
        print(f"  ERROR: {sad_out} not found. Run sadpoint first!")
        return False

    # Get TS geometry from sadpoint output
    geom = parse_geometry_from_out(sad_out)
    if geom is None:
        print("  Could not parse geometry from sadpoint output")
        return False

    # Get energy and Hessian
    e_sad = parse_energy_from_out(sad_out)
    if e_sad is None:
        print(f"  Could not parse energy from {sad_out}")
        return False

    # Try to get Hessian
    _, hess_lines = parse_hessian_from_out(sad_out)
    if hess_lines is None or len(hess_lines) < 2:
        # Fall back to hessian's hessian
        print("  No Hessian in sadpoint output, falling back to hessian")
        hess_dir = os.path.join(BASE, "c3h7f_hessian")
        hess_out = os.path.join(hess_dir, "c3h7f_hessian.out")
        _, hess_lines = parse_hessian_from_out(hess_out)

    if hess_lines is None or len(hess_lines) < 2:
        print("  Could not get Hessian for IRC")
        return False

    # Get the IRC step geometry from sadpoint
    # In sadpoint output, the final optimized TS geometry should be used
    # For IRC, we use the same geometry as sadpoint (the TS)

    print(f"  TS energy: {e_sad:.10f} hartree")
    print(f"  TS geometry: {len(geom)} atoms")

    # Build $HESS block for IRC
    hess_block_lines = [" $HESS"]
    hess_block_lines.append(f"ENERGY IS     {e_sad:.10f} E(NUC) IS      0.0")
    for hl in hess_lines:
        if "ENERGY" in hl and "E(NUC)" in hl:
            continue
        hess_block_lines.append(hl)
    hess_block_lines.append(" $END")
    hess_block = "\n".join(hess_block_lines)

    # Generate forward IRC
    for direction, suffix in [("FORWRD=.T.", "c3h7f_irc_step_19"), ("FORWRD=.F.", "c3h7f_irc_reverse_step_19")]:
        irc_dir = os.path.join(BASE, suffix)
        os.makedirs(irc_dir, exist_ok=True)

        extra = f" $IRC {direction} MXOPT=100 NPOINT=35 PACE=GS2 SADDLE=.T. $END"
        inp = make_inp(geom, runtyp="IRC", extra_blocks=extra, hess_block=hess_block)

        inp_path = os.path.join(irc_dir, f"{suffix}.inp")
        with open(inp_path, "w") as f:
            f.write(inp)

        # Copy run.sh
        import shutil
        shutil.copy(
            os.path.join(BASE, "new_file_opt_00", "run.sh"),
            os.path.join(irc_dir, "run.sh")
        )

        print(f"  Created: {inp_path}")

    return True

# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Parse energies and generate hessian/sadpoint/IRC inputs")
    parser.add_argument("--stage", default="all",
                       choices=["1", "2", "3", "4", "all"],
                       help="Stage to run (1=find max, 2=generate hessian, 3=generate sadpoint, 4=generate IRC)")
    args = parser.parse_args()

    import shutil
    global shutil

    stages = ["1", "2", "3", "4"] if args.stage == "all" else [args.stage]

    # Track max frame info across stages
    max_idx = None
    max_energy = None
    max_coords = None

    for s in stages:
        if s == "1":
            max_idx, max_energy, max_coords = stage1_find_max()
            if max_idx is None:
                print("Stage 1 failed. Aborting.")
                return
            # Save max info for other stages
            config_path = os.path.join(BASE, ".max_frame_config")
            with open(config_path, "w") as f:
                f.write(f"{max_idx} {max_energy:.10f}\n")
            print(f"  Saved max frame info to .max_frame_config")
        elif s == "2":
            if max_idx is None:
                config_path = os.path.join(BASE, ".max_frame_config")
                if os.path.exists(config_path):
                    with open(config_path) as f:
                        line = f.readline().strip()
                        parts = line.split()
                        max_idx = int(parts[0])
                        max_energy = float(parts[1])
                        max_coords = frame_coords_from_xyz(max_idx)
                else:
                    print("No saved config. Run stage 1 first.")
                    return
            stage2_generate_hessian(max_idx, max_energy, max_coords)
        elif s == "3":
            stage3_generate_sadpoint()
        elif s == "4":
            stage4_generate_irc()

if __name__ == "__main__":
    main()
