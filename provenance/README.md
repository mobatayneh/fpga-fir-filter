# Source provenance and attribution

The baseline is recovered from the supplied report **Hardware Design, Analysis
and Optimization of an 8-bit 4-Tap FIR Filter Using Resource Sharing and Pipelining**,
EE-8208, Toronto Metropolitan University, August 2026.

Original report authors: **Mohammad Albatayneh and Ashvin Selvakumar**. Individual
responsibilities are not specified in the supplied report and are not inferred.
Both authors' credit is retained in this repository.

- `rtl/fir_filter.vhd`: 113 numbered lines, report section 4.5, PDF pages 21–24.
- `tb/tb_fir_filter_original.vhd`: 102 numbered lines, section 4.6, PDF pages 25–27.
- Recovery uses the editable Word version to avoid PDF line-wrapping corruption.
  Only printed line-number prefixes were removed; original comments and logic remain.
- `source_manifest.json` records SHA-256 and byte lengths of both supplied files.
- `scripts/extract_original.py REPORT.docx NEW_DIRECTORY` reproduces extraction.

The original PDF and DOCX remain at their supplied locations. Full extracted report
text, review images and local tooling are ignored by Git. The source bundle
excludes the report, including its student identifiers. No redistribution license
has been assigned on behalf of both authors. The public code does not imply an
open-source license grant or establish each author's individual responsibilities.

New development consists of the separately named streaming implementation,
assertion-based verification, Python reference/orchestration, CI, reproducibility
exports and explanatory documentation. Their measured status is reported separately.
