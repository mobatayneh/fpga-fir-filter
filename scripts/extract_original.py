"""Recover numbered original VHDL listings from the supplied Word report.

Only paragraph text and printed line-number prefixes are processed. The input
is never modified. Existing output files are rejected. Python standard library.
"""
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with zipfile.ZipFile(args.report) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = ["".join(t.text or "" for t in p.findall(".//w:t", ns))
                  for p in root.findall("./w:body/w:p", ns)]
    blocks, current = [], []
    for line in paragraphs:
        match = re.match(r"^\s*(\d+)  (.*)$", line)
        if match:
            number = int(match[1])
            if number == 1 and current:
                blocks.append(current)
                current = []
            if number != len(current) + 1:
                raise ValueError("Noncontiguous printed line numbers; inspect the document manually.")
            current.append(match[2])
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    if [len(b) for b in blocks] != [113, 102]:
        raise ValueError("Report does not match the expected two complete source listings.")
    args.output.mkdir(parents=True, exist_ok=False)
    names = ["fir_filter.vhd", "tb_fir_filter_original.vhd"]
    for name, block in zip(names, blocks):
        (args.output / name).write_text("\n".join(block) + "\n", encoding="utf-8")
    manifest = {"source_sha256": hashlib.sha256(args.report.read_bytes()).hexdigest(),
                "transformation": "Removed printed line numbers only; no RTL edits",
                "outputs": {name: hashlib.sha256((args.output/name).read_bytes()).hexdigest() for name in names}}
    (args.output / "extraction.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
