# Firefly Parser - Quick Start

## Installation

The parser is in `src/firefly_parser/`. Run examples from the project root:

```python
from src.firefly_parser import read_total_energy, read_scan, read_state_energies
```

## Usage

### Single Energy (Pract01)

```python
from src.firefly_parser import read_total_energy

E = read_total_energy("projects/01_hartree_fock/h2_rhf_sto3g/h2_rhf_sto3g.out")
print(f"Energy: {E:.10f} Ha")
```

### Bond Length Scan (Pract02)

```python
from src.firefly_parser import read_scan, read_total_energy
import numpy as np

r_values = np.linspace(0.4, 5.0, 11)
output_files = [
    "projects/02_h2_potential_curves/h2_curve/h2_rhf_surf.out"
] * len(r_values)

result = read_scan(r_values, output_files, read_total_energy)

# Access data
print("R values:", result['x'])
print("Energies:", result['y'])
```

### CI States (Pract03 - when complete)

```python
from src.firefly_parser import read_state_energies

E_states = read_state_energies(
    "projects/03_lif_potential_surfaces/lif_scan/LiF_CI.out",
    n_states=3
)

print(f"Ground state: {E_states[0]:.10f} Ha")
print(f"State 2:      {E_states[1]:.10f} Ha")
print(f"State 3:      {E_states[2]:.10f} Ha")
```

## Run Examples

```bash
python3 src/firefly_parser/real_examples.py
```

## API Reference

| Function | Input | Output |
|----------|-------|--------|
| `read_total_energy(path)` | file path | float (energy in Ha) |
| `read_converged(path)` | file path | bool |
| `read_state_energies(path, n_states)` | file path | ndarray(n_states,) |
| `read_scan(x, files, reader)` | x_values, output_files, function | dict with 'x' and 'y' |
| `read_state_scan(x, files, n_states)` | x_values, output_files, int | dict with 'x' and 'state_N' |

## Files in `src/firefly_parser/`

- `parsing.py` - Core functions
- `__init__.py` - Module exports
- `examples.py` - Generic examples
- `real_examples.py` - Real Pract01-03 examples
- `README.md` - Reference
- `USAGE.md` - Full API documentation

## Notes

- All functions return numpy arrays or dicts with numpy arrays
- No tuples, no complex nesting
- Direct access: `result['x']`, `result['state_1']`
- Large files processed efficiently
- Handles incomplete calculations gracefully
