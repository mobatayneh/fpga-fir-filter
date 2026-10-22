# Optional Vivado synthesis comparison

The primary runnable experiment uses GHDL simulation and needs no FPGA board. This optional step maps both architectures to the same FPGA device to compare estimated resource usage. It requires AMD Vivado with Zynq-7000 support for `xc7z020clg484-1`, the part named in the source report.

The supplied script has not been executed in Vivado in the current environment. Its commands were checked against AMD documentation; only an actual successful Vivado run can establish synthesis results. No new LUT, register, DSP, power, or hardware clock-rate claims are made here.

## Run

Open a Vivado command prompt or a shell where `vivado` is on `PATH`. From the repository root, choose a new result directory and new log filenames:

```powershell
vivado -mode batch -log results/vivado_run_001.log -journal results/vivado_run_001.jou -source scripts/vivado_synth.tcl -tclargs results/vivado_run_001
```

The `results` parent directory must exist. The script refuses to use an existing output directory and preserves partial output after a failure. Use a new suffix for every attempt, including the log and journal names. Vivado opens its log before executing Tcl, so the script cannot prevent a reused command-line log filename from being overwritten.

The script creates a fresh in-memory project for each top, copies the exact RTL inputs into the result directory, applies one shared clock constraint, synthesizes, and exports reports. It records the complete tool version, target part, synthesis settings, and the constraint file. No board is needed for this stage.

## Interpretation

Both designs use out-of-context synthesis, a 10 ns clock target, VHDL-2008, and `rebuilt` hierarchy flattening. Out-of-context synthesis disables top-level I/O buffer insertion. Compare the two new reports against one another; the original report's 28 LUTs and 102 flip-flops came from a separate synthesis flow and are not an identical experimental baseline. AMD documents the out-of-context behavior in [`synth_design`](https://docs.amd.com/r/2023.2-English/ug835-vivado-tcl-commands/synth_design).

| File | What to inspect |
| --- | --- |
| `environment.txt`, `clock_only.xdc` | Exact tool version, part, clock target, and declared assumptions |
| `<top>/<top>.vhd` | RTL snapshot actually used in this run |
| `<top>/utilization.rpt` | LUTs, flip-flops, DSPs, and memory inferred by synthesis |
| `<top>/clocks.rpt` | Confirm that `fir_clk` has a 10 ns period |
| `<top>/check_timing.rpt` | Missing constraints and timing-check problems |
| `<top>/timing_summary.rpt` | Estimated timing and explicitly reported unconstrained paths |
| `<top>/drc.rpt` | Design-rule findings to review |
| `<top>/post_synth.dcp` | Synthesized design database for inspection in Vivado |
| `status.txt` or `failure.txt` | Whether the script completed or stopped with an error |

The constraint file defines only the clock. There are no input/output delays, board pins, reset release constraints, switching activity, or explicit clock uncertainty. Thus, external interface paths are not fully constrained. The report should expose these limitations instead of hiding them with broad false-path exceptions. A positive estimated slack on internal paths does not prove that the complete design runs at 100 MHz on a board. AMD's [`check_timing`](https://docs.amd.com/r/2023.1-English/ug835-vivado-tcl-commands/check_timing) identifies missing constraints, while [`report_timing_summary`](https://docs.amd.com/r/2022.2-English/ug835-vivado-tcl-commands/report_timing_summary) reports timing on the current synthesized or implemented design.

Utilization can change after placement and routing, so retain the stage label alongside every result. AMD explicitly notes that [`report_utilization`](https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/report_utilization) becomes more accurate as implementation progresses. Neither source uses a general-purpose runtime multiplier in the new fixed-coefficient specialization; only a synthesis report establishes the actual mapped resource counts.

Power estimation is intentionally absent because representative switching activity, clock definitions, and integration conditions are needed for a useful comparison. Do not reuse the source report's theoretical 4.4 W as measured device power.

## Next experiments

1. Run this script and retain both raw report directories, the top-level log, and the journal. Check warnings and constraint coverage before writing a comparison table.
2. If a physical target is selected, define a board wrapper, clock source, reset synchronization, and interface timing constraints. Run placement and routing and preserve the post-route timing reports.
3. Add a board demonstration only when hardware is available. Simulation success, synthesis success, implementation success, and observed board behavior are distinct evidence levels.

The arithmetic design remains useful without a board: bit-exact verification, a clear streaming protocol, measured simulation cycle counts, and a reproducible comparison are already inspectable engineering deliverables.
