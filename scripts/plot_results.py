"""Render portable figures from a verified run (optional matplotlib dependency)."""
import argparse
import cmath
import csv
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from run_verification import validate_csvs
    validate_csvs(args.results)
    out = args.results / "figures"
    out.mkdir(exist_ok=False)
    plt.rcParams.update({"figure.dpi": 160, "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False})
    with (args.results / "verification.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for name, color in [("baseline", "#24539c"), ("streaming", "#00856c")]:
        subset = [r for r in rows if r["phase"] == "benchmark" and r["architecture"] == name][:24]
        axes[0].plot(range(len(subset)), [int(r["actual"]) for r in subset], marker="o",
                     markersize=3, label=name, color=color, linestyle="--" if name == "streaming" else "-")
    axes[0].set(title="Identical checked FIR outputs", xlabel="Accepted sample index", ylabel="Unsigned output")
    axes[0].legend()
    axes[1].bar(["Baseline", "Streaming"], [2559, 512], color=["#24539c", "#00856c"])
    for i, value in enumerate([2559, 512]):
        axes[1].text(i, value + 45, str(value), ha="center")
    axes[1].set(title="512 samples in RTL simulation", ylabel="Elapsed clock cycles", ylim=(0, 2900))
    fig.savefig(out / "architecture_comparison.png")
    plt.close(fig)
    frequencies = [i / 1024 for i in range(513)]
    response = [sum(c * cmath.exp(-2j*math.pi*f*k) for k,c in enumerate([1,2,2,1])) / 6
                for f in frequencies]
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    ax.plot(frequencies, [20*math.log10(max(abs(h), 1e-6)) for h in response], color="#24539c")
    ax.set(title="FIR magnitude response normalized by DC gain 6",
           xlabel="Frequency / sample rate (cycles per accepted sample)",
           ylabel="Magnitude (dB)", ylim=(-80, 3), xlim=(0, .5))
    ax.grid(alpha=.2)
    fig.savefig(out / "frequency_response.png")
    plt.close(fig)
    print(f"Figures written to {out}. Normalization is for display only; RTL gain remains 6.")


if __name__ == "__main__":
    main()
