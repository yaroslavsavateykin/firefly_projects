#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

HARTREE_TO_EV = 27.211386245988
HARTREE_TO_KJ_MOL = 2625.499638
HARTREE_TO_CM = 219474.6313705
BOHR_PER_ANG = 1.8897261255

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"


@dataclass
class Record:
    source_file: str
    calculation_group: str
    calculation_type: str
    status: str
    R_A: Optional[float]
    state: int
    energy_Ha: Optional[float]
    energy_rel_eV: Optional[float] = None
    gap_to_previous_Ha: Optional[float] = None
    gap_to_previous_eV: Optional[float] = None
    dipole_D: Optional[float] = None
    dipole_x_D: Optional[float] = None
    dipole_y_D: Optional[float] = None
    dipole_z_D: Optional[float] = None
    multiplicity: Optional[float] = None
    s2: Optional[float] = None
    leading_configuration: str = ""
    leading_ci_coefficient: Optional[float] = None
    second_configuration: str = ""
    second_ci_coefficient: Optional[float] = None
    charge_Li: Optional[float] = None
    charge_F: Optional[float] = None
    natural_occupation_summary: str = ""
    notes: str = ""


@dataclass
class BasisSummary:
    source_file: str
    calculation_group: str
    calculation_type: str
    status: str
    cityp: str = ""
    scftyp: str = ""
    basis: str = ""
    n_shells: Optional[int] = None
    n_basis_functions: Optional[int] = None
    n_electrons_total: Optional[int] = None
    ncore: Optional[int] = None
    nact: Optional[int] = None
    nels_active: Optional[int] = None
    nstate: Optional[int] = None
    determinant_count: Optional[int] = None
    csf_singlet_count: Optional[int] = None
    csf_triplet_count: Optional[int] = None
    has_polarization_functions: bool = False
    has_diffuse_functions: bool = False
    evidence: str = ""


@dataclass
class CiCoefficient:
    source_file: str
    calculation_group: str
    calculation_type: str
    status: str
    R_A: Optional[float]
    state: int
    energy_Ha: Optional[float]
    spin_S: Optional[float]
    multiplicity: Optional[float]
    alpha: str
    beta: str
    coefficient: float


@dataclass
class ParseResult:
    records: list[Record] = field(default_factory=list)
    basis: Optional[BasisSummary] = None
    ci_coefficients: list[CiCoefficient] = field(default_factory=list)
    property_lines: dict[str, list[int]] = field(
        default_factory=lambda: defaultdict(list)
    )


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def calculation_group(path: Path) -> str:
    try:
        parts = path.resolve().relative_to(ROOT).parts
    except ValueError:
        return "external"
    if not parts:
        return "unknown"
    if parts[0] == "new_runs" and len(parts) > 1:
        return parts[1]
    return parts[0]


def calculation_type(path: Path, text: str) -> str:
    if "single_points_properties" in path.parts:
        return "single_point"
    if "OVERALL RESULTS OF THE POTENTIAL SURFACE SCAN" in text:
        return "surface"
    if re.search(r"RUNTYP\s*=\s*ENERGY", text):
        return "single_point"
    return "unknown"


def find_outputs() -> list[Path]:
    patterns = [
        "lif_scan/*.out",
        "extended_scan/*.out",
        "fine_crossing/*.out",
        "new_runs/scan_selected/*.out",
        "new_runs/scan_crossing/*.out",
        "new_runs/scan_dissociation/*.out",
        "new_runs/single_points_properties/outputs/*.out",
    ]
    outputs: list[Path] = []
    for pat in patterns:
        outputs.extend(sorted(ROOT.glob(pat)))
    return sorted(set(outputs))


def read_text(path: Path) -> str:
    return path.read_text(errors="replace").replace("\r", "")


def line_numbers(text: str, pattern: str) -> list[int]:
    rx = re.compile(pattern, re.I)
    return [i for i, line in enumerate(text.splitlines(), start=1) if rx.search(line)]


def parse_R_from_filename(path: Path) -> Optional[float]:
    m = re.search(r"R_(\d+)_(\d+)", path.stem)
    if not m:
        return None
    return float(f"{m.group(1)}.{m.group(2)}")


def parse_initial_R(text: str) -> Optional[float]:
    m = re.search(r"INPUT CARD>\s*F\s+9\.0\s+[-0-9.]+\s+[-0-9.]+\s+([-0-9.]+)", text)
    if m:
        z = abs(float(m.group(1)))
        return z / BOHR_PER_ANG if z > 20.0 else z
    m = re.search(r"^\s*F\s+9\.0\s+[-0-9.]+\s+[-0-9.]+\s+([-0-9.]+)", text, re.M)
    if m:
        z = abs(float(m.group(1)))
        return z / BOHR_PER_ANG if z > 20.0 else z
    return None


