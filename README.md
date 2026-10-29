<p align="center"><img src="assets/social-day.png" alt="slipbox — Organize card notes with AI. Build your collection over time. Reuse it across agents." width="960"></p>

# slipbox | AI-powered card notes across agents

**Organize card notes with AI. Build your collection over time. Reuse it across agents.**

slipbox is an AI-powered card note tool that works across agents. Use AI to capture, organize, and retrieve your notes, and keep reusing the same collection across platforms.

[Website & interactive demo](https://xinyou9999.github.io/slipbox-skill/) · [简体中文](README.zh-CN.md) · [Install](docs/INSTALL.md) · [Three-minute start](docs/QUICKSTART.md) · [Give this to your AI](docs/AI_INSTALL.md)

The website offers a bilingual, light/dark product tour with an in-memory demo. It does not connect to your real notes or call a model.

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

1. Download a ZIP from [v0.1.0](https://github.com/xinyou9999/slipbox-skill/releases/tag/v0.1.0), or [build one from source](#build-and-check).
2. Follow the [installation guide](docs/INSTALL.md) for your host.
3. Try the [isolated quick start](docs/QUICKSTART.md), then ask your agent to save and retrieve one card.

**Working with an AI assistant?** Paste the [installation request](docs/AI_INSTALL.md). It tells the assistant how to identify its host and environment, find the script, and verify a synthetic note without overwriting existing data.

| Bundle | English | 简体中文 |
|---|---|---|
| Codex / Hermes / OpenClaw (generic) | [Download ZIP](https://github.com/xinyou9999/slipbox-skill/releases/download/v0.1.0/slipbox-0.1.0-generic-en.zip) | [下载 ZIP](https://github.com/xinyou9999/slipbox-skill/releases/download/v0.1.0/slipbox-0.1.0-generic-zh.zip) |
| WorkBuddy | [Download ZIP](https://github.com/xinyou9999/slipbox-skill/releases/download/v0.1.0/slipbox-0.1.0-workbuddy-en.zip) | [下载 ZIP](https://github.com/xinyou9999/slipbox-skill/releases/download/v0.1.0/slipbox-0.1.0-workbuddy-zh.zip) |

[SHA-256 checksums](https://github.com/xinyou9999/slipbox-skill/releases/download/v0.1.0/SHA256SUMS). Install through your host; this is a Skill, not a hosted note editor. Host evidence is listed below.

## Host status

**DeepSeek Harness native plugin is now available:** [installation and market guide](docs/HARNESS_PLUGIN.md) · [download prebuilt0.1.1](https://github.com/xinyou9999/slipbox-skill/releases/tag/dsh-v0.1.1). It adds a real card-note page and uses the host default model. **Hermes:** [copy this installation request to your running agent](docs/HERMES_INSTALL_REQUEST.md).

| Host | Path provided | Evidence |
|---|---|---|
| Codex | User/project Skill directory | Documented; host untested |
| Hermes | Active profile Skill directory | Documented; host untested |
| OpenClaw | Shared/workspace Skill directory | Documented; host untested |
| WorkBuddy | Upload the WorkBuddy ZIP | Documented; host untested |
| DeepSeek Harness | Native bundle0.1.1; portable Skill also available | Windows0.2.1-rc.3 native page and default-model flow tested locally; other versions/OS untested |

Package execution checks do not certify host integrations. Help turn a documented path into a tested one: [report your host/version and walkthrough](CONTRIBUTING.md).

## What it does today

Capture, list, search, show, edit, delete and review Markdown cards; inspect/add/merge tags; rebuild the search index. Semantic reasoning belongs to the host agent. The CLI currently uses literal substring search, not embedding or semantic search.

Cards and `tags.json` are authoritative. SQLite is a disposable index. Local writes are serialized, but stale edits still need care: re-read before editing and keep one writer per card. The native DSH plugin provides a graphical editor; the portable Skill uses the host agent. No built-in cross-device sync, multi-user permissions or attachments.

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
