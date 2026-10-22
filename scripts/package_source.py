"""Create a compact source archive for Colab without local tools or run results."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    "README.md", "PROJECT_AUDIT.md", ".gitignore", "run_simulation.ps1",
    "requirements-figures.txt",
}
SOURCE_DIRS = {
    "rtl", "tb", "scripts", "tests", "docs", "notebooks", "provenance", ".github",
}
TEXT_SUFFIXES = {".vhd", ".vhdl", ".py", ".md", ".json", ".ipynb", ".tcl",
                 ".ps1", ".txt", ".yml", ".yaml", ".xdc"}
ESSENTIAL = {
    "README.md", "PROJECT_AUDIT.md", "rtl/fir_filter.vhd",
    "rtl/fir_filter_streaming.vhd", "tb/tb_fir_filter_original.vhd",
    "tb/tb_fir_verification.vhd", "scripts/fir_reference.py",
    "scripts/run_verification.py", "tests/test_reference.py",
    "tests/test_result_validation.py", "notebooks/01_fir_simulation.ipynb",
}


def collect_sources() -> dict[str, bytes]:
    """Read only explicitly permitted text source paths into an immutable snapshot."""
    candidates = [ROOT / name for name in ROOT_FILES if (ROOT / name).is_file()]
    for directory in SOURCE_DIRS:
        base = ROOT / directory
        if base.exists():
            candidates.extend(p for p in base.rglob("*") if p.is_file()
                              and p.suffix.lower() in TEXT_SUFFIXES
                              and "__pycache__" not in p.parts)
    summary = ROOT / "results" / "summary"
    if summary.exists():
        candidates.extend(p for p in summary.iterdir() if p.is_file()
                          and p.suffix.lower() in {".png", ".json", ".csv", ".txt", ".md"})
    snapshot = {}
    for path in sorted(candidates):
        relative = path.relative_to(ROOT)
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f"Refusing linked source outside the package: {relative}")
        for parent in path.parents:
            if parent == ROOT:
                break
            if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                raise ValueError(f"Refusing linked source directory: {relative}")
        payload = path.read_bytes()
        if path.suffix.lower() != ".png":
            payload.decode("utf-8")
        snapshot[relative.as_posix()] = payload
    missing = ESSENTIAL - snapshot.keys()
    if missing:
        raise FileNotFoundError(f"Required source files are missing: {sorted(missing)}")
    return snapshot


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "fir_filter_source.zip",
                        help="New ZIP file; existing files are rejected")
    args = parser.parse_args()
    target = args.output.resolve()
    if target.exists():
        raise FileExistsError(f"Archive already exists; choose another --output path: {target}")
    snapshot = collect_sources()
    manifest = {"schema_version": 1,
                "algorithm": "sha256",
                "files": {name: hashlib.sha256(payload).hexdigest()
                          for name, payload in snapshot.items()}}
    snapshot["source_checksums.json"] = (json.dumps(manifest, indent=2, sort_keys=True)
                                          + "\n").encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also rejects a file created between the check and open.
    with target.open("xb") as handle, zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(snapshot.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, payload)
    print(f"Packaged {len(snapshot)-1} source files: {target}")
    print(f"Archive SHA-256: {hashlib.sha256(target.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