def parse_basis(path: Path, text: str, status: str, ctype: str) -> BasisSummary:
    b = BasisSummary(
        source_file=rel(path),
        calculation_group=calculation_group(path),
        calculation_type=ctype,
        status=status,
    )
    m = re.search(r"CITYP\s*=\s*([A-Z0-9]+)", text)
    if m:
        b.cityp = m.group(1)
    m = re.search(r"SCFTYP\s*=\s*([A-Z0-9]+)", text)
    if m:
        b.scftyp = m.group(1)
    m = re.search(r'\$BASIS REQUESTS READING THE "([^"]+)" BASIS SET', text)
    if m:
        b.basis = m.group(1)
    else:
        m = re.search(r"GBASIS\s*=\s*([A-Za-z0-9+\-]+)", text)
        if m:
            b.basis = m.group(1)

    patterns = [
        ("n_shells", r"TOTAL NUMBER OF SHELLS\s*=\s*(\d+)"),
        ("n_basis_functions", r"TOTAL NUMBER OF BASIS FUNCTIONS\s*=\s*(\d+)"),
        ("n_electrons_total", r"NUMBER OF ELECTRONS\s*=\s*(\d+)"),
        ("ncore", r"NUMBER OF CORE ORBITALS\s*=\s*(\d+)"),
        ("nact", r"NUMBER OF ACTIVE ORBITALS\s*=\s*(\d+)"),
        ("nstate", r"NUMBER OF CI STATES REQUESTED\s*=\s*(\d+)"),
        ("determinant_count", r"WITH SZ=\s*[-0-9.]+\s+IS\s+(\d+)"),
        ("csf_singlet_count", r"WHICH INCLUDES\s+(\d+)\s+CSFS WITH S=\s*0\.0"),
        ("csf_triplet_count", r"WHICH INCLUDES\s+(\d+)\s+CSFS WITH S=\s*1\.0"),
    ]
    for attr, pat in patterns:
        m = re.search(pat, text)
        if m:
            setattr(b, attr, int(m.group(1)))

    m = re.search(r"\$CIDET\b(.*?)\$END", text, re.S)
    if m:
        cidet = {
            k.upper(): int(v)
            for k, v in re.findall(r"\b([A-Z]+)\s*=\s*(\d+)", m.group(1), re.I)
        }
        b.ncore = cidet.get("NCORE", b.ncore)
        b.nact = cidet.get("NACT", b.nact)
        b.nels_active = cidet.get("NELS", b.nels_active)
        b.nstate = cidet.get("NSTATE", b.nstate)

    atom_basis = text.split("ATOMIC BASIS SET", 1)[-1]
    b.has_polarization_functions = bool(re.search(r"^\s*\d+\s+D\s+", atom_basis, re.M))
    small_exponents = [
        float(x)
        for x in re.findall(
            r"^\s*\d+\s+[SP]\s+\d+\s+([0-9]*\.[0-9]+)", atom_basis, re.M
        )
    ]
    b.has_diffuse_functions = any(x < 0.1 for x in small_exponents)

    evidence = []
    for pat in [
        r"TOTAL NUMBER OF BASIS FUNCTIONS",
        r"\$BASIS REQUESTS",
        r"\$CIDET",
        r"THE NUMBER OF DETERMINANTS",
        r"TOTAL NUMBER OF SHELLS",
    ]:
        nums = line_numbers(text, pat)
        if nums:
            evidence.append(f"{pat}: lines {','.join(map(str, nums[:5]))}")
    b.evidence = "; ".join(evidence)
    return b


def parse_surface_records(
    path: Path, text: str, status: str, ctype: str
) -> list[Record]:
    if "OVERALL RESULTS OF THE POTENTIAL SURFACE SCAN" not in text:
        return []
    r0 = parse_initial_R(text)
    if r0 is None:
        r0 = 0.0
    section = text.split("OVERALL RESULTS OF THE POTENTIAL SURFACE SCAN", 1)[1]
    section = section.split("ENERGY DELTA MAP", 1)[0]
    records: list[Record] = []
    for sm in re.finditer(
        r"RESULTS FOR STATE NUMBER\s+(\d+)(.*?)(?=\n\s*RESULTS FOR STATE NUMBER|\Z)",
        section,
        re.S,
    ):
        state = int(sm.group(1))
        body = sm.group(2)
        for coord, energy in re.findall(
            r"^\s*\d+ \(\s*([0-9.]+)\)\|\s*(-?[0-9.]+)", body, re.M
        ):
            records.append(
                Record(
                    source_file=rel(path),
                    calculation_group=calculation_group(path),
                    calculation_type=ctype,
                    status=status,
                    R_A=r0 + float(coord),
                    state=state,
                    energy_Ha=float(energy),
                    notes="surface_scan",
                )
            )
    return records


