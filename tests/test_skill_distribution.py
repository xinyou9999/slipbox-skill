import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGER = ROOT / "scripts" / "package_skill.py"
EXPECTED_FILES = {
    "slipbox/SKILL.md",
    "slipbox/LICENSE",
    "slipbox/scripts/slipbox.py",
    "slipbox/references/data-format.md",
    "slipbox/references/tagging-policy.md",
    "slipbox/templates/tags.example.json",
    "slipbox/docs/INSTALL.md",
    "slipbox/docs/QUICKSTART.md",
    "slipbox/docs/AI_INSTALL.md",
    "slipbox/docs/capabilities.json",
    "slipbox/PACKAGE_SHA256SUMS",
}


class SkillDistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, language="zh", target="generic", cwd=None):
        result = subprocess.run(
            [sys.executable, str(PACKAGER), "--language", language,
             "--target", target, "--output-dir", str(self.base / "dist")],
            cwd=cwd or self.base, text=True, encoding="utf-8", capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        archive = self.base / "dist" / f"slipbox-0.1.0-{target}-{language}.zip"
        self.assertTrue(archive.is_file(), result.stdout)
        return archive

    def test_language_packages_have_only_allowlisted_files_and_selected_instructions(self):
        for language, source in (("zh", "SKILL.md"), ("en", "SKILL.en.md")):
            with self.subTest(language=language):
                archive = self.build(language)
                with zipfile.ZipFile(archive) as bundle:
                    self.assertEqual(set(bundle.namelist()), EXPECTED_FILES)
                    self.assertEqual(len(bundle.namelist()), len(EXPECTED_FILES))
                    self.assertEqual(bundle.read("slipbox/SKILL.md"), (ROOT / source).read_bytes())
                    for name in EXPECTED_FILES - {"slipbox/SKILL.md", "slipbox/PACKAGE_SHA256SUMS"}:
                        self.assertEqual(bundle.read(name), (ROOT / name.removeprefix("slipbox/")).read_bytes())
        self.assertEqual(len(list((self.base / "dist").glob("*.zip"))), 2)

    def test_extracted_packages_run_core_from_an_unrelated_working_directory(self):
        for language in ("zh", "en"):
            with self.subTest(language=language):
                archive = self.build(language)
                extracted = self.base / f"installed-{language}"
                with zipfile.ZipFile(archive) as bundle:
                    bundle.extractall(extracted)
                cli = extracted / "slipbox" / "scripts" / "slipbox.py"
                home = self.base / f"library-{language}"
                env = {**os.environ, "SLIPBOX_HOME": str(home), "PYTHONUTF8": "1"}

                def run(*args):
                    result = subprocess.run(
                        [sys.executable, str(cli), *args, "--json"], cwd=self.base,
                        env=env, text=True, encoding="utf-8", capture_output=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    return json.loads(result.stdout)

                self.assertEqual(run("init")["status"], "initialized")
                run("tag-add", "工作", "--alias", "work", "--description", "工作事项")
                card = run("add", "可移植卡片 portable marker", "--tag", "work")
                self.assertEqual(card["tags"], ["工作"])
                self.assertEqual(run("search", "portable marker")["cards"][0]["id"], card["id"])
                self.assertTrue((home / "cards" / f"{card['id']}.md").is_file())
                self.assertFalse((extracted / "slipbox" / "cards").exists())

    def test_workbuddy_variants_add_market_metadata_without_changing_core(self):
        for language in ("zh", "en"):
            with self.subTest(language=language):
                generic = self.build(language)
                workbuddy = self.build(language, "workbuddy")
                with zipfile.ZipFile(generic) as plain, zipfile.ZipFile(workbuddy) as market:
                    self.assertEqual(set(market.namelist()), EXPECTED_FILES)
                    for name in EXPECTED_FILES - {"slipbox/SKILL.md", "slipbox/PACKAGE_SHA256SUMS"}:
                        self.assertEqual(plain.read(name), market.read(name))
                    generic_skill = plain.read("slipbox/SKILL.md").decode("utf-8")
                    market_skill = market.read("slipbox/SKILL.md").decode("utf-8")
                    frontmatter = market_skill.split("---", 2)[1]
                    fields = dict(line.split(":", 1) for line in frontmatter.strip().splitlines())
                    for key in ("display_name", "display_name_en", "description_zh", "description_en"):
                        self.assertTrue(json.loads(fields[key].strip()))
                    self.assertEqual(json.loads(fields["version"].strip()), "0.1.0")
                    self.assertEqual(json.loads(fields["author"].strip()), "Slipbox contributors")
                    self.assertEqual(fields["name"].strip(), "slipbox")
                    self.assertEqual(generic_skill.split("---", 2)[2], market_skill.split("---", 2)[2])
                    self.assertNotIn("display_name:", generic_skill.split("---", 2)[1])

    def test_package_checksums_cover_exact_payload_and_external_checksums_cover_variants(self):
        archives = [self.build(language, target) for language in ("zh", "en") for target in ("generic", "workbuddy")]
        for archive in archives:
            with self.subTest(archive=archive.name), zipfile.ZipFile(archive) as bundle:
                sums = bundle.read("slipbox/PACKAGE_SHA256SUMS").decode("utf-8")
                entries = dict(line.split("  ", 1)[::-1] for line in sums.splitlines())
                self.assertEqual(set(entries), {name.removeprefix("slipbox/") for name in EXPECTED_FILES - {"slipbox/PACKAGE_SHA256SUMS"}})
                for name, checksum in entries.items():
                    self.assertEqual(checksum, hashlib.sha256(bundle.read("slipbox/" + name)).hexdigest())
        sums_path = self.base / "dist" / "SHA256SUMS"
        self.assertTrue(sums_path.is_file())
        sums = dict(line.split("  ", 1)[::-1] for line in sums_path.read_text(encoding="utf-8").splitlines())
        self.assertEqual(set(sums), {archive.name for archive in archives})
        for archive in archives:
            self.assertEqual(sums[archive.name], hashlib.sha256(archive.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
