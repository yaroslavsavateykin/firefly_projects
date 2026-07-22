#!/usr/bin/env python3
"""Plot H2/STO-3G method energies and all available spin diagnostics."""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


MAIN_CSV = Path("results/h2_surface_methods_comparison.csv")
FCI_ROOTS_CSV = Path("results/h2_fci_roots.csv")

MAIN_PNG = Path("results/h2_surface_methods_energy_spin.png")
MAIN_PDF = Path("results/h2_surface_methods_energy_spin.pdf")
FCI_SPIN_PNG = Path("results/h2_fci_spin_roots.png")
FCI_SPIN_PDF = Path("results/h2_fci_spin_roots.pdf")
ALL_SPIN_PNG = Path("results/h2_all_spin_states.png")
ALL_SPIN_PDF = Path("results/h2_all_spin_states.pdf")
ENERGY_ZOOM_PNG = Path("results/h2_surface_methods_energy_zoom.png")
ENERGY_ZOOM_PDF = Path("results/h2_surface_methods_energy_zoom.pdf")

MAIN_COLUMNS = (
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
)

FCI_ROOT_COLUMNS = (
    "R_angstrom",
    "E_root0",
    "E_root1",
    "E_root2",
    "E_root3",
    "S2_root0",
    "S2_root1",
    "S2_root2",
    "S2_root3",
)

METHOD_STYLES = {
    "RHF": {
        "color": "black",
        "linestyle": "-",
        "marker": "o",
        "markersize": 8,
        "energy": "E_RHF_hartree",
        "s2": "S2_RHF",
    },
    "UHF": {
        "color": "tab:blue",
        "linestyle": "-",
        "marker": "s",
        "markersize": 3.8,
        "energy": "E_UHF_plain_hartree",
        "s2": "S2_UHF_plain",
    },
    "UHF mixed": {
        "color": "tab:green",
        "linestyle": "-",
        "marker": "^",
        "markersize": 4.2,
        "energy": "E_UHF_mix_hartree",
        "s2": "S2_UHF_mix",
    },
    "MP2": {
        "color": "tab:red",
        "linestyle": "-",
        "marker": "D",
        "markersize": 8,
        "energy": "E_MP2_hartree",
        "s2": "S2_MP2_ref",
        "spin_label": "MP2",
    },
    "UMP2": {
        "color": "tab:orange",
        # "linestyle": (0, (5, 2, 1, 2)),
        "linestyle": "-",
        "marker": "v",
        "markersize": 4.5,
        "energy": "E_UMP2_hartree",
        "s2": "S2_UMP2_ref",
        "spin_label": "UMP2",
    },
    "UMP2 mixed": {
        "color": "tab:brown",
        # "linestyle": (0, (3, 1, 1, 1)),
        "linestyle": "-",
        "marker": "P",
        "markersize": 4.8,
        "energy": "E_UMP2_mix_hartree",
        "s2": "S2_UMP2_mix",
        "spin_label": "UMP2 mixed",
    },
    "FCI": {
        "color": "tab:purple",
        "linestyle": "-",
        "marker": "d",
        "markersize": 5.0,
        "energy": "E_FCI0_hartree",
        "s2": "S2_FCI0",
        "spin_label": "FCI root 0",
    },
}

FCI_ROOT_STYLES = {
    "Root 0": {
        "color": "black",
        "linestyle": "-",
        "marker": "o",
        "markersize": 3.5,
        "s2": "S2_root0",
    },
    "Root 1": {
        "color": "tab:blue",
        "linestyle": "--",
        "marker": "s",
        "markersize": 4.0,
        "s2": "S2_root1",
    },
    "Root 2": {
        "color": "tab:green",
        "linestyle": "-.",
        "marker": "^",
        "markersize": 4.5,
        "s2": "S2_root2",
    },
    "Root 3": {
        "color": "tab:red",
        "linestyle": ":",
        "marker": "D",
        "markersize": 4.8,
        "s2": "S2_root3",
    },
}


