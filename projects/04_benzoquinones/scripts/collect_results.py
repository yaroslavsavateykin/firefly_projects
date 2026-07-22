from pathlib import Path
import csv
import re

ROOT = Path(__file__).resolve().parents[1]
H2EV = 27.211386245988

STAGE_FILES = {
    ("p_bq", "01_mp2_opt"): ROOT / "p_bq/01_mp2_opt/p_bq_mp2_opt.out",
    ("p_bq", "02_cis"): ROOT / "p_bq/02_cis/p_bq_cis.out",
    ("p_bq", "03_cis_opt_geometry"): ROOT / "p_bq/03_cis_opt_geometry/p_bq_cis_opt_geometry.out",
    ("p_bq", "04_xmcqdpt2"): ROOT / "p_bq/04_xmcqdpt2/p_bq_xmcqdpt2.out",
    ("o_bq", "01_mp2_opt"): ROOT / "o_bq/01_mp2_opt/o_bq_mp2_opt.out",
    ("o_bq", "02_cis"): ROOT / "o_bq/02_cis/o_bq_cis.out",
    ("o_bq", "03_cis_opt_geometry"): ROOT / "o_bq/03_cis_opt_geometry/o_bq_cis_opt_geometry.out",
    ("o_bq", "04_xmcqdpt2"): ROOT / "o_bq/04_xmcqdpt2/o_bq_xmcqdpt2.out",
}


def read(path: Path) -> str:
    return path.read_text(errors="ignore")


def last_float(pattern: str, text: str):
    values = [float(x) for x in re.findall(pattern, text)]
    return values[-1] if values else None


def first_float(pattern: str, text: str):
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def status(text: str) -> str:
    if "TERMINATED NORMALLY" in text:
        return "normal"
    if "TERMINATED ABNORMALLY" in text:
        return "abnormal"
    return "unknown"


def timing(text: str):
    cpu = last_float(r"GLOBAL CPU TIME ELAPSED\s*=\s*([0-9.]+) SECONDS", text)
    wall = last_float(r"RANK 0 WALL CLOCK TIME\s*=\s*([0-9.]+) SECONDS", text)
    return cpu, wall


def fmt(value, digits=6) -> str:
    if value == "" or value is None:
        return ""
    return f"{float(value):.{digits}f}"