def parse_ci_property_root(text: str) -> Optional[int]:
    m = re.search(r"CI PROPERTIES WILL BE FOUND FOR ROOT NUMBER\s+(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def parse_total_dipole(
    text: str,
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    blocks = list(
        re.finditer(
            r"ELECTROSTATIC MOMENTS(.*?)(?:END OF PROPERTY EVALUATION|TIMING STATISTICS)",
            text,
            re.S,
        )
    )
    if not blocks:
        return None, None, None, None
    block = blocks[-1].group(1)
    m = re.search(
        r"DX\s+DY\s+DZ\s+/D/.*?\n\s*([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)",
        block,
        re.S,
    )
    if not m:
        return None, None, None, None
    dx, dy, dz, total = (float(m.group(i)) for i in range(1, 5))
    return total, dx, dy, dz


def parse_charges(text: str) -> tuple[Optional[float], Optional[float]]:
    blocks = list(
        re.finditer(
            r"TOTAL MULLIKEN AND LOWDIN ATOMIC POPULATIONS(.*?)(?:BOND ORDER|ELECTROSTATIC MOMENTS|END OF PROPERTY)",
            text,
            re.S,
        )
    )
    if not blocks:
        return None, None
    li = f = None
    for line in blocks[-1].group(1).splitlines():
        m = re.match(
            r"\s*\d+\s+(LI|Li|F)\s+[-0-9.]+\s+([-0-9.]+)\s+[-0-9.]+\s+[-0-9.]+",
            line,
        )
        if not m:
            continue
        if m.group(1).upper() == "LI":
            li = float(m.group(2))
        elif m.group(1).upper() == "F":
            f = float(m.group(2))
    return li, f


def parse_natural_occupations(text: str) -> str:
    m = re.search(
        r"NATURAL ORBITALS IN ATOMIC ORBITAL BASIS(.*?)(?:WARNING!|DONE WITH ONE PARTICLE)",
        text,
        re.S,
    )
    if not m:
        return ""
    values: list[str] = []
    for line in m.group(1).splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if all(re.fullmatch(r"-?\d+\.\d+", p) for p in parts):
            values.extend(parts)
            break
    if not values:
        return ""
    return " ".join(values[:12])


def parse_ci_states(path: Path, text: str, status: str, ctype: str) -> list[Record]:
    R = parse_R_from_filename(path) if ctype == "single_point" else None
    if R is None:
        R = parse_initial_R(text)
    prop_root = parse_ci_property_root(text)
    dipole, dx, dy, dz = parse_total_dipole(text)
    charge_li, charge_f = parse_charges(text)
    occupations = parse_natural_occupations(text)
    records: list[Record] = []

    matches = list(
        re.finditer(
            r"STATE\s+(\d+)\s+ENERGY=\s*(-?[0-9.]+)\s+S=\s*([0-9.]+)",
            text,
        )
    )
    for idx, m in enumerate(matches):
        state = int(m.group(1))
        energy = float(m.group(2))
        spin = float(m.group(3))
        end = matches[idx + 1].start() if idx + 1 < len(matches) else -1
        done = text.find("..... DONE WITH DETERMINANT CI COMPUTATION", m.end())
        if end < 0 or (done > 0 and done < end):
            end = done
        if end < 0:
            end = min(len(text), m.end() + 5000)
        block = text[m.end() : end]
        coeffs: list[tuple[float, str]] = []
        for cm in re.finditer(
            r"^\s*([01]+)\s*\|\s*([01]+)\s*\|\s*(-?[0-9.]+)", block, re.M
        ):
            coeffs.append((float(cm.group(3)), f"{cm.group(1)}|{cm.group(2)}"))
        coeffs.sort(key=lambda item: abs(item[0]), reverse=True)

        rec = Record(
            source_file=rel(path),
            calculation_group=calculation_group(path),
            calculation_type=ctype,
            status=status,
            R_A=R,
            state=state,
            energy_Ha=energy,
            multiplicity=2 * spin + 1,
            s2=spin * (spin + 1),
            leading_configuration=coeffs[0][1] if coeffs else "",
            leading_ci_coefficient=coeffs[0][0] if coeffs else None,
            second_configuration=coeffs[1][1] if len(coeffs) > 1 else "",
            second_ci_coefficient=coeffs[1][0] if len(coeffs) > 1 else None,
            notes="ci_eigenvector",
        )
        if prop_root is None or prop_root == state:
            rec.dipole_D = dipole
            rec.dipole_x_D = dx
            rec.dipole_y_D = dy
            rec.dipole_z_D = dz
            rec.charge_Li = charge_li
            rec.charge_F = charge_f
            rec.natural_occupation_summary = occupations
        records.append(rec)

    if records:
        return records

    for m in re.finditer(
        r"CI EIGENSTATE\s+(\d+)\s+TOTAL ENERGY\s*=\s*(-?[0-9.]+)", text
    ):
        state = int(m.group(1))
        rec = Record(
            source_file=rel(path),
            calculation_group=calculation_group(path),
            calculation_type=ctype,
            status=status,
            R_A=R,
            state=state,
            energy_Ha=float(m.group(2)),
            notes="ci_eigenstate_energy_only",
        )
        if prop_root is None or prop_root == state:
            rec.dipole_D = dipole
            rec.dipole_x_D = dx
            rec.dipole_y_D = dy
            rec.dipole_z_D = dz
            rec.charge_Li = charge_li
            rec.charge_F = charge_f
            rec.natural_occupation_summary = occupations
        records.append(rec)
    return records


def parse_ci_coefficients_all(
    path: Path, text: str, status: str, ctype: str
) -> list[CiCoefficient]:
    R = parse_R_from_filename(path) if ctype == "single_point" else None
    if R is None:
        R = parse_initial_R(text)
    matches = list(
        re.finditer(
            r"STATE\s+(\d+)\s+ENERGY=\s*(-?[0-9.]+)\s+S=\s*([0-9.]+)",
            text,
        )
    )
    rows: list[CiCoefficient] = []
    for idx, m in enumerate(matches):
        state = int(m.group(1))
        energy = float(m.group(2))
        spin = float(m.group(3))
        end = matches[idx + 1].start() if idx + 1 < len(matches) else -1
        done = text.find("..... DONE WITH DETERMINANT CI COMPUTATION", m.end())
        if end < 0 or (done > 0 and done < end):
            end = done
        if end < 0:
            end = min(len(text), m.end() + 5000)
        block = text[m.end() : end]
        for cm in re.finditer(
            r"^\s*([01]+)\s*\|\s*([01]+)\s*\|\s*(-?[0-9.]+)", block, re.M
        ):
            rows.append(
                CiCoefficient(
                    source_file=rel(path),
                    calculation_group=calculation_group(path),
                    calculation_type=ctype,
                    status=status,
                    R_A=R,
                    state=state,
                    energy_Ha=energy,
                    spin_S=spin,
                    multiplicity=2 * spin + 1,
                    alpha=cm.group(1),
                    beta=cm.group(2),
                    coefficient=float(cm.group(3)),
                )
            )
    return rows


def parse_output(path: Path) -> ParseResult:
    text = read_text(path)
    status = (
        "normal" if "EXECUTION OF FIREFLY TERMINATED NORMALLY" in text else "incomplete"
    )
    ctype = calculation_type(path, text)
    result = ParseResult()
    result.basis = parse_basis(path, text, status, ctype)
    result.records.extend(parse_surface_records(path, text, status, ctype))
    result.records.extend(parse_ci_states(path, text, status, ctype))
    result.ci_coefficients.extend(parse_ci_coefficients_all(path, text, status, ctype))

    for key, pat in {
        "dipoles": r"ELECTROSTATIC MOMENTS|DX\s+DY\s+DZ",
        "charges": r"TOTAL MULLIKEN AND LOWDIN ATOMIC POPULATIONS",
        "ci_coefficients": r"ALPHA\s+\|\s+BETA\s+\|\s+COEFFICIENT|ALPH\|BETA\|\s*COEFFICIENT|PRINTING .*CI COEFFICIENTS|STATE\s+\d+\s+ENERGY=",
        "spin": r"STATE\s+\d+\s+ENERGY=.*S=",
        "natural_orbitals": r"NATURAL ORBITALS",
        "basis": r"TOTAL NUMBER OF BASIS FUNCTIONS|\$BASIS REQUESTS",
    }.items():
        result.property_lines[key].extend(line_numbers(text, pat))
    return result


def enrich(records: list[Record]) -> None:
    valid_energies = [
        r.energy_Ha for r in records if r.status == "normal" and r.energy_Ha is not None
    ]
    if valid_energies:
        e0 = min(valid_energies)
        for r in records:
            if r.energy_Ha is not None:
                r.energy_rel_eV = (r.energy_Ha - e0) * HARTREE_TO_EV

    by_point: dict[tuple[str, Optional[float]], list[Record]] = defaultdict(list)
    for r in records:
        key_r = None if r.R_A is None else round(r.R_A, 8)
        by_point[(r.source_file, key_r)].append(r)
    for rows in by_point.values():
        rows.sort(key=lambda x: x.state)
        prev = None
        for r in rows:
            if (
                prev is not None
                and r.energy_Ha is not None
                and prev.energy_Ha is not None
            ):
                r.gap_to_previous_Ha = r.energy_Ha - prev.energy_Ha
                r.gap_to_previous_eV = r.gap_to_previous_Ha * HARTREE_TO_EV
            prev = r


def fmt(x: Optional[float], digits: int = 10) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return ""
    return f"{x:.{digits}f}"


def row_dict(r: Record) -> dict[str, str | int]:
    return {
        "source_file": r.source_file,
        "calculation_group": r.calculation_group,
        "calculation_type": r.calculation_type,
        "status": r.status,
        "R_A": fmt(r.R_A, 6),
        "state": r.state,
        "energy_Ha": fmt(r.energy_Ha, 12),
        "energy_rel_eV": fmt(r.energy_rel_eV, 8),
        "gap_to_previous_Ha": fmt(r.gap_to_previous_Ha, 12),
        "gap_to_previous_eV": fmt(r.gap_to_previous_eV, 8),
        "dipole_D": fmt(r.dipole_D, 8),
        "dipole_x_D": fmt(r.dipole_x_D, 8),
        "dipole_y_D": fmt(r.dipole_y_D, 8),
        "dipole_z_D": fmt(r.dipole_z_D, 8),
        "multiplicity": fmt(r.multiplicity, 3),
        "s2": fmt(r.s2, 6),
        "leading_configuration": r.leading_configuration,
        "leading_ci_coefficient": fmt(r.leading_ci_coefficient, 8),
        "second_configuration": r.second_configuration,
        "second_ci_coefficient": fmt(r.second_ci_coefficient, 8),
        "charge_Li": fmt(r.charge_Li, 8),
        "charge_F": fmt(r.charge_F, 8),
        "natural_occupation_summary": r.natural_occupation_summary,
        "notes": r.notes,
    }


def write_lif_csv(records: list[Record]) -> None:
    fields = [
        "source_file",
        "calculation_group",
        "calculation_type",
        "status",
        "R_A",
        "state",
        "energy_Ha",
        "energy_rel_eV",
        "gap_to_previous_Ha",
        "gap_to_previous_eV",
        "dipole_D",
        "dipole_x_D",
        "dipole_y_D",
        "dipole_z_D",
        "multiplicity",
        "s2",
        "leading_configuration",
        "leading_ci_coefficient",
        "second_configuration",
        "second_ci_coefficient",
        "charge_Li",
        "charge_F",
        "natural_occupation_summary",
        "notes",
    ]
    with (ANALYSIS / "lif_all_data.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(
            records, key=lambda x: (x.R_A is None, x.R_A or 0.0, x.state, x.source_file)
        ):
            w.writerow(row_dict(r))


def write_single_point_csv(records: list[Record]) -> None:
    fields = [
        "source_file",
        "R_A",
        "state",
        "energy_Ha",
        "energy_rel_eV",
        "dipole_D",
        "dipole_x_D",
        "dipole_y_D",
        "dipole_z_D",
        "charge_Li",
        "charge_F",
        "s2",
        "multiplicity",
        "leading_configuration",
        "leading_ci_coefficient",
        "second_configuration",
        "second_ci_coefficient",
        "natural_occupation_summary",
        "status",
        "notes",
    ]
    with (ANALYSIS / "lif_single_point_properties.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(
            [x for x in records if x.calculation_type == "single_point"],
            key=lambda x: (x.R_A is None, x.R_A or 0.0, x.state, x.source_file),
        ):
            data = row_dict(r)
            w.writerow({field: data[field] for field in fields})


def write_ci_coefficients_all_csv(rows: list[CiCoefficient]) -> None:
    fields = [
        "source_file",
        "calculation_group",
        "calculation_type",
        "status",
        "R_A",
        "state",
        "energy_Ha",
        "spin_S",
        "multiplicity",
        "alpha",
        "beta",
        "coefficient",
        "weight",
        "notes",
    ]
    with (ANALYSIS / "lif_ci_coefficients_all.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in sorted(
            rows,
            key=lambda x: (
                x.R_A is None,
                x.R_A or 0.0,
                x.state,
                -abs(x.coefficient),
                x.source_file,
            ),
        ):
            w.writerow(
                {
                    "source_file": row.source_file,
                    "calculation_group": row.calculation_group,
                    "calculation_type": row.calculation_type,
                    "status": row.status,
                    "R_A": fmt(row.R_A, 6),
                    "state": row.state,
                    "energy_Ha": fmt(row.energy_Ha, 12),
                    "spin_S": fmt(row.spin_S, 3),
                    "multiplicity": fmt(row.multiplicity, 3),
                    "alpha": row.alpha,
                    "beta": row.beta,
                    "coefficient": fmt(row.coefficient, 8),
                    "weight": fmt(row.coefficient * row.coefficient, 8),
                    "notes": "printed_ci_coefficient_threshold_from_output",
                }
            )


def write_basis_csv(bases: list[BasisSummary]) -> None:
    fields = [
        "source_file",
        "calculation_group",
        "calculation_type",
        "status",
        "cityp",
        "scftyp",
        "basis",
        "n_shells",
        "n_basis_functions",
        "n_electrons_total",
        "ncore",
        "nact",
        "nels_active",
        "nstate",
        "determinant_count",
        "csf_singlet_count",
        "csf_triplet_count",
        "has_polarization_functions",
        "has_diffuse_functions",
        "evidence",
    ]
    with (ANALYSIS / "fci_basis_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for b in bases:
            w.writerow({field: getattr(b, field) for field in fields})

    lines = ["# FCI and basis summary", ""]
    for b in bases:
        lines.append(f"## {b.source_file}")
        lines.append("")
        lines.append(f"- status: {b.status}")
        lines.append(f"- calculation type: {b.calculation_type}")
        lines.append(
            f"- method: CITYP={b.cityp or 'not found'}, SCFTYP={b.scftyp or 'not found'}"
        )
        lines.append(f"- basis: {b.basis or 'not found'}")
        lines.append(
            f"- shells/basis functions: {b.n_shells or 'not found'} / {b.n_basis_functions or 'not found'}"
        )
        lines.append(
            f"- electrons: total={b.n_electrons_total or 'not found'}, active={b.nels_active or 'not found'}"
        )
        lines.append(
            f"- active space: NCORE={b.ncore or 'not found'}, NACT={b.nact or 'not found'}, NSTATE={b.nstate or 'not found'}"
        )
        lines.append(f"- determinant count: {b.determinant_count or 'not found'}")
        lines.append(f"- polarization functions: {b.has_polarization_functions}")
        lines.append(f"- diffuse functions: {b.has_diffuse_functions}")
        lines.append(f"- evidence: {b.evidence or 'not found'}")
        lines.append("")
    (ANALYSIS / "fci_basis_summary.md").write_text("\n".join(lines))


def write_dissociation(records: list[Record]) -> None:
    rows = [
        r
        for r in records
        if r.status == "normal"
        and r.calculation_type == "surface"
        and r.state == 1
        and r.R_A is not None
        and r.energy_Ha is not None
    ]
    fields = [
        "R_min_A",
        "E_min_Ha",
        "R_limit_A",
        "E_limit_Ha",
        "De_Ha",
        "De_eV",
        "De_kJ_mol",
        "De_cm-1",
        "source_limit",
        "notes",
    ]
    with (ANALYSIS / "dissociation_energy.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        if not rows:
            return
        min_row = min(rows, key=lambda r: r.energy_Ha)
        limit_row = max(rows, key=lambda r: r.R_A)
        de = limit_row.energy_Ha - min_row.energy_Ha
        sorted_far = sorted(rows, key=lambda r: r.R_A)
        note = "dissociation limit is provisional; verify energy plateau at largest R"
        if len(sorted_far) >= 2:
            last_delta = sorted_far[-1].energy_Ha - sorted_far[-2].energy_Ha
            note += f"; last step dE={last_delta:.10f} Ha"
        w.writerow(
            {
                "R_min_A": fmt(min_row.R_A, 6),
                "E_min_Ha": fmt(min_row.energy_Ha, 12),
                "R_limit_A": fmt(limit_row.R_A, 6),
                "E_limit_Ha": fmt(limit_row.energy_Ha, 12),
                "De_Ha": fmt(de, 12),
                "De_eV": fmt(de * HARTREE_TO_EV, 8),
                "De_kJ_mol": fmt(de * HARTREE_TO_KJ_MOL, 6),
                "De_cm-1": fmt(de * HARTREE_TO_CM, 3),
                "source_limit": limit_row.source_file,
                "notes": note,
            }
        )


def setup_matplotlib():
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Computer Modern Roman", "CMU Serif", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "axes.grid": True,
            "figure.dpi": 150,
        }
    )
    return plt


def plot_empty(plt, path: Path, message: str) -> None:
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def unique_xy(rows: list[Record], y_attr: str) -> tuple[list[float], list[float]]:
    grouped: dict[float, list[float]] = defaultdict(list)
    for r in rows:
        x = r.R_A
        y = getattr(r, y_attr)
        if x is not None and y is not None:
            grouped[round(x, 6)].append(float(y))
    xs = sorted(grouped)
    ys = [sum(grouped[x]) / len(grouped[x]) for x in xs]
    return xs, ys


def spline_xy(xs: list[float], ys: list[float]) -> tuple[list[float], list[float]]:
    if len(xs) < 4:
        return xs, ys
    try:
        import numpy as np
        from scipy.interpolate import make_interp_spline

        pairs = sorted(set(zip(xs, ys)))
        x_arr = np.array([p[0] for p in pairs], dtype=float)
        y_arr = np.array([p[1] for p in pairs], dtype=float)
        if len(x_arr) < 4:
            return x_arr.tolist(), y_arr.tolist()
        x_smooth = np.linspace(x_arr.min(), x_arr.max(), max(200, 12 * len(x_arr)))
        spline = make_interp_spline(x_arr, y_arr, k=min(3, len(x_arr) - 1))
        return x_smooth.tolist(), spline(x_smooth).tolist()
    except Exception:
        return xs, ys


def plot_series_with_spline(ax, xs: list[float], ys: list[float], label: str) -> None:
    sx, sy = spline_xy(xs, ys)
    (line,) = ax.plot(sx, sy, lw=1.2, label=label)
    ax.plot(xs, ys, linestyle="None", marker="o", ms=3, color=line.get_color())


def plot_outputs(records: list[Record]) -> None:
    try:
        plt = setup_matplotlib()
    except Exception as exc:
        (ANALYSIS / "plot_error.txt").write_text(
            f"Could not import/use matplotlib: {exc}\n"
        )
        return

    normal = [
        r
        for r in records
        if r.status == "normal" and r.R_A is not None and r.energy_Ha is not None
    ]
    surface = [r for r in normal if r.calculation_type == "surface"]
    single = [r for r in normal if r.calculation_type == "single_point"]
    if not normal:
        for name in [
            "lif_pes.pdf",
            "lif_pes_relative_ev.pdf",
            "lif_gaps.pdf",
            "lif_crossing_zoom.pdf",
            "lif_pes_with_property_points.pdf",
            "lif_dipoles.pdf",
            "lif_charges.pdf",
            "lif_ci_weights.pdf",
        ]:
            plot_empty(
                plt, ANALYSIS / name, "Нет успешно завершенных расчетов с энергиями"
            )
        return

    energy_rows = surface if surface else normal
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for state in sorted({r.state for r in energy_rows}):
        xs, ys = unique_xy([r for r in energy_rows if r.state == state], "energy_Ha")
        plot_series_with_spline(ax, xs, ys, f"состояние {state}")
    ax.set_xlabel(r"$R_{\mathrm{Li-F}}$, A")
    ax.set_ylabel("Энергия, Хартри")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ANALYSIS / "lif_pes.pdf")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for state in sorted({r.state for r in energy_rows}):
        xs, ys = unique_xy(
            [r for r in energy_rows if r.state == state], "energy_rel_eV"
        )
        plot_series_with_spline(ax, xs, ys, f"состояние {state}")
    ax.set_xlabel(r"$R_{\mathrm{Li-F}}$, A")
    ax.set_ylabel("Относительная энергия, эВ")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ANALYSIS / "lif_pes_relative_ev.pdf")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for state in sorted({r.state for r in energy_rows}):
        xs, ys = unique_xy(
            [r for r in energy_rows if r.state == state], "energy_rel_eV"
        )
        plot_series_with_spline(ax, xs, ys, f"состояние {state}")
    sp_rs = sorted({round(r.R_A, 6) for r in single if r.R_A is not None})
    if sp_rs:
        y_min, y_max = ax.get_ylim()
        ax.scatter(
            sp_rs,
            [y_min + 0.03 * (y_max - y_min)] * len(sp_rs),
            marker="|",
            s=70,
            label="single-point свойства",
        )
    ax.set_xlabel(r"$R_{\mathrm{Li-F}}$, A")
    ax.set_ylabel("Относительная энергия, эВ")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ANALYSIS / "lif_pes_with_property_points.pdf")
    plt.close(fig)

    gap_rows = [r for r in energy_rows if r.gap_to_previous_eV is not None]
    if gap_rows:
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        for state in sorted({r.state for r in gap_rows}):
            xs, ys = unique_xy(
                [r for r in gap_rows if r.state == state], "gap_to_previous_eV"
            )
            plot_series_with_spline(ax, xs, ys, f"E{state}-E{state - 1}")
        ax.set_xlabel(r"$R_{\mathrm{Li-F}}$, A")
        ax.set_ylabel("Энергетический зазор, эВ")
        ax.legend()
        fig.tight_layout()
        fig.savefig(ANALYSIS / "lif_gaps.pdf")
        plt.close(fig)
    else:
        plot_empty(
            plt, ANALYSIS / "lif_gaps.pdf", "Нет данных по энергетическим зазорам"
        )

    zoom_rows = [r for r in energy_rows if 5.0 <= r.R_A <= 7.0]
    if zoom_rows:
        local_min = min(r.energy_Ha for r in zoom_rows if r.energy_Ha is not None)
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        for state in sorted({r.state for r in zoom_rows}):
            rows = [r for r in zoom_rows if r.state == state]
            grouped: dict[float, list[float]] = defaultdict(list)
            for r in rows:
                grouped[round(r.R_A, 6)].append(
                    (r.energy_Ha - local_min) * HARTREE_TO_EV
                )
            xs = sorted(grouped)
            ys = [sum(grouped[x]) / len(grouped[x]) for x in xs]
            plot_series_with_spline(ax, xs, ys, f"состояние {state}")
        ax.set_xlabel(r"$R_{\mathrm{Li-F}}$, A")
        ax.set_ylabel(r"$\Delta E$, эВ")
        ax.set_xlim(5.0, 7.0)
        ax.legend()
        fig.tight_layout()
        fig.savefig(ANALYSIS / "lif_crossing_zoom.pdf")
        plt.close(fig)
    else:
        plot_empty(
            plt,
            ANALYSIS / "lif_crossing_zoom.pdf",
            "Нет данных в окне R = 5-7 A",
        )

    dip_rows = [r for r in normal if r.dipole_D is not None]
    if dip_rows:
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        for state in sorted({r.state for r in dip_rows}):
            xs, ys = unique_xy([r for r in dip_rows if r.state == state], "dipole_D")
            plot_series_with_spline(ax, xs, ys, f"состояние {state}")
        ax.set_xlabel(r"$R_{\mathrm{Li-F}}$, A")
        ax.set_ylabel("Дипольный момент, Д")
        ax.legend()
        fig.tight_layout()
        fig.savefig(ANALYSIS / "lif_dipoles.pdf")
        plt.close(fig)
    else:
        plot_empty(
            plt, ANALYSIS / "lif_dipoles.pdf", "Дипольные моменты в output не найдены"
        )

    charge_rows = [
        r for r in normal if r.charge_Li is not None or r.charge_F is not None
    ]
    if charge_rows:
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        for attr, label in [("charge_Li", "Li"), ("charge_F", "F")]:
            xs, ys = unique_xy(
                [r for r in charge_rows if getattr(r, attr) is not None], attr
            )
            if xs:
                plot_series_with_spline(ax, xs, ys, label)
        ax.set_xlabel(r"$R_{\mathrm{Li-F}}$, A")
        ax.set_ylabel("Заряд, e")
        ax.legend()
        fig.tight_layout()
        fig.savefig(ANALYSIS / "lif_charges.pdf")
        plt.close(fig)
    else:
        plot_empty(
            plt, ANALYSIS / "lif_charges.pdf", "Заряды/заселенности в output не найдены"
        )

    ci_rows = [r for r in normal if r.leading_ci_coefficient is not None]
    if ci_rows:
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        for state in sorted({r.state for r in ci_rows}):
            rows = [r for r in ci_rows if r.state == state]
            grouped: dict[float, list[float]] = defaultdict(list)
            for r in rows:
                grouped[round(r.R_A, 6)].append(
                    abs(r.leading_ci_coefficient or 0.0) ** 2
                )
            xs = sorted(grouped)
            ys = [sum(grouped[x]) / len(grouped[x]) for x in xs]
            plot_series_with_spline(ax, xs, ys, f"состояние {state}")
        ax.set_xlabel(r"$R_{\mathrm{Li-F}}$, A")
        ax.set_ylabel("Вес ведущей CI-конфигурации")
        ax.legend()
        fig.tight_layout()
        fig.savefig(ANALYSIS / "lif_ci_weights.pdf")
        plt.close(fig)
    else:
        plot_empty(
            plt, ANALYSIS / "lif_ci_weights.pdf", "CI-коэффициенты в output не найдены"
        )

    s2_rows = [r for r in normal if r.s2 is not None]
    s2_path = ANALYSIS / "lif_s2_multiplicity.pdf"
    if s2_rows:
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        for state in sorted({r.state for r in s2_rows}):
            xs, ys = unique_xy([r for r in s2_rows if r.state == state], "s2")
            plot_series_with_spline(ax, xs, ys, f"состояние {state}")
        ax.set_xlabel(r"$R_{\mathrm{Li-F}}$, A")
        ax.set_ylabel(r"$\langle S^2 \rangle$")
        ax.legend()
        fig.tight_layout()
        fig.savefig(s2_path)
        plt.close(fig)
    elif s2_path.exists():
        s2_path.unlink()


