# Demo and asset provenance

The social day/night covers and CLI animation are original code-rendered graphics. They use slipbox's mineral-paper / blue-hour palette, system typography and simple card geometry. They do not reproduce a third-party product screenshot or claim generation by a specific image model.

`scripts/record_demo.py` executes the actual local CLI with a fresh temporary library and synthetic notes. It records complete JSON/Markdown output, preserving returned IDs and card contents. Temporary machine paths are replaced with `<temporary-library>`; no real personal notes are used. The animation is 48 seconds, six steps; longer output is visibly abridged on-screen and available in full in `assets/demo-transcript.json`.

The recording is a CLI walkthrough, not a host integration test. It does not claim semantic search or automatic cross-device sharing. Covers are 1280×640 PNGs with editable SVG counterparts, not a mock production interface.

To regenerate the recording without graphics:

```sh
python scripts/record_demo.py --output demo-output
```

Maintainer-only graphics regeneration uses `--render` and an available Pillow installation. Pillow is an optional authoring dependency, not a requirement of the CLI or installed Skill. Font files are resolved from the local system and are not distributed in the repository. Rendering may differ slightly with available fonts.

Original code and assets are distributed under the repository's MIT license. Any later imported work needs its own attribution and license check.

The cover wording was updated on 2026-10-26 using the approved [brand copy](brand-copy.md). Only cover typography changed; the existing real CLI transcript and demo recording were preserved.
