"""Reject incomplete or inconsistent simulation evidence before reporting PASS."""
import copy
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_verification import validate_csvs


TRACE_FIELDS = ["architecture", "phase", "cycle", "input_index", "expected", "actual", "latency"]
BENCHMARK_FIELDS = ["architecture", "samples", "first_accept_cycle", "last_output_cycle",
                    "elapsed_cycles", "initiation_interval_cycles"]


class ResultValidationTests(unittest.TestCase):
    def setUp(self):
        temp_parent = Path(__file__).resolve().parents[1] / "work" / "test_tmp"
        temp_parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.rows = []
        self.benchmarks = []
        # These synthetic validator fixtures are not hardware-run evidence.
        samples = [(index * 73 + 19) % 256 for index in range(512)]
        history = [0, 0, 0]
        expected = []
        for value in samples:
            expected.append(value + 2 * history[0] + 2 * history[1] + history[2])
            history = [value, *history[:2]]
        for architecture, latency, interval in [("baseline", 4, 5), ("streaming", 1, 1)]:
            first_accept = 10
            for index, value in enumerate(expected):
                self.rows.append({
                    "architecture": architecture, "phase": "benchmark",
                    "cycle": first_accept + index * interval + latency,
                    "input_index": index + 1, "expected": value,
                    "actual": value, "latency": latency,
                })
            last_output = first_accept + 511 * interval + latency
            self.benchmarks.append({
                "architecture": architecture, "samples": 512,
                "first_accept_cycle": first_accept,
                "last_output_cycle": last_output,
                "elapsed_cycles": last_output - first_accept,
                "initiation_interval_cycles": interval,
            })
            for index in range(1100 if architecture == "baseline" else 3100):
                phase = "directed" if index < 20 else "random"
                if architecture == "streaming" and index == 20:
                    phase = "reset_recovery"
                self.rows.append({
                    "architecture": architecture, "phase": phase,
                    "cycle": last_output + (index + 1) * interval,
                    "input_index": 513 + index, "expected": 0,
                    "actual": 0, "latency": latency,
                })

    def validate(self, rows=None, benchmarks=None):
        for name, fields, records in [
            ("verification.csv", TRACE_FIELDS, self.rows if rows is None else rows),
            ("benchmark.csv", BENCHMARK_FIELDS,
             self.benchmarks if benchmarks is None else benchmarks),
        ]:
            with (self.directory / name).open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(records)
        return validate_csvs(self.directory)

    def test_consistent_fixture(self):
        result = self.validate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["checked_outputs"], {"baseline": 1612, "streaming": 3612})

    def test_empty_output_trace_rejected(self):
        with self.assertRaisesRegex(ValueError, "No checked hardware outputs"):
            self.validate(rows=[])

    def test_missing_architecture_rejected(self):
        with self.assertRaisesRegex(ValueError, "Both architectures"):
            self.validate(rows=[r for r in self.rows if r["architecture"] == "baseline"])

    def test_arithmetic_mismatch_rejected(self):
        self.rows[0]["actual"] += 1
        with self.assertRaisesRegex(ValueError, "Arithmetic mismatch"):
            self.validate()

    def test_output_overflow_rejected(self):
        self.rows[0]["actual"] = self.rows[0]["expected"] = 1531
        with self.assertRaisesRegex(ValueError, "outside fixed-coefficient range"):
            self.validate()

    def test_incorrect_latency_rejected(self):
        self.rows[0]["latency"] = 5
        with self.assertRaisesRegex(ValueError, "Latency mismatch"):
            self.validate()

    def test_duplicate_benchmark_summary_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly one benchmark row"):
            self.validate(benchmarks=[self.benchmarks[0], self.benchmarks[0]])

    def test_truncated_benchmark_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly 512 checked outputs"):
            self.validate(rows=self.rows[1:])

    def test_false_summary_rejected(self):
        for field in ["first_accept_cycle", "last_output_cycle", "elapsed_cycles",
                      "initiation_interval_cycles"]:
            with self.subTest(field=field):
                summaries = copy.deepcopy(self.benchmarks)
                summaries[0][field] += 1
                with self.assertRaisesRegex(ValueError, "summary disagrees"):
                    self.validate(benchmarks=summaries)

    def test_incorrect_interval_rejected(self):
        self.rows[7]["cycle"] += 1
        with self.assertRaisesRegex(ValueError, "output interval differs"):
            self.validate()

    def test_disagreement_between_architectures_rejected(self):
        # Even if each trace says its own arithmetic matched, the two designs
        # must agree for the common benchmark input sequence.
        target = next(r for r in self.rows if r["architecture"] == "streaming"
                      and r["phase"] == "benchmark")
        target["actual"] += 1
        target["expected"] += 1
        with self.assertRaisesRegex(ValueError, "independent Python reference"):
            self.validate()

    def test_matching_but_wrong_architectures_rejected(self):
        for row in self.rows:
            if row["phase"] == "benchmark":
                row["expected"] = row["actual"] = 0
        with self.assertRaisesRegex(ValueError, "independent Python reference"):
            self.validate()

    def test_benchmark_index_corruption_rejected(self):
        self.rows[10]["input_index"] = 10
        with self.assertRaisesRegex(ValueError, "input indices"):
            self.validate()

    def test_insufficient_coverage_rejected(self):
        with self.assertRaisesRegex(ValueError, "Insufficient checked outputs"):
            self.validate(rows=[r for r in self.rows if r["phase"] == "benchmark"])

    def test_missing_phase_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing required verification phase"):
            self.validate(rows=[r for r in self.rows if r["phase"] != "reset_recovery"])

    def test_repeated_output_cycle_rejected(self):
        self.rows[520]["cycle"] = self.rows[519]["cycle"]
        with self.assertRaisesRegex(ValueError, "strictly increase"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