def ranges_for(rows: list[Record], attr: str) -> str:
    vals = sorted(
        {
            round(r.R_A, 2)
            for r in rows
            if r.R_A is not None and getattr(r, attr) is not None
        }
    )
    if not vals:
        return "not found"
    return f"{vals[0]:.2f}-{vals[-1]:.2f} Ang; {len(vals)} R points"


def evidence_lines(results: dict[Path, ParseResult], key: str) -> str:
    parts = []
    for path, parsed in sorted(results.items()):
        nums = parsed.property_lines.get(key, [])
        if nums:
            parts.append(f"`{rel(path)}` lines {', '.join(map(str, nums[:6]))}")
    return "; ".join(parts) if parts else "not found"


def write_properties_audit(
    results: dict[Path, ParseResult],
    records: list[Record],
    ci_coefficients: list[CiCoefficient],
) -> None:
    normal = [r for r in records if r.status == "normal"]
    dip_rows = [r for r in normal if r.dipole_D is not None]
    charge_rows = [
        r for r in normal if r.charge_Li is not None or r.charge_F is not None
    ]
    ci_rows = [r for r in normal if r.leading_ci_coefficient is not None]
    s2_rows = [r for r in normal if r.s2 is not None]
    nat_rows = [r for r in normal if r.natural_occupation_summary]
    lines = ["# Properties audit", ""]
    lines.append("Generated only from local Firefly output files.")
    lines.append("")
    lines.append("## 1. Dipole moments")
    lines.append("")
    lines.append(f"- status: {'found' if dip_rows else 'not found'}")
    lines.append(f"- R coverage: {ranges_for(dip_rows, 'dipole_D')}")
    lines.append(f"- evidence: {evidence_lines(results, 'dipoles')}")
    lines.append("")
    lines.append("## 2. Charges/populations")
    lines.append("")
    lines.append(f"- status: {'found' if charge_rows else 'not found'}")
    lines.append(f"- R coverage: {ranges_for(charge_rows, 'charge_Li')}")
    lines.append(
        "- type parsed: Mulliken atomic charges from `TOTAL MULLIKEN AND LOWDIN ATOMIC POPULATIONS`"
    )
    lines.append(f"- evidence: {evidence_lines(results, 'charges')}")
    lines.append("")
    lines.append("## 3. CI coefficients / leading configurations")
    lines.append("")
    lines.append(f"- status: {'found' if ci_rows else 'not found'}")
    lines.append(f"- R coverage: {ranges_for(ci_rows, 'leading_ci_coefficient')}")
    lines.append(
        f"- printed determinant coefficients parsed: {len(ci_coefficients)} rows in `lif_ci_coefficients_all.csv`"
    )
    lines.append(f"- evidence: {evidence_lines(results, 'ci_coefficients')}")
    for state in sorted({r.state for r in ci_rows}):
        sample = [r for r in ci_rows if r.state == state and r.R_A is not None]
        sample = sorted(sample, key=lambda r: r.R_A)
        if sample:
            first, last = sample[0], sample[-1]
            lines.append(
                f"- state {state}: first R={first.R_A:.2f} leading={first.leading_configuration} c={first.leading_ci_coefficient:.6f}; "
                f"last R={last.R_A:.2f} leading={last.leading_configuration} c={last.leading_ci_coefficient:.6f}"
            )
    lines.append("")
    lines.append("## 4. Multiplicity / <S^2>")
    lines.append("")
    lines.append(f"- status: {'found' if s2_rows else 'not found'}")
    lines.append(f"- R coverage: {ranges_for(s2_rows, 's2')}")
    lines.append(f"- evidence: {evidence_lines(results, 'spin')}")
    lines.append("")
    lines.append("## 5. Natural occupations")
    lines.append("")
    lines.append(f"- status: {'found' if nat_rows else 'not found'}")
    lines.append(f"- R coverage: {ranges_for(nat_rows, 'natural_occupation_summary')}")
    lines.append(f"- evidence: {evidence_lines(results, 'natural_orbitals')}")
    lines.append("")
    lines.append("## 6. Recharge conclusion")
    lines.append("")
    if dip_rows and (ci_rows or charge_rows or nat_rows):
        lines.append(
            "There is non-energy evidence available for the recharge discussion. Use PES/gaps together with dipoles and at least one of CI coefficients, Mulliken charges, or natural occupations."
        )
    elif dip_rows:
        lines.append(
            "Dipole data are available, so recharge can be discussed only partially until CI/charge/population evidence is obtained."
        )
    else:
        lines.append(
            "Recharge is not proven from the current outputs. PES/gaps alone are insufficient."
        )
    lines.append("")
    lines.append("## Output-by-output evidence")
    lines.append("")
    for path, parsed in sorted(results.items()):
        lines.append(f"### {rel(path)}")
        lines.append("")
        status = parsed.basis.status if parsed.basis else "unknown"
        lines.append(f"- status: {status}")
        for key in [
            "dipoles",
            "charges",
            "ci_coefficients",
            "spin",
            "natural_orbitals",
            "basis",
        ]:
            nums = parsed.property_lines.get(key, [])
            lines.append(
                f"- {key}: {'lines ' + ', '.join(map(str, nums[:8])) if nums else 'not found'}"
            )
        rows = [r for r in records if r.source_file == rel(path)]
        lines.append(f"- parsed records: {len(rows)}")
        lines.append("")
    (ANALYSIS / "properties_audit.md").write_text("\n".join(lines))


