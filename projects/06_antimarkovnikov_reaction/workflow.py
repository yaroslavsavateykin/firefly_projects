#!/usr/bin/env python3
"""Small parsers, geometry checks, profile analysis, and Firefly $HESS round trip."""
from pathlib import Path
import argparse, csv, math, re

ROOT = Path(__file__).resolve().parent
HARTREE_TO_KJ = 2625.49962

def xyz_read(path):
    lines = Path(path).read_text().splitlines(); n = int(lines[0]); atoms = []
    for line in lines[2:2+n]:
        p = line.split(); atoms.append((p[0], *map(float, p[1:4])))
    if len(atoms) != n or n != 11 or [a[0] for a in atoms] != ["C"]*3+["H"]*7+["F"] or not all(math.isfinite(v) for a in atoms for v in a[1:]):
        raise ValueError(f"invalid XYZ: {path}")
    return atoms

def distance(a, b): return math.dist(a[1:], b[1:])
def bonds(g):
    return {"C1-C2": distance(g[0],g[1]), "C2-C3": distance(g[1],g[2]), "H10-F11": distance(g[9],g[10]), "C2-H10": distance(g[1],g[9]), "C3-F11": distance(g[2],g[10])}

def sanity(g):
    cc = [distance(g[0],g[1]), distance(g[1],g[2])]
    ch = min(distance(g[i], g[j]) for i in range(3) for j in range(3,10))
    assert 1.0 < min(cc) < 1.7 and 0.7 < ch < 1.3, f"suspect units: C-C={cc}, C-H={ch}"

def parse_energy(path):
    from launch import validate
    import hashlib, json
    path = Path(path)
    state = json.loads(path.with_suffix(".json").read_text())
    inp = path.with_suffix(".inp").read_bytes()
    if not state.get("success") or state["sha256"] != hashlib.sha256(inp).hexdigest() or state["output_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError(f"stale or failed calculation: {path}")
    return validate(path.read_text(errors="replace"), inp.decode())

def output_geometry(path):
    text = Path(path).read_text(errors="replace")
    blocks = text.split("COORDINATES OF ALL ATOMS ARE (ANGS)")[1:]
    if not blocks:
        raise ValueError("missing Angstrom geometry")
    atoms = []
    for line in blocks[-1].splitlines():
        p = line.split()
        if len(p) == 5 and p[0] in {"C","H","F"}:
            atoms.append((p[0],*map(float,p[2:])))
            if len(atoms) == 11:
                sanity(atoms); return atoms
    raise ValueError("incomplete final geometry")

def input_with_geometry(template, geometry, target):
    from generate import replace_geometry, xyz
    target = Path(target)
    target.write_text(replace_geometry(Path(template).read_text(),geometry,target.stem,"ENERGY"))
    xyz(target.with_suffix(".xyz"),geometry,target.stem)

def prepare_scan(mark=False):
    import numpy as np
    from geodesic_interpolate.interpolation import redistribute
    from geodesic_interpolate.geodesic import Geodesic
    from geodesic_interpolate.fileio import write_xyz
    name = "mark_product" if mark else "product"
    prefix = "mark_" if mark else ""
    product_out=ROOT/name/(name+".out")
    parse_energy(product_out)
    atoms = output_geometry(product_out)
    hc,fc = (2,1) if mark else (1,2)
    if not (0.95 < distance(atoms[hc],atoms[9]) < 1.2 and 1.2 < distance(atoms[fc],atoms[10]) < 1.6):
        raise ValueError("optimized product has wrong connectivity")
    from generate import xyz
    xyz(ROOT/(name+".xyz"),atoms,"Optimized "+name)
    start=xyz_read(ROOT/"reactant.xyz")
    symbols = [a[0] for a in start]
    np.random.seed(42)
    endpoints = np.array([[a[1:] for a in g] for g in [start,atoms]])
    raw = redistribute(symbols,endpoints,11,tol=1e-3)
    smoother = Geodesic(symbols,raw,1.7,threshold=3,friction=1e-2)
    smoother.smooth(tol=2e-3,max_iter=100)
    write_xyz(str(ROOT/(prefix+"geodesic_interpolation.xyz")),symbols,smoother.path)
    frames = [[(e,*r) for e,r in zip(symbols,g)] for g in smoother.path]
    for i,g in enumerate(frames):
        d=ROOT/f"{prefix}scan_{i:02d}"; d.mkdir(exist_ok=True)
        input_with_geometry(ROOT/"reactant/reactant.inp",g,d/(d.name+".inp"))

def analyse_scan(mark=False):
    prefix = "mark_" if mark else ""
    rows=[]
    for d in [ROOT/f"{prefix}scan_{i:02d}" for i in range(11)]:
        e=parse_energy(d/(d.name+".out")); g=xyz_read(d/(d.name+".xyz")) if (d/(d.name+".xyz")).exists() else None
        if e is not None and g: rows.append([d.name,e,*bonds(g).values()])
    if not rows: raise SystemExit("no completed scan outputs")
    ref=rows[0][1]
    with (ROOT/(prefix+"energy_profile.csv")).open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["frame","energy_hartree","delta_kj_mol","C1-C2_A","C2-C3_A","H10-F11_A","C2-H10_A","C3-F11_A"])
        for r in rows: w.writerow([r[0],f"{r[1]:.10f}",f"{(r[1]-ref)*HARTREE_TO_KJ:.3f}",*map(lambda x:f"{x:.6f}",r[2:])])
    peak=max(rows,key=lambda r:r[1]); (ROOT/(prefix+"scan_peak.txt")).write_text(f"{peak[0]} {peak[1]:.10f}\n")

def hess_format(matrix):
    # Firefly card format: row, sequential block number, up to five values.
    return "\n".join(f" {i+1:3d} {block+1:3d}  "+" ".join(f"{x: .16E}".replace("E","D") for x in row[5*block:5*block+5]) for i,row in enumerate(matrix) for block in range((len(row)+4)//5))

def hess_parse(text,n):
    out=[[0.0]*n for _ in range(n)]
    seen = set()
    for line in text.splitlines():
        p=line.replace("D","E").split()
        if len(p)>=3 and p[0].isdigit() and p[1].isdigit():
            i=int(p[0])-1; start=(int(p[1])-1)*5
            if not 0 <= i < n or not 0 <= start < n or len(p[2:]) != min(5,n-start):
                raise ValueError("invalid Hessian card")
            for j,x in enumerate(p[2:]):
                if (i,start+j) in seen: raise ValueError("duplicate Hessian element")
                seen.add((i,start+j)); out[i][start+j]=float(x)
    if len(seen) != n*n: raise ValueError("incomplete Hessian")
    return out

def hess_test():
    a=[[float(i*10+j)/7 for j in range(33)] for i in range(33)]
    b=hess_parse(hess_format(a),33); err=max(abs(x-y) for r,s in zip(a,b) for x,y in zip(r,s)); assert err < 1e-13, err
    print(f"$HESS round-trip max abs error: {err:.3e}")

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("command",choices=["prepare-scan","analyse-scan","hess-test"]); p.add_argument("--mark",action="store_true"); a=p.parse_args()
    if a.command == "hess-test": hess_test()
    else: {"prepare-scan":prepare_scan,"analyse-scan":analyse_scan}[a.command](a.mark)
