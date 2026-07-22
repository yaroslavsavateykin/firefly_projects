#!/usr/bin/env python3
"""Parse Firefly SURFACE outputs into compact H2 comparison CSV files."""

from __future__ import annotations

import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path


RESULTS = Path("results")
MAIN_CSV = RESULTS / "h2_surface_methods_comparison.csv"
FCI_ROOTS_CSV = RESULTS / "h2_fci_roots.csv"

FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
FINAL_RE = re.compile(rf"^\s*FINAL ENERGY IS\s+({FLOAT})\b", re.IGNORECASE)
MP2_RE = re.compile(
    rf"\b(?:E\((?:U)?MP2\)|(?:TOTAL\s+)?(?:U)?MP2\s+ENERGY)\s*=\s*({FLOAT})\b",
    re.IGNORECASE,
)
COORD_RE = re.compile(rf"^\s*COORD\s+1=\s*({FLOAT})\b", re.IGNORECASE)
HAS_ENERGY_VALUE_RE = re.compile(rf"^\s*HAS ENERGY VALUE\s+({FLOAT})\b", re.IGNORECASE)
HAS_ENERGY_VALUES_RE = re.compile(r"^\s*HAS ENERGY VALUES\s+(.+)$", re.IGNORECASE)
H_GEOM_RE = re.compile(rf"^\s*H\s+({FLOAT})\s+({FLOAT})\s+({FLOAT})\s*$", re.IGNORECASE)
INPUT_H_RE = re.compile(
    rf"^\s*H\s+1\.0\s+({FLOAT})\s+({FLOAT})\s+({FLOAT})\s*$", re.IGNORECASE
)
CI_STATE_RE = re.compile(
    rf"^\s*STATE\s+(\d+)\s+ENERGY=\s*({FLOAT})\s+S=\s*({FLOAT})\s+SZ=\s*({FLOAT})",
    re.IGNORECASE,
)
S2_PATTERNS = (
    re.compile(rf"\bS-SQUARED\s*=\s*({FLOAT})\b", re.IGNORECASE),
    re.compile(rf"\bS\*\*2\b\s*=?\s*({FLOAT})\b", re.IGNORECASE),
    re.compile(rf"<\s*S\*\*2\s*>\s*=?\s*({FLOAT})\b", re.IGNORECASE),
    re.compile(rf"\bSPIN CONTAMINATION\b.*?({FLOAT})\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class MethodFile:
    method: str
    inp: Path
    out: Path
    kind: str


METHODS = (
    MethodFile(
        "RHF",
        Path("inputs/h2_rhf_surface.inp"),
        Path("outputs/h2_rhf_surface.out"),
        "rhf",
    ),
    MethodFile(
        "UHF_plain",
        Path("inputs/h2_uhf_plain_surface.inp"),
        Path("outputs/h2_uhf_plain_surface.out"),
        "uhf",
    ),
    MethodFile(
        "UHF_mix",
        Path("inputs/h2_uhf_mix_surface.inp"),
        Path("outputs/h2_uhf_mix_surface.out"),
        "uhf",
    ),
    MethodFile(
        "MP2",
        Path("inputs/h2_mp2_surface.inp"),
        Path("outputs/h2_mp2_surface.out"),
        "mp2",
    ),
    MethodFile(
        "UMP2",
        Path("inputs/h2_ump2_surface.inp"),
        Path("outputs/h2_ump2_surface.out"),
        "ump2",
    ),
    MethodFile(
        "FCI",
        Path("inputs/h2_fci_surface.inp"),
        Path("outputs/h2_fci_surface.out"),
        "fci",
    ),
    MethodFile(
        "UMP2_mix",
        Path("inputs/h2_ump2_mix_surface.inp"),
        Path("outputs/h2_ump2_mix_surface.out"),
        "ump2",
    ),
)

MAIN_COLUMNS = [
    "R_angstrom",
    "E_RHF_hartree",
    "E_UHF_plain_hartree",
    "E_UHF_mix_hartree",
    "E_MP2_hartree",
    "E_UMP2_hartree",
    "E_FCI0_hartree",
    "E_UMP2_mix_hartree",
    "S2_RHF",
    "S2_UHF_plain",
    "S2_UHF_mix",
    "S2_MP2_ref",
    "S2_UMP2_ref",
    "S2_FCI0",
    "S2_UMP2_mix",
]

FCI_ROOT_COLUMNS = [
    "R_angstrom",
    "E_root0",
    "E_root1",
    "E_root2",
    "E_root3",
    "S2_root0",
    "S2_root1",
    "S2_root2",
    "S2_root3",
]


def parse_float(text: str) -> float:
    return float(text.replace("D", "E").replace("d", "e"))


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def data_distance_from_input(path: Path) -> float | None:
    coords: list[tuple[float, float, float]] = []
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = INPUT_H_RE.match(line)
        if match:
            coords.append(tuple(parse_float(match.group(i)) for i in range(1, 4)))
    if len(coords) >= 2:
        return distance(coords[0], coords[1])
    return None


def find_s2(lines: list[str]) -> float | None:
    value: float | None = None
    for line in lines:
        if "INPUT CARD>" in line:
            continue
        for pattern in S2_PATTERNS:
            match = pattern.search(line)
            if match:
                value = parse_float(match.group(1))
    return value


def find_ci_s2(lines: list[str]) -> dict[int, float]:
    s2_by_root: dict[int, float] = {}
    for line in lines:
        if "INPUT CARD>" in line:
            continue
        match = CI_STATE_RE.match(line)
        if not match:
            continue
        root = int(match.group(1)) - 1
        spin = parse_float(match.group(3))
        s2_by_root[root] = spin * (spin + 1.0)
    return s2_by_root


def find_all_ci_s2(lines: list[str]) -> dict[int, float]:
    """Scan the whole output for CI spin assignments if Firefly prints them."""
    return find_ci_s2(lines)


def parse_energy_values(line: str) -> list[float]:
    return [parse_float(value) for value in re.findall(FLOAT, line)]


def parse_surface_block(
    block: list[str], data_r: float | None
) -> tuple[float | None, float | None, list[float]]:
    coord1: float | None = None
    scalar_energy: float | None = None
    root_energies: list[float] = []
    h_coords: list[tuple[float, float, float]] = []

    for line in block:
        coord_match = COORD_RE.match(line)
        if coord_match:
            coord1 = parse_float(coord_match.group(1))

        scalar_match = HAS_ENERGY_VALUE_RE.match(line)
        if scalar_match:
            scalar_energy = parse_float(scalar_match.group(1))

        values_match = HAS_ENERGY_VALUES_RE.match(line)
        if values_match:
            root_energies = parse_energy_values(values_match.group(1))

        geom_match = H_GEOM_RE.match(line)
        if geom_match:
            h_coords.append(
                tuple(parse_float(geom_match.group(i)) for i in range(1, 4))
            )

    if len(h_coords) >= 2:
        r_value = distance(h_coords[0], h_coords[1])
    elif coord1 is not None and data_r is not None:
        r_value = data_r + coord1
    else:
        r_value = coord1
    return r_value, scalar_energy, root_energies


def find_last_energy(lines: list[str], pattern: re.Pattern[str]) -> float | None:
    values = [
        parse_float(match.group(1))
        for line in lines
        if "INPUT CARD>" not in line
        for match in [pattern.search(line)]
        if match
    ]
    return values[-1] if values else None


def parse_method(method_file: MethodFile) -> list[dict[str, object]]:
    if not method_file.out.exists():
        print(f"Missing {method_file.out}. Run: bash run.sh", file=sys.stderr)
        return []

    lines = method_file.out.read_text(encoding="utf-8", errors="replace").splitlines()
    normal_end = any(
        "EXECUTION OF FIREFLY TERMINATED NORMALLY" in line for line in lines
    )
    data_r = data_distance_from_input(method_file.inp)
    block_starts = [
        i for i, line in enumerate(lines) if "SURFACE MAPPING GEOMETRY" in line
    ]

    rows: list[dict[str, object]] = []
    previous = 0
    for start in block_starts:
        pre = lines[previous:start]
        block_end = next(
            (
                i
                for i in range(start + 1, len(lines))
                if "SURFACE MAPPING GEOMETRY" in lines[i]
            ),
            len(lines),
        )
        block = lines[start:block_end]
        r_value, has_energy, root_energies = parse_surface_block(block, data_r)

        energy: float | None
        roots: list[float] = []
        s2: float | None = None
        root_s2: dict[int, float] = {}

        if method_file.kind == "mp2":
            energy = find_last_energy(pre, MP2_RE)
            s2 = 0.0
        elif method_file.kind == "ump2":
            energy = find_last_energy(pre, MP2_RE)
            s2 = find_s2(pre)
        elif method_file.kind == "fci":
            roots = root_energies[:4]
            if not roots:
                ci_energies = {
                    int(match.group(1)) - 1: parse_float(match.group(2))
                    for line in pre
                    if "INPUT CARD>" not in line
                    for match in [CI_STATE_RE.match(line)]
                    if match
                }
                roots = [ci_energies[i] for i in range(4) if i in ci_energies]
            energy = roots[0] if roots else has_energy
            root_s2 = find_ci_s2(pre)
            s2 = root_s2.get(0)
        else:
            energy = find_last_energy(pre, FINAL_RE)
            if energy is None:
                energy = has_energy
            if method_file.kind == "rhf":
                s2 = 0.0
            else:
                s2 = find_s2(pre)

        pre_text = "\n".join(pre)
        scf_converged = (
            "DENSITY CONVERGED" in pre_text or "ENERGY CONVERGED" in pre_text
        )
        converged = bool(
            energy is not None
            and normal_end
            and (scf_converged or method_file.kind == "fci")
        )

        if method_file.kind == "uhf" and s2 is None:
            print(
                f"WARNING: {method_file.method}: <S^2> not found near line {start + 1}",
                file=sys.stderr,
            )
        if method_file.kind == "ump2" and s2 is None:
            print(
                f"WARNING: UMP2: reference <S^2> not found near line {start + 1}",
                file=sys.stderr,
            )
        if method_file.kind in {"mp2", "ump2"} and energy is None:
            print(
                f"WARNING: {method_file.method} total MP2 energy not found near line {start + 1}",
                file=sys.stderr,
            )
        if method_file.kind == "fci" and len(roots) < 4:
            print(
                f"WARNING: FCI: parsed only {len(roots)} CI root energies near line {start + 1}",
                file=sys.stderr,
            )
        if not converged:
            print(
                f"WARNING: {method_file.method}: point near line {start + 1} may be unconverged/incomplete",
                file=sys.stderr,
            )

        rows.append(
            {
                "R_angstrom": r_value,
                "E_hartree": energy if converged else None,
                "S2": s2,
                "converged": converged,
                "roots": roots,
                "root_s2": root_s2,
            }
        )
        previous = start

    rows = [row for row in rows if row["R_angstrom"] is not None]
    rows.sort(key=lambda row: float(row["R_angstrom"]))
    converged_count = sum(bool(row["converged"]) for row in rows)
    print(
        f"{method_file.method}: parsed {len(rows)} surface points, converged {converged_count}."
    )
    if method_file.kind == "fci":
        whole_output_s2 = find_all_ci_s2(lines)
        if whole_output_s2:
            for row in rows:
                root_s2 = dict(row.get("root_s2") or {})
                root_s2.update(
                    {k: v for k, v in whole_output_s2.items() if k not in root_s2}
                )
                row["root_s2"] = root_s2
                if row.get("S2") is None:
                    row["S2"] = root_s2.get(0)
    return rows


def fmt_float(value: object, digits: int = 12, missing: str = "") -> str:
    if value is None:
        return missing
    return f"{float(value):.{digits}f}"


def row_map(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {f"{float(row['R_angstrom']):.6f}": row for row in rows}


def build_main_rows(
    method_rows: dict[str, list[dict[str, object]]],
) -> list[dict[str, str]]:
    mapped = {method: row_map(rows) for method, rows in method_rows.items()}
    r_keys = sorted(set().union(*(rows.keys() for rows in mapped.values())), key=float)
    for method, rows in mapped.items():
        missing = [r_key for r_key in r_keys if r_key not in rows]
        if missing:
            print(
                f"WARNING: {method}: missing {len(missing)} R values in common grid",
                file=sys.stderr,
            )

    output: list[dict[str, str]] = []
    for r_key in r_keys:
        rhf = mapped["RHF"].get(r_key, {})
        plain = mapped["UHF_plain"].get(r_key, {})
        mix = mapped["UHF_mix"].get(r_key, {})
        mp2 = mapped["MP2"].get(r_key, {})
        ump2 = mapped["UMP2"].get(r_key, {})
        ump2_mix = mapped["UMP2_mix"].get(r_key, {})
        fci = mapped["FCI"].get(r_key, {})
        output.append(
            {
                "R_angstrom": f"{float(r_key):.2f}",
                "E_RHF_hartree": fmt_float(rhf.get("E_hartree"), missing="NaN"),
                "E_UHF_plain_hartree": fmt_float(plain.get("E_hartree"), missing="NaN"),
                "E_UHF_mix_hartree": fmt_float(mix.get("E_hartree"), missing="NaN"),
                "E_MP2_hartree": fmt_float(mp2.get("E_hartree"), missing="NaN"),
                "E_UMP2_hartree": fmt_float(ump2.get("E_hartree"), missing="NaN"),
                "E_FCI0_hartree": fmt_float(fci.get("E_hartree"), missing="NaN"),
                "E_UMP2_mix_hartree": fmt_float(ump2_mix.get("E_hartree"), missing="NaN"),
                "S2_RHF": fmt_float(rhf.get("S2"), 6, missing="0.000000"),
                "S2_UHF_plain": fmt_float(plain.get("S2"), 6, missing="NaN"),
                "S2_UHF_mix": fmt_float(mix.get("S2"), 6, missing="NaN"),
                "S2_MP2_ref": fmt_float(mp2.get("S2"), 6, missing="0.000000"),
                "S2_UMP2_ref": fmt_float(ump2.get("S2"), 6, missing="NaN"),
                "S2_FCI0": fmt_float(fci.get("S2"), 6, missing="NaN"),
                "S2_UMP2_mix": fmt_float(ump2_mix.get("S2"), 6, missing="NaN"),
            }
        )
    return output


def build_fci_root_rows(
    fci_rows: list[dict[str, object]],
) -> tuple[list[dict[str, str]], bool]:
    output: list[dict[str, str]] = []
    any_s2 = False
    for row in sorted(fci_rows, key=lambda item: float(item["R_angstrom"])):
        roots = list(row.get("roots") or [])
        root_s2 = dict(row.get("root_s2") or {})
        any_s2 = any_s2 or bool(root_s2)
        out_row = {"R_angstrom": f"{float(row['R_angstrom']):.2f}"}
        for i in range(4):
            out_row[f"E_root{i}"] = fmt_float(
                roots[i] if i < len(roots) else None, missing="NaN"
            )
        for i in range(4):
            out_row[f"S2_root{i}"] = fmt_float(root_s2.get(i), 6, missing="NaN")
        output.append(out_row)
    return output, any_s2


def nonblank_float(row: dict[str, str], key: str) -> float | None:
    if not row.get(key):
        return None
    value = float(row[key])
    if math.isnan(value):
        return None
    return value


def print_summary(
    main_rows: list[dict[str, str]],
    method_rows: dict[str, list[dict[str, object]]],
    fci_s2_found: bool,
) -> None:
    s2_mix = [
        value
        for row in main_rows
        for value in [nonblank_float(row, "S2_UHF_mix")]
        if value is not None
    ]
    s2_ump2 = [
        value
        for row in main_rows
        for value in [nonblank_float(row, "S2_UMP2_ref")]
        if value is not None
    ]
    s2_ump2_mix = [
        value
        for row in main_rows
        for value in [nonblank_float(row, "S2_UMP2_mix")]
        if value is not None
    ]
    fci_roots_with_s2 = sum(
        1
        for i in range(4)
        if any(
            nonblank_float(row, f"S2_root{i}") is not None
            for row in build_fci_root_rows(method_rows["FCI"])[0]
        )
    )
    print(f"Wrote {MAIN_CSV} with {len(main_rows)} R rows.")
    print("Summary:")
    print(f"  RHF points: {len(method_rows['RHF'])}")
    print(f"  UHF points: {len(method_rows['UHF_plain'])}")
    print(f"  UHF+MIX points: {len(method_rows['UHF_mix'])}")
    print(f"  MP2 points: {len(method_rows['MP2'])}")
    print(f"  UMP2 points: {len(method_rows['UMP2'])}")
    print(f"  UMP2 mixed points: {len(method_rows['UMP2_mix'])}")
    print(f"  FCI points: {len(method_rows['FCI'])}")
    print(f"  max <S^2> UHF+MIX: {max(s2_mix) if s2_mix else float('nan'):.6f}")
    print(
        f"  max <S^2> UMP2 reference: {max(s2_ump2) if s2_ump2 else float('nan'):.6f}"
    )
    print(
        f"  max <S^2> UMP2 mixed reference: {max(s2_ump2_mix) if s2_ump2_mix else float('nan'):.6f}"
    )
    print(f"  FCI root S2 parsed: {'yes' if fci_s2_found else 'no'}")
    print(f"  FCI roots plotted on spin graph: {fci_roots_with_s2}")


def main() -> None:
    method_rows = {method.method: parse_method(method) for method in METHODS}
    main_rows = build_main_rows(method_rows)
    fci_root_rows, fci_s2_found = build_fci_root_rows(method_rows["FCI"])

    RESULTS.mkdir(parents=True, exist_ok=True)
    with MAIN_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAIN_COLUMNS)
        writer.writeheader()
        writer.writerows(main_rows)

    with FCI_ROOTS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FCI_ROOT_COLUMNS)
        writer.writeheader()
        writer.writerows(fci_root_rows)
    print(f"Wrote {FCI_ROOTS_CSV} with {len(fci_root_rows)} R rows.")

    if not fci_s2_found:
        print(
            "WARNING: S2 for FCI roots was not found in the surface output.",
            file=sys.stderr,
        )
    print_summary(main_rows, method_rows, fci_s2_found)


if __name__ == "__main__":
    main()
