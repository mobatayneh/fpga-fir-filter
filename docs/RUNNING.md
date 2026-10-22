# Running the FIR project

This is VHDL hardware simulation, not model training. A GPU, dataset and FPGA
board are unnecessary for this stage. Python orchestrates a real GHDL simulation;
the Python reference alone is not evidence that the VHDL works.

## Windows

Use Python 3.10 or newer and [GHDL](https://github.com/ghdl/ghdl/releases/tag/v6.0.0).
The local working copy already has a portable GHDL 6.0.0 in the ignored `.tools`
folder. On a fresh copy, open PowerShell in the repository root and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_ghdl.ps1
```

This process-level policy applies to that script invocation only. The helper
downloads the official Windows x64 archive, checks its pinned SHA-256, and
extracts it inside the project. It does not install system services or change PATH.
An existing GHDL installation is also supported.

Run the complete verification:

```powershell
powershell -ExecutionPolicy Bypass -File run_simulation.ps1
```

If Python is not found, supply its executable:

```powershell
./run_simulation.ps1 -PythonExecutable 'C:/path/to/python.exe'
```

Or use the cross-platform runner directly:

```text
python scripts/run_verification.py --ghdl C:/path/to/ghdl.exe
```

Every run creates a new timestamped directory under `results/runs/`. Existing
results are never overwritten. Inspect `metrics.json`, `evaluation_report.md`,
the two CSV traces and `simulation.txt`. `verification.vcd` can be opened with
GTKWave or another VCD viewer. `original.vcd` reproduces the report's original
six-sample stimulus; its unconditional success message is not the verification gate.

GHDL 6.0.0 on Windows could not parse its generated library metadata when the
build directory contained Arabic characters. The runner stages copies in an
ASCII build directory, while preserving results in your project. If the default
temporary folder is not writable, pass `--build-root C:/your-writable-ascii-folder`.
The prepared local copy already has this configured in ignored local settings.

## Linux

```bash
sudo apt-get update
sudo apt-get install -y ghdl python3
python3 scripts/run_verification.py
```

The core runner and tests have no third-party Python dependencies. GHDL versions
can differ by distribution; the exact version is included in every result export.
The source uses VHDL-2008. See the official
[analysis, elaboration and simulation workflow](https://ghdl.github.io/ghdl/quick_start/simulation/index.html).

## Google Colab alternative

Open `notebooks/01_fir_simulation.ipynb` in Colab and use a standard CPU runtime.
Upload the generated `fir_filter_source.zip` when prompted, then run the cells
in order. The notebook installs GHDL, runs the same verification and downloads
`results_for_review.zip`. No training is involved. Both Windows GHDL 6.0.0 and
the submitted Colab Linux GHDL 4.1.0 run have passed, with the same 5272 outputs
and cycle counts. See [the evidence review](COLAB_RESULTS_REVIEW.md).

## Review a returned result archive

```text
python scripts/review_results.py results/colab-2026-10-21/results_for_review.zip --notebook results/colab-2026-10-21/executed_notebook.ipynb --output work/new_review.json
```

The output path must be new. This checks the complete SHA-256 manifest, numerical
configuration, CSV metrics, raw VCD signal behavior, completion logs and notebook
evidence. It reads the archived source as data and never executes it. A full
repository checkout contains the preserved historical result archive; the compact
source bundle used for Colab intentionally omits that historical evidence.

## Optional figures

```text
python -m pip install -r requirements-figures.txt
python scripts/plot_results.py results/runs/YOUR_RUN
```

This adds numerical-comparison and frequency-response PNGs in a new `figures`
directory. The frequency response is normalized by six for plotting only. The
hardware still produces the unnormalized integer weighted sum.

## What to return for review

Return the `results_for_review.zip` printed by the runner. It contains the exact
RTL and test source snapshot, simulator version, configuration, raw logs, waveforms,
per-output checks, benchmark, summary and SHA-256 manifest. If a run fails, return
its `FAILED.txt` and logs instead. For later optional Vivado work, return the full
new synthesis output directory described in `VIVADO.md`.
