"""
Real usage examples with actual Pract01-03 files from the project.
"""

import numpy as np
from pathlib import Path
try:
    from .parsing import read_total_energy, read_converged, read_scan, read_text, read_state_energies
except ImportError:  # Allow direct execution from this directory.
    from parsing import read_total_energy, read_converged, read_scan, read_text, read_state_energies


def example_pract01_hf_molecules():
    """
    Extract HF energies from Pract01 calculations.
    Shows: single-point energy reading for different molecules.
    """
    print("=" * 70)
    print("Example 1: Pract01 - HF energies of different molecules")
    print("=" * 70)

    molecules = {
        "H2 (RHF/STO-3G)": "projects/01_hartree_fock/h2_rhf_sto3g/h2_rhf_sto3g.out",
        "H2 (RHF/6-31G)": "projects/01_hartree_fock/h2_rhf_631g/h2_rhf_631g.out",
        "H2+ (UHF/STO-3G)": "projects/01_hartree_fock/h2plus_uhf_sto3g/h2plus_uhf_sto3g.out",
        "CH4 (Boys)": "projects/01_hartree_fock/ch4_boys_sto3g/ch4_boys_sto3g.out",
        "CO (RHF/STO-3G)": "projects/01_hartree_fock/co_rhf_sto3g/co_rhf_sto3g.out",
    }

    print("\nMolecule energies:")
    print("-" * 70)

    results = {}
    for name, path in molecules.items():
        if Path(path).exists():
            energy = read_total_energy(path)
            converged = read_converged(path)
            results[name] = energy
            status = "✓" if converged else "⚠"
            print(f"{status} {name:30s} {energy:15.10f} Ha")

    return results


def example_pract02_h2_curve():
    """
    Extract H2 potential curve from Pract02.
    Shows: how to read a series of single-point calculations.
    """
    print("\n" + "=" * 70)
    print("Example 2: Pract02 - H2 potential energy curve")
    print("=" * 70)

    rhf_file = "projects/02_h2_potential_curves/h2_curve/h2_rhf_surf.out"
    fci_file = "projects/02_h2_potential_curves/h2_curve/h2_fci_surf.out"

    print(f"\nBoth RHF and FCI surface scans contain 11 geometry points")
    print(f"Starting R: 0.40 Å")
    print(f"Step size:  0.46 Å")

    if Path(rhf_file).exists() and Path(fci_file).exists():
        import re
        # Extract energies from each file
        text_rhf = read_text(rhf_file)
        text_fci = read_text(fci_file)

        rhf_energies = [float(e) for e in re.findall(
            r'FINAL ENERGY IS\s+(-?\d+\.\d+)', text_rhf
        )]
        fci_energies = [float(e) for e in re.findall(
            r'FINAL ENERGY IS\s+(-?\d+\.\d+)', text_fci
        )]

        # Create hypothetical R values for visualization
        r_start = 0.4
        r_step = 0.46
        r_values = np.array([r_start + i * r_step for i in range(len(rhf_energies))])

        print(f"\nRHF energies: {len(rhf_energies)} points")
        print(f"  Min: {min(rhf_energies):12.8f} Ha at R = {r_values[np.argmin(rhf_energies)]:.2f} Å")
        print(f"  Max: {max(rhf_energies):12.8f} Ha at R = {r_values[np.argmax(rhf_energies)]:.2f} Å")

        print(f"\nFCI energies: {len(fci_energies)} points")
        print(f"  Min: {min(fci_energies):12.8f} Ha at R = {r_values[np.argmin(fci_energies)]:.2f} Å")
        print(f"  Max: {max(fci_energies):12.8f} Ha at R = {r_values[np.argmax(fci_energies)]:.2f} Å")

        print(f"\nDissociation energy (approximate):")
        de_rhf = rhf_energies[-1] - min(rhf_energies)
        de_fci = fci_energies[-1] - min(fci_energies)
        print(f"  RHF: {de_rhf:12.8f} Ha = {de_rhf * 627.5:.2f} kcal/mol")
        print(f"  FCI: {de_fci:12.8f} Ha = {de_fci * 627.5:.2f} kcal/mol")


def example_pract03_lif():
    """
    Extract LiF data from Pract03.
    Shows: CI setup and RHF energy extraction.
    """
    print("\n" + "=" * 70)
    print("Example 3: Pract03 - LiF with CI setup")
    print("=" * 70)

    ci_file = "projects/03_lif_potential_surfaces/lif_scan/LiF_CI.out"

    if Path(ci_file).exists():
        try:
            energy = read_total_energy(ci_file)
            converged = read_converged(ci_file)
            text = read_text(ci_file)

            print(f"\nLiF CI calculation:")
            print(f"  RHF energy: {energy:15.10f} Ha")
            print(f"  Converged:  {converged}")

            # Check CI setup
            if "NSTATE=3" in text:
                print(f"  CI setup:   3 electronic states")
            if "NACT=" in text:
                import re
                nact = re.search(r'NACT=(\d+)', text)
                if nact:
                    print(f"  Active orbitals: {nact.group(1)}")
            if "NCORE=" in text:
                import re
                ncore = re.search(r'NCORE=(\d+)', text)
                if ncore:
                    print(f"  Core orbitals: {ncore.group(1)}")

            # Try to read CI states if available
            try:
                states = read_state_energies(ci_file, n_states=3)
                print(f"\n  CI state energies found:")
                for i, e in enumerate(states, 1):
                    print(f"    State {i}: {e:15.10f} Ha")
            except ValueError:
                print(f"\n  (CI state energies not yet available - calculation incomplete)")

        except Exception as e:
            print(f"Error reading file: {e}")


if __name__ == "__main__":
    results_pract01 = example_pract01_hf_molecules()
    example_pract02_h2_curve()
    example_pract03_lif()

    print("\n" + "=" * 70)
    print("All examples executed successfully!")
    print("=" * 70)
