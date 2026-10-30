# slipbox for DeepSeek Harness

[简体中文](#中文安装与市场说明) · [Hermes installation request](HERMES_INSTALL_REQUEST.md)

The native plugin adds a permanent **卡片笔记** page, local Markdown cards, tags, search, editing, light/dark themes and an AI action that starts a conversation with your existing host default model. It shares the portable Skill's storage format and requires no separate model key.

## Install from the DSH market (0.1.2)

Add this index URL to your actual DSH profile:

```text
https://xinyou9999.github.io/slipbox-skill/dsh/index.json
```

1. Open **插件**, open the menu beside **实验性插件**, and enable **自定义插件市场**.
2. Open **发现 → 添加索引源**, paste the URL above and save. Keep your existing sources.
3. Search **slipbox** or **卡片笔记**, open the result and choose **安装** (or **更新** when0.1.1 is already installed).
4. Check the confirmation: GitHub repository `xinyou9999/slipbox-skill`, fixed commit `a4a5cd05a53cc859e9ec5008bf93890957969839`, directory `packages/dsh-slipbox`, version0.1.2. Confirm and follow any restart notice. Open **卡片笔记** in the sidebar afterward.

This self-contained package includes its Python core and needs no installation build script or separate model key. The market source is hosted on GitHub Pages and pins an immutable GitHub commit. Every other computer/profile must add the index once; it is not part of a universal built-in catalog. No npm account is needed.

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

slipbox now supplies its own [HTTPS index](https://xinyou9999.github.io/slipbox-skill/dsh/index.json), including bilingual metadata, icon, exact0.1.2 version, engine range and the full package commit. Add it using the steps above. The documented schema accepts npm and Git sources; this index uses Git, not a fabricated tarball source type.

For wider discovery, maintainers of an existing community index may include this package at their discretion. There is no automatic universal listing. No npm publication or third-party listing has been made. See the [official bundle installation guide](https://deepseek-harness.github.io/deepseek-harness/develop/basic/publish).

## 中文安装与市场说明

这是真正的 DSH 原生插件：插件管理可见、左侧常驻“卡片笔记”、点击进入本地 Markdown 卡片页面，AI 操作调用宿主已配置的默认模型。

从上方插件发布页下载 `.tgz` 与校验和，核对后执行安装命令，再完全退出并重新打开应用。Windows 桌面版使用 `desktop` profile；其他环境要选择自己实际运行的 profile。可先保存一张“安装验证”卡片，再搜索读回。

**现在可以添加上方索引，搜索 slipbox 后安装0.1.2。** 插件和索引都托管在 GitHub，不需要 npm 账号。每台电脑在实际使用的 profile 添加一次索引；有旧版时选择更新。更广泛传播仍需要用户添加此源或已有社区索引收录，不代表所有 DSH 默认都能搜到。

Hermes 使用通用 Skill，而不是这个 DSH `.tgz`。把[安装请求](HERMES_INSTALL_REQUEST.md)整段发给实际运行的 Hermes，安装后用 `/slipbox` 记卡片、检索和回顾。

不同智能体复用要求能访问同一个实际资料库，或手动迁移 Markdown 与 `tags.json` 后重建索引。本插件不包含自动跨设备同步。AI 可能将卡片交给宿主配置的模型服务，请使用适合资料隐私要求的宿主设置。
