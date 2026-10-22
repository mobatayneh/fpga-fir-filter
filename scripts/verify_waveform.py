"""Independently check FIR behavior from GHDL VCD input/output signals.

This deliberately supports the scalar/binary VCD emitted by this project's
testbench, not arbitrary VCD dialects. Archived HDL/Python is never executed.
All changes at one timestamp are sampled together after delta-cycle settling.
CSV cycle numbering is aligned using one inferred offset and checked on every
output. The returned offset makes the initial uncounted testbench edge explicit.
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter


SIGNALS = {"clk": 1, "reset_n": 1, "b_valid": 1, "s_valid": 1,
           "b_in": 8, "s_in": 8, "b_out": 18, "s_out": 18,
           "b_busy": 1, "s_busy": 1, "b_strobe": 1, "s_strobe": 1}


def _read_vcd(text: str):
    if "$enddefinitions $end" not in text:
        raise ValueError("Missing VCD definitions terminator.")
    header, body = text.split("$enddefinitions $end", 1)
    scale = re.search(r"\$timescale\s+(\d+)\s*(fs|ps|ns|us|ms|s)\s+\$end", header)
    if scale is None:
        raise ValueError("Missing or unsupported VCD timescale.")
    multiplier = int(scale[1]) * {"fs": 1, "ps": 10**3, "ns": 10**6,
                                "us": 10**9, "ms": 10**12, "s": 10**15}[scale[2]]
    scope, identifiers, found = [], {}, set()
    for line in header.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "$scope":
            scope.append(parts[2])
        elif parts[0] == "$upscope":
            if not scope:
                raise ValueError("Unbalanced VCD scope.")
            scope.pop()
        elif parts[0] == "$var" and scope == ["tb_fir_verification"]:
            name = parts[4].split("[")[0]
            if name in SIGNALS:
                if name in found or int(parts[2]) != SIGNALS[name]:
                    raise ValueError(f"Duplicate or incorrect width for VCD signal {name}.")
                if parts[3] in identifiers:
                    raise ValueError("Aliased top-level VCD signals are unsupported.")
                identifiers[parts[3]] = name
                found.add(name)
    if found != set(SIGNALS):
        raise ValueError(f"Missing VCD signals: {sorted(set(SIGNALS)-found)}")

    def snapshots():
        values, current = {}, None
        for raw in body.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                timestamp = int(line[1:]) * multiplier
                if timestamp < 0 or (current is not None and timestamp < current):
                    raise ValueError("VCD timestamps are not monotonic.")
                if current is not None and timestamp != current:
                    yield current, values.copy()
                current = timestamp
                continue
            if current is None:
                raise ValueError("VCD value precedes first timestamp.")
            if line[0] in "bB":
                bits, identifier = line[1:].split()
            elif line[0] in "01xXzZ":
                bits, identifier = line[0], line[1:]
            else:
                raise ValueError(f"Unsupported VCD body record: {line[:60]}")
            if identifier in identifiers:
                name = identifiers[identifier]
                if not re.fullmatch("[01]+", bits) or len(bits) > SIGNALS[name]:
                    raise ValueError(f"Unknown or malformed VCD value for {name}.")
                values[name] = int(bits, 2)
        if current is not None:
            yield current, values.copy()

    return snapshots()


def verify_waveform(vcd_text: str, csv_text: str) -> dict:
    """Recompute every emitted value and handshake from raw accepted inputs.

    The mathematical reference is an integer convolution over accepted samples.
    Pending results are canceled by reset. A baseline input arriving on its
    completion edge is ignored because Busy was high before that edge.
    """
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if not rows:
        raise ValueError("The output trace is empty.")
    models = {name: {"history": [0, 0, 0], "pending": None, "output": 0,
                     "strobe": 0, "accepted": 0, "aborted": 0, "ignored": 0}
              for name in ("baseline", "streaming")}
    seen = Counter()
    previous = None
    rising_edge = 0
    rising_times = []
    row_index = 0
    cycle_offset = None
    resets = 0
    final_time = None
    for timestamp, values in _read_vcd(vcd_text):
        if set(values) != set(SIGNALS):
            raise ValueError("VCD does not initialize all required signals.")
        final_time = timestamp
        is_rising = previous is not None and previous["clk"] == 0 and values["clk"] == 1
        if is_rising:
            rising_edge += 1
            rising_times.append(timestamp)
        if values["reset_n"] == 0:
            if previous is None or previous["reset_n"] != 0:
                resets += 1
            for model in models.values():
                model["aborted"] += int(model["pending"] is not None)
                model.update(history=[0, 0, 0], pending=None, output=0, strobe=0)
        elif is_rising:
            # This testbench changes input/reset away from rising edges. Reject
            # an ambiguous trace rather than choose a sampling race convention.
            for name in ("reset_n", "b_valid", "s_valid", "b_in", "s_in"):
                if values[name] != previous[name]:
                    raise ValueError(f"Input changes at a rising edge: {name}.")
            for architecture, prefix, latency in [("baseline", "b", 4), ("streaming", "s", 1)]:
                model = models[architecture]
                pending = model["pending"]
                was_busy = architecture == "baseline" and pending is not None
                model["strobe"] = 0
                due = pending is not None and pending["due"] == rising_edge
                if due:
                    model.update(output=pending["expected"], strobe=1, pending=None)
                    if row_index >= len(rows):
                        raise ValueError("Waveform contains an output absent from the CSV trace.")
                    row = rows[row_index]
                    offset = rising_edge - int(row["cycle"])
                    if cycle_offset is None:
                        cycle_offset = offset
                    if offset != cycle_offset:
                        raise ValueError("CSV cycle numbering disagrees with waveform timing.")
                    if (row["architecture"] != architecture or
                            int(row["input_index"]) != pending["index"] or
                            int(row["latency"]) != latency or
                            int(row["expected"]) != pending["expected"] or
                            int(row["actual"]) != values[prefix + "_out"] or
                            values[prefix + "_out"] != pending["expected"]):
                        raise ValueError(f"CSV/waveform/reference mismatch at row {row_index + 1}.")
                    row_index += 1
                    seen[architecture] += 1
                if values[prefix + "_valid"]:
                    if was_busy:
                        model["ignored"] += 1
                    else:
                        value = values[prefix + "_in"]
                        h0, h1, h2 = model["history"]
                        expected = value + 2*h0 + 2*h1 + h2
                        model["history"] = [value, h0, h1]
                        model["accepted"] += 1
                        model["pending"] = {"due": rising_edge + latency,
                                            "expected": expected,
                                            "index": model["accepted"]}

        # Check every timestamp, including asynchronous reset and off-edge holds.
        for architecture, prefix in [("baseline", "b"), ("streaming", "s")]:
            model = models[architecture]
            busy = int(architecture == "baseline" and model["pending"] is not None)
            for suffix, expected in [("out", model["output"]), ("strobe", model["strobe"]), ("busy", busy)]:
                if values[prefix + "_" + suffix] != expected:
                    raise ValueError(f"{architecture} {suffix} mismatch at {timestamp} fs.")
        previous = values

    if row_index != len(rows):
        raise ValueError("CSV contains outputs absent from the complete waveform.")
    if any(m["pending"] is not None for m in models.values()):
        raise ValueError("Waveform ends with pending results.")
    if previous is None or previous["reset_n"] != 1 or any(previous[n] for n in ("b_valid", "s_valid", "b_strobe", "s_strobe")):
        raise ValueError("Waveform does not finish in a drained, idle testbench state.")
    intervals = {b-a for a, b in zip(rising_times, rising_times[1:])}
    if intervals != {10_000_000}:
        raise ValueError("Observed clock is not the configured uniform 10 ns period.")
    if set(seen) != {"baseline", "streaming"}:
        raise ValueError("Both architectures must have waveform-backed outputs.")
    return {"status": "PASS", "checked_outputs": dict(seen),
            "accepted_inputs": {name: m["accepted"] for name, m in models.items()},
            "aborted_by_reset": {name: m["aborted"] for name, m in models.items()},
            "ignored_baseline_busy_requests": models["baseline"]["ignored"],
            "reset_assertions_including_initial": resets,
            "clock_period_fs": 10_000_000, "rising_edges_observed": rising_edge,
            "csv_cycle_offset_from_vcd_rising_edge": cycle_offset,
            "last_vcd_timestamp_fs": final_time, "arithmetic_mismatches": 0,
            "method": "Integer convolution from raw top-level accepted inputs; all outputs, handshakes and holds checked"}
