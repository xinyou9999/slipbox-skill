# FAQ / 常见问题

**Is this an AI memory service?** It is a card-note Skill: explicit capture, governed tags, literal retrieval and recent-card review. It does not automatically capture every conversation.

**How is it different from a full notes app?** Your agent provides the conversational interface and semantic judgment; slipbox supplies a small local card workflow. There is no production graphical editor in this release.

**Does “find it again” mean semantic search?** No. The current CLI searches literal substrings and tags. Your host model can formulate searches and interpret results; the script does not embed documents or call a model.

**Can different agents share notes?** Yes when their execution environments can access the same local `SLIPBOX_HOME`. Containers, separate users and remote hosts may have different filesystems. No automatic cross-device sync is included.

**Are my notes private?** The CLI writes local files and makes no network requests. A host may send the notes it reads to its model provider. Review that host's settings and keep the library private.

**Do I need another API key?** Not for slipbox. Your host's own subscription/model access still applies.

**Does it install on all advertised hosts?** We provide routes based on official docs. They are marked untested until reproducible host-level evidence exists; DeepSeek harness is experimental.

**Why only three tags?** To encourage stable reusable concepts instead of a separate tag for every card. Tags have canonical names and aliases; new tags are created explicitly.

**Can two agents edit together?** Commands serialize writes locally, but stale edits can overwrite newer content. Re-read before an edit and keep one writer per card.

**How do I leave?** Back up `cards/` and `tags.json`. Your cards are Markdown. Uninstalling the Skill should not remove the separate library; rebuild the disposable index after restoration.

**中文用户怎么开始？** 先读 [中文首页](../README.zh-CN.md)，再做 [快速体验](QUICKSTART.md)。可以用中文提 issue 或反馈安装情况。
