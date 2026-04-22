# CatbunGithub — Discord → GitHub Issues

A Red Bot cog that automatically creates GitHub Issues from Discord bug reports
and feature requests. Built for indie game studios who want community feedback
funneled into their private GitHub repo without third-party tools.

## Features

- **Forum thread watching** — new post in a watched forum channel instantly creates a GitHub Issue
- **Developer commands** — `^bug` and `^feature` create a forum thread + GitHub Issue in one step
- **Triage mode** — in-game reports held until a Developer reacts ✅ to approve or ❌ to dismiss
- **GitHub sync** — polls GitHub every 5 min; closing an issue there locks the Discord thread automatically
- **`^resolve`** — Developer command to close the GitHub issue and lock the thread from Discord
- **Thread auto-delete** — resolved threads are automatically deleted after a configurable number of days
- **Screenshot support** — Discord CDN attachment links embedded in every issue body
- **Log channel** — private channel receives a one-liner link for every issue created
- **Secure** — GitHub token stored in Red Bot's encrypted Config system, never in code

## Installation

```
^repo add matsu-cogs https://github.com/Matsukami7/matsu-cogs
^cog install matsu-cogs catbun_github
^load catbun_github
```

## GitHub Token

Create a fine-grained token at GitHub → Settings → Developer Settings → Fine-grained tokens:

- Repository access: your target repo only
- Permissions: **Issues → Read and Write** (nothing else needed)

## Setup

Run all commands in a private config channel. All `^cbgithub` commands are bot-owner only.

**1. Set repo and token:**
```
^cbgithub setrepo owner/repo-name
^cbgithub settoken ghp_yourtoken
```
The token message is deleted immediately after saving.

**2. Register forum channels (right-click channel → Copy ID):**
```
^cbgithub addbugchannel 1234567890
^cbgithub addfeaturechannel 1234567890
```
These must be Discord forum channels (channel type 15), not text channels.

**3. Register the in-game triage channel:**
```
^cbgithub addtriagechannel #ingame-reports
```
Messages here are held — a Developer reacts ✅ to create a GitHub Issue, ❌ to dismiss.

**4. Set the log channel:**
```
^cbgithub setlogchannel #catbun-bot-config
```

**5. (Optional) Configure thread auto-deletion:**
```
^cbgithub setthreaddelay 7
```
Resolved threads will be permanently deleted this many days after being locked. Default is `7`. Set to `0` to keep threads indefinitely.

**6. (Optional) Change the triage role name:**
```
^cbgithub setdevrolename Developer
```
Default is `Developer`. This role controls who can use `^bug`, `^feature`, `^resolve`, and triage reactions.

**7. Verify config:**
```
^cbgithub settings
```

## Commands

### Admin (`^cbgithub`) — Bot owner only

| Command | Description |
|---------|-------------|
| `^cbgithub setrepo owner/repo` | Set the GitHub repo |
| `^cbgithub settoken <token>` | Set GitHub PAT (message deleted immediately) |
| `^cbgithub addbugchannel <channel_id>` | Watch a forum channel for bug reports |
| `^cbgithub addfeaturechannel <channel_id>` | Watch a forum channel for feature requests |
| `^cbgithub addtriagechannel #channel` | Watch a text channel in triage mode (in-game reports) |
| `^cbgithub setdevrolename <name>` | Set the role that can triage and resolve (default: `Developer`) |
| `^cbgithub setlogchannel #channel` | Set the private issue log channel |
| `^cbgithub setthreaddelay <days>` | Days after locking before a thread is deleted (`0` = never) |
| `^cbgithub settings` | Show all current config and pending deletion count |

### Developer role only

| Command | Description |
|---------|-------------|
| `^bug <description>` | Create a bug report forum thread + GitHub Issue |
| `^feature <description>` | Create a feature request forum thread + GitHub Issue |
| `^resolve [reason]` | Close the current thread's GitHub issue and lock the thread |

`^bug` and `^feature` silently ignore users without the Developer role.

`^resolve` must be run inside a tracked forum thread. It closes the GitHub issue with a comment, posts a summary message in the thread, then locks and archives it.

### Triage reactions — in-game reports channel

| Reaction | Who | Effect |
|----------|-----|--------|
| ✅ | Developer role | Creates a GitHub Issue labeled `source:in-game` |
| ❌ | Developer role | Dismisses with a 30-second reply |

## Automatic Behaviors

**New forum thread (posted by a player):**
- GitHub Issue created immediately with `bug`/`feature-request`, `source:discord`, `status:triage` labels
- Bot replies in the thread confirming receipt
- GitHub URL is only posted to the private log channel — not visible in the public thread
- Thread ID → issue number stored internally for `^resolve` and GitHub sync

**GitHub issue closed directly on GitHub:**
- Cog polls GitHub every 5 minutes for newly closed issues
- Matching Discord thread gets a closing message, then is locked and archived
- Thread is queued for deletion per the configured delay
- First run after `^load`/`^reload` sets a baseline — no retroactive closures

**Thread auto-deletion:**
- Triggered by both `^resolve` and the GitHub sync path
- Deletion is checked every 5 minutes alongside the GitHub poll
- If the thread is already gone (deleted manually), the entry is cleaned up silently
- Use `^cbgithub settings` to see how many threads are pending deletion

## GitHub Labels Used

Create these labels in your repo before using the cog:

| Group | Labels |
|-------|--------|
| Type | `bug`, `feature-request` |
| Source | `source:discord`, `source:in-game` |
| Status | `status:triage` |

## Permissions Required

| Channel | Permissions needed |
|---------|--------------------|
| Forum channels | View Channel, Send Messages in Threads, Create Public Threads, Manage Threads |
| Triage channel | View Channel, Send Messages, Add Reactions, Read Message History |
| Log channel | View Channel, Send Messages |

## License

GPL-3.0 — Copyright (C) 2026 Lone Pixel Studios
