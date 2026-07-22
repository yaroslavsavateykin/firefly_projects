#!/usr/bin/env python3
"""Fix Hessian format in Markovnikov IRC inputs.
Convert from pair/lower-triangle to row-by-row free format.
"""
import re, os, math

BASE = os.path.dirname(os.path.abspath(__file__))

def read_hessian_pairs(path):
    """Read Hessian from $HESS block in pair format (I J value)."""
    with open(path) as f:
        text = f.read()
    
    hess_start = text.find("$HESS")
    if hess_start < 0:
        return None, None
    hess_text = text[hess_start:]
    hess_end = hess_text.find("$END")
    if hess_end < 0:
        return None, None
    
    block = hess_text[:hess_end]
    
    # Parse energy
    energy = None
    m = re.search(r"ENERGY IS\s+([-\d.]+)", block)
    if m:
        energy = float(m.group(1))
    
    # Parse pairs: I J value
    pairs = {}
    for line in block.split("\n"):
        line = line.strip()
        if not line or line.startswith("$") or "ENERGY" in line:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            i = int(parts[0])
            j = int(parts[1])
            v = float(parts[2].replace('D', 'E'))
            pairs[(i, j)] = v
        except (ValueError, IndexError):
            continue
    
    if not pairs:
        return None, None
    
    # Determine matrix size
    n = int(math.sqrt(2 * len(pairs)))  # approximate
    # Actually find max index
    max_idx = max(max(i, j) for i, j in pairs)
    n = max_idx
    
    # Build full matrix from lower triangle
    mat = [[0.0] * n for _ in range(n)]
    for (i, j), v in pairs.items():
        mat[i-1][j-1] = v
        mat[j-1][i-1] = v  # symmetrize
    
    return energy, mat

def write_hessian_free_format(mat):
    """Convert matrix to Firefly free-format lines (row-by-row, 5 elements per line)."""
    n = len(mat)
    lines = []
    for i in range(n):
        line_parts = []
        for j in range(n):
            line_parts.append(f"{mat[i][j]:24.16E}".replace('E', 'D'))
            if len(line_parts) == 5 or (j == n - 1 and line_parts):
                idx_str = f"{i+1:3d}{i+1:3d}" if j == 0 else f"{i+1:3d}{j-3:3d}"  # hack
                # Actually the format is: row col val1 val2 val3 val4 val5
                # where row and col are the starting position
                col_start = j - len(line_parts) + 1
                lines.append(f" {i+1:3d} {col_start:3d}  " + " ".join(line_parts))
                line_parts = []
    return "\n".join(lines)

def write_hessian_free_format_v2(mat):
    """Write in the exact format that working anti-Markovnikov IRC uses.
    Format: I J val1 val2 val3 val4 val5   (5 or up to 7 per line)
    Where I is row, J is starting column, and values are columns J through J+4
    """
    n = len(mat)
    lines = []
    for i in range(n):
        row = mat[i]
        col = 0
        while col < n:
            remaining = n - col
            chunk_size = min(5, remaining)
            vals = row[col:col+chunk_size]
            line = f" {i+1:3d} {col+1:3d}  " + " ".join(f"{v:24.16E}".replace('E', 'D') for v in vals)
            lines.append(line)
            col += chunk_size
    return "\n".join(lines)

def write_hessian_free_format_v3(mat):
    """Exact format from the working anti-Markovnikov example.
    Looking at:
     1  1  5.59453230065534500D-01  1.26650391081748600D-02  ...
     1  2 -1.75826137125499000D-02 ...
     1  7 -4.68292953325640000D-03 ...
     2  1  1.26650391081748600D-02 ...
     
    It seems like: I J val1 val2 ... val7 (7 per row line)
    No, the values go: row 1 col 1 through 5 (5 vals), then row 1 col 6 through 10... 
    Wait, the second line says "1  2" which would mean row 1 starting at col 2 with 5 vals.
    But that means col 2 through col 6.
    Then "1  7" means row 1 starting col 7 with 3 vals remaining.
    
    So it's 5 per line for big rows, and the starting column is J.
    """
    n = len(mat)
    lines = []
    for i in range(n):
        row = mat[i]
        col = 0
        while col < n:
            remaining = n - col
            chunk_size = min(5, remaining)
            vals = row[col:col+chunk_size]
            parts = [f"{v:24.16E}".replace('E', 'D') for v in vals]
            line = f" {i+1:3d} {col+1:3d}  " + " ".join(parts)
            lines.append(line)
            col += chunk_size
    return "\n".join(lines)

def fix_irc_input(inp_path):
    """Fix Hessian in an IRC input file."""
    with open(inp_path) as f:
        text = f.read()
    
    energy, mat = read_hessian_pairs(inp_path)
    if energy is None or mat is None:
        print(f"  Could not parse Hessian from {inp_path}")
        return False
    
    n = len(mat)
    print(f"  Matrix: {n}x{n}, energy={energy:.10f}")
    
    hess_free = write_hessian_free_format_v3(mat)
    
    # Replace $HESS block
    hess_start = text.find("$HESS")
    hess_text = text[hess_start:]
    hess_end = hess_text.find("$END")
    if hess_end < 0:
        print("  No $END after $HESS")
        return False
    
    old_block = hess_text[:hess_end + 5]  # include $END
    
    new_block = f"$HESS\nENERGY IS     {energy:.10f} E(NUC) IS      0.0\n{hess_free}\n $END"
    
    new_text = text.replace(old_block, new_block)
    
    # Write
    with open(inp_path, 'w') as f:
        f.write(new_text)
    
    print(f"  Fixed and wrote {inp_path}")
    return True

# Fix both IRC inputs
for suffix in ["c3h7f_irc_step_19", "c3h7f_irc_reverse_step_19"]:
    path = os.path.join(BASE, suffix, f"{suffix}.inp")
    if os.path.exists(path):
        print(f"Fixing {suffix}...")
        ok = fix_irc_input(path)
        if ok:
            print(f"  OK")
        else:
            print(f"  FAILED")
    else:
        print(f"  {suffix} not found")
