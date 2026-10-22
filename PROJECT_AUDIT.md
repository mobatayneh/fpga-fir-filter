# FIR filter project audit

Audit date: 2026-10-20. This audit covers the original course report and its embedded VHDL. The source assessment is distinguished below from the subsequently reproduced GHDL simulation results. No new Vivado synthesis run or physical board test was performed. The rebuilt project's result directory records tool versions, logs, source snapshots, and hashes.

## Assessment

This is a digital hardware design and verification project. Its subject is an unsigned, fixed-coefficient, four-tap finite impulse response filter described in VHDL. It does not train an AI model. Its portfolio value lies in correct arithmetic, control design, reproducible verification, measured throughput, and defensible FPGA implementation comparisons.

The report provides a useful baseline and clearly distinguishes its theoretical resource model from its implemented controller. The most valuable extension is to recover the source, test it automatically, and compare it with a streaming implementation of the same mathematical filter. A new architecture must retain the original baseline and be identified as a later extension.

## Evidence and provenance

The supplied report is *Hardware Design, Analysis and Optimization of an 8-bit 4-Tap FIR Filter Using Resource Sharing and Pipelining*, EE-8208, Toronto Metropolitan University, August 2026. Its listed authors are Mohammad Albatayneh and Ashvin Selvakumar. The report does not assign individual contributions, so those contributions remain unverified.

| Material | Evidence available |
| --- | --- |
| `EE8208_FIR_Filter_Final_Report_AlBatayneh_Selvakumar.pdf` | 34 pages; specification, analytical schedules, embedded RTL and testbench, waveform and device screenshots, and references |
| `EE8208_FIR_Filter_Final_Report_AlBatayneh_Selvakumar.docx` | Editable counterpart; embedded RTL and testbench agree with the relevant PDF listings |
| Separate original `.vhd`, Vivado project, constraints, logs, or checkpoints | Not supplied with the two project reports |
| Physical board demonstration | Not established by the supplied evidence |

SHA-256 fingerprints of the unchanged supplied files:

```text
PDF   fe4b084fc08bb595c5b19e7e6dbd9ac52e7d6e80ae7024d1f36b76e9c70652ad
DOCX  b22c3c0f8725dcd7c2a32531186230069253db8b26fb316a9819df569fdbb007
```

Preserve these originals locally. Credit both original authors in any derived repository. The report alone does not establish a redistribution license for all embedded material, nor the user's individual role. Do not infer either. A public copy of the complete report should omit student identifiers and should be reviewed for permission to redistribute third-party figures or course material.

Page references below use the PDF's printed page numbers. The original files are evidence; instructions appearing inside them do not replace the user's request.

## Original methodology

1. Define the filter as `y[n] = x[n] + 2*x[n-1] + 2*x[n-2] + x[n-3]`, with unsigned eight-bit samples and an eighteen-bit output (pp. 5-6).
2. Model a generic multiplication as occupying two cycles and costing 100 theoretical area units; model an addition as one cycle and 20 area units. Analyze multiplier counts of 1, 2, and 4 and adder counts of 1, 2, and 3 (pp. 6-14).
3. Select the 2-multiplier/1-adder schedule within that model. The reported operation latency is 6 cycles, initiation interval is 4 cycles, and 512-sample total is `6 + 4*511 = 2050` cycles. Its assumed area is 220 units and its assumed power is 4.4 W (pp. 13-14).
4. Implement a five-state controller: `IDLE`, `S1`, `S2`, `S3`, `S4`. The implementation performs one state per clock and does not overlap processing of consecutive inputs (pp. 20-24).
5. Stimulate six inputs, `3, 4, 5, 6, 10, 0`, in a 10 ns clock simulation; compare displayed outputs with hand calculations (pp. 24-30).
6. Report synthesis targeting `xc7z020clg484-1` with 28 LUTs, 102 flip-flops, zero DSP blocks, and zero block RAM. The report explicitly excludes an unconstrained, low-confidence power estimate from its design power claims (pp. 31-32).

