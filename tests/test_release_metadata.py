import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_release", ROOT / "scripts/verify_release.py")
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class ReleaseMetadataTests(unittest.TestCase):
    def test_capabilities_match_real_cli_and_runtime(self):
        self.assertEqual(verify.validate_metadata(ROOT), [])

    def test_unknown_commands_and_overstated_host_evidence_fail(self):
        path = ROOT / "docs/capabilities.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        data = copy.deepcopy(original)
        data["commands"]["semantic-search"] = "unsupported"
        data["hosts"][0]["status"] = "verified"
        read = Path.read_text

        def patched(p, *args, **kwargs):
            return json.dumps(data) if p == path else read(p, *args, **kwargs)

        with mock.patch.object(Path, "read_text", patched):
            errors = verify.validate_metadata(ROOT)
        self.assertTrue(any("commands" in e for e in errors))
        self.assertTrue(any("evidence" in e for e in errors))

    def test_changed_archive_and_missing_checksum_are_rejected(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.zip"
            with zipfile.ZipFile(path, "w") as bundle:
                bundle.writestr("slipbox/SKILL.md", "changed")
                bundle.writestr("slipbox/PACKAGE_SHA256SUMS", "0" * 64 + "  SKILL.md\n")
            self.assertTrue(any("invalid checksum" in e for e in verify.validate_archive(path)))
            self.assertTrue(any("SHA256SUMS" in e for e in verify.validate_dist(Path(tmp))))


if __name__ == "__main__":
    unittest.main()
