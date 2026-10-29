# Slipbox data format

## CLI encoding

The command-line entrypoint emits UTF-8 on stdout and stderr, independent of the parent terminal's default code page. Process consumers should decode these streams explicitly as UTF-8 (for example, `subprocess.run(..., text=True, encoding="utf-8")`). Configure this before mutations so a successful write containing non-ASCII text cannot be reported as a failed command because of output encoding.

## Library layout

```text
~/.slipbox/                 # or SLIPBOX_HOME
├── cards/
│   └── <32-hex-id>.md        # source of truth
├── tags.json                 # governed vocabulary; counts are derived
└── index.sqlite3             # disposable cache
```

Do not synchronize SQLite as authoritative data. Delete or replace it and run `rebuild-index`; rebuilding creates a fresh temporary database and atomically replaces the old index. Filtering uses the normalized `card_tags` table and does not require SQLite JSON1.

## Card Markdown

Each card has JSON-compatible YAML frontmatter followed by the original text:

```markdown
---
id: "0123456789abcdef0123456789abcdef"
created_at: "2026-01-01T08:00:00.000Z"
updated_at: "2026-01-01T08:00:00.000Z"
tags: ["工作", "灵感"]
---
原文正文，按纯文本保存。
```

The filename must equal `<id>.md`. IDs are 32 lowercase hexadecimal characters and never change. Timestamps must parse as UTC ISO 8601 and end in `Z`; `updated_at` cannot precede `created_at`. Tags must be strings, unique, known canonical names, and no more than three. Content is nonblank and at most 100,000 characters. Malformed metadata produces a structured JSON CLI error.

## Tag library

`tags.json` has exactly this top-level shape:

```json
{
  "version": 1,
  "tags": [
    {
      "name": "工作",
      "aliases": ["work"],
      "description": "工作事项",
      "usage_count": 3
    }
  ]
}
```

Every entry has exactly those fields with string `name`/`description`, a string alias list, and a non-negative integer count. Canonical names and aliases are NFKC/case-normalized for collision checks. `usage_count` is derived from cards.

## Mutation and recovery semantics

Markdown cards and the governed vocabulary are authoritative. Card writes commit Markdown first; if index/count refresh then fails, the command returns the committed card identity plus `repair_required: true` and tells the caller to run `rebuild-index`. Do not retry `add`, because that would duplicate the committed card.

`tag-merge` is stricter because tags and cards are both authoritative. It writes a private recovery journal, applies all files, and rebuilds the index. Failure rolls authoritative files back. A process interruption leaves the journal for automatic rollback on the next locked operation. Every snapshot is parsed and validated before any authoritative file is written: `tags.json` must load as a valid tag library, each card must re-parse against the journaled tags with a valid card file name, and an index snapshot must be a regular file.

A journal is replayed only while it still carries both its recovery name (`.merge-journal-*`) and its `manifest.json`; that pair means "not committed". Closing the journal - renaming it to `.merge-retired-*`, or removing the manifest when the rename itself fails - is the commit marker, and it is written after the merge commits (or after a rollback completes) and before any cleanup. An interrupted or failing cleanup therefore leaves only remains that a later command deletes; it can never turn a committed merge back into a replayable journal.

A journal whose snapshots do not validate is never applied: the authoritative files stay byte-for-byte unchanged, the journal is moved to `.merge-quarantine/<journal-name>` so it remains intact for manual inspection, one `warning: merge journal <name> quarantined at <path>; manual inspection recommended` line goes to stderr, and the command itself continues normally instead of failing. If even that move fails, the journal stays where it is and the warning says so. A broken journal can never make the library unusable and never blocks unrelated commands.

Mutations, rebuilds, and tag maintenance serialize through a kernel-level exclusive lock (`fcntl.flock(LOCK_EX)` on POSIX, `msvcrt.locking` on Windows) held on the persistent `.lock` file. The lock file is never removed, so release cannot delete a lock that a replacement owner already holds and no critical sections can overlap; a holder that crashes releases the lock in the kernel instead of relying on age-based stealing. Wait is bounded to ten seconds before returning a structured busy error. The owner metadata recorded inside `.lock` is diagnostic only and is never used to grant or transfer ownership.

## Permissions, durability, and threat boundary

On POSIX, every directory (the library, `cards/`, and merge-journal directories) is `0700`; every regular file (tags, cards, SQLite, sidecars, lock, journal manifests/snapshots, and temporary files) is `0600`. Replacements flush file data and fsync the parent directory after `os.replace`; SQLite rebuilds retain the private `mkstemp` file rather than unlinking and recreating it, and the database is fully closed and fsynced before index replacement. If replacement/removal commits but a later chmod or directory fsync fails, card add/edit/delete returns the stable card ID with `repair_required: true` and a warning instead of claiming full durability or reporting an ambiguous generic failure. Windows has no portable POSIX mode-bit equivalent: use an NTFS ACL/private user profile directory.

Final-component symlinks are rejected. Reads use `os.open` with `O_NOFOLLOW` where available and verify the opened descriptor is a regular file. Symlinked ancestors of a legitimate home path are allowed for common home-directory layouts. On platforms without `O_NOFOLLOW`, descriptor checks plus fixed-symlink checks are the fallback.

This is local-tool hardening, not a hostile multi-user sandbox. A user or attacker who can concurrently rewrite entries inside the private library directory can still race path checks or tamper with data. Keep the directory private and do not grant untrusted users write access.

Back up `cards/` and `tags.json` together. The index can always be rebuilt.

## Known limitations

- **Index replacement while another process holds the file (Windows).** `rebuild-index` builds the new database and swaps it in with `os.replace`. Windows refuses to replace a file that another process has open, so a second process holding `index.sqlite3` (a viewer, an editor preview, antivirus scanning) makes the swap fail; POSIX has no such restriction and renames over an open database. The failure is reported and nothing authoritative is touched, because the index is always rebuildable from Markdown: close the other handle and retry, or simply delete `index.sqlite3` and run `rebuild-index`.
- **One trailing newline is the canonical content form.** Card content is stored as the text followed by exactly one newline. Content that ends with several newlines, or with none, is normalized on its first write, and `show` returns the canonical text. This is deliberate file-format normalization, not a lost edit.
- **A journal that cannot be closed or quarantined is reported, not resolved.** If both the closing rename and the manifest removal fail (a broken or permission-less filesystem), `tag-merge` returns a structured error telling the caller to remove the journal manually; an already committed merge is never rolled back, but the leftover journal needs that manual step.
