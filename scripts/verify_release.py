#!/usr/bin/env python3
"""Validate product metadata, local links and release-bundle checksums offline."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def module_at(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_metadata(root: Path) -> list[str]:
    errors = []
    data = json.loads((root / "docs/capabilities.json").read_text(encoding="utf-8"))
    packager = module_at("slipbox_release_packager", root / "scripts/package_skill.py")
    core = module_at("slipbox_release_core", root / "scripts/slipbox.py")
    if data.get("version") != packager.VERSION:
        errors.append("capability version differs from bundle version")
    commands = next(a.choices for a in core.parser()._actions if isinstance(a, argparse._SubParsersAction))
    if set(data.get("commands", {})) != set(commands):
        errors.append("capability commands differ from CLI")
    if data.get("python_requires") != ">=3.10" or data.get("runtime_dependencies") != []:
        errors.append("runtime requirements differ from supported product")
    if data.get("calls_model_api") is not False or data.get("cross_device_sync") is not False:
        errors.append("capabilities overstate networking or synchronization")
    if data.get("search") != "literal_substring_and_tag" or data.get("maximum_tags_per_card") != 3:
        errors.append("capabilities differ from search/tag contract")
    expected_hosts = {"Codex", "Hermes", "OpenClaw", "WorkBuddy", "DeepSeek harness"}
    hosts = data.get("hosts", [])
    if len(hosts) != len(expected_hosts) or {h.get("name") for h in hosts} != expected_hosts:
        errors.append("host manifest differs from release scope")
    for h in hosts:
        status = "experimental_untested" if h["name"] == "DeepSeek harness" else "documented_untested"
        if h.get("status") != status:
            errors.append(f"host evidence requires review: {h['name']}")
    paths = [data.get("entrypoint", ""), *data.get("instructions", {}).values(), *data.get("documentation", [])]
    for value in paths:
        p = PurePosixPath(value)
        if not value or p.is_absolute() or ".." in p.parts or not (root / value).is_file():
            errors.append(f"missing or unsafe capability reference: {value}")
    return errors


def validate_links(root: Path) -> list[str]:
    errors = []
    # Only product-facing entrypoints, not private development plans.
    paths = [root / n for n in ("README.md", "README.zh-CN.md", "README.en.md", "CONTRIBUTING.md", "SECURITY.md", "ROADMAP.md", "llms.txt")]
    paths.extend((root / "docs").glob("*.md"))
    for path in paths:
        if not path.is_file():
            continue
        for value in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value) or value.startswith("#"):
                continue
            local = value.split("#", 1)[0].split("?", 1)[0].strip("<>")
            if local and not (path.parent / local).is_file() and not (path.parent / local).is_dir():
                errors.append(f"broken local link in {path.relative_to(root)}: {value}")
        for value in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', path.read_text(encoding="utf-8")):
            if "://" not in value and not (path.parent / value).is_file():
                errors.append(f"missing image in {path.relative_to(root)}: {value}")
    return errors


def validate_archive(path: Path) -> list[str]:
    errors = []
    with zipfile.ZipFile(path) as bundle:
        names = bundle.namelist()
        if len(set(names)) != len(names):
            errors.append(f"{path.name}: duplicate entries")
        if any(not n.startswith("slipbox/") or ".." in PurePosixPath(n).parts or "\\" in n for n in names):
            errors.append(f"{path.name}: unsafe entry")
        checksum_name = "slipbox/PACKAGE_SHA256SUMS"
        if checksum_name not in names:
            return errors + [f"{path.name}: missing package checksums"]
        rows = bundle.read(checksum_name).decode("ascii").splitlines()
        seen = set()
        for row in rows:
            digest, name = row.split("  ", 1)
            # PACKAGE_SHA256SUMS names are relative to the installed skill root.
            archive_name = name if name.startswith("slipbox/") else "slipbox/" + name
            if archive_name in seen or archive_name not in names or hashlib.sha256(bundle.read(archive_name)).hexdigest() != digest:
                errors.append(f"{path.name}: invalid checksum for {name}")
            seen.add(archive_name)
        if seen != set(names) - {checksum_name}:
            errors.append(f"{path.name}: incomplete checksum coverage")
    return errors


def validate_dist(directory: Path) -> list[str]:
    errors = []
    archives = sorted(directory.glob("*.zip"))
    for path in archives:
        errors.extend(validate_archive(path))
    if archives:
        checksum_file = directory / "SHA256SUMS"
        if not checksum_file.is_file():
            return errors + ["dist is missing SHA256SUMS"]
        expected = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in archives}
        observed = {}
        for row in checksum_file.read_text(encoding="ascii").splitlines():
            digest, name = row.split("  ", 1)
            if name in observed:
                errors.append("dist checksum lists a file twice")
            observed[name] = digest
        if observed != expected:
            errors.append("dist checksums do not match the generated ZIPs")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        errors = validate_metadata(ROOT) + validate_links(ROOT) + validate_dist(args.dist)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        errors = [str(error)]
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Release metadata, local links and available bundle checksums: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
