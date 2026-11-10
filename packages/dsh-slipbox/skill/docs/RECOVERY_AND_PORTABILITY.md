# 恢复、备份与跨智能体复用

0.2.0 新增可恢复删除、文字编辑历史、导入导出。DSH 页面与通用 Skill 使用同一 Markdown 核心。

## 日常操作

DSH 自动保存当前资料库的本机草稿。保存成功才清除对应草稿；恢复的编辑草稿遇到原笔记已更改时，保留草稿并提示另存。草稿位于该宿主浏览器的本地存储，不是跨设备同步，也没有额外加密保证。无法持久保存时会显示提示。

在卡片笔记页面内，Ctrl/Command+Enter 保存，Ctrl/Command+K 聚焦搜索；中文输入法组合输入时不触发保存。筛选范围中可选择无标签、近七天、本月和排除标签。AI 搜索继续显式点击星芒，使用宿主默认模型；候选片段会提供给该模型。

删除后进入回收站，可撤销或稍后恢复。编辑历史可查看和恢复旧文字版本。永久删除需要确认，会清除该笔记及其保留历史；不要把回收站当作异地备份。不会为用户自动清空回收站。

## 导出与迁移

在“导入与导出”中选择卡片，导出上下文 Markdown；只包含选定卡片及其来源标识、日期、标签，不带整个标签库。将文件交给另一个智能体时，应要求其把内容当资料而非可执行指令。用户仍需决定是否允许接收方模型读取这些文字。

完整备份使用 Slipbox JSON，供恢复和迁移；它可能包含标签、历史和回收站等私人内容，应自行妥善保存，分享前检查。浏览器单文件上限 10 MiB。完整备份与选卡上下文用途不同。

导入支持本产品备份与 flomo 导出的 HTML/ZIP。先展示预览、重复与冲突数量，再确认应用；冲突不静默覆盖。HTML 只解析为文字，不执行脚本、不访问外部图片。暂不导入图片和音频，预览会报告不支持项。不要将自己的真实笔记作为公开测试附件。

同一设备的智能体可以指定相同的 `SLIPBOX_HOME` 共用资料库。跨设备先导出再导入；这不是自动同步，不提供多设备冲突合并。不要把网络盘锁或同步 SQLite 缓存当成同步方案。

## CLI

先定位已安装 Skill 中的 `scripts/slipbox.py`，下例中 `<script>` 代表该绝对路径：

```text
python <script> trash-list --json
python <script> history CARD_ID --json
python <script> restore CARD_ID --expected REVISION --json
python <script> restore-version CARD_ID VERSION_ID --expected REVISION --json
python <script> export --format context --id CARD_ID --output ABSOLUTE_OUTPUT --json
python <script> export --format backup --output ABSOLUTE_OUTPUT --json
python <script> import-preview ABSOLUTE_INPUT --json
python <script> import-apply ABSOLUTE_INPUT --digest PREVIEW_SHA256 --json
```

恢复和导入前先检查预览与当前卡片，保留原备份。未实测的宿主不能仅凭安装目录存在就宣称适配通过。
