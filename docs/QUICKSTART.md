# 三分钟体验 / Three-minute quick start

这条路径无需 Agent 或模型 API，可以检查安装包是否完整。要求 Python 3.10+；Windows 通常使用 `python`，macOS/Linux 如只有 `python3` 则替换命令名。在临时演示库中操作，避免修改现有笔记。

This walkthrough runs without an Agent or API key. Use Python 3.10+, replace `python` with `python3` if needed, and keep the demo separate from real notes.

## Windows / PowerShell

先按 [安装说明](INSTALL.md) 解压包，将下方技能路径替换为自己实际的安装路径。`$demoLibrary` 自动创建新的临时目录。变量的设置仅影响当前终端。

```powershell
$scriptPath = (Resolve-Path "$HOME/.agents/skills/slipbox/scripts/slipbox.py").Path
$demoLibrary = Join-Path ([System.IO.Path]::GetTempPath()) ('slipbox-demo-' + [guid]::NewGuid().ToString('N'))
$env:SLIPBOX_HOME = $demoLibrary
python $scriptPath init --json
python $scriptPath tag-add learning --alias 学习 --description 'Learning notes' --json
python $scriptPath add 'A small reusable idea: write one thought per card.' --tag learning --json
python $scriptPath search reusable --tag learning --json
python $scriptPath review --days 7 --json
Get-ChildItem -LiteralPath (Join-Path $demoLibrary 'cards')
```

## macOS / Linux / POSIX shell

Adjust `SCRIPT` to the installed location. The subshell keeps the demo environment from changing your normal library setting.

```sh
(
  SCRIPT="$HOME/.agents/skills/slipbox/scripts/slipbox.py"
  export SLIPBOX_HOME="$(mktemp -d)/library"
  python3 "$SCRIPT" init --json
  python3 "$SCRIPT" tag-add learning --alias 学习 --description 'Learning notes' --json
  python3 "$SCRIPT" add 'A small reusable idea: write one thought per card.' --tag learning --json
  python3 "$SCRIPT" search reusable --tag learning --json
  python3 "$SCRIPT" review --days 7 --json
  ls "$SLIPBOX_HOME/cards"
)
```

## 看到了什么 / What to expect

`add` 返回稳定卡片 ID，`search` 应返回刚才那张卡。`cards/` 中可直接打开 Markdown 文件，标签库保存在 `tags.json`，SQLite 是可重建检索缓存。终端输出 JSON 不等于某个 Agent 已经验证兼容。

`add` returns a stable card ID; search should find it. Open the Markdown file in `cards/` to inspect your own data. `tags.json` governs tags; SQLite can be rebuilt. Running this CLI walkthrough does not certify a host integration.

## 然后交给 Agent / Continue with an Agent

关闭演示终端，或恢复之前的 `SLIPBOX_HOME`；按安装说明为宿主设置正式资料库。在宿主中说：

> 使用 Slipbox，先查看现有标签，把“每张卡片只记录一个可复用想法”保存为卡片。优先复用标签；如果没有合适标签，先提出建议。再检索刚保存的内容，展示卡片 ID。

> Use Slipbox to inspect existing tags, capture “One reusable idea per card”, then retrieve it and show its stable ID. Reuse existing tags; suggest a new tag only if necessary.

跨宿主示例：在 Hermes 保存一张卡，再用 Codex 搜索它。前提是两者实际运行环境访问同一个 `SLIPBOX_HOME`。这是推荐验收场景，本轮没有声称已经实测。标签合并、删除卡片应单独确认。

Try capturing with one host and retrieving with another that shares the same library. This is a suggested acceptance exercise, not a recorded host test. Confirm deletions and tag merges separately.
