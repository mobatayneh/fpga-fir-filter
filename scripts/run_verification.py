"""Run real VHDL simulation and export an inspectable, checksummed result set."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_ghdl(requested: str | None) -> Path:
    candidate = requested or os.environ.get("GHDL") or shutil.which("ghdl")
    if candidate:
        path = Path(shutil.which(candidate) or candidate).resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"GHDL executable not found: {path}")
    candidates = list((ROOT / ".tools" / "ghdl-6.0.0").rglob("ghdl.exe"))
    if len(candidates) == 1:
        return candidates[0].resolve()
    raise FileNotFoundError("Install GHDL or pass --ghdl PATH. See docs/RUNNING.md.")


def run_command(command: list[str], cwd: Path, log: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, text=True, encoding="utf-8",
                               errors="replace", stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=120)
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"Command failed ({completed.returncode}): {command}\n{completed.stdout}")
    return completed.stdout


def validate_csvs(directory: Path) -> dict:
    from fir_reference import fir

    with (directory / "verification.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("No checked hardware outputs were recorded.")
    counts = Counter()
    phases = Counter()
    for row in rows:
        architecture = row["architecture"]
        if architecture not in {"baseline", "streaming"}:
            raise ValueError(f"Unknown architecture: {architecture}")
        if int(row["actual"]) != int(row["expected"]):
            raise ValueError(f"Arithmetic mismatch: {row}")
        if not 0 <= int(row["actual"]) <= 1530:
            raise ValueError(f"Output outside fixed-coefficient range: {row}")
        latency = {"baseline": 4, "streaming": 1}[architecture]
        if int(row["latency"]) != latency:
            raise ValueError(f"Latency mismatch: {row}")
        counts[architecture] += 1
        phases[row["phase"]] += 1
    if set(counts) != {"baseline", "streaming"}:
        raise ValueError("Both architectures must be tested.")
    with (directory / "benchmark.csv").open(newline="", encoding="utf-8") as f:
        benchmarks = list(csv.DictReader(f))
    if len(benchmarks) != 2 or {r["architecture"] for r in benchmarks} != set(counts):
        raise ValueError("Expected exactly one benchmark row per architecture.")
    benchmark_expected = fir([(i * 73 + 19) % 256 for i in range(512)])
    for row in benchmarks:
        name = row["architecture"]
        selected = [r for r in rows if r["architecture"] == name and r["phase"] == "benchmark"]
        if len(selected) != 512 or int(row["samples"]) != 512:
            raise ValueError("Benchmark must contain exactly 512 checked outputs.")
        if [int(r["input_index"]) for r in selected] != list(range(1, 513)):
            raise ValueError("Benchmark input indices must be exactly 1 through 512 in order.")
        if [int(r["actual"]) for r in selected] != benchmark_expected:
            raise ValueError(f"Benchmark outputs disagree with independent Python reference for {name}.")
        cycles = [int(r["cycle"]) for r in selected]
        ii = {"baseline": 5, "streaming": 1}[name]
        if any(b-a != ii for a, b in zip(cycles, cycles[1:])):
            raise ValueError(f"Measured output interval differs from {ii} for {name}.")
        first_accept = cycles[0] - int(selected[0]["latency"])
        elapsed = cycles[-1] - first_accept
        if (int(row["first_accept_cycle"]), int(row["last_output_cycle"]),
            int(row["elapsed_cycles"]), int(row["initiation_interval_cycles"])) != (
                first_accept, cycles[-1], elapsed, ii):
            raise ValueError("Benchmark summary disagrees with per-output trace.")
        if elapsed != {"baseline": 2559, "streaming": 512}[name]:
            raise ValueError(f"Unexpected measured block duration: {row}")
    baseline_values = [int(r["actual"]) for r in rows if r["architecture"] == "baseline" and r["phase"] == "benchmark"]
    streaming_values = [int(r["actual"]) for r in rows if r["architecture"] == "streaming" and r["phase"] == "benchmark"]
    if baseline_values != streaming_values:
        raise ValueError("Architectures disagree on the identical benchmark sample sequence.")
    for name, minimum in {"baseline": 1500, "streaming": 3500}.items():
        if counts[name] <= minimum:
            raise ValueError(f"Insufficient checked outputs for {name}: {counts[name]}.")
        cycles = [int(r["cycle"]) for r in rows if r["architecture"] == name]
        if any(b <= a for a, b in zip(cycles, cycles[1:])):
            raise ValueError(f"Output cycles must strictly increase for {name}.")
    if not {"benchmark", "directed", "random", "reset_recovery"}.issubset(phases):
        raise ValueError("Missing required verification phase.")
    return {"status": "PASS", "checked_outputs": dict(counts),
            "checked_outputs_by_phase": dict(phases), "mismatches": 0,
            "benchmark": benchmarks,
            "evidence_level": "RTL behavioral simulation; no FPGA hardware timing or power measurement"}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ghdl", help="Path to a GHDL executable")
    parser.add_argument("--output", type=Path, help="New output directory; must not exist")
    parser.add_argument("--build-root", type=Path, help="Writable ASCII path for GHDL build directories")
    args = parser.parse_args()
    ghdl = find_ghdl(args.ghdl)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    out = (args.output or ROOT / "results" / "runs" / stamp).resolve()
    out.mkdir(parents=True, exist_ok=False)
    local_settings = ROOT / ".tools" / "local_settings.json"
    local = json.loads(local_settings.read_text(encoding="utf-8")) if local_settings.exists() else {}
    default_build = ROOT / "work" / "ghdl" if str(ROOT).isascii() else Path(tempfile.gettempdir()) / "fir_ghdl"
    build_root = Path(args.build_root or os.environ.get("FIR_BUILD_ROOT") or local.get("build_root") or default_build).resolve()
    build = build_root / stamp
    sources = [ROOT / p for p in ("rtl/fir_filter.vhd", "rtl/fir_filter_streaming.vhd",
                                  "tb/tb_fir_filter_original.vhd", "tb/tb_fir_verification.vhd")]
    try:
        if not str(build).isascii():
            raise ValueError("GHDL on Windows needs an ASCII build path here. Set --build-root to a writable ASCII directory.")
        build.mkdir(parents=True, exist_ok=False)
        for path in sources:
            shutil.copy2(path, build / path.name)
        version = run_command([str(ghdl), "--version"], build, out / "ghdl_version.txt")
        run_command([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
                    ROOT, out / "python_tests.txt")
        run_command([str(ghdl), "-a", "--std=08", *[p.name for p in sources]], build, out / "analysis.txt")
        run_command([str(ghdl), "-e", "--std=08", "tb_fir_filter"], build, out / "original_elaboration.txt")
        run_command([str(ghdl), "-r", "--std=08", "tb_fir_filter", "--stop-time=500ns",
                     "--assert-level=error", "--vcd=original.vcd"], build, out / "original_simulation.txt")
        run_command([str(ghdl), "-e", "--std=08", "tb_fir_verification"], build, out / "elaboration.txt")
        simulation = run_command([str(ghdl), "-r", "--std=08", "tb_fir_verification",
                                  "--assert-level=error", "--vcd=verification.vcd"], build, out / "simulation.txt")
        if "PASSED" not in simulation:
            raise RuntimeError("Simulation ended without the verification completion sentinel.")
        for name in ["verification.csv", "benchmark.csv", "original.vcd", "verification.vcd"]:
            shutil.copy2(build / name, out / name)
        metrics = validate_csvs(out)
        metrics["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        env = {"python": sys.version, "platform": platform.platform(), "ghdl": version,
               "clock_period_ns": 10, "coefficient_order_current_to_oldest": [1, 2, 2, 1],
               "input_signed": False, "input_width": 8, "output_width": 18,
               "random_seed": "0x82080001 (VHDL LFSR); 8208 (Python reference tests)",
               "timing_convention": "Elapsed rising-edge intervals from accepted input to valid output",
               "hardware_executed": False, "vivado_executed": False}
        (out / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
        source_dir = out / "source"
        for path in [*sources, *sorted((ROOT / "scripts").glob("*.py")), *sorted((ROOT / "tests").glob("*.py"))]:
            target = source_dir / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        report = ["# Verification results", "", "Both VHDL designs passed assertion-based behavioral simulation.",
                  "", f"Checked outputs: {dict(metrics['checked_outputs'])}. Arithmetic mismatches: 0.",
                  "", "| Architecture | Samples | Elapsed cycles | Initiation interval |",
                  "|---|---:|---:|---:|"]
        for row in metrics["benchmark"]:
            report.append(f"| {row['architecture']} | {row['samples']} | {row['elapsed_cycles']} | {row['initiation_interval_cycles']} |")
        report += ["", "At a common clock, the measured steady-state acceptance rate increases 5x.",
                   "This is a cycle-level simulation comparison, not measured FPGA Fmax, area, or power.",
                   "The fixed-coefficient streaming extension does not implement the report's abstract shared-multiplier resource model.",
                   "Vivado synthesis, physical timing closure, and board validation remain separate work."]
        (out / "evaluation_report.md").write_text("\n".join(report)+"\n", encoding="utf-8")
        checksums = {p.relative_to(out).as_posix(): sha256(p) for p in sorted(out.rglob("*"))
                     if p.is_file() and p.suffix != ".cf"}
        (out / "checksums.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")
        archive = out / "results_for_review.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for rel in [*checksums, "checksums.json"]:
                z.write(out / rel, rel)
        print(json.dumps(metrics, indent=2))
        print(f"Results: {out}\nReview archive: {archive}")
        return 0
    except Exception as exc:
        if build.exists():
            for name in ["verification.csv", "benchmark.csv", "original.vcd", "verification.vcd"]:
                if (build / name).is_file():
                    shutil.copy2(build / name, out / name)
        (out / "FAILED.txt").write_text(str(exc), encoding="utf-8")
        print(f"FAILED: {exc}\nPartial logs preserved in {out}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
