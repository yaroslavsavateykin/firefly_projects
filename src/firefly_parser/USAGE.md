# Analysis Module Usage Guide

## Quick Start

```python
from analysis import read_total_energy, read_scan

# Single energy
E = read_total_energy("output.out")

# Series of energies
result = read_scan([1.0, 1.2, 1.4], files, read_total_energy)
print(result["x"])   # R values
print(result["y"])   # Energies
```

## Available Functions

### Basic Reading

```python
read_text(path) -> str
```
Read output file as raw text.

```python
read_total_energy(path) -> float
```
Extract total energy (final converged value).

```python
read_converged(path) -> bool
```
Check if calculation converged.

### CI States

```python
read_state_energies(path, n_states=None) -> np.ndarray
```
Extract energies of multiple electronic states (CI output).
Returns array of shape `(n_states,)`.

### Scans

```python
read_scan(x_values, output_files, reader_func) -> dict
```
Read a series of single-point calculations.

**Args:**
- `x_values`: array of parameter values (R, angle, etc.)
- `output_files`: list of output file paths
- `reader_func`: function to extract data (e.g., `read_total_energy`)

**Returns:**
```python
{
    "x": ndarray,  # x_values
    "y": ndarray,  # extracted values (same length as x_values)
}
```

```python
read_state_scan(x_values, output_files, n_states=3) -> dict
```
Read a series with multiple electronic states.

**Returns:**
```python
{
    "x": ndarray,
    "state_1": ndarray,
    "state_2": ndarray,
    "state_3": ndarray,
}
```

## Pract01 Example: HF Energies

```python
from analysis import read_total_energy

molecules = {
    "h2": "projects/01_hartree_fock/h2_rhf_sto3g/h2_rhf_sto3g.out",
    "co": "projects/01_hartree_fock/co_rhf_sto3g/co_rhf_sto3g.out",
}

for name, path in molecules.items():
    E = read_total_energy(path)
    print(f"{name}: {E:.10f} Ha")
```

## Pract02 Example: H2 Potential Curve

```python
from analysis import read_scan, read_text
import re
import numpy as np

# Read energies from surface scan
text = read_text("projects/02_h2_potential_curves/h2_rhf_surf.out")
energies = [float(e) for e in re.findall(
    r'FINAL ENERGY IS\s+(-?\d+\.\d+)', text
)]

# Create R values (ORIG1=0.40, DISP1=0.46, NDISP1=11)
r_values = np.linspace(0.40, 0.40 + 10*0.46, 11)

# Plot or analyze
import matplotlib.pyplot as plt
plt.plot(r_values, energies)
plt.xlabel("R / Å")
plt.ylabel("E / Ha")
plt.show()
```

## Pract03 Example: LiF CI States

```python
from analysis import read_state_energies

# When CI calculation is complete:
E_states = read_state_energies("projects/03_lif_potential_surfaces/lif_scan/LiF_CI.out", n_states=3)

print(f"Ground state:      {E_states[0]:.10f} Ha")
print(f"1st excited:       {E_states[1]:.10f} Ha")
print(f"2nd excited:       {E_states[2]:.10f} Ha")
```

## Notes

- All functions return numpy arrays or dicts with numpy arrays
- No tuples, no complex nesting
- Direct usage: `result["x"]`, `result["state_1"]`, etc.
- Error handling: functions raise ValueError with descriptive messages

## Extending the Parser

To add support for a new data type:

1. Add a function to `parsing.py`:
   ```python
   def read_something(path):
       """Extract something from output."""
       text = read_text(path)
       # Use regex to find pattern
       match = re.search(r'pattern', text)
       if match:
           return extracted_value
       raise ValueError(f"Pattern not found in {path}")
   ```

2. Update `__init__.py` to export it

3. Use it with `read_scan`:
   ```python
   result = read_scan(x_values, files, read_something)
   ```

That's it! No classes, no boilerplate, just functions.
