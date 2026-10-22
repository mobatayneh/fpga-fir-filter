# FIR arithmetic and interfaces

Both implementations compute the same four-tap unsigned FIR operation on the sequence of accepted input samples:

```text
y[n] = x[n] + 2*x[n-1] + 2*x[n-2] + x[n-3]
```

Inputs are unsigned integers from 0 to 255. Reset initializes all sample history to zero. The output is the full integer weighted sum, without rounding, saturation, division, or normalization. Its maximum is `6 * 255 = 1530`; 11 bits suffice for these fixed coefficients. The external output remains 18 bits to match the original interface, with unused upper bits zero.

The coefficient sum is six, so a constant input of value `c` eventually produces `6*c`. Dividing by six may be useful for displaying a smoothing demonstration, but that display operation is not part of either hardware design. Signed samples, configurable coefficients, and a general-purpose FIR generator would require a different arithmetic specification and additional tests.

## Preserved baseline

`rtl/fir_filter.vhd` is recovered from the source report, with printed line numbers removed. Its five-state controller accepts a sample only in `IDLE` and then executes `S1`, `S2`, `S3`, and `S4` on successive rising clock edges.

| Edge | Baseline action |
| --- | --- |
| `k` | Accept `DataIn` with `StrobeIn=1`; shift the sample history; assert `Busy` |
| `k+1` | Register the first pair of products |
| `k+2` | Register the second pair of products and first partial sum |
| `k+3` | Register the second partial sum |
| `k+4` | Register `DataOut`, assert `StrobeOut`, deassert `Busy`, return to `IDLE` |
| `k+5` | Earliest edge that can accept another sample |

Latency measured between the acceptance edge and the output-valid edge is four elapsed clock periods. The minimum initiation interval is five clock periods. An input strobe presented while busy is ignored, including one presented at the output-completion edge when `Busy` was high before the edge. A producer should hold or retry a sample until an edge on which `Busy=0` before that edge.

The source describes two shared multipliers and one shared adder in its theoretical architecture. The behavioral arithmetic statements alone do not establish those physical resource counts. Constant coefficients of one and two allow synthesis to optimize the multiplication, and the actual mapped structure must be inspected in a synthesis result.

## Streaming specialization

`rtl/fir_filter_streaming.vhd` exploits symmetry without changing the arithmetic:

```text
outer = x[n] + x[n-3]       # 9 bits, maximum 510
inner = x[n-1] + x[n-2]     # 9 bits, maximum 510
y[n]  = outer + (inner << 1) # 11 bits, maximum 1530
```

At acceptance edge `k`, the first stage registers the two pair sums and advances the three-sample delay line. At edge `k+1`, the second stage registers their final weighted sum and marks it valid. The pair sums must be widened before the shift and addition so that the maximum input does not overflow. The result is then zero-extended to the 18-bit output.

The new core accepts one sample on every rising edge with `StrobeIn=1`. It has one elapsed clock period of latency and a one-cycle initiation interval. It retains the port names but changes their streaming semantics:

| Signal or event | Baseline | Streaming specialization |
| --- | --- | --- |
| Acceptance | `StrobeIn=1` while idle | Every edge with `StrobeIn=1` |
| `Busy` | High during an outstanding computation | Always low because the pipeline can accept every cycle |
| `StrobeOut` | Isolated one-cycle pulse | Output-valid indicator; may remain high on consecutive cycles |
| `DataOut` | Changes only when an output completes | Changes only when an output completes |
| Input gap | No accepted sample; history unchanged | No accepted sample; history unchanged; earlier output may still emerge |
| Reset low | Clears history, state, and outputs asynchronously | Clears history, pipeline-valid state, and outputs asynchronously |
| Output backpressure | Unsupported | Unsupported |

For consecutive streaming outputs, consumers must sample `DataOut` on every valid cycle. They must not treat a rising edge of `StrobeOut` as the only event. The implementation has no `ready` input and cannot pause completed outputs for a slow consumer. A future ready/valid wrapper must add buffering and stall handling with dedicated tests.

The sample index advances on acceptance, not on every clock tick. If an upstream source intends a uniformly sampled physical signal, it must provide a defined sampling cadence or use an appropriate buffer. A missing strobe is not automatically a zero-valued signal sample.

## Timing comparison

For a block of `N` samples accepted at each design's maximum rate, elapsed cycles from the first acceptance edge through the last output edge are:

```text
baseline: 4 + 5*(N-1)
streaming: 1 + (N-1)
```

For 512 samples these expressions give 2559 and 512 elapsed cycles respectively. Counting the initial edge as one produces 2560 and 513 edge positions, which is a different counting convention. The verification benchmark records explicit first-accept and last-output cycle numbers to avoid this ambiguity. These are RTL scheduling expectations; use the saved simulation results for executed measurements.

The original report's 2050-cycle estimate uses a different model: a six-cycle operation latency, two-cycle abstract multipliers, and overlapped starts every four cycles. That analysis does not describe the preserved FSM's implemented throughput. The streaming specialization also changes the architecture, so it does not prove the report's minimum-area claim under its abstract resource model.

A one-cycle initiation interval gives five times the baseline's steady-state sample rate at the same clock frequency. Actual nanoseconds, area savings, power savings, and attainable clock frequency require implementation evidence. A simulation clock period alone cannot establish physical timing closure.

## Verification targets

Use an independent integer convolution reference for accepted samples. Check arithmetic and timing together: reset during outstanding work, valid gaps, ignored input strobes while the baseline is busy, sustained input-valid signals, maximum unsigned values, impulse and step responses, alternating values, and deterministic randomized traffic. The 512-sample benchmark should feed both cores the same sample sequence using each core's acceptance rules.

The current specialization is deliberately narrow. A convincing next extension would compare architecture tradeoffs using reproducible synthesis reports, or add a ready/valid wrapper that safely tolerates downstream stalls. Add configurable coefficients or signed fixed-point arithmetic only with explicit width, rounding, overflow, and reset contracts.
