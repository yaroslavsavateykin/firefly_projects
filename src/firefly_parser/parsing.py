"""
Minimal Firefly/GAMESS output parser for quantum chemistry data.
"""

import re
import numpy as np
from pathlib import Path


def read_text(path):
    """Read output file as text."""
    with open(path, 'r', errors='ignore') as f:
        return f.read()


def read_total_energy(path):
    """
    Extract total energy (RHF/MP2/etc) from output.
    Returns the LAST energy found (final converged energy).
    """
    text = read_text(path)
    matches = re.findall(r'FINAL ENERGY IS\s+(-?\d+\.\d+)', text)
    if matches:
        return float(matches[-1])
    raise ValueError(f"No FINAL ENERGY found in {path}")


def read_state_energies(path, n_states=None):
    """
    Extract energies of multiple electronic states from CI output.
    Returns array of shape (n_states,).

    For ALDET CI, looks for "STATE #N" energy blocks.
    """
    text = read_text(path)

    # Pattern for CI state energies
    # Matches: "STATE #1, ENERGY = -75.1234567890"
    pattern = r'STATE\s*#\s*(\d+).*?ENERGY\s*=\s*(-?[\d.]+)'
    matches = re.findall(pattern, text)

    if not matches:
        raise ValueError(f"No CI states found in {path}")

    states = {int(state_num): float(energy) for state_num, energy in matches}
    n_found = len(states)

    if n_states is not None and n_found != n_states:
        raise ValueError(
            f"Expected {n_states} states but found {n_found} in {path}"
        )

    sorted_states = sorted(states.items())
    energies = np.array([e for _, e in sorted_states])

    return energies


def read_optimized_energy(path):
    """
    Extract final optimized energy from geometry optimization.
    Same as read_total_energy (returns last FINAL ENERGY).
    """
    return read_total_energy(path)


def read_converged(path):
    """
    Check if optimization/calculation converged.
    Simple heuristic: look for convergence indicators.
    """
    text = read_text(path)

    has_convergence = bool(
        re.search(r'DENSITY CONVERGED|DIIS CONVERGED', text)
    )
    has_final_energy = bool(re.search(r'FINAL ENERGY IS', text))

    return has_convergence and has_final_energy


def read_scan(x_values, output_files, reader_func):
    """
    Read a series of single-point calculations (e.g., bond length scan).

    Args:
        x_values: array of parameter values (e.g., bond lengths)
        output_files: list of output file paths, same length as x_values
        reader_func: function(path) -> float, e.g., read_total_energy

    Returns:
        dict with keys "x" and "y", both numpy arrays
    """
    x_array = np.asarray(x_values)
    y_array = np.array([reader_func(f) for f in output_files])

    if len(x_array) != len(y_array):
        raise ValueError(
            f"Mismatch: {len(x_array)} x-values but {len(y_array)} energies"
        )

    return {
        "x": x_array,
        "y": y_array,
    }


def read_state_scan(x_values, output_files, n_states=3):
    """
    Read a series of calculations with multiple electronic states.

    Args:
        x_values: array of parameter values
        output_files: list of output file paths
        n_states: number of electronic states per calculation

    Returns:
        dict with keys "x", "state_1", "state_2", ..., "state_N"
    """
    x_array = np.asarray(x_values)

    state_arrays = {i: [] for i in range(1, n_states + 1)}

    for f in output_files:
        energies = read_state_energies(f, n_states=n_states)
        for i, energy in enumerate(energies, start=1):
            state_arrays[i].append(energy)

    result = {"x": x_array}
    for i in range(1, n_states + 1):
        result[f"state_{i}"] = np.array(state_arrays[i])

    return result