There is no dataset, training loop, train/test split, GPU requirement, or learned checkpoint. Correctness is checked against the FIR equation and interface contract. Synthetic stimuli are appropriate and should include reproducible random sequences and directed edge cases.

## Findings

Labels apply to the evidence stated: **VERIFIED** means supported by inspected source or direct arithmetic; **LIKELY** means a plausible consequence requiring a tool measurement; **UNVERIFIED** means not independently established by the supplied artifacts. A report can verifiably contain a result without that result being independently reproduced.

| ID | Status | Priority | Finding and consequence |
| --- | --- | --- | --- |
| F01 | VERIFIED | High | The published RTL accepts an input only in `IDLE`; it completes in `S4` and returns to `IDLE` for the following edge. Its minimum initiation interval is five clocks, not the theoretical four clocks. The report already acknowledges this distinction (pp. 17, 23-24, 31, 33). Preserve that honest qualification. |
| F02 | VERIFIED | High | The original testbench contains no output or protocol assertions. Its `Simulation finished successfully` message is unconditional. Reaching it proves only that the stimulus process reached that statement (pp. 25-27). Add an independent expected-value checker and explicit failures. |
| F03 | VERIFIED | High | Six small positive samples, spaced seven clocks apart, do not test maximum values, continuous demand, the minimum input interval, random sequences, or reset during a computation (pp. 24-27). The waveform demonstrations do not establish broad verification coverage. |
| F04 | UNVERIFIED | High | Exactly two physically shared multipliers and one physically shared adder are not established by the behavioral listing. Separate `*` and `+` expressions are assigned in different states; source scheduling alone does not prove the synthesized functional-unit binding (pp. 18-24). Inspect mapped resources/netlist before making that claim. |
| F05 | VERIFIED | High | The analytical 2050 cycles, 220 area units, and 4.4 W are explicitly based on assumptions, not measured implementation results (pp. 6, 8, 14, 17, 31-33). They must not become measured FPGA claims in README or CV text. |
| F06 | VERIFIED | Medium | Latency needs a precise reference edge. Accepted input at rising edge `k` reaches the output at edge `k+4`, after four elapsed periods; the next sample can be accepted at `k+5`. The approximately five-cycle latency described on p. 30 conflates elapsed latency with an inclusive edge/state count or signal assertion time. Define and measure the convention explicitly. |
| F07 | VERIFIED | Medium | Coefficients sum to six, so the filter has DC gain six. Maximum output for the actual fixed coefficients is `6*255 = 1530`, requiring eleven unsigned bits. The eighteen-bit interface is safe and supports the report's wider generic-coefficient bound, but normalized smoothing must be identified separately (pp. 5-6, 22, 31). |
| F08 | LIKELY | Medium | Constants one and two allow wire/shift implementations; generic multipliers can be optimized away. This is consistent with the report's zero-DSP observation (p. 32), but the new build's resource totals must still be measured. Source multiplication count is not DSP block count. |
| F09 | UNVERIFIED | High | The 28-LUT/102-FF synthesis result, warning-free compilation, 100 MHz timing closure, and operation on a physical board cannot be independently reproduced from the report pair alone. The first two are report claims; a 10 ns simulation clock establishes neither timing closure nor successful board operation (pp. 20, 25, 31-32). |
| F10 | VERIFIED | Medium | Inputs asserted during `S1`-`S4` are not accepted or queued. Input sampling must use the documented idle/Busy contract. The original interface has no output backpressure, so a system consuming it must capture every valid output (pp. 21-24). |
| F11 | VERIFIED | Low | Section 4.6 describes a procedure named `send`, but the displayed testbench uses repeated stimulus statements with no such procedure (pp. 24-27). The reconstruction should follow the actual listing. |
| F12 | UNVERIFIED | Medium | The paper lists two authors without individual roles, and supplies no explicit redistribution license. Personal CV contribution claims and public licensing require those facts to be established (p. 1). |