def require_matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        print(
            "matplotlib is required for plotting. Install it or run only parse_outputs.py for CSV generation.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    plt.rcParams.update(
        {
            "font.family": "serif",
            "mathtext.fontset": "cm",
            "font.size": 12,
            "axes.labelsize": 13,
            "legend.fontsize": 10,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
        }
    )
    return plt


def parse_number(value: str) -> float | None:
    if value == "":
        return None
    number = float(value)
    if math.isnan(number):
        return None
    return number


def read_csv(path: Path, expected_columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.exists():
        print(f"Missing {path}. Run: python3 parse_outputs.py", file=sys.stderr)
        raise SystemExit(1)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(expected_columns):
            print(
                f"Unexpected CSV columns in {path}: {reader.fieldnames}. "
                f"Expected: {list(expected_columns)}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return list(reader)


def values(rows: list[dict[str, str]], key: str) -> tuple[list[float], list[float]]:
    x_values: list[float] = []
    y_values: list[float] = []
    for row in rows:
        y = parse_number(row[key])
        if y is None:
            continue
        x_values.append(float(row["R_angstrom"]))
        y_values.append(y)
    return x_values, y_values


def style_axes(ax) -> None:
    ax.grid(True, alpha=0.25, linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(frameon=False)


def plot_curve(
    ax, x: list[float], y: list[float], label: str, style: dict[str, object]
) -> None:
    ax.plot(
        x,
        y,
        label=label,
        color=style["color"],
        linestyle=style["linestyle"],
        marker=style["marker"],
        markevery=4,
        linewidth=1.8,
        markersize=float(style.get("markersize", 4.0)),
        markerfacecolor="white",
    )


def plot_main_energy_spin(plt, main_rows: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(11, 4.2),
        dpi=300,
        constrained_layout=True,
    )

    for label, style in METHOD_STYLES.items():
        x, y = values(main_rows, str(style["energy"]))
        if y:
            plot_curve(axes[0], x, y, label, style)
    axes[0].set_xlabel(r"$R_{\mathrm{H-H}},\ \mathrm{\AA}$")
    axes[0].set_ylabel(r"$E,\ E_\mathrm{h}$")
    style_axes(axes[0])

    for label, style in METHOD_STYLES.items():
        x, y = values(main_rows, str(style["s2"]))
        if not y:
            if label == "FCI":
                print(
                    "WARNING: S2_FCI0 is empty; FCI is not plotted on the main spin panel.",
                    file=sys.stderr,
                )
            continue
        plot_curve(axes[1], x, y, str(style.get("spin_label", label)), style)
    axes[1].set_xlabel(r"$R_{\mathrm{H-H}},\ \mathrm{\AA}$")
    axes[1].set_ylabel(r"$\langle S^2 \rangle$")
    style_axes(axes[1])

    fig.savefig(MAIN_PNG)
    fig.savefig(MAIN_PDF)
    plt.close(fig)
    print(f"Wrote {MAIN_PNG}")
    print(f"Wrote {MAIN_PDF}")


def energy_points(main_rows: list[dict[str, str]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for style in METHOD_STYLES.values():
        x_values, y_values = values(main_rows, str(style["energy"]))
        points.extend(zip(x_values, y_values))
    return points


def apply_minimum_zoom(ax, main_rows: list[dict[str, str]]) -> None:
    points = energy_points(main_rows)
    if not points:
        return

    min_r, min_e = min(points, key=lambda item: item[1])
    all_r = [point[0] for point in points]
    # x_left = max(min(all_r), min_r - 0.45)
    # x_right = min(max(all_r), min_r + 0.55)
    x_left = 0.25
    x_right = 2

    zoom_energies = [
        energy for r_value, energy in points if x_left <= r_value <= x_right
    ]
    if not zoom_energies:
        return

    y_min = min(zoom_energies)
    y_max = max(zoom_energies)
    margin = max((y_max - y_min) * 0.08, 0.002)

    ax.set_xlim(x_left, x_right)
    ax.set_ylim(y_min - margin, y_max + margin)


def plot_energy_with_minimum_zoom(plt, main_rows: list[dict[str, str]]) -> None:
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(11, 4.2),
        dpi=300,
        constrained_layout=True,
    )

    for ax in axes:
        for label, style in METHOD_STYLES.items():
            x, y = values(main_rows, str(style["energy"]))
            if y:
                plot_curve(ax, x, y, label, style)
        ax.set_xlabel(r"$R_{\mathrm{H-H}},\ \mathrm{\AA}$")
        ax.set_ylabel(r"$E,\ E_\mathrm{h}$")
        style_axes(ax)

    apply_minimum_zoom(axes[1], main_rows)

    fig.savefig(ENERGY_ZOOM_PNG)
    fig.savefig(ENERGY_ZOOM_PDF)
    plt.close(fig)
    print(f"Wrote {ENERGY_ZOOM_PNG}")
    print(f"Wrote {ENERGY_ZOOM_PDF}")


def plot_fci_spin_roots(plt, fci_rows: list[dict[str, str]]) -> int:
    fig, ax = plt.subplots(figsize=(6.2, 4.2), dpi=300, constrained_layout=True)
    plotted = 0
    for label, style in FCI_ROOT_STYLES.items():
        x, y = values(fci_rows, str(style["s2"]))
        if not y:
            continue
        plotted += 1
        plot_curve(ax, x, y, label, style)
    ax.set_xlabel(r"$R_{\mathrm{H-H}},\ \mathrm{\AA}$")
    ax.set_ylabel(r"$\langle S^2 \rangle$")
    style_axes(ax)
    fig.savefig(FCI_SPIN_PNG)
    fig.savefig(FCI_SPIN_PDF)
    plt.close(fig)
    print(f"Wrote {FCI_SPIN_PNG}")
    print(f"Wrote {FCI_SPIN_PDF}")
    print(f"FCI roots plotted on spin graph: {plotted}")
    return plotted


def plot_all_spin_states(
    plt,
    main_rows: list[dict[str, str]],
    fci_rows: list[dict[str, str]],
) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.4), dpi=300, constrained_layout=True)
    for label, style in METHOD_STYLES.items():
        x, y = values(main_rows, str(style["s2"]))
        if y:
            plot_curve(ax, x, y, str(style.get("spin_label", label)), style)
    for label, style in FCI_ROOT_STYLES.items():
        x, y = values(fci_rows, str(style["s2"]))
        if y:
            root_style = dict(style)
            root_style["linewidth"] = 1.4
            plot_curve(ax, x, y, f"FCI {label}", root_style)
    ax.set_xlabel(r"$R_{\mathrm{H-H}},\ \mathrm{\AA}$")
    ax.set_ylabel(r"$\langle S^2 \rangle$")
    style_axes(ax)
    fig.savefig(ALL_SPIN_PNG)
    fig.savefig(ALL_SPIN_PDF)
    plt.close(fig)
    print(f"Wrote {ALL_SPIN_PNG}")
    print(f"Wrote {ALL_SPIN_PDF}")


def main() -> None:
    main_rows = read_csv(MAIN_CSV, MAIN_COLUMNS)
    fci_rows = read_csv(FCI_ROOTS_CSV, FCI_ROOT_COLUMNS)
    Path("results").mkdir(parents=True, exist_ok=True)

    plt = require_matplotlib()
    plot_main_energy_spin(plt, main_rows)
    plot_energy_with_minimum_zoom(plt, main_rows)
    plot_fci_spin_roots(plt, fci_rows)
    plot_all_spin_states(plt, main_rows, fci_rows)


if __name__ == "__main__":
    main()
