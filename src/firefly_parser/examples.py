"""
Usage examples for the Firefly/GAMESS output parser.
"""

import numpy as np
try:
    from .parsing import (
        read_text,
        read_total_energy,
        read_state_energies,
        read_converged,
        read_scan,
        read_state_scan,
    )
except ImportError:  # Allow direct execution from this directory.
    from parsing import (
        read_text,
        read_total_energy,
        read_state_energies,
        read_converged,
        read_scan,
        read_state_scan,
    )


# ===== EXAMPLE 1: Pract01 - Single-point HF energies =====
def example_pract01():
    """Extract HF energy from a single-point calculation."""
    path = "projects/01_hartree_fock/h2_rhf_sto3g/h2_rhf_sto3g.out"

    energy = read_total_energy(path)
    converged = read_converged(path)

    print(f"H2 RHF/STO-3G energy: {energy:.10f} Ha")
    print(f"Converged: {converged}")


# ===== EXAMPLE 2: Pract02 - Bond length scan =====
def example_pract02_scan():
    """
    Extract H2 potential curve.
    Assumes output files for each R value are available.
    """
    r_values = np.linspace(0.4, 3.0, 30)  # Angstroms
    output_files = [
        f"projects/02_h2_potential_curves/out_{r:.2f}.out" for r in r_values
    ]

    # This would work if files exist:
    # result = read_scan(r_values, output_files, read_total_energy)
    # energies = result['y']
    # # Now can plot or analyze
    # print(f"Min energy: {energies.min():.10f} at R = {r_values[energies.argmin()]}")

    print("Pract02 scan would return: {'x': [0.4, 0.46, ..., 3.0], 'y': [E1, E2, ...]}")


# ===== EXAMPLE 3: Pract03 - LiF with multiple states =====
def example_pract03_states():
    """
    Extract LiF energies for 3 electronic states across R values.
    Assumes output files are available.
    """
    r_values = np.linspace(1.0, 6.0, 20)  # Angstroms
    output_files = [
        f"projects/03_lif_potential_surfaces/lif_scan/LiF_R{r:.2f}.out" for r in r_values
    ]

    # This would work if files exist:
    # result = read_state_scan(r_values, output_files, n_states=3)
    # print("Keys:", list(result.keys()))
    # plot(result['x'], result['state_1'], label='Ground state')
    # plot(result['x'], result['state_2'], label='1st excited')
    # plot(result['x'], result['state_3'], label='2nd excited')

    print("Pract03 result would contain:")
    print("  - result['x']: R values [1.0, 1.26, ..., 6.0]")
    print("  - result['state_1']: ground state energies")
    print("  - result['state_2']: 1st excited state energies")
    print("  - result['state_3']: 2nd excited state energies")


# ===== EXAMPLE 4: Custom analysis =====
def example_custom_analysis():
    """Example of computing dissociation energy."""
    # Read H2 energies at various R
    r_values = np.array([0.4, 0.5, 0.6, 0.7, 1.0, 2.0, 5.0])
    # (in real usage, would read from actual output files)

    # result = read_scan(r_values, output_files, read_total_energy)
    # e_equilibrium = result['y'].min()
    # e_separated = result['y'][-1]  # At large R
    # dissociation_energy = e_separated - e_equilibrium

    print("Custom analysis example:")
    print("  De = E(R→∞) - E(R_eq)  # Dissociation energy")


if __name__ == "__main__":
    print("Firefly/GAMESS Output Parser - Usage Examples\n")

    print("=" * 60)
    print("Pract01: Single-point HF energies")
    print("=" * 60)
    # example_pract01()  # Uncomment if files exist

    print("\n" + "=" * 60)
    print("Pract02: Bond length scan")
    print("=" * 60)
    example_pract02_scan()

    print("\n" + "=" * 60)
    print("Pract03: Electronic states at different geometries")
    print("=" * 60)
    example_pract03_states()

    print("\n" + "=" * 60)
    print("Custom: Energy analysis")
    print("=" * 60)
    example_custom_analysis()
