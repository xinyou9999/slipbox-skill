# Changelog

## DSH plugin0.1.11 — 2026-11-09

- Expand the native workspace with measured responsive gutters, removing the fixed centered width limit.
- Move Writing activity to a full-width panel below the header; default to365days, with a12week switch and month/weekday guides.
- Enlarge date cells, retain keyboard/date-picker access and keep narrow-screen scrolling inside the calendar. Counting/privacy and portable Skill0.1.2 remain unchanged.

## Portable Skill0.1.2 / DSH plugin0.1.10 — 2026-11-08

- Add a local writing calendar with dated GitHub-style squares, zero-filled days, four intensity levels and keyboard navigation.
- Count existing cards by creation date in the library host timezone; editing and AI tagging do not inflate counts, deletion reduces them. No event tracking or schema migration.
- Select a date to filter notes without losing the draft; combine date, text, tag and pagination filters.
- Shared portable CLI exposes `activity --days 84` (1–366) and `list/search --created-on YYYY-MM-DD` for every compatible agent.

## Portable Skill 0.1.1 / DSH plugin 0.1.9 — 2026-11-07

- Remove the per-note three-tag restriction across the shared Markdown core, generic/WorkBuddy Skills and DSH. Canonical validation, deduplication and revision checks remain.
- Group tag selection, automatic AI tagging and save controls in one compact toolbar. AI privacy details remain accessible and expanded until acknowledged.
- Hide internal card IDs, align quiet edit/delete icons, retain native DSH dark appearance and lavender light mode.
- AI adds a bounded batch of relevant suggestions without capping or discarding existing manual tags. Portable Skills use their host agent for semantic tagging; DSH provides its native interface.

## DSH plugin 0.1.8 — 2026-11-07

- Replace the nested deletion box with a compact, quiet confirmation strip: concise heading, muted hint, aligned Cancel/Delete actions and responsive wrapping.
- Keep both themes and languages consistent; focus Cancel on opening and support Escape to cancel. Explicit confirmation and revision-checked deletion remain intact.
- Match DSH's native dark theme using its appearance service and color tokens; theme changes stay synchronized with the host. The approved light palette remains.
- GitHub and the custom Git index distribute this version. The community listing still uses npm0.1.5 until its source is updated; a GitHub release alone does not update that listing.

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
