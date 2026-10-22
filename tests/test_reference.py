"""Independent convolution and numerical-range checks for the Python reference."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fir_reference import MAX_OUTPUT, fir


class ReferenceTests(unittest.TestCase):
    def test_report_sequence(self):
        self.assertEqual(fir([3, 4, 5, 6, 10, 0]), [3, 10, 19, 27, 36, 37])

    def test_impulse(self):
        self.assertEqual(fir([255, 0, 0, 0, 0]), [255, 510, 510, 255, 0])

    def test_full_scale_step(self):
        self.assertEqual(fir([255] * 6), [255, 765, 1275, 1530, 1530, 1530])
        self.assertEqual(MAX_OUTPUT, 1530)
        self.assertEqual(MAX_OUTPUT.bit_length(), 11)

    def test_independent_convolution(self):
        rng = random.Random(8208)
        x = [rng.randrange(256) for _ in range(4096)]
        padded = [0, 0, 0] + x
        expected = [padded[i + 3] + 2*padded[i + 2] +
                    2*padded[i + 1] + padded[i] for i in range(len(x))]
        self.assertEqual(fir(x), expected)
        self.assertTrue(all(0 <= y <= MAX_OUTPUT for y in expected))

    def test_empty_and_invalid(self):
        self.assertEqual(fir([]), [])
        for invalid in [-1, 256, 1.5, True, "1"]:
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                fir([invalid])

    def test_new_run_clears_history(self):
        fir([255] * 4)
        self.assertEqual(fir([0, 0]), [0, 0])


if __name__ == "__main__":
    unittest.main()
