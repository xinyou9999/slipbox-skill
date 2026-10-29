# slipbox for DeepSeek Harness

[简体中文](#中文安装与市场说明) · [Hermes installation request](HERMES_INSTALL_REQUEST.md)

The native plugin adds a permanent **卡片笔记** page, local Markdown cards, tags, search, editing, light/dark themes and an AI action that starts a conversation with your existing host default model. It shares the portable Skill's storage format and requires no separate model key.

## Install the prebuilt plugin

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

The command prints the archive path under ignored `.local-release/`. It copies a fixed set of plugin and core/Skill files, then runs `npm pack --ignore-scripts`; it does not publish to npm or install dependencies. The unbundled `plugins/dsh-slipbox` source directory is not a standalone Git-installable package: the packager supplies its `skill/` subtree. Use the prebuilt archive for installation.

## DSH market discovery

According to the [official market documentation](https://deepseek-harness.github.io/deepseek-harness/guide/plugin-market), DSH currently ships **no built-in index source**. Its experimental custom market reads JSON indexes selected by each profile. Publishing this GitHub repository or a Release does not make the plugin searchable on every DSH installation.

To distribute through the market:

1. Provide an installable **npm package** containing the prebuilt files, or a **self-contained Git package** pinned to a full commit SHA. This repository's current source subdirectory is not the latter; the release `.tgz` is the ready-to-install artifact.
2. Publish a UTF-8 JSON index (`format: 1`) over HTTPS, returning 2xx without redirects. Include `dsh-slipbox`, bilingual title/description, icon, author, exact version, Unix publication timestamp, matching `engines.dsh` and an actual npm or Git source. The documented index schema does not accept a tarball source type; do not put a Release URL into a fabricated source type.
3. Users open **插件 → 实验性插件 → 自定义插件市场**, enable it, then open **发现 → 添加索引源** and paste the index URL. They can then search **slipbox** and confirm installation.
4. For wider discovery, ask maintainers of an existing trusted community index to include the package. Their review/acceptance is independent; there is no documented universal approval step that makes all DSH users see it automatically.

No npm publication, market index or third-party listing has been made by this GitHub release. See the [official bundle installation guide](https://deepseek-harness.github.io/deepseek-harness/develop/basic/publish) for the supported packaging paths.

## 中文安装与市场说明

这是真正的 DSH 原生插件：插件管理可见、左侧常驻“卡片笔记”、点击进入本地 Markdown 卡片页面，AI 操作调用宿主已配置的默认模型。

从上方插件发布页下载 `.tgz` 与校验和，核对后执行安装命令，再完全退出并重新打开应用。Windows 桌面版使用 `desktop` profile；其他环境要选择自己实际运行的 profile。可先保存一张“安装验证”卡片，再搜索读回。

**GitHub 公开不等于插件市场自动上架。** DSH 当前通过用户自行添加的市场索引发现插件。下一步可发布预构建 npm 包，再把其版本和元数据加入 HTTPS 市场索引；其他电脑添加该索引后才能搜索安装。更广泛传播需要已有社区索引收录。这一版先提供可直接下载的安装包，尚未发布市场索引。

Hermes 使用通用 Skill，而不是这个 DSH `.tgz`。把[安装请求](HERMES_INSTALL_REQUEST.md)整段发给实际运行的 Hermes，安装后用 `/slipbox` 记卡片、检索和回顾。

不同智能体复用要求能访问同一个实际资料库，或手动迁移 Markdown 与 `tags.json` 后重建索引。本插件不包含自动跨设备同步。AI 可能将卡片交给宿主配置的模型服务，请使用适合资料隐私要求的宿主设置。