def write_report_fragments(
    records: list[Record],
    bases: list[BasisSummary],
    ci_coefficients: list[CiCoefficient],
) -> None:
    normal = [
        r
        for r in records
        if r.status == "normal" and r.R_A is not None and r.energy_Ha is not None
    ]
    surface = [r for r in normal if r.calculation_type == "surface"]
    single = [r for r in normal if r.calculation_type == "single_point"]
    lines = ["# Report fragments", ""]
    lines.append("## Зачем сделаны single-point расчеты")
    lines.append("")
    lines.append(
        "Сканирование `RUNTYP=SURFACE` использовано для построения ППЭ, но такие output-файлы не содержат полного набора свойств волновой функции. Поэтому дополнительно подготовлена ветка `new_runs/single_points_properties/` с расчетами `RUNTYP=ENERGY` в отдельных характерных точках R."
    )
    lines.append("")
    if single:
        rs = sorted({r.R_A for r in single if r.R_A is not None})
        lines.append(
            f"Single-point точки покрывают R = {rs[0]:.2f}-{rs[-1]:.2f} A, всего {len(rs)} расстояний."
        )
    else:
        lines.append(
            "Single-point output-файлы пока не дали нормально распарсенных точек."
        )
    lines.append("")
    lines.append("## Выбор расстояний")
    lines.append("")
    lines.append(
        "Точки выбраны из `analysis/lif_all_data.csv`: минимум основного состояния около 1.60 A, область квазипересечения E3-E2 около 5.85 A, область малого E2-E1 на больших R около 9.00 A, а также диссоциационная область 8.00-9.00 A."
    )
    lines.append("")
    lines.append("## Три нижние ППЭ")
    lines.append("")
    if surface:
        rmin = min(r.R_A for r in surface if r.R_A is not None)
        rmax = max(r.R_A for r in surface if r.R_A is not None)
        states = sorted({r.state for r in surface})
        lines.append(
            f"ППЭ построены по surface-output для состояний {states}; диапазон R = {rmin:.2f}-{rmax:.2f} A."
        )
    else:
        lines.append("Успешные surface-output для ППЭ не найдены.")
    lines.append(
        "Графики для отчета: `lif_pes.pdf`, `lif_pes_relative_ev.pdf`, `lif_crossing_zoom.pdf`, `lif_pes_with_property_points.pdf`."
    )
    lines.append("")
    lines.append("## Перезарядка")
    lines.append("")
    if any(r.dipole_D is not None for r in single):
        lines.append(
            "Дипольные моменты извлечены из single-point output и вынесены в `lif_single_point_properties.csv` и `lif_dipoles.pdf`."
        )
    else:
        lines.append("Дипольные моменты из single-point output пока не извлечены.")
    if any(r.leading_ci_coefficient is not None for r in single):
        lines.append(
            "Ведущие CI-конфигурации и коэффициенты извлечены из блоков `STATE ... ENERGY= ...` / `ALPHA | BETA | COEFFICIENT`; использовать `lif_ci_weights.pdf` и таблицу CSV."
        )
        lines.append(
            f"Все напечатанные Firefly CI-коэффициенты выше порога вывода собраны в `lif_ci_coefficients_all.csv`, всего строк: {len(ci_coefficients)}."
        )
    else:
        lines.append(
            "CI-коэффициенты в успешно обработанных LiF output пока не найдены."
        )
    if any(r.charge_Li is not None or r.charge_F is not None for r in single):
        lines.append(
            "Mulliken-заряды Li/F извлечены из блока `TOTAL MULLIKEN AND LOWDIN ATOMIC POPULATIONS`; использовать `lif_charges.pdf`."
        )
    else:
        lines.append("Заряды/заселенности Li/F пока не извлечены.")
    lines.append("")
    lines.append("## Мультиплетность")
    lines.append("")
    if any(r.s2 is not None for r in single):
        lines.append(
            "Мультиплетность подтверждается строками `STATE ... S= ...`; значения сохранены в столбцах `s2` и `multiplicity`."
        )
    else:
        lines.append(
            "Строки `STATE ... S= ...` для LiF single-point output пока не найдены; мультиплетность roots не закрыта output-подтверждением."
        )
    lines.append("")
    lines.append("## Энергия диссоциации")
    lines.append("")
    lines.append(
        "Оценка энергии диссоциации записана в `dissociation_energy.csv`: минимум берется по state 1, предел - по самой дальней успешной surface-точке. Проверять устойчивость предела нужно по последним точкам R."
    )
    lines.append("")
    lines.append("## Output-фрагменты для скриншотов")
    lines.append("")
    lines.append(
        "- `properties_audit.md`: строки output, где найдены диполи, заряды, CI-коэффициенты, natural occupations и S."
    )
    lines.append(
        "- `lif_single_point_properties.csv`: компактная таблица значений по R и state."
    )
    lines.append(
        "- `fci_basis_summary.md`: подтверждение метода FCI/ALDET, активного пространства и базиса."
    )
    lines.append("")
    lines.append("## File provenance")
    lines.append("")
    for b in bases:
        lines.append(
            f"- `{b.source_file}`: status={b.status}, type={b.calculation_type}, basis={b.basis or 'not found'}, functions={b.n_basis_functions or 'not found'}, CIDET NACT={b.nact or 'not found'}, NELS={b.nels_active or 'not found'}, NSTATE={b.nstate or 'not found'}."
        )
    (ANALYSIS / "report_fragments.md").write_text("\n".join(lines))


def main() -> None:
    ANALYSIS.mkdir(exist_ok=True)
    results: dict[Path, ParseResult] = {}
    records: list[Record] = []
    bases: list[BasisSummary] = []
    ci_coefficients: list[CiCoefficient] = []

    for path in find_outputs():
        parsed = parse_output(path)
        results[path] = parsed
        records.extend(parsed.records)
        ci_coefficients.extend(parsed.ci_coefficients)
        if parsed.basis:
            bases.append(parsed.basis)

    enrich(records)
    write_lif_csv(records)
    write_single_point_csv(records)
    write_ci_coefficients_all_csv(ci_coefficients)
    write_basis_csv(bases)
    write_dissociation(records)
    plot_outputs(records)
    write_properties_audit(results, records, ci_coefficients)
    write_report_fragments(records, bases, ci_coefficients)

    print(f"Parsed {len(results)} output files")
    print(f"Wrote {len(records)} data rows to {ANALYSIS / 'lif_all_data.csv'}")
    print(f"Wrote single-point rows to {ANALYSIS / 'lif_single_point_properties.csv'}")
    print(
        f"Wrote printed CI coefficients to {ANALYSIS / 'lif_ci_coefficients_all.csv'}"
    )


if __name__ == "__main__":
    main()