def collect():
    rows = []
    summary = []
    for (iso, stage), path in STAGE_FILES.items():
        text = read(path)
        basis = first_float(r"TOTAL NUMBER OF BASIS FUNCTIONS\s*=\s*([0-9]+)", text)
        cpu, wall = timing(text)
        energy = None
        nsearch = None
        maxg = ""
        rmsg = ""
        mcit = None
        if stage == "01_mp2_opt":
            geometry = "initial -> MP2 optimized"
            energy = last_float(r"TOTAL ENERGY\s*=\s*(-?[0-9]+\.[0-9]+)", text)
            searches = [int(x) for x in re.findall(r"NSERCH=\s*([0-9]+)", text)]
            nsearch = max(searches) if searches else None
            gradients = re.findall(
                r"MAXIMUM GRADIENT =\s*([0-9.]+)\s+RMS GRADIENT =\s*([0-9.]+)",
                text,
            )
            if gradients:
                maxg, rmsg = map(float, gradients[-1])
            note = "MP2 geometry optimization; OPTTOL=1D-4, NSTEP=100"
        elif stage in ("02_cis", "03_cis_opt_geometry"):
            geometry = "initial" if stage == "02_cis" else "MP2 optimized"
            energy = last_float(r"FINAL ENERGY IS\s*(-?[0-9]+\.[0-9]+)", text)
            note = "CIS/RHF single point"
        else:
            geometry = "MP2 optimized"
            energy = last_float(r"FINAL MCSCF ENERGY IS\s*(-?[0-9]+\.[0-9]+)", text)
            match = re.search(
                r"FINAL MCSCF ENERGY IS\s*-?[0-9]+\.[0-9]+ AFTER\s*([0-9]+) ITERATIONS",
                text,
            )
            mcit = int(match.group(1)) if match else None
            if iso == "p_bq":
                note = "XMCQDPT2/CASSCF(12,10); MP2 geometry, CIS $VEC, ACURCY=5D-2 ENGTOL=1D-2"
            else:
                note = "XMCQDPT2/CASSCF(12,10); MP2 geometry, CIS $VEC, ACURCY=5D-3 ENGTOL=1D-3"
        item = {
            "isomer": iso,
            "stage": stage,
            "status": status(text),
            "geometry": geometry,
            "basis_functions": int(basis) if basis else "",
            "energy_hartree": energy,
            "nsearch_or_mcscf_iter": nsearch if nsearch is not None else (mcit if mcit is not None else ""),
            "max_gradient": maxg,
            "rms_gradient": rmsg,
            "cpu_seconds": cpu,
            "wall_seconds": wall,
            "note": note,
            "file": str(path.relative_to(ROOT)),
        }
        summary.append(item)
        rows.append({"row_type": "stage", **item, "xmc_state": "", "spin_s": "", "excitation_ev": ""})

    for iso in ("p_bq", "o_bq"):
        path = STAGE_FILES[(iso, "04_xmcqdpt2")]
        text = read(path)
        energies = [float(x) for x in re.findall(r"TOTAL ENERGY =\s*(-?[0-9]+\.[0-9]+)", text)][-5:]
        base = energies[0]
        for index, energy in enumerate(energies, 1):
            rows.append(
                {
                    "row_type": "xmc_state",
                    "isomer": iso,
                    "stage": "04_xmcqdpt2",
                    "status": "normal",
                    "geometry": "MP2 optimized",
                    "basis_functions": 160,
                    "energy_hartree": energy,
                    "xmc_state": index,
                    "spin_s": "",
                    "excitation_ev": (energy - base) * H2EV,
                    "nsearch_or_mcscf_iter": "",
                    "max_gradient": "",
                    "rms_gradient": "",
                    "cpu_seconds": "",
                    "wall_seconds": "",
                    "note": "XMCQDPT2 state total energy; excitation relative to state 1",
                    "file": str(path.relative_to(ROOT)),
                }
            )

    attempts = [
        ("o_bq", "04_xmcqdpt2_failed_andrew_vec", "o_bq/04_xmcqdpt2/o_bq_xmcqdpt2_failed_andrew_vec.out", "abnormal", "Andrew p-BQ $VEC on o-BQ; MCSCF did not converge"),
        ("o_bq", "04_xmcqdpt2_failed_own_mcscf_vec", "o_bq/04_xmcqdpt2/o_bq_xmcqdpt2_failed_own_mcscf_vec.out", "abnormal", "Restart from failed o-BQ MCSCF $VEC; MCSCF did not converge in 200 iterations"),
        ("o_bq", "04_xmcqdpt2_failed_mp2geom_nstate5", "o_bq/04_xmcqdpt2/o_bq_xmcqdpt2_failed_mp2geom_nstate5.out", "abnormal", "NSTATE=5 had only 3 singlet CI eigenvectors, DETDM2 error"),
        ("o_bq", "04_xmcqdpt2_failed_mp2geom_nstate9", "o_bq/04_xmcqdpt2/o_bq_xmcqdpt2_failed_mp2geom_nstate9.out", "abnormal", "NSTATE=9 still insufficient for five singlet averaged roots, DETDM2 error"),
        ("o_bq", "01_mp2_opt_trmax005_failed", "o_bq/01_mp2_opt/o_bq_mp2_opt_trmax005_failed.out", "abnormal", "Initial o-BQ MP2 with TRMAX=0.05 failed; final used restart geometry and TRMAX=0.01"),
    ]
    for iso, stage, rel, st, note in attempts:
        path = ROOT / rel
        if not path.exists():
            continue
        text = read(path)
        cpu, wall = timing(text)
        rows.append(
            {
                "row_type": "attempt",
                "isomer": iso,
                "stage": stage,
                "status": st,
                "geometry": "various test geometries",
                "basis_functions": int(first_float(r"TOTAL NUMBER OF BASIS FUNCTIONS\s*=\s*([0-9]+)", text) or 160),
                "energy_hartree": "",
                "xmc_state": "",
                "spin_s": "",
                "excitation_ev": "",
                "nsearch_or_mcscf_iter": "",
                "max_gradient": "",
                "rms_gradient": "",
                "cpu_seconds": cpu or "",
                "wall_seconds": wall or "",
                "note": note,
                "file": rel,
            }
        )
    return rows, summary


