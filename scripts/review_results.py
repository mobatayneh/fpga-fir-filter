"""Independently review a returned FIR result archive without executing its source."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def read_checked_archive(path: Path) -> tuple[dict[str, bytes], dict]:
    """Check the complete manifest and member set before consuming result data."""
    raw = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if not 1 <= len(entries) <= 1000 or sum(e.file_size for e in entries) > 64*1024*1024:
            raise ValueError("Unexpected result archive size or entry count.")
        payloads = {}
        for entry in entries:
            name = entry.filename
            p = PurePosixPath(name)
            if (entry.is_dir() or p.is_absolute() or "\\" in name or ":" in name
                    or any(part in {"", ".", ".."} for part in name.split("/"))
                    or name in payloads or stat.S_ISLNK(entry.external_attr >> 16)
                    or entry.file_size > 32*1024*1024):
                raise ValueError(f"Unexpected archive member: {name!r}")
            payloads[name] = archive.read(entry)
    manifest = json.loads(payloads["checksums.json"])
    if not isinstance(manifest, dict) or set(payloads) != set(manifest) | {"checksums.json"}:
        raise ValueError("Archive members differ from the checksum manifest.")
    for name, expected in manifest.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"Invalid SHA-256 for {name}.")
        if hashlib.sha256(payloads[name]).hexdigest() != expected:
            raise ValueError(f"Checksum mismatch: {name}")
    return payloads, {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                      "verified_manifest_entries": len(manifest)}


def review(archive: Path, notebook: Path | None = None) -> dict:
    from run_verification import validate_csvs
    from verify_waveform import verify_waveform

    payloads, archive_info = read_checked_archive(archive)
    required = {"metrics.json", "environment.json", "verification.csv", "benchmark.csv",
                "verification.vcd", "simulation.txt", "python_tests.txt", "ghdl_version.txt",
                "analysis.txt", "elaboration.txt", "original_elaboration.txt",
                "original_simulation.txt", "source/rtl/fir_filter.vhd",
                "source/rtl/fir_filter_streaming.vhd", "source/tb/tb_fir_verification.vhd"}
    if not required.issubset(payloads):
        raise ValueError(f"Incomplete result set: {sorted(required - payloads.keys())}")
    env = json.loads(payloads["environment.json"])
    expected_config = {"clock_period_ns": 10, "coefficient_order_current_to_oldest": [1, 2, 2, 1],
                       "input_signed": False, "input_width": 8, "output_width": 18,
                       "hardware_executed": False, "vivado_executed": False,
                       "random_seed": "0x82080001 (VHDL LFSR); 8208 (Python reference tests)",
                       "timing_convention": "Elapsed rising-edge intervals from accepted input to valid output"}
    for key, expected in expected_config.items():
        if env.get(key) != expected:
            raise ValueError(f"Unexpected experiment configuration for {key}: {env.get(key)!r}")
    if env["ghdl"] != payloads["ghdl_version.txt"].decode("utf-8"):
        raise ValueError("Simulator version disagrees with environment metadata.")
    for name in ["analysis.txt", "elaboration.txt", "original_elaboration.txt"]:
        if payloads[name].strip():
            raise ValueError(f"Nonempty compiler log requires manual review: {name}")
    tmp_root = ROOT / "work" / "archive_review"
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=tmp_root) as temporary:
        directory = Path(temporary)
        for name in ["verification.csv", "benchmark.csv"]:
            (directory / name).write_bytes(payloads[name])
        recomputed = validate_csvs(directory)
    reported = json.loads(payloads["metrics.json"])
    for key, actual in recomputed.items():
        if reported.get(key) != actual:
            raise ValueError(f"Reported metrics disagree with independently checked CSVs: {key}")
    waveform = verify_waveform(payloads["verification.vcd"].decode("utf-8"),
                               payloads["verification.csv"].decode("utf-8"))
    simulation = payloads["simulation.txt"].decode("utf-8")
    match = re.search(r"PASSED: baseline_outputs=(\d+) streaming_outputs=(\d+) cycles=(\d+) random_cycles=(\d+) seed=(0x[0-9a-fA-F]+)", simulation)
    if not match or tuple(map(int, match.groups()[:4])) != (1620, 3652, 9191, 6000) or match[5] != "0x82080001":
        raise ValueError("Missing or inconsistent complete-simulation sentinel.")
    if "simulation stopped @91916ns" not in simulation:
        raise ValueError("Simulation did not reach the expected completed run time.")
    test_log = payloads["python_tests.txt"].decode("utf-8")
    count = re.search(r"Ran (\d+) tests", test_log)
    if not count or not test_log.rstrip().endswith("OK") or "... FAIL" in test_log or "... ERROR" in test_log:
        raise ValueError("Python test log does not show a complete successful suite.")
    sources = []
    for name, source in payloads.items():
        if name.startswith("source/"):
            relative = name.removeprefix("source/")
            current = ROOT / relative
            exact = current.is_file() and source == current.read_bytes()
            # Documentation or later helper changes may differ; execution-critical
            # RTL and testbench must match the reviewed experiment in this release.
            if relative.startswith(("rtl/", "tb/")) and not exact:
                raise ValueError(f"Executed hardware source differs from reviewed source: {relative}")
            sources.append({"path": relative, "sha256": hashlib.sha256(source).hexdigest(),
                            "matches_current_workspace": exact})
    result = {"status": "PASS", "archive": archive_info,
              "experiment_generated_at_utc": reported["generated_at_utc"],
              "environment": env, "recomputed_metrics": recomputed,
              "waveform_review": waveform, "submitted_python_test_count": int(count[1]),
              "executed_sources": sources,
              "limitations": ["Finite behavioral simulation, not a formal proof",
                              "No Vivado synthesis, physical timing, power or board validation",
                              "Checksums establish internal consistency, not independent attestation of a hosted service"]}
    if notebook:
        nb_raw = notebook.read_bytes()
        nb = json.loads(nb_raw)
        code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
        executions = [c.get("execution_count") for c in code_cells]
        if executions != list(range(1, len(code_cells) + 1)):
            raise ValueError("Notebook code execution counts are incomplete or nonsequential.")
        if any(o.get("output_type") == "error" for c in code_cells for o in c.get("outputs", [])):
            raise ValueError("Notebook contains an error output.")
        output_text = "\n".join("".join(o.get("text", [])) for c in code_cells for o in c.get("outputs", []))
        if archive_info["sha256"] not in output_text:
            raise ValueError("Notebook does not identify this exact result archive checksum.")
        for cell in code_cells:
            compile("".join(cell["source"]), "submitted-notebook-cell", "exec")
        result["notebook"] = {"sha256": hashlib.sha256(nb_raw).hexdigest(),
                              "executed_code_cells": len(code_cells), "execution_counts": executions,
                              "error_outputs": 0, "result_archive_hash_matches": True}
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--notebook", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New review JSON file; never overwrites")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = review(args.archive, args.notebook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(f"PASS: reviewed {result['archive']['verified_manifest_entries']} manifest entries; "
          f"{sum(result['recomputed_metrics']['checked_outputs'].values())} outputs; saved {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