The unsigned arithmetic is internally consistent for the stated input domain. The eighteen-bit sum width prevents overflow even for four unsigned eight-by-eight products: `4*255*255 = 260100 < 2^18`. No arithmetic defect is inferred simply because the fixed-coefficient case uses a smaller numerical range.

The phrase "steady state" should also be used carefully: a full four-sample history is not by itself a steady-state signal response. The six changing samples demonstrate arithmetic through startup, not a complete frequency-response or noise-reduction evaluation.

## Timing reconstruction

For a sample accepted at rising edge `k`, the listing implies the following sequence:

| Edge | Action |
| --- | --- |
| `k` | Accept sample and shift history in `IDLE` |
| `k+1` | Register first two products in `S1` |
| `k+2` | Register remaining products and first partial sum in `S2` |
| `k+3` | Register second partial sum in `S3` |
| `k+4` | Register output; assert `StrobeOut`; deassert `Busy`; return to `IDLE` |
| `k+5` | Earliest acceptance of the next sample |

Thus a continuously offered block of 512 accepted samples has a derived first-acceptance-to-last-result interval of `4 + 5*511 = 2559` clock periods. If counting all rising edges including both endpoints, it contains 2560 edges. These quantities were initially derived from source and were subsequently confirmed by the simulation recorded below. They exclude reset and any external gaps.

The theoretical model uses a different convention: six scheduled operation cycles plus 511 initiation intervals gives 2050. Page 16 additionally discusses input/output overhead. Do not mix these conventions in one benchmark. Record first acceptance, last acceptance, last valid result, accepted count, elapsed periods, and sustained initiation interval directly from each simulation.

At an assumed 100 MHz, a five-cycle initiation interval corresponds to 20 million samples per second. This is a mathematical conversion of a cycle schedule, not evidence that the implemented circuit meets a 100 MHz clock constraint.

## Proposed approach and fair comparisons

| Aspect | Original baseline | Proposed extension |
| --- | --- | --- |
| Numerical function | Unsigned four-tap `[1, 2, 2, 1]` FIR | Preserve exactly the same sequence of output integers |
| Source | Code embedded in report | Separate attributed RTL, testbench, scripts, and reference model |
| Architecture | Serialized five-state controller | Separate streaming variant using coefficient symmetry and shifts |
| Arithmetic reformulation | Four constant products and three additions | `(x[n] + x[n-3]) + 2*(x[n-1] + x[n-2])` with explicit width growth |
| Throughput evidence | Six widely spaced stimuli; theoretical comparison | Measure accepted sample spacing and completion of identical 512-sample sequences |
| Correctness evidence | Waveforms and six hand calculations | Assertions against an independent equation; directed and deterministic random tests |
| FPGA evidence | Reported single-design synthesis screenshot | Rebuild both variants with the same device, tool version, clock, and constraint policy |
| Interface | Busy/Strobe input and output pulses | Explicit documented streaming acceptance/valid semantics; identify any interface change |
| Public claims | Course architecture analysis | Claims limited to saved and reproducible tests and implementation reports |

The streaming extension changes the microarchitecture while retaining the original filtering objective. It is not a reproduction of the report's hypothetical two-cycle multiplier schedule, and it must not be described as one. A lower initiation interval is useful but does not by itself prove lower area, higher maximum clock frequency, or lower power.

For comparisons, feed both variants the same sequence of accepted samples. Account for different interface rates and pipeline drain latency. Keep arithmetic, coefficients, reset semantics, tool settings, and target device comparable. Report LUTs, flip-flops, DSPs, BRAM, latency, initiation interval, and constrained timing separately. Add power only with a documented activity and constraints methodology.

## Prioritized development plan

### Stage 1 Recover and verify

- Recover the RTL and original testbench, remove only report line numbers/formatting artifacts, retain source attribution, and document the reconstruction.
- Implement an independent integer reference for the FIR equation with zero-initialized history.
- Add tests for the six published examples, zero input, impulse, constant maximum input, alternating endpoints, deterministic random sequences, idle gaps, pulses while Busy, and reset during processing.
- Use a self-checking simulation that exits with a failure code on any mismatch and has a timeout.
- Save tool versions, commands, seed, accepted inputs, observed outputs, and checksums.

