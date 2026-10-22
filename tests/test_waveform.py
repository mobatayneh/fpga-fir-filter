"""Small, explicit waveform fixtures exercise independent result verification."""
import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_waveform import SIGNALS, verify_waveform


def fixture(abort=False):
    # Hand-worked two-sample traces. Baseline ignores the second input at35 ns,
    # accepts it at75 ns, then emits10 at115 ns unless reset aborts it at90 ns.
    names = list(SIGNALS)
    ids = {name: f"v{i}" for i, name in enumerate(names)}
    header = ["$timescale 1 ns $end", "$scope module tb_fir_verification $end"]
    for name, width in SIGNALS.items():
        header.append(f"$var reg {width} {ids[name]} {name} $end")
    header += ["$upscope $end", "$enddefinitions $end"]
    state = {name: 0 for name in names}
    events = {
        16: {"reset_n": 1},
        20: {"b_valid": 1, "s_valid": 1, "b_in": 3, "s_in": 3},
        25: {"b_busy": 1},
        30: {"b_in": 4, "s_in": 4},
        35: {"s_out": 3, "s_strobe": 1},
        40: {"b_valid": 0, "s_valid": 0},
        45: {"s_out": 10},
        55: {"s_strobe": 0},
        65: {"b_out": 3, "b_busy": 0, "b_strobe": 1},
        70: {"b_valid": 1},
        75: {"b_busy": 1, "b_strobe": 0},
        80: {"b_valid": 0},
        115: {"b_out": 10, "b_busy": 0, "b_strobe": 1},
        125: {"b_strobe": 0},
    }
    if abort:
        events[90] = {"reset_n": 0, "b_busy": 0, "b_out": 0, "s_out": 0}
        events[96] = {"reset_n": 1}
        events.pop(115)
    for time in sorted(set(range(0, 131, 5)) | set(events)):
        if time % 5 == 0:
            state["clk"] = int(time % 10 == 5)
        state.update(events.get(time, {}))
        header.append(f"#{time}")
        for name, value in state.items():
            header.append(f"b{value:0{SIGNALS[name]}b} {ids[name]}")
    rows = [("streaming", "directed", 3, 1, 3, 3, 1),
            ("streaming", "directed", 4, 2, 10, 10, 1),
            ("baseline", "directed", 6, 1, 3, 3, 4)]
    if not abort:
        rows.append(("baseline", "directed", 11, 2, 10, 10, 4))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["architecture", "phase", "cycle", "input_index", "expected", "actual", "latency"])
    writer.writerows(rows)
    return "\n".join(header) + "\n", buf.getvalue()


class WaveformTests(unittest.TestCase):
    def test_hand_worked_outputs_and_busy_rejection(self):
        report = verify_waveform(*fixture())
        self.assertEqual(report["checked_outputs"], {"streaming": 2, "baseline": 2})
        self.assertEqual(report["ignored_baseline_busy_requests"], 1)
        self.assertEqual(report["csv_cycle_offset_from_vcd_rising_edge"], 1)

    def test_async_reset_aborts_pending_result(self):
        report = verify_waveform(*fixture(abort=True))
        self.assertEqual(report["aborted_by_reset"], {"baseline": 1, "streaming": 0})
        self.assertEqual(report["accepted_inputs"]["baseline"], 2)

    def test_wrong_output_rejected(self):
        vcd, trace = fixture()
        vcd = vcd.replace("b000000000000001010 v7", "b000000000000001011 v7")
        with self.assertRaises(ValueError):
            verify_waveform(vcd, trace)

    def test_wrong_busy_rejected(self):
        vcd, trace = fixture()
        at = vcd.index("#65\n")
        vcd = vcd[:at] + vcd[at:].replace("b0 v8", "b1 v8", 1)
        with self.assertRaises(ValueError):
            verify_waveform(vcd, trace)

    def test_off_edge_output_change_rejected(self):
        vcd, trace = fixture()
        at = vcd.index("#30\n")
        vcd = vcd[:at] + vcd[at:].replace("b000000000000000000 v6", "b000000000000000001 v6", 1)
        with self.assertRaises(ValueError):
            verify_waveform(vcd, trace)

    def test_unknown_output_rejected(self):
        vcd, trace = fixture()
        vcd = vcd.replace("b000000000000000000 v6", "bx v6", 1)
        with self.assertRaises(ValueError):
            verify_waveform(vcd, trace)

    def test_reset_output_failure_rejected(self):
        vcd, trace = fixture(abort=True)
        at = vcd.index("#90\n")
        vcd = vcd[:at] + vcd[at:].replace("b000000000000000000 v6", "b000000000000000011 v6", 1)
        with self.assertRaises(ValueError):
            verify_waveform(vcd, trace)

    def test_truncated_waveform_rejected(self):
        vcd, trace = fixture()
        with self.assertRaises(ValueError):
            verify_waveform(vcd.split("#110\n")[0], trace)

    def test_csv_expected_and_actual_corruption_rejected(self):
        vcd, trace = fixture()
        with self.assertRaises(ValueError):
            verify_waveform(vcd, trace.replace(",4,2,10,10,1", ",4,2,11,11,1"))

    def test_csv_cycle_inconsistency_rejected(self):
        vcd, trace = fixture()
        with self.assertRaises(ValueError):
            verify_waveform(vcd, trace.replace(",4,2,10,10,1", ",5,2,10,10,1"))

    def test_pending_at_end_rejected(self):
        vcd, trace = fixture()
        trace = "\n".join(trace.splitlines()[:-1]) + "\n"
        with self.assertRaises(ValueError):
            verify_waveform(vcd.split("#110\n")[0], trace)


if __name__ == "__main__":
    unittest.main()
