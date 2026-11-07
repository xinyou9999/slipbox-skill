# slipbox for DeepSeek Harness

Native bundle with an installed plugin item, permanent **卡片笔记** navigation, real Markdown card UI and tagging through the host's configured default model. The Python standard-library core is shared with the portable Skill; no separate model credential is required.

Desktop layout: notes on the left, navigation on the right. On narrow screens navigation sits above the notes.

The page defaults to Chinese **卡片笔记** / **我的笔记**. Switch to **English** for **slipbox · Card Notes** / **My Notes**, or **简体中文** to return. Language preference persists while original notes, tags, draft, filters and theme remain intact. Package name remains `dsh-slipbox`.

For version0.1.8, add `https://xinyou9999.github.io/slipbox-skill/dsh/index.json` in DSH's experimental custom market, search **slipbox** and confirm installation. It installs a self-contained GitHub package pinned to a fixed commit; no npm account or installation build permission is needed. See the [step-by-step guide](../../docs/HARNESS_PLUGIN.md).

The homepage displays selected tags only. Search to add a tag on demand (up to8 matches); the separate **标签列表** page provides search,48-item pagination and explicit creation. Drafts survive view switches. Native light/dark UI was verified with371 tags, with500-tag interaction regressions.

Download the prebuilt archive from the [DSH plugin release](https://github.com/xinyou9999/slipbox-skill/releases/tag/dsh-v0.1.8). Build from the public repository root with `node scripts/package_harness_plugin.mjs`. Install the resulting local `.tgz` with `dsh plugin --profile desktop add <absolute-tgz-path> --ignore-scripts`. Select the profile you actually run, then fully quit and reopen Harness. See [installation and market discovery](../../docs/HARNESS_PLUGIN.md). GitHub publication does not register the plugin in a marketplace.

Plugin settings: `libraryPath` is the actual local library (default `SLIPBOX_HOME` or `~/.slipbox`); `pythonPath` is a Python 3.10+ executable accessible to the host. Using the same local library across agents requires the same accessible filesystem. Removing the plugin preserves the library.

Version0.1.8 saves notes locally first, then fills available tag slots in the background using the current DSH default model. Turn **自动 AI 标签** off to keep saving entirely local, or use the explicit **保存并用 AI 打标签** action. When enabled, this note and tag vocabulary are sent to the configured provider after saving; typing alone sends nothing. Existing tags are preserved, at most3 tags are stored, and stale AI results cannot overwrite later edits. Failures keep the note and offer a retry. No model tools, new conversation, separate credential or automatic content rewrite is involved.

Type `#标签` or select/create tags through **添加标签**. Existing aliases resolve to canonical names. Code blocks, inline code, URL fragments, Markdown headings and `C#` are not tags. Names containing spaces can be selected as chips. The **标签列表 → AI 整理标签库** action analyzes tag metadata only and presents descriptions, aliases and duplicate suggestions. Apply suggestions individually; merging requires a second confirmation. Automatic tagging can add at most one described new concept per note and fill empty descriptions, but never merges or deletes vocabulary.

Limits: up to800 vocabulary entries and96,000 input characters per AI request, two concurrent requests per library configuration, and a60-second deadline. Requests exceeding these limits leave the saved note intact. Get0.1.8 from the [GitHub release](https://github.com/xinyou9999/slipbox-skill/releases/tag/dsh-v0.1.8) or custom Git index; npm and the community npm catalog still provide0.1.5.

Version0.1.1 was validated on Windows Harness0.2.1-rc.3: installed item, persistent navigation, create/search/edit/tag controls, two themes and a real default-model tag-list/add/show cycle. Version0.1.2 adds complete Git distribution and corrects the diagnostic version, retaining the note behavior. Other operating systems and host versions remain untested. `plugins/dsh-slipbox` is development source; `packages/dsh-slipbox` is the self-contained Git distribution. The older0.1.1 archive remains available as a separate release.

In0.1.8, dark appearance uses the native DSH theme and tokens. The page switch stays synchronized with host appearance. A compact deletion strip supports Cancel/Escape and returns focus to the action icon.
