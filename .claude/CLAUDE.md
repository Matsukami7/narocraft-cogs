# matsu-cogs — Claude Context

Custom Red Bot cogs for a live Discord server. The bot prefix is `^`.

## Repo Structure

```
matsu-cogs/
├── catbun_github/
│   ├── catbun_github.py   ← main cog logic
│   ├── __init__.py
│   └── README.md
├── patchnotes/
│   ├── patchnotes.py
│   ├── __init__.py
└── README.md              ← root docs covering both cogs
```

## catbun_github — What It Does

Funnels Discord bug reports and feature requests into GitHub Issues, with bidirectional sync.

### Sources

| Source | Trigger | Label |
|--------|---------|-------|
| Forum thread (player) | New post in watched forum channel | `source:discord` |
| `^bug` / `^feature` | Developer command | `source:discord` |
| In-game triage | Dev reacts ✅ in triage channel | `source:in-game` |

### Lifecycle of a thread

1. Thread created → GitHub Issue created → thread ID stored in `thread_issues` config
2. Issue closed (GitHub or `^resolve`) → thread locked + archived → thread queued in `pending_deletions`
3. After configured delay → thread permanently deleted, entry removed from both maps

### Background task (`poll_github_closed`, every 5 min)

Does two things in one loop:
- Fetches GitHub issues closed since `last_github_sync`, locks matching Discord threads
- Sweeps `pending_deletions`, deletes threads whose timestamp has passed

First run after `^reload` sets `last_github_sync` baseline and returns — intentional, prevents mass-closing old threads.

### Config keys (all stored via Red Bot's `Config` system)

| Key | Type | Notes |
|-----|------|-------|
| `github_token` | str | Fine-grained PAT, Issues read+write only |
| `github_repo` | str | `owner/repo` format |
| `bug_channel_ids` | list[int] | Forum channel IDs for bug reports |
| `feature_channel_ids` | list[int] | Forum channel IDs for feature requests |
| `triage_channel_ids` | list[int] | Text channels for in-game triage |
| `log_channel_id` | int | Private log channel |
| `dev_role_name` | str | Role name for triage/resolve access (default: `Developer`) |
| `thread_issues` | dict[str, int] | thread_id → GitHub issue number |
| `last_github_sync` | str | ISO timestamp of last closed-issue poll |
| `thread_delete_after_days` | int | Days after locking to delete thread (0 = never, default 7) |
| `pending_deletions` | dict[str, str] | thread_id → ISO timestamp to delete at |

### Key design decisions

- **GitHub URL hidden from public threads** — players see a confirmation reply; the issue URL only goes to the private log channel. Never change this behavior.
- **`on_thread_create` skips bot-owned threads** — `^bug`/`^feature` create bot-owned threads; `on_thread_create` bails on `thread.owner_id == self.bot.user.id` to avoid double-creating issues.
- **`create_thread()` returns `ThreadWithMessage`** — extract `.thread` from the result; the object is not the thread itself.
- **`asyncio.sleep(1)` before `thread.send()`** — Discord needs a brief delay before a newly created forum thread accepts messages.
- **Triage reactions: only Developer role** — non-Developer reactions on triage channels are silently ignored.
- **`^resolve` only works inside tracked forum threads** — checks `parent_id` against `bug_channel_ids` + `feature_channel_ids`.
- **Deletion is best-effort** — `discord.Forbidden` and `discord.NotFound` on delete are caught and swallowed; the entry is still cleaned up from the map.

### Commands summary

```
# Bot owner only
^cbgithub setrepo owner/repo
^cbgithub settoken <token>        ← message deleted immediately
^cbgithub addbugchannel <id>
^cbgithub addfeaturechannel <id>
^cbgithub addtriagechannel #channel
^cbgithub setdevrolename <name>
^cbgithub setlogchannel #channel
^cbgithub setthreaddelay <days>   ← 0 to disable auto-delete
^cbgithub settings

# Developer role only
^bug <description>
^feature <description>
^resolve [reason]
```

## patchnotes — What It Does

Fetches game patch notes from the Steam API and announces them in a configured Discord channel. Polls every 5 minutes. Not currently under active development.

## Working With This Repo

- The bot is **live in production** — be conservative with changes that affect event listeners or the background task.
- All config is stored in Red Bot's `Config` system (not files or env vars). Never hardcode tokens or IDs.
- After any code change, the cog needs `^reload catbun_github` on the live bot.
- GitHub labels (`bug`, `feature-request`, `source:discord`, `source:in-game`, `status:triage`) must exist in the target repo before the cog can apply them.
- Both `README.md` (root) and `catbun_github/README.md` should be kept in sync when commands or behaviors change.