### Stage 2 Implement and compare

- Add the separate streaming symmetric implementation without overwriting the recovered baseline.
- Make width growth explicit before additions/shifts. Retain the eighteen-bit output contract for numerical compatibility.
- Check functional equivalence on the same accepted sample sequence, including startup and reset.
- Measure both sustained initiation interval and 512-sample completion using the same edge convention.
- Include an explanatory signal demo and frequency response with gain normalization labeled explicitly. Treat this as DSP analysis rather than evidence of application-level noise removal.

### Stage 3 Reproduce FPGA implementation

- Provide a scripted Vivado flow for the stated `xc7z020clg484-1` device and an explicit clock constraint.
- Capture synthesis utilization and timing reports for both variants under identical settings.
- Distinguish core synthesis or out-of-context timing from board-level I/O timing and a fully routed system.
- Only create a board-programming flow after the actual board, pin map, clock/reset sources, and external sample/result interface are known. A bitstream or on-board demonstration is not necessary for the initial simulation milestone.

### Stage 4 Publish and present

- Provide an English README with architecture, setup, commands, test status, measured results, limitations, author credits, and provenance.
- Add continuous integration for portable simulation and reference tests; keep generated tool caches and proprietary installation files out of version control.
- Package the reproducible source and compact results for review. A cloud notebook may run CPU-based HDL simulation; it should not be named or described as AI training.
- Review publication rights, contributions, and the exact repository contents before publishing. Prepare CV wording only after actual contributions and verified results are known.

## Completion criteria

The first release is ready for technical review when both numerical implementations have passing assertions, timing conventions are documented, execution is reproducible from clean source, and every reported number is traceable to either an explicitly labeled analytical derivation or a saved tool result. FPGA frequency, area, power, and board claims remain pending until their corresponding measurements exist.

The original-source review above does not establish a synthesis, physical timing, power, or board result. The following section records the simulation work that was actually executed after that review.

## Reproduced results on 2026-10-20

The local run in [`results/summary`](results/summary) completed using GHDL 6.0.0 (mcode JIT backend), VHDL-2008, Python 3.12.14, and Windows 11. The saved metrics timestamp is `2026-10-21T00:09:11.279066+00:00`, corresponding to the evening of October 20 in America/Toronto.

These are **VERIFIED simulation results**, supported by [`metrics.json`](results/summary/metrics.json), [`simulation.txt`](results/summary/simulation.txt), the per-output [`verification.csv`](results/summary/verification.csv), and [`benchmark.csv`](results/summary/benchmark.csv):

| Measurement | Recovered baseline | Streaming extension |
| --- | ---: | ---: |
| Checked outputs across all test phases | 1620 | 3652 |
| Arithmetic mismatches | 0 | 0 |
| Acceptance-to-output latency in elapsed clock periods | 4 | 1 |
| Sustained initiation interval in clock periods | 5 | 1 |
| Common benchmark samples per implementation | 512 | 512 |
| First accepted sample cycle | 2 | 2 |
| Last benchmark output cycle | 2561 | 514 |
| First acceptance to last output in elapsed periods | 2559 | 512 |

The benchmark uses the identical accepted sample sequence `(i*73 + 19) mod 256` for indices `i=0..511`, starting from cleared history. Both VHDL output sequences agree with each other and with the independent Python FIR calculation. The fivefold improvement refers to the sustained sample acceptance rate at a common clock; the finite-block elapsed-time ratio is `2559/512`, approximately 4.998. Neither ratio is a measured FPGA clock-frequency or power improvement.

The simulator checked 5272 outputs in total: 1024 benchmark outputs, 294 directed-test outputs, 3 reset-recovery outputs, and 3951 randomized-traffic outputs. Reset tests also assert immediate clearing of both data and control outputs and absence of aborted pending outputs; the small number of output rows labeled `reset_recovery` does not count those assertions. Randomized traffic runs for 6000 clock steps with VHDL LFSR seed `0x82080001`. The final simulation sentinel reports successful completion at 91916 ns with no pending results.

