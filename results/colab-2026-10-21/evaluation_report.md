# Verification results

Both VHDL designs passed assertion-based behavioral simulation.

Checked outputs: {'streaming': 3652, 'baseline': 1620}. Arithmetic mismatches: 0.

| Architecture | Samples | Elapsed cycles | Initiation interval |
|---|---:|---:|---:|
| baseline | 512 | 2559 | 5 |
| streaming | 512 | 512 | 1 |

At a common clock, the measured steady-state acceptance rate increases 5x.
This is a cycle-level simulation comparison, not measured FPGA Fmax, area, or power.
The fixed-coefficient streaming extension does not implement the report's abstract shared-multiplier resource model.
Vivado synthesis, physical timing closure, and board validation remain separate work.
