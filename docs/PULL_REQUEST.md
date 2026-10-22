# Publication review

Repository: [mobatayneh/fpga-fir-filter](https://github.com/mobatayneh/fpga-fir-filter).
Pull request: [#1](https://github.com/mobatayneh/fpga-fir-filter/pull/1).

## Scope

Recover the original four-tap VHDL FIR filter from the jointly authored EE-8208
report and preserve it as a baseline. Add a separate symmetric streaming
implementation of the same unsigned `[1, 2, 2, 1]` weighted sum. Under the
documented acceptance protocol, the new design accepts one sample per cycle
instead of every five cycles; the common 512-sample simulation completes in
512 rather than 2559 elapsed cycles.

Add assertion-based hardware verification, an integer reference, reproducible
CPU Colab execution, raw-waveform auditing, result manifests, a Linux CI workflow
and optional Vivado synthesis scripts. Preserve the submitted Colab notebook
and archive, and document independently verified results and both original
authors' attribution.

Validation:

- Submitted Colab Linux/GHDL 4.1.0: 22 Python tests passed; 5272 RTL outputs,
  zero arithmetic mismatches; all 25 archive manifest entries verified.
- Independent VCD review: recomputed every output from accepted input signals;
  checked resets, aborted results, busy-time requests, validity and output holds.
- Expanded local suite: 38 Python tests passed; Windows/GHDL 6.0.0 reran the
  same 5272-output experiment successfully.
- All eight submitted notebook code cells executed without errors; its final
  archive checksum matches the preserved returned ZIP.

Limits: no new Vivado utilization, placement/routing, physical clock closure,
power or board results. [Hosted CI](https://github.com/mobatayneh/fpga-fir-filter/actions/runs/39723764246)
passed on Ubuntu with GHDL 4.1.0: 38 tests and 5272 outputs. Its exported archive
also passed a separate review of all 29 manifest entries and every waveform
output; see the [hosted evidence](../results/github-actions-2026-10-22/README.md).
The streaming core
uses fixed unsigned coefficients and has no output backpressure. The claimed
fivefold improvement is steady-state sample throughput at a common clock.

No new FIR CV entry or LinkedIn changes are included. No redistribution license
is assigned on behalf of both original authors.