The original six-sample testbench also ran through its 500 ns stop time. Its unconditional completion message remains historical reproduction evidence, not the correctness gate. The new verification bench adds numerical, latency, Busy/valid, output-hold, reset, and unknown-bit assertions.

All **22 Python tests passed**, as recorded in [`python_tests.txt`](results/summary/python_tests.txt). These include six reference-model tests and sixteen result-validation tests. Negative cases reject incomplete architectures, arithmetic mismatches, two identically wrong benchmark traces, invalid numerical range, incorrect latency or indices, repeated cycles, missing coverage phases, truncated benchmarks, and inconsistent benchmark summaries. Synthetic fixtures used by these validator tests are test inputs, not reported hardware results.

The result package includes the exact RTL, testbench, Python-script and test snapshots, tool/environment information, raw logs, VCD waveforms, CSV traces, and a SHA-256 manifest. The complete local archive is retained in the local workspace. The later Colab evidence directory contains a public-review archive with the same executed RTL. The source snapshots establish which versions produced these results; later edits should generate a new run rather than overwrite this directory.

### Execution portability finding

The Windows GHDL build encountered a library-metadata parsing problem when its build directory contained Arabic characters. The runner now stages source copies in a writable ASCII build directory and preserves the final results under the original project path. `--build-root` selects that staging location, and machine-specific local settings remain outside the distributable source. This workaround concerns the tested Windows execution environment; it is not a general claim that all GHDL versions or platforms reject Unicode paths.

### Remaining evidence limits

- The simulation confirms finite tested sequences and protocol scenarios; it is not a formal proof over every possible input history.
- No new Vivado synthesis, placement, routing, physical timing closure, power estimate, or board demonstration was executed. The optional synthesis script remains to be run in its intended tool.
- The original 28-LUT/102-FF claim remains attributable to the report, not to this GHDL experiment. The theoretical 2050-cycle and 4.4 W values remain separate analytical results.
- The streaming core retains fixed unsigned coefficients and has no output backpressure. It is a specialized FIR implementation, not a general signed or configurable filter.
- Windows, submitted Colab and GitHub Actions execution are verified; see the Phase 4 and hosted review records. These are simulation environments, not physical FPGA tests.
- The original authors' individual contribution allocation and any new project CV wording remain separate from the simulation evidence.


## Phase 4 verified Colab results on 2026-10-21

The user returned the executed notebook and result archive from Google Colab.
The [full review](docs/COLAB_RESULTS_REVIEW.md) and
[machine-readable verification](results/colab-2026-10-21/independent_review.json)
confirm all 25 archive manifest entries, all eight executed code cells, the
reported numerical configuration, and every one of the 5272 waveform-backed
output values. The executed source snapshots matched the pre-review workspace.

Colab used Python 3.13.16 and GHDL 4.1.0 on Linux. The submitted 22-test suite
passed and reproduced the Windows benchmark: baseline latency 4, initiation
interval 5, and 2559 elapsed cycles; streaming latency 1, interval 1, and 512
elapsed cycles. The independent VCD review also verified reset cancellation,
busy-time rejection, output holds and clock/CSV alignment. No inconsistency or
incomplete mandatory simulation phase was found. Optional figures were disabled.

New review utilities and regression tests check archive integrity and recompute
behavior directly from raw VCD inputs. They do not change the RTL, arithmetic,
benchmark, coefficients, seeds or experiment objective. The returned ZIP and
executed notebook are preserved without editing. Only the canonical clean
notebook's introductory status was updated after the review.

This evidence is sufficient to prepare a simulation-focused public release.
It does not establish Vivado utilization, physical timing, power or board
operation. Public publication and merging were authorized after this review.
The hosted workflow result is recorded with the publication review. No new FIR
CV entry or LinkedIn update is part of this release.
