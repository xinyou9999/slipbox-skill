# 安装 Slipbox / Install Slipbox

首批目标为 **Codex、Hermes、OpenClaw、WorkBuddy**；DeepSeek harness 为实验性接入。要求运行环境具备 Python 3.10+、命令执行能力，以及资料库读写权限。无需安装 Python 依赖，也不要求配置模型 API Key。宿主使用什么模型，由宿主配置决定。

也可以把[安装请求](AI_INSTALL.md)复制给可信 AI 助手；[机器可读能力](capabilities.json)提供命令和验证级别索引。You can give the [installation request](AI_INSTALL.md) to your trusted assistant.

## 兼容状态 / Compatibility

截至 2026-10-25，下表中的安装路径根据官方文档整理；**本次没有进行任何宿主的加载、模型调用或端到端实机测试**。构建检查、CLI 测试与宿主兼容认证是不同的证据。

| 宿主 / Host | 安装入口 / Installation | 状态 / Status |
|---|---|---|
| Codex | 将解压所得 `slipbox/` 放入 `~/.agents/skills/`，或项目的 `.agents/skills/` | 文档核查；未实机验证 / documented, untested |
| Hermes | 放入当前 profile 的 `$HERMES_HOME/skills/`；默认通常是 `~/.hermes/skills/` | 文档核查；未实机验证 / documented, untested |
| OpenClaw | 放入 `~/.openclaw/skills/`，或活动工作区的 `skills/` | 文档核查；未实机验证 / documented, untested |
| WorkBuddy | 技能 → 添加技能 → 上传技能，选择 WorkBuddy ZIP | 文档核查；未实机验证 / documented, untested |
| DeepSeek harness | 放入项目的 `.dsh/skills/`，或有效 `dshHome` 下的 `skills/` | 实验性；未实机验证 / experimental, untested |

Claude Code 不属于本轮适配、说明或验收目标。这里的“多智能体”指不同宿主可以使用同一资料库，不包含团队权限系统或多设备自动同步。

## 获取安装包 / Get a bundle

从维护者实际发布的版本附件获取 ZIP；若没有版本附件，在仓库根目录构建：

```sh
python scripts/package_skill.py --language zh
python scripts/package_skill.py --language en
python scripts/package_skill.py --language zh --target workbuddy
```

构建器会打印输出文件路径；`dist/` 下的 `generic` 包用于 Codex、Hermes、OpenClaw 和实验性 DeepSeek harness。WorkBuddy 请使用带 `workbuddy` 的包。英文包将 `SKILL.en.md` 映射成安装态的 `SKILL.md`。

ZIP 只包含 `slipbox/` 下的技能指令、核心脚本、规则、模板、许可证和安装/快速开始文档。不要将完整开发仓库当作安装包复制，也不要只复制 `SKILL.md`：它引用的脚本和规则同样必需。

构建器同时生成 `dist/SHA256SUMS`，每个包内的 `PACKAGE_SHA256SUMS` 覆盖安装文件。下载后将 ZIP 的 SHA-256 与发布清单对比；校验和验证内容一致性，不单独证明下载来源可信。源码维护者可运行 `python scripts/verify_release.py` 检查元数据和已构建包。

Build the bundles from the repository if release assets are not available. Use the `generic` archive for directory installs and the `workbuddy` archive for WorkBuddy upload. Extract once: the final layout must be `<skills-root>/slipbox/SKILL.md`, never `<skills-root>/slipbox/slipbox/SKILL.md`. The English bundle already installs the English entrypoint as `SKILL.md`.

## 各宿主步骤 / Host steps

### Codex

将通用包中的 `slipbox/` 放到 `~/.agents/skills/`（用户级），或 `<project>/.agents/skills/`（项目级）。在对话中使用 `$slipbox`，或明确要求使用 Slipbox 记卡片。新安装未出现时重启 Codex。执行脚本时仍受当前会话权限限制。

