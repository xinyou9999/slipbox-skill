# slipbox for DeepSeek Harness

[简体中文](#中文安装与市场说明) · [Hermes installation request](HERMES_INSTALL_REQUEST.md)

The native plugin adds a permanent **卡片笔记** page, local Markdown cards, tags, search, editing, light/dark themes and background tagging through your existing host default model. It shares the portable Skill's storage format and requires no separate model key.

## New in0.1.7: automatic and manual tags

Save locally first, then let the DSH default model fill tag slots in the background. Manual `#标签` entry and search/create buttons share canonical tags and aliases, with at most3 tags per note. Turn **自动 AI 标签** off per library, or use **保存并用 AI 打标签** explicitly. When enabled, the saved note and vocabulary are sent to your configured provider; typing alone sends nothing. Failures preserve the note and offer retry, and stale responses cannot overwrite later edits.

Open **标签列表 → AI 整理标签库** for metadata-only descriptions, aliases and duplicate proposals. Changes require explicit application, with a second confirmation for merges. No automatic merging/deletion, body rewrite, model tools, new conversation or separate key. Calls are limited to800 vocabulary entries,96,000 input characters, two concurrent requests per library and60 seconds.

Download `dsh-slipbox-0.1.7.tgz` and `SHA256SUMS` from the [0.1.7 release](https://github.com/xinyou9999/slipbox-skill/releases/tag/dsh-v0.1.7), verify the checksum, then run `dsh plugin --profile desktop add <absolute-tgz-path> --ignore-scripts` and normally restart DSH. The custom Git index below also provides the version advertised in its live index; npm/mirror/community npm listing still provide0.1.5. Windows DSH0.2.1-rc.3 isolated upgrade and production-model interface were validated using a deterministic test adapter, and additional real configured-model calls on synthetic notes with371 synthetic tags. Individual suggestions still need review.

Version0.1.5 places the note editor and collection on the left, with compact navigation on the right. Narrow screens retain navigation above the notes. Both themes and languages share this layout.

Version0.1.4 defaults to Chinese: page title **卡片笔记**, navigation **我的笔记**. Use **English** in the header for the English view (**slipbox · Card Notes**, **My Notes**); use **简体中文** to return. The preference is remembered. Switching preserves drafts, selected tags, filters and themes, and never translates or rewrites your actual notes or tag names. The package identifier remains `dsh-slipbox`.

Version0.1.3 keeps the homepage card-first: it shows selected tags only, with an on-demand tag search capped at8 results. Open **标签列表** to search all tags, page through48 at a time or explicitly create a tag. Switching views preserves the current draft. This UI was checked in the native Windows app with371 tags;500-tag interaction regressions also cover the selection limit and avoiding accidental draft submission on Enter.

## Install from the DSH market (0.1.5)

Add this index URL to your actual DSH profile:

```text
https://xinyou9999.github.io/slipbox-skill/dsh/index.json
```

1. Open **插件**, open the menu beside **实验性插件**, and enable **自定义插件市场**.
2. Open **发现 → 添加索引源**, paste the URL above and save. Keep your existing sources.
3. Search **slipbox** or **卡片笔记**, open the result and choose **安装** (or **更新** when0.1.1 is already installed).
4. Check the confirmation: GitHub repository `xinyou9999/slipbox-skill`, fixed commit `a6da475d72feb6e0688e7c379c11f1458e598789`, directory `packages/dsh-slipbox`, version0.1.5. Confirm and follow any restart notice. Open **卡片笔记** in the sidebar afterward.

This self-contained package includes its Python core and needs no installation build script or separate model key. The market source is hosted on GitHub Pages and pins an immutable GitHub commit. Every other computer/profile must add the index once; it is not part of a universal built-in catalog. No npm account is needed.

## Install from npm or a mainland China mirror (0.1.5)

The complete native plugin is now published as [`dsh-slipbox@0.1.5`](https://www.npmjs.com/package/dsh-slipbox), with a verified [npmmirror copy](https://npmmirror.com/package/dsh-slipbox). The npm and mirror archives have identical SHA-256 and SHA-512 integrity values. Installing does not require an npm publishing account or two-factor authentication.

If you use the community [`@easytz/dsh-market`](https://github.com/EasyTZ/dsh-market) plugin, enable its **国内镜像** switch, search **dsh-slipbox**, and install version **0.1.5**. This market searches npm packages using `dsh-plugin` metadata; it is separate from DSH's built-in custom-index interface. No application to a universal official catalog has been made.

Search verification on2026-11-04: the mirror returns the exact package name, but the combined query `keywords:dsh-plugin dsh-slipbox` has not returned the package yet. Community-market discovery is therefore not fully verified; use the CLI command below or the Git index above if the result is absent. Registry indexing and query handling may differ.

For CLI installation on Windows desktop, use your existing Harness CLI:

```powershell
$env:npm_config_registry = 'https://registry.npmmirror.com'
dsh plugin --profile desktop add dsh-slipbox@0.1.5 --ignore-scripts
```

The registry variable applies to the current shell and its child processes. Use your actual profile on other platforms. Version0.1.5 was installed in an isolated Windows Harness0.2.1-rc.3 profile from this registry; all19 installed package files matched the published archive. Keep Python3.10+ available. Follow the host's restart notice after installation and open **卡片笔记** in the sidebar. The Git index above remains available as an alternative.

## Alternative: prebuilt plugin (0.1.1)

1. Download `dsh-slipbox-0.1.1.tgz` and `SHA256SUMS` from the [DSH plugin release](https://github.com/xinyou9999/slipbox-skill/releases/tag/dsh-v0.1.1). This is separate from portable Skill v0.1.0.
2. Verify the downloaded archive's SHA-256 against the checksum file (`Get-FileHash` on PowerShell or `sha256sum` on Linux). The archive includes executable plugin code: inspect its source before installing.
3. Run the command below with the actual absolute archive path. Use the profile your application actually runs; the Windows desktop app validated here uses `desktop`. If `dsh` is not in PATH, use the launcher shipped with your installation.

```sh
dsh plugin --profile desktop add /absolute/path/dsh-slipbox-0.1.1.tgz --ignore-scripts
```

4. Fully quit and reopen Harness. In **插件 → 已安装**, find **slipbox · 卡片笔记**. Open **卡片笔记** in the global sidebar.
5. Write a sample card, save, search and read it back. **交给默认 AI 整理** opens a host conversation; follow its result, then refresh the card page. Starting a conversation alone does not prove that a card was saved.

The host needs Python3.10+ (`python` by default, including the bundled runtime when available). Library defaults to the host process's `SLIPBOX_HOME` or `~/.slipbox`. The plugin schema exposes `libraryPath` and `pythonPath`; configuration uses Harness's normal plugin configuration mechanisms. Keep cards outside the installed package. Uninstalling the plugin should not remove your library.

This release was tested locally on **Windows / Harness0.2.1-rc.3**, including the visible plugin/page, native read/write/search/tags/theme controls and an actual default-model tag-list/add/show cycle. Declared compatibility is `>=0.2.1-rc.3 <0.3.0`; this range is not a claim that every version or OS was tested. Other host reports are welcome.

## Build from source

From the public repository root, with Node22+ and npm available:

```sh
node --test tests/test_harness_plugin.mjs
node scripts/package_harness_plugin.mjs
```

The command prints the current source version's archive path under ignored `.local-release/`. It copies a fixed set of plugin and core/Skill files, then runs `npm pack --ignore-scripts`; it does not publish to npm or install dependencies. `plugins/dsh-slipbox` contains development source; the public `packages/dsh-slipbox` directory is the self-contained Git distribution with its own `skill/` subtree. Market installation uses the latter at the fixed commit above.

## DSH market discovery

According to the [official market documentation](https://deepseek-harness.github.io/deepseek-harness/guide/plugin-market), DSH currently ships **no built-in index source**. Its experimental custom market reads JSON indexes selected by each profile. Publishing this GitHub repository or a Release does not make the plugin searchable on every DSH installation.

slipbox now supplies its own [HTTPS index](https://xinyou9999.github.io/slipbox-skill/dsh/index.json), including bilingual metadata, icon, exact0.1.5 version, engine range and the full package commit. Add it using the steps above. The documented schema accepts npm and Git sources; this index uses Git, not a fabricated tarball source type.

For wider discovery, maintainers of an existing community index may include this package at their discretion. There is no automatic universal listing. npm and npmmirror distribution are available; no third-party curated-index submission has been made. See the [official bundle installation guide](https://deepseek-harness.github.io/deepseek-harness/develop/basic/publish).

## 中文安装与市场说明

这是真正的 DSH 原生插件：插件管理可见、左侧常驻“卡片笔记”、点击进入本地 Markdown 卡片页面，AI 操作调用宿主已配置的默认模型。

从上方插件发布页下载 `.tgz` 与校验和，核对后执行安装命令，再完全退出并重新打开应用。Windows 桌面版使用 `desktop` profile；其他环境要选择自己实际运行的 profile。可先保存一张“安装验证”卡片，再搜索读回。

**当前版本0.1.5已发布到npm，并已同步国内npmmirror镜像。** 如果使用社区 `@easytz/dsh-market`，打开“国内镜像”后搜索 **dsh-slipbox** 安装；普通用户不用注册npm，也不用配置发布者的两步验证。DSH自带的“发现”界面则仍需添加上方GitHub索引；两种市场入口不同，不能保证所有DSH默认都能搜到。

2026-11-04实测：镜像直接搜索包名已有结果，但社区市场常用的“插件关键词＋包名”组合查询暂未返回此包。因此市场内搜索尚未完整验证；搜不到时使用上面的CLI命令或现有GitHub索引安装。

中文版显示“卡片笔记”和“我的笔记”，默认中文；右上角可切换English并记住选择。笔记在左，导航在右；窄屏导航在上方。首页不再铺开全部标签；进入“标签列表”后搜索、分页查看或新建，编辑卡片时按需搜索添加，最多三个。已有用户可在对应来源选择更新。

Hermes 使用通用 Skill，而不是这个 DSH `.tgz`。把[安装请求](HERMES_INSTALL_REQUEST.md)整段发给实际运行的 Hermes，安装后用 `/slipbox` 记卡片、检索和回顾。

不同智能体复用要求能访问同一个实际资料库，或手动迁移 Markdown 与 `tags.json` 后重建索引。本插件不包含自动跨设备同步。AI 可能将卡片交给宿主配置的模型服务，请使用适合资料隐私要求的宿主设置。
