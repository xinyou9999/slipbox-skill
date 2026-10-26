<p align="center"><img src="assets/social-day.png" alt="slipbox — Make fleeting thoughts useful again." width="960"></p>

# slipbox

**Make fleeting thoughts useful again.**

An open-source card-note Skill for your AI agents. Capture one useful thought, keep tags consistent, and ask your agent to find it when you need it. Your notes stay in Markdown files you control.

[简体中文](README.zh-CN.md) · [Install](docs/INSTALL.md) · [Three-minute start](docs/QUICKSTART.md) · [Give this to your AI](docs/AI_INSTALL.md)

![Local CLI demo: capture, retrieve, review, inspect Markdown](assets/cli-demo.gif)

*A real local CLI walkthrough using synthetic notes. This is not a recording of a host integration.* [Full transcript](assets/demo-transcript.json) · [Static version](assets/demo-static.png)

## From a passing thought to a reusable card

You read an idea, save it somewhere, then forget where it went. slipbox gives your agent a small, explicit workflow: **capture → reuse tags → retrieve → review**.

> “Save this idea: the best meeting note ends with a decision.”
>
> “Find my cards about decisions before I plan the next meeting.”
>
> “Review the cards I updated this week and show their IDs.”

The agent chooses semantic tags from the existing vocabulary. The CLI validates tags, writes Markdown and searches literal text. Review shows recently updated cards; summaries and interpretation come from your host's model. [How the demo was made](docs/asset-provenance.md)

## Why slipbox?

- **Small cards, ready to reuse.** Keep the user's wording and retrieve a specific thought by text or tag.
- **Tags that stay useful.** Canonical names, aliases and at most three tags per card. Unknown tags are explicit choices, not silently growing clutter.
- **Your files, your agents.** One local library can be used by different hosts. Python 3.10+, no third-party runtime dependencies, no built-in model API or account.

Switch agents without starting your notebook over. Set the same absolute `SLIPBOX_HOME` in each host's execution environment: sharing means the **same accessible local directory**, not automatic cloud sync. The host may send notes to its configured model; inspect its privacy settings.

## Start here

1. Download a ZIP from an **actually published release**, or [build one from source](#build-and-check).
2. Follow the [installation guide](docs/INSTALL.md) for your host.
3. Try the [isolated quick start](docs/QUICKSTART.md), then ask your agent to save and retrieve one card.

**Working with an AI assistant?** Paste the [installation request](docs/AI_INSTALL.md). It tells the assistant how to identify its host and environment, find the script, and verify a synthetic note without overwriting existing data.

## Host status

| Host | Path provided | Evidence |
|---|---|---|
| Codex | User/project Skill directory | Documented; host untested |
| Hermes | Active profile Skill directory | Documented; host untested |
| OpenClaw | Shared/workspace Skill directory | Documented; host untested |
| WorkBuddy | Upload the WorkBuddy ZIP | Documented; host untested |
| DeepSeek harness | Configured filesystem Skill root | Experimental; host untested |

Package execution checks do not certify host integrations. Help turn a documented path into a tested one: [report your host/version and walkthrough](CONTRIBUTING.md).

## What it does today

Capture, list, search, show, edit, delete and review Markdown cards; inspect/add/merge tags; rebuild the search index. Semantic reasoning belongs to the host agent. The CLI currently uses literal substring search, not embedding or semantic search.

Cards and `tags.json` are authoritative. SQLite is a disposable index. Local writes are serialized, but stale edits still need care: re-read before editing and keep one writer per card. No built-in cross-device sync, multi-user permissions, attachments or graphical note editor.

## Build and check

```sh
python -m unittest discover -s tests -v
python scripts/verify_release.py
python scripts/package_skill.py --language en
python scripts/package_skill.py --language zh
python scripts/package_skill.py --target workbuddy --language en
python scripts/package_skill.py --target workbuddy --language zh
```

Bundles are written under `dist/`. Use `python3` on systems where that is the Python 3 command. Never keep personal notes in the installed Skill directory. [Commands and safety boundaries](SKILL.en.md) · [Machine-readable capabilities](docs/capabilities.json)

## Help shape the next version

Start with a host installation report, a small bug reproduction, a documentation improvement or a useful card workflow. [Contribute](CONTRIBUTING.md) · [Roadmap](ROADMAP.md) · [FAQ](docs/FAQ.md) · [Security](SECURITY.md)

If this solves a problem for you, a Star helps others find it. An installation report or a concrete example helps us improve it.

MIT licensed. [License](LICENSE) · [Release notes](CHANGELOG.md)
