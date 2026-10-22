# Colab simulation evidence review

The submitted run is complete and internally consistent for its defined behavioral
simulation protocol. It reproduces the earlier Windows results on Linux with a
different GHDL version. This is VHDL simulation, not machine-learning training.
The review found no incorrect metric, missing required simulation phase or
numerical mismatch. Optional plotting was disabled and is not claimed as executed.

## Preserved evidence

The unchanged [result archive](../results/colab-2026-10-21/results_for_review.zip)
contains 25 files covered by its SHA-256 manifest, plus the manifest itself.
All digests and the complete member set passed validation. All 11 archived source
files matched the pre-review workspace byte for byte, including both RTL designs,
both testbenches, five Python helpers and two test modules.

The [executed notebook](../results/colab-2026-10-21/executed_notebook.ipynb) has
15 cells whose sources matched the distributed template at intake. Its eight
code cells executed in order, with no error outputs. The final notebook output
identifies the exact returned ZIP by SHA-256. Its displayed metrics and test log
match the archive. Installation stdout is not retained in the notebook; the
archive contains the simulator version and detailed simulation/test logs.

The source-bundle checksum printed in the notebook matches the checksum recorded
when the bundle was distributed. That original source ZIP is no longer in `dist`,
so this historical check is not a fresh hash of the original source ZIP. The
returned archive independently contains the exact executed source snapshots.

## Experiment configuration

| Field | Submitted value |
|---|---|
| Result timestamp | 2026-10-21 04:59:47 UTC, 00:59:47 America/Toronto |
| Python | 3.13.16 |
| OS | Linux x86-64, glibc 2.39 |
| Simulator | GHDL 4.1.0, Ubuntu package 4.1.0+dfsg-0ubuntu2.1, mcode |
| HDL standard | VHDL-2008, as invoked by the matching runner |
| Clock | 10 ns simulated period, independently observed in the waveform |
| Arithmetic | unsigned 8-bit inputs; coefficients `[1, 2, 2, 1]`; exact 18-bit output |
| Maximum mathematical result | 1530 |
| VHDL random generator | 32-bit LFSR, seed `0x82080001`, 6000 steps |
| Benchmark | 512 accepted values per design; `(73*i + 19) mod 256` |

The [environment file](../results/colab-2026-10-21/environment.json) explicitly
records that neither Vivado nor physical hardware ran.

## Independently verified results

| Measurement | Baseline | Streaming |
|---|---:|---:|
| Checked output values | 1620 | 3652 |
| Arithmetic mismatches | 0 | 0 |
| Latency in elapsed cycles | 4 | 1 |
| Sustained initiation interval | 5 | 1 |
| Common benchmark outputs | 512 | 512 |
| First accepted benchmark cycle | 2 | 2 |
| Last benchmark output cycle | 2561 | 514 |
| Elapsed benchmark cycles | 2559 | 512 |

Both benchmark sequences also match an independent Python convolution. The
same-clock steady-state acceptance rate improves fivefold. The finite-block
ratio is 2559/512, approximately 4.998; neither quantity is a measured FPGA Fmax
or power improvement. The original theoretical 2050-cycle schedule remains a
separate model and is not used as the implemented baseline.

The review reads raw top-level VCD inputs and independently models sample history,
acceptance, reset cancellation, output timing, Busy, validity and output holds.
It then matches every observed output to the CSV. This verifies all 5272 results
without trusting the CSV's expected-value column or executing submitted code.

The waveform contains 1628 accepted baseline inputs and 3656 streaming inputs.
Resets intentionally abort 8 and 4 pending results respectively; subtracting
those cancellations gives the recorded 1620 and 3652 completed outputs. Another
2033 requests arrive while the baseline is busy and are correctly ignored.
Sixteen reset assertions, including initialization, were observed. These count
differences are expected protocol behavior, not missing experiment outputs.

The VCD has 9192 rising edges. Its CSV alignment differs by one initial uncounted
edge, consistently across all outputs. The final VCD timestamp is 91915 ns;
the bench checks settled outputs one nanosecond later and stops at 91916 ns.
The completion log reports 9191 counted testbench cycles and no pending outputs.

The submitted suite passed all 22 Python tests. The later review adds archive
integrity and waveform validation tests; these are separate local validation,
not retroactively attributed to the Colab run.
The expanded local suite passed all **38 tests**, followed by another complete
5272-output GHDL simulation. The saved local review-stage test log is in
[`results/phase4-validation`](../results/phase4-validation).

Git attributes preserve the original mixed line endings in `rtl/` and `tb/`
and preserve the submitted evidence byte for byte. This prevents checkout-time
newline conversion from invalidating the source-provenance hashes.

## Reproduce the review

```text
python scripts/review_results.py results/colab-2026-10-21/results_for_review.zip --notebook results/colab-2026-10-21/executed_notebook.ipynb --output work/repeated_colab_review.json
python -m unittest discover -s tests -v
```

Use a new output filename. Inspect the saved
[independent review](../results/colab-2026-10-21/independent_review.json) and
[notebook review](../results/colab-2026-10-21/notebook_review.json).

## Remaining limitations

This is evidence for the finite tested protocol, not a formal proof over all
possible histories. Checksums establish internal consistency, not independent
attestation by the hosted service. No new synthesis utilization, placement,
routing, physical timing closure, power analysis or board measurement exists.
Hosted workflow results are recorded separately in the publication review.
The core remains a fixed-coefficient unsigned FIR without output
backpressure. No CV or LinkedIn claims are prepared in this phase.