Extract the generic bundle into the user or project `.agents/skills` directory, then invoke `$slipbox`. Restart if discovery does not update. See [official skill documentation](https://developers.openai.com/codex/skills).

### Hermes

先解析当前 profile 的实际 `HERMES_HOME`，将 `slipbox/` 放进其 `skills/`。未设置时通常是 `~/.hermes/skills/slipbox/`。开启新会话，请它使用 Slipbox；执行环境若为容器或远程终端，需要在那个环境中提供 Python 和资料库路径。

Place the generic bundle under the active profile's skills directory and start a new session. Do not assume every profile shares the default home. See [official skills documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/).

### OpenClaw

将通用包的 `slipbox/` 放进共享 `~/.openclaw/skills/` 或活动工作区 `skills/`。也可按当前版本官方说明安装本地技能目录。指令中的 `{baseDir}` 是宿主提供的技能根目录。若沙箱执行脚本，Python、技能目录和资料库都必须在沙箱内可访问。新开会话并检查技能是否可见；不要为解决不可见问题直接关闭安全策略。

Use the shared or active workspace skill root. Ensure both the installed script and library are available in the actual execution sandbox. See [official skill documentation](https://docs.openclaw.ai/tools/skills).

### WorkBuddy

选择 WorkBuddy 包，进入“技能 → 添加技能 → 上传技能”，上传完整 ZIP。导入后在已安装列表确认 Slipbox 已启用，开启对话要求使用它。请检查当前执行环境能运行 Python 并持久保存文件。此处是用户导入路径，**不表示 Slipbox 已上架 WorkBuddy/SkillHub 市场或通过平台审核**。

Import the WorkBuddy ZIP through Skills → Add skill → Upload skill, enable it, and ask WorkBuddy to use it. The variant supplies platform display metadata while retaining the same core script. See [official upload instructions](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) and [package format](https://open.workbuddy.cn/docs/skill).

### DeepSeek harness（实验性 / experimental）

将通用包的 `slipbox/` 放入 `<project>/.dsh/skills/`，或当前配置的 `<dshHome>/skills/`。部分版本也发现 `.agents/skills/`，不要为了兼容性同时安装同名副本。需要启用文件系统 skill provider、skill registry 和模型侧 skill loader，并允许命令执行与私有文件读写。若分发版不暴露这些能力，本轮不声明可用。加载后可尝试 `/slipbox`；未出现时检查当前版本的发现根目录和插件配置。

The official filesystem provider supports directory bundles, but a specific desktop/CLI distribution may configure discovery and tools differently. Install under a configured root; ensure the registry, filesystem provider and skill tool are enabled. This is an experimental installation route, not a tested product integration. Sources: [filesystem provider](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md), [skill loader](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/tool-skill/README.md).

## 共用资料库 / Share one local library

默认资料库是执行环境中的 `~/.slipbox`，不是技能目录。多个宿主指向**同一台机器、同一文件系统上的同一绝对路径**即可共用；不同系统账户、容器、WSL 或远程主机的 `~` 并不相同。

在每个宿主实际启动进程的环境中设置相同的 `SLIPBOX_HOME`，再启动或重载宿主。只在某个终端设置变量，不会自动改变已运行的图形应用。路径请替换为自己的私有目录。

```powershell
# PowerShell：仅影响当前终端及其后续启动的子进程
$env:SLIPBOX_HOME = Join-Path $HOME 'Documents/slipbox-library'
```

```sh
# POSIX shell：从该终端启动各宿主
export SLIPBOX_HOME="$HOME/slipbox-library"
```

现有内核锁会串行化本地写入，但不提供协作编辑版本检测。两个 Agent 根据旧内容编辑同一卡片，仍可能发生后写覆盖；让一个 Agent 负责该卡片的修改，修改前重新读取。不要依赖网络盘/云盘同步来提供分布式锁或多设备冲突解决。笔记内容会成为宿主模型的输入；CLI 不自行联网，不代表宿主不会把内容发送给其模型服务。

Each host must receive the same absolute `SLIPBOX_HOME` in its actual execution environment. Local locks serialize mutations; they do not detect stale edits or coordinate different machines. Keep one writer per card, re-read before edits, and check the host's model/privacy settings before sharing sensitive notes.

## 更新、卸载与反馈 / Updates, removal and reports

更新前备份资料库；记录所用安装包及其 SHA-256。保留上一版包，在关闭相关 Agent 后替换技能目录；不要覆盖自定义规则。更换技能不会迁移笔记格式。升级若声明格式变化，先按对应迁移说明执行。回退脚本前确认该版本支持当前资料格式。

卸载仅移除宿主安装的技能目录，**保留资料库**。反馈请提供宿主与版本、系统、Python 版本、安装包名称、脱敏错误，以及能否完成快速开始。不要上传真实卡片、密钥或整个资料库。

Updates replace the installed skill, not the external library. Back up data and retain the previous bundle. Removal should preserve notes. Report host/version, OS, Python version, bundle and a redacted error; never upload private notes or credentials.
