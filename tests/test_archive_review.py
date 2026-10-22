"""Result archive integrity failures must be rejected before evidence is used."""
import hashlib
import json
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from review_results import read_checked_archive


class ArchiveReviewTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / "work" / "test_tmp"
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "results.zip"

    def write_zip(self, entries, manifest):
        with warnings.catch_warnings(), zipfile.ZipFile(self.path, "w") as z:
            warnings.simplefilter("ignore", UserWarning)
            for name, content in entries:
                z.writestr(name, content)
            z.writestr("checksums.json", json.dumps(manifest))

    def test_valid_manifest(self):
        self.write_zip([("sample.txt", b"evidence")], {"sample.txt": hashlib.sha256(b"evidence").hexdigest()})
        payloads, metadata = read_checked_archive(self.path)
        self.assertEqual(payloads["sample.txt"], b"evidence")
        self.assertEqual(metadata["verified_manifest_entries"], 1)

    def test_changed_payload(self):
        self.write_zip([("sample.txt", b"altered")], {"sample.txt": hashlib.sha256(b"evidence").hexdigest()})
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            read_checked_archive(self.path)

    def test_unlisted_member(self):
        self.write_zip([("sample.txt", b"extra")], {})
        with self.assertRaisesRegex(ValueError, "members differ"):
            read_checked_archive(self.path)

    def test_duplicate_member(self):
        self.write_zip([("same.txt", b"a"), ("same.txt", b"b")], {"same.txt": hashlib.sha256(b"b").hexdigest()})
        with self.assertRaisesRegex(ValueError, "Unexpected archive member"):
            read_checked_archive(self.path)

    def test_unsafe_path(self):
        self.write_zip([("../escape.txt", b"a")], {"../escape.txt": hashlib.sha256(b"a").hexdigest()})
        with self.assertRaisesRegex(ValueError, "Unexpected archive member"):
            read_checked_archive(self.path)


if __name__ == "__main__":
    unittest.main()