def write_csv(rows):
    fields = [
        "row_type",
        "isomer",
        "stage",
        "status",
        "geometry",
        "basis_functions",
        "energy_hartree",
        "xmc_state",
        "spin_s",
        "excitation_ev",
        "nsearch_or_mcscf_iter",
        "max_gradient",
        "rms_gradient",
        "cpu_seconds",
        "wall_seconds",
        "note",
        "file",
    ]
    with (ROOT / "results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows, summary):
    p_mp2 = next(x for x in summary if x["isomer"] == "p_bq" and x["stage"] == "01_mp2_opt")
    o_mp2 = next(x for x in summary if x["isomer"] == "o_bq" and x["stage"] == "01_mp2_opt")
    lines = [
        "# Отчет по пересборке и расчетам практикума 4",
        "",
        "## Что было сделано",
        "",
        "1. Новая директория пересобрана по образцу Андрея: входные файлы Firefly генерируются скриптом `scripts/build_andrew_style.sh`, запуск двух изомеров описан в `run_all.sh`.",
        "2. Внешний `acc-pVDZ` заменен встроенным кастомным базисом из `basis_templates/quinone_MP2.inp`. Во всех финальных расчетах 160 базисных функций.",
        "3. Выполнены MP2-оптимизация, CIS single point, CIS на последующей геометрии и XMCQDPT2/CASSCF(12,10).",
        "4. После замечания схема исправлена: stage 03 CIS и stage 04 XMCQDPT2 для обоих изомеров считаются на MP2-оптимизированной геометрии. Stage 02 CIS оставлен как single point на исходной геометрии для сравнения.",
        "5. На MP2-оптимизированной геометрии строгая CASSCF-сходимость для XMC не достигалась устойчиво; полные XMC-расчеты получены с ослабленной MCSCF-предподготовкой. Для `p_bq`: `ACURCY=5D-2`, `ENGTOL=1D-2`; для `o_bq`: `ACURCY=5D-3`, `ENGTOL=1D-3`.",
        "",
        "## Базис и активное пространство",
        "",
        "Базисные блоки C/O/H извлекаются из Андреевского MP2-ввода и печатаются после каждого атома в `$DATA`; `$BASIS EXTFIL` не используется. Активное пространство XMC: `NCORE=22`, `NACT=10`, `NELS=12`, то есть CAS(12,10). XMC считает 5 состояний с равными весами.",
        "",
        "## Итог по стадиям",
        "",
        "| Изомер | Стадия | Геометрия | Статус | Энергия, Hartree | Шаги/итер. | Max grad | RMS grad | CPU, s | Wall, s |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summary:
        lines.append(
            f"| {item['isomer']} | {item['stage']} | {item['geometry']} | {item['status']} | {fmt(item['energy_hartree'], 10)} | {item['nsearch_or_mcscf_iter']} | {fmt(item['max_gradient'], 7)} | {fmt(item['rms_gradient'], 7)} | {fmt(item['cpu_seconds'], 1)} | {fmt(item['wall_seconds'], 1)} |"
        )
    lines += [
        "",
        "## XMCQDPT2 состояния",
        "",
        "| Изомер | State | Energy, Hartree | Excitation, eV |",
        "|---|---:|---:|---:|",
    ]
    for row in [x for x in rows if x["row_type"] == "xmc_state"]:
        lines.append(f"| {row['isomer']} | {row['xmc_state']} | {fmt(row['energy_hartree'], 10)} | {fmt(row['excitation_ev'], 4)} |")
    lines += [
        "",
        "## Ключевые выводы",
        "",
        f"- MP2-минимизация `p_bq` сошлась за {p_mp2['nsearch_or_mcscf_iter']} шагов: E = {fmt(p_mp2['energy_hartree'], 10)} Hartree, max/RMS gradient = {fmt(p_mp2['max_gradient'], 7)}/{fmt(p_mp2['rms_gradient'], 7)}.",
        f"- MP2-минимизация `o_bq` сошлась за {o_mp2['nsearch_or_mcscf_iter']} шагов: E = {fmt(o_mp2['energy_hartree'], 10)} Hartree, max/RMS gradient = {fmt(o_mp2['max_gradient'], 7)}/{fmt(o_mp2['rms_gradient'], 7)}.",
        "- Stage 02 CIS считается на исходной геометрии, поэтому его энергия не обязана совпадать со stage 03. Stage 03 CIS и XMC теперь считаются на MP2-оптимизированной геометрии.",
        "- Главная причина падений XMC на MP2-геометрии была в MCSCF-части: строгая орбитальная оптимизация активного пространства CAS(12,10) начинала колебаться.",
        "- Попытки `NSTATE=5` и `NSTATE=9` не подходят: среди первых корней недостаточно пяти синглетов для усреднения, поэтому Firefly завершал `DETDM2` с ошибкой.",
        "- Финальные XMC-расчеты являются численно завершенными на правильной MP2-геометрии, но их MCSCF-критерии слабее Андреевского. Для строгого сравнения возбужденных состояний это надо явно учитывать.",
        "",
        "## Файлы",
        "",
        "- CSV-таблица: `results.csv`",
        "- Финальные выходы: `p_bq/*/*.out`, `o_bq/*/*.out`",
        "- Основные скрипты: `scripts/build_andrew_style.sh`, `run_all.sh`",
        "",
    ]
    (ROOT / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    all_rows, stage_summary = collect()
    write_csv(all_rows)
    write_report(all_rows, stage_summary)
    print("wrote report.md")
    print("wrote results.csv")
