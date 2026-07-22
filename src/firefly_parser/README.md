# Firefly/GAMESS Output Parser

Minimal, purpose-built parser for quantum chemistry calculations.

## Functions

### Single-point energies
```python
from analysis import read_total_energy, read_converged

energy = read_total_energy(path)      # float: final energy in Ha
converged = read_converged(path)      # bool: convergence check
```

### Electronic states (CI)
```python
from analysis import read_state_energies

energies = read_state_energies(path, n_states=3)  # np.ndarray of shape (3,)
```

### Scans (bond length, geometry parameter, etc.)
```python
from analysis import read_scan

result = read_scan(
    x_values=[0.5, 1.0, 1.5],
    output_files=["out1.out", "out2.out", "out3.out"],
    reader_func=read_total_energy
)
# result = {"x": array([0.5, 1.0, 1.5]), "y": array([E1, E2, E3])}
```

### Multi-state scans (e.g., Pract03 LiF)
```python
from analysis import read_state_scan

result = read_state_scan(
    x_values=r_values,
    output_files=output_files,
    n_states=3
)
# result = {
#     "x": array([...]),
#     "state_1": array([...]),
#     "state_2": array([...]),
#     "state_3": array([...])
# }
```

## Usage

```python
import numpy as np
from analysis import read_scan, read_total_energy

# Read a scan
r_values = np.linspace(0.5, 3.0, 30)
output_files = [f"h2_r{r:.2f}.out" for r in r_values]

result = read_scan(r_values, output_files, read_total_energy)

# Access data
print(result["x"])        # R values
print(result["y"])        # Energies
```

## Features

- **Simple API**: Functions return dicts with numpy arrays, no tuples
- **Minimal**: Only supports Pract01-03 use cases
- **No classes**: Just functions
- **No plotting**: Use your own visualization
- **No file I/O**: Only reading from output files

## Supported formats

- RHF single-point energies
- MP2 energies
- Full CI (ALDET) with multiple states
- SURFACE scans (multiple geometries)
- OPTIMIZE (geometry optimization)
