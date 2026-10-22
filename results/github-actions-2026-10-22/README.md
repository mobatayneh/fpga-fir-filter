# Hosted validation on 2026-10-22

[Pull-request workflow](https://github.com/mobatayneh/fpga-fir-filter/actions/runs/39723764246)
completed successfully for source commit
`97c7549e5336e0e1e06cf8c38caba59ad058f027`, tree
`140a45233c8c66c8b96cf602365bc32d5e75eaf2`.
The corresponding push workflow also passed.

- Ubuntu 24.04; Python 3.12.3; GHDL 4.1.0.
- [38 Python tests passed](python_tests.txt).
- [5272 RTL outputs](metrics.json), zero mismatches; baseline block 2559 cycles,
  streaming block 512 cycles.
- [Independent artifact review](independent_review.json): 29 SHA-256 manifest
  entries verified, reported metrics recomputed, every output checked directly
  from accepted VCD inputs, including reset and interface behavior.

The downloaded workflow artifact passed its ZIP CRC check. Its nested result
archive was 400273 bytes with SHA-256
`c9c32e4eea2f23c7b1f68224dbe89da662b98a25a31d3f8298b3bce8f4f908d6`.
The original artifact is available from the workflow while GitHub retains it;
the complete downloaded archive is also retained locally. The small records
here are copied from that artifact without editing, except the independent
review JSON, which was generated locally by `scripts/review_results.py`.

This is a separate run from the historical Colab submission. Documentation
added after this run does not change its executed RTL, scripts or test sources.
No synthesis, physical timing, power or board measurement was performed.
