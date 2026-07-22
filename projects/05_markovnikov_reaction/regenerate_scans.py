#!/usr/bin/env python3
"""Regenerate scan input files with proper formatting (matching reference)."""

import os, shutil

BASE = "/home/yaroslav/firefly_projects/projects/05_markovnikov_reaction"
REF_SCAN = os.path.join(BASE, "c3h7f_scan_00", "c3h7f_scan_00.inp")

# Read reference template
with open(REF_SCAN) as f:
    template = f.read()

# Find $DATA section to understand coordinate positions
with open(REF_SCAN) as f:
    lines = f.readlines()

# Find coordinate lines in template (atom header lines in $DATA)
data_start = next(i for i, l in enumerate(lines) if l.strip().startswith("$DATA"))
coord_lines_idx = []
in_data = False
for i in range(data_start + 1, len(lines)):
    stripped = lines[i].strip()
    if stripped == "$END":
        break
    if stripped.startswith("C1"):
        continue
    if stripped.startswith("C3H7F"):
        continue
    parts = stripped.split()
    if len(parts) >= 5:
        try:
            float(parts[1])
            float(parts[2])
            float(parts[3])
            float(parts[4])
            coord_lines_idx.append(i)
        except ValueError:
            pass

print(f"Found {len(coord_lines_idx)} coordinate lines in template")

# Read geodesic interpolation frames
with open(os.path.join(BASE, "geodesic_interpolation.xyz")) as f:
    xyz = f.readlines()

def parse_frames(raw):
    frames = []
    i = 0
    while i < len(raw):
        line = raw[i].strip()
        if not line:
            i += 1
            continue
        nat = int(line)
        i += 2  # skip nat and title
        coords = []
        for j in range(nat):
            parts = raw[i + j].strip().split()
            coords.append((parts[0], parts[1], parts[2], parts[3]))
        frames.append(coords)
        i += nat
    return frames

frames = parse_frames(xyz)
print(f"Parsed {len(frames)} frames")

# For each frame, replace coordinates in template and write to scan dir
for idx, coords in enumerate(frames):
    dirname = f"c3h7f_scan_{idx:02d}"
    d = os.path.join(BASE, dirname)
    os.makedirs(d, exist_ok=True)

    new_lines = list(lines)  # copy
    for j, line_idx in enumerate(coord_lines_idx):
        elem = coords[j][0]
        x, y, z = coords[j][1], coords[j][2], coords[j][3]
        old_line = new_lines[line_idx]
        # Preserve the format: element, spaces, charge, spaces, x, y, z
        parts = old_line.split()
        charge = parts[1]
        # Format: C     6.0     X     Y     Z
        xf, yf, zf = float(x), float(y), float(z)
        new_line = f"{elem:<5}  {charge:<5}  {xf:>20.10f}  {yf:>20.10f}  {zf:>20.10f}\n"
        new_lines[line_idx] = new_line

    inp_path = os.path.join(d, f"{dirname}.inp")
    with open(inp_path, "w") as f:
        f.writelines(new_lines)

    # run.sh
    run_sh = os.path.join(BASE, "new_file_opt_00", "run.sh")
    shutil.copy(run_sh, os.path.join(d, "run.sh"))

    print(f"  Updated {dirname}/")
