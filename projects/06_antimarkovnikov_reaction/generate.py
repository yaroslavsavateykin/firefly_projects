#!/usr/bin/env python3
"""Generate the reproducible HF + propene anti-Markovnikov workflow."""
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parent
REF = ROOT.parent / "05_markovnikov_reaction" / "c3h7f_scan_00" / "c3h7f_scan_00.inp"
ELEMENTS = ["C", "C", "C", "H", "H", "H", "H", "H", "H", "H", "F"]
Z = {"C": 6.0, "H": 1.0, "F": 9.0}

def reference_geometry():
    text = REF.read_text()
    data = text.split("$DATA", 1)[1].split("$END", 1)[0]
    atoms = []
    for line in data.splitlines()[2:]:
        p = line.split()
        if len(p) == 5 and p[0] in Z:
            try:
                atoms.append((p[0], *map(float, p[2:])))
            except ValueError:
                pass
    assert len(atoms) == 11, len(atoms)
    return atoms

def replace_geometry(template, geometry, title, runtyp, blocks=""):
    text = template
    text = re.sub(r"RUNTYP=\w+", f"RUNTYP={runtyp}", text, count=1)
    text = re.sub(r"\bUNITS=\w+\s*", "", text)
    text = text.replace("$CONTRL", "$CONTRL UNITS=ANGS", 1)
    before, data_and_after = text.split("$DATA", 1)
    data, after = data_and_after.split("$END", 1)
    lines = data.splitlines()
    lines[1] = " " + title
    atom = 0
    for i, line in enumerate(lines):
        p = line.split()
        if len(p) == 5 and p[0] in Z:
            e, x, y, z = geometry[atom]
            lines[i] = ("\n" if atom and lines[i-1].strip() else "") + f" {e} {Z[e]:.1f} {x:.10f} {y:.10f} {z:.10f}"
            atom += 1
    assert atom == 11
    before = re.sub(r"\s*\$SMP.*?\$END", "", before, flags=re.S)
    before = "\n".join(textwrap.fill(line, width=78, subsequent_indent="  ", break_long_words=False) for line in before.splitlines())
    return before.rstrip() + "\n $SMP NP=1 MKLNP=1 TPOOL=1 $END\n" + blocks + " $DATA" + "\n".join(lines).rstrip() + "\n\n $END" + after

def xyz(path, geometry, label):
    path.write_text(f"{len(geometry)}\n{label}; coordinates in Angstrom\n" + "\n".join(
        f"{e:2s} {x: .10f} {y: .10f} {z: .10f}" for e, x, y, z in geometry) + "\n")

def write_input(directory, name, geometry, runtyp, blocks=""):
    directory.mkdir(parents=True, exist_ok=True)
    template = REF.read_text()
    (directory / f"{name}.inp").write_text(replace_geometry(template, geometry, name, runtyp, blocks))
    xyz(directory / f"{name}.xyz", geometry, name)

def product_geometry(reactant, mark=False):
    import numpy as np
    from rdkit import Chem
    from rdkit.Chem import AllChem
    mol = Chem.RWMol()
    for e in ELEMENTS:
        mol.AddAtom(Chem.Atom(e))
    edges = [(0,1),(1,2),(0,3),(0,4),(0,5),(1,6),(2,7),(2,8),
             (2 if mark else 1,9),(1 if mark else 2,10)]
    for a,b in edges:
        mol.AddBond(a,b,Chem.BondType.SINGLE)
    mol = mol.GetMol(); Chem.SanitizeMol(mol)
    if AllChem.EmbedMolecule(mol, randomSeed=42) != 0:
        raise RuntimeError("product embedding failed")
    if AllChem.MMFFOptimizeMolecule(mol, maxIters=1000) != 0:
        raise RuntimeError("product seed force-field optimization failed")
    coords = mol.GetConformer().GetPositions()
    target = np.array([a[1:] for a in reactant])
    center = coords[:9].mean(axis=0); dest = target[:9].mean(axis=0)
    u, _, vt = np.linalg.svd((coords[:9]-center).T @ (target[:9]-dest))
    rotation = u @ np.diag([1,1,np.linalg.det(u @ vt)]) @ vt
    coords = (coords-center) @ rotation + dest
    return [(e,*r) for e,r in zip(ELEMENTS,coords)]

def main():
    reactant = reference_geometry()
    xyz(ROOT / "reactant.xyz", reactant, "Shared reactant from 05 scan 00 input")
    write_input(ROOT / "reactant", "reactant", reactant, "ENERGY")
    for mark, name in [(False,"product"),(True,"mark_product")]:
        seed = product_geometry(reactant, mark)
        xyz(ROOT / (name+"_seed.xyz"), seed, name+" MMFF seed, not a DFT result")
        write_input(ROOT/name, name, seed, "OPTIMIZE", " $STATPT METHOD=QA OPTTOL=1D-5 NSTEP=200 $END\n")

if __name__ == "__main__":
    main()
