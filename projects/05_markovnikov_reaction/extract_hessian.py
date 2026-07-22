#!/usr/bin/env python3
"""Extract Hessian from Firefly output and write $HESS block."""
import re, sys

def extract_hessian(outpath):
    with open(outpath) as f:
        text = f.read()

    idx = text.find("CARTESIAN FORCE CONSTANT MATRIX")
    if idx == -1:
        return None, None

    chunk = text[idx:]
    # skip header lines
    lines = chunk.split("\n")
    data_start = 0
    for i, l in enumerate(lines):
        if l.strip().startswith("1") and "C" in l and "X" in l:
            data_start = i
            break

    matrix = [[0.0]*33 for _ in range(33)]
    row = 0
    i = data_start
    while row < 33 and i < len(lines):
        l = lines[i]
        # Extract numbers from a line
        nums = [float(m) for m in re.findall(r'[-+]?\d*\.\d+(?:[DdEe][-+]?\d+)?', l)]
        # Filter out just the 6 numbers per row segment
        # Each row has up to 5 segments of 6 values (or less for the last)
        if not nums:
            i += 1
            continue
        # Check if this is a data row (has atomic label + X/Y/Z)
        stripped = l.strip()
        if not any(c.isalpha() for c in stripped[:3]):
            i += 1
            continue
        parts = stripped.split()
        if len(parts) < 5:
            i += 1
            continue
        # Check if last part looks like a coords line
        if not parts[0].isdigit():
            i += 1
            continue
        # This row belongs to the matrix - collect continuation lines
        all_vals = []
        j = i
        while j < len(lines):
            sl = lines[j].rstrip()
            subnums = re.findall(r'[-+]?\d*\.\d+(?:[DdEe][-+]?\d+)?', sl)
            if not subnums:
                j += 1
                continue
            sstripped = sl.strip()
            nparts = sstripped.split()
            # Check if next row starts
            if len(nparts) >= 1 and nparts[0].isdigit() and len(sstripped) > 3 and sstripped[0].isdigit() and j > i:
                if sum(1 for c in sstripped[:10] if c.isalpha()) > 0:
                    # This is a new row
                    break
            # Check for X/Y/Z label at start
            if any(tok in sstripped[:5] for tok in ['X ', 'Y ', 'Z ']):
                pass
            all_vals.extend(float(v) for v in subnums)
            j += 1
            if len(all_vals) >= 33:
                break

        if row < 33:
            for col, val in enumerate(all_vals[:33]):
                matrix[row][col] = val
        row += 1
        i += 1

    return matrix, text

def matrix_to_hess_block(matrix, text):
    m = re.search(r"TOTAL ENERGY\s*=\s*([-\d.]+)", text)
    energy = float(m.group(1)) if m else 0.0
    m2 = re.search(r"E\(NUC\)\s+=\s+([-\d.]+)", text)
    enuc = float(m2.group(1)) if m2 else 0.0

    lines = [" $HESS"]
    lines.append(f"ENERGY IS     {energy:.10f} E(NUC) IS      {enuc:.10f}")
    nz = 0
    for i in range(33):
        for j in range(i, 33):
            val = matrix[i][j]
            if abs(val) < 1e-12:
                continue
            nz += 1
            lines.append(f"{i+1:2d} {j+1:2d} {val:24.15E}")
    lines.append(" $END")
    return "\n".join(lines), energy

if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else "c3h7f_hessian/c3h7f_hessian.out"
    out = sys.argv[2] if len(sys.argv) > 2 else "c3h7f_hessian_hess_block.txt"

    matrix, text = extract_hessian(inp)
    if matrix is None:
        print("Could not extract Hessian matrix")
        sys.exit(1)

    block, energy = matrix_to_hess_block(matrix, text)
    with open(out, "w") as f:
        f.write(block)

    nlines = len(block.split("\n")) - 2
    print(f"Extracted Hessian: 33x33, {nlines} entries, energy={energy:.10f}")
    print("\n".join(block.split("\n")[:6]))
