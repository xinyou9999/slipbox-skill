# Changelog

## DSH plugin 0.1.7 — 2026-11-07

- Save notes locally first, then fill tag slots with the configured DSH default model; per-library opt-out and failure retry.
- Add tags with inline `#` completion or compact search/create buttons; manual choices take priority, up to3 canonical tags.
- Review AI proposals for tag descriptions, aliases and duplicates; merges require explicit confirmation.
- Use familiar pencil/trash icons for editing and confirmed deletion; refuse deletion if the note changed meanwhile.
- Detect a stale host backend, show safe failure reasons and empty tag results, and repair invalid structured output once within the same deadline.
- Reject stale AI results, bound model calls, and atomically recover failed vocabulary/card updates. AI never rewrites note bodies or receives executable tools.
- Verified on Windows DSH0.2.1-rc.3 with isolated upgrades, a deterministic host adapter and the configured DeepSeek model on synthetic notes with371 synthetic tags. Other operating systems remain unverified; suggestions still need user judgment.

Available through the GitHub release and custom Git index.0.1.6 was a local development candidate. npm and the community npm catalog remain0.1.5 until publisher privacy is resolved.

## 0.1.0 — 2026-10-26

- Capture, retrieve, revise and review Markdown cards using a standard-library Python CLI.
- Govern tags with canonical names, aliases and explicit creation.
- Build generic and WorkBuddy bundles with Chinese/English instructions.
- Add a real synthetic-note CLI demonstration and an AI-guided installation request.
- Document host integration routes and machine-readable capabilities without claiming untested compatibility.

Published as the [initial release](https://github.com/xinyou9999/slipbox-skill/releases/tag/v0.1.0), with Chinese and English generic/WorkBuddy bundles. Host end-to-end tests have not been performed; DeepSeek harness remains experimental. Verification and the exact source revision are recorded with the release.
