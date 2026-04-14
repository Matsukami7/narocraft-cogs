# narocraft-cogs

Custom Red Bot cogs for Discord servers. All cogs are GPL-3.0 licensed and designed for self-hosted Red Bot instances.

**Bot prefix used in examples:** `^`

---

## Cogs

| Cog | Purpose |
|-----|---------|
| [catbun_github](#catbun_github) | Funnels Discord bug reports and feature requests into GitHub Issues |
| [patchnotes](#patchnotes) | Fetches and announces game patch notes from Steam |

---

## Installation

```
^repo add narocraft-cogs https://github.com/Matsukami7/narocraft-cogs
^cog install narocraft-cogs catbun_github
^cog install narocraft-cogs patchnotes
^load catbun_github patchnotes
```

---

---

# catbun_github

Automatically creates GitHub Issues from Discord bug reports and feature requests. Designed for indie game studios who want community feedback funneled directly into a private GitHub repo — no third-party tools, no webhooks exposed to the internet.

## How It Works

```
Discord forum post (player)     → GitHub Issue created automatically
^bug / ^feature (Developer)     → GitHub Issue created automatically
In-game report → #ingame-reports → Developer reacts ✅ to approve → GitHub Issue
GitHub issue closed              → Discord forum thread locked automatically (polls every 5 min)
```

All sensitive config (GitHub token, repo name, channel IDs) is stored in Red Bot's Config system. Nothing is hardcoded in the cog.

## Requirements

- Red Bot v3 with `^` prefix (or your configured prefix)
- A GitHub fine-grained Personal Access Token — Issues read+write only, scoped to one repo
- Forum channels for bug reports and feature requests (Discord channel type: Forum)
- A private text channel for in-game reports (triage mode)
- A private text channel for the issue log

## Setup

Run all setup commands in a private config channel.

**1. Set the GitHub repo and token:**
```
^cbgithub setrepo owner/repo-name
^cbgithub settoken ghp_yourtoken
```
The token message is deleted immediately after saving.

**2. Register your forum channels (right-click channel → Copy ID):**
```
^cbgithub addbugchannel 1234567890
^cbgithub addfeaturechannel 1234567890
```
These must be forum-type channels (Discord channel type 15).

**3. Register the in-game triage channel:**
```
^cbgithub addtriagechannel #ingame-reports
```
Reports here are held until a Developer reacts ✅ to approve or ❌ to dismiss.

**4. Set the log channel:**
```
^cbgithub setlogchannel #catbun-bot-config
```
Every created issue is logged here with a link.

**5. (Optional) Change the Developer role name:**
```
^cbgithub setdevrolename Developer
```
Default is `Developer`. This role controls who can triage in-game reports and use `^bug`/`^feature`/`^resolve`.

**6. Verify config:**
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
| `^cbgithub setdevrolename <name>` | Set the role name for triage/resolve access (default: `Developer`) |
| `^cbgithub setlogchannel #channel` | Set the private issue log channel |
| `^cbgithub settings` | Show all current config |

### Developer role only

| Command | Description |
|---------|-------------|
| `^bug <description>` | Create a GitHub bug report issue |
| `^feature <description>` | Create a GitHub feature request issue |
| `^resolve [reason]` | Close the current forum thread and its GitHub issue |

`^bug` and `^feature` silently do nothing if run by someone without the Developer role.

`^resolve` must be run inside a tracked forum thread. Posts a closing message, closes the GitHub issue with a comment, and locks + archives the thread.

### Triage reactions (in-game reports channel)

| Reaction | Who | Effect |
|----------|-----|--------|
| ✅ | Developer | Creates a GitHub Issue from the message |
| ❌ | Developer | Dismisses with a reply (deleted after 30s) |

## Automatic Behaviors

**Forum thread created by a player:**
- GitHub Issue created immediately with `bug` or `feature-request`, `source:discord`, `status:triage` labels
- Bot replies in the thread: "✅ Thanks for your report! We've received it..."
- GitHub URL only posted to the private log channel (not visible in the public thread)
- Thread ID → issue number stored for later `^resolve` and GitHub sync

**GitHub issue closed on GitHub directly:**
- Cog polls GitHub every 5 minutes for newly closed issues
- If a matching Discord forum thread is found and not already archived, bot posts a closing message and locks the thread
- First run after `^reload` sets the baseline — no retroactive closes

## GitHub Labels Used

The cog tags every issue with labels from three groups. Create these in your repo before using:

**Type:**
- `bug`
- `feature-request`

**Source:**
- `source:discord`
- `source:in-game`

**Status:**
- `status:triage`

## Permissions Required

The bot needs these permissions in the relevant channels:

| Channel | Permissions Needed |
|---------|--------------------|
| Forum channels | View Channel, Send Messages in Threads, Create Public Threads, Manage Threads |
| Triage channel | View Channel, Send Messages, Add Reactions, Read Message History |
| Log channel | View Channel, Send Messages |

---

---

# patchnotes

Fetches and announces game patch notes from the Steam API. Built as a free replacement for paid patch note announcement bots.

## Supported Games

| Game | Command | Aliases |
|------|---------|---------|
| Factorio | `^factorio` | `factorio` |
| Stellaris | `^patchnotes stellaris` | `stellaris` |
| Final Fantasy XIV | `^patchnotes ffxiv` | `ffxiv`, `ff14` |
| No Man's Sky | `^patchnotes nms` | `nms`, `nomanssky` |
| Path of Exile | `^patchnotes pathofexile` | `poe`, `poe1` |
| Path of Exile 2 | `^patchnotes pathofexile2` | `poe2` |

## Setup

```
^cog install narocraft-cogs patchnotes
^load patchnotes
^patchconfig channel #patch-notes
^patchconfig subscribe factorio
^patchconfig toggle
```

## Commands

### Patch Notes

| Command | Description |
|---------|-------------|
| `^patchnotes` | List all available games |
| `^patchnotes <game> [count]` | Get patch notes for a game (count: 1–10, default 3) |
| `^factorio [count]` | Shortcut for Factorio patch notes |
| `^patchhelp` | Full command reference |

### Configuration (Admin only)

| Command | Description |
|---------|-------------|
| `^patchconfig channel [#channel]` | Set default announcement channel |
| `^patchconfig remove` | Remove announcement channel |
| `^patchconfig status` | Show current config |
| `^patchconfig subscribe <game> [#channel]` | Subscribe to auto-announcements for a game |
| `^patchconfig unsubscribe <game>` | Unsubscribe from a game |
| `^patchconfig toggle` | Enable/disable auto-announcements |

Auto-announcements check for new patches every 5 minutes. Per-game channels override the default channel when set.

## Permissions Required

- Send Messages
- Embed Links
- Read Message History

---

## License

GPL-3.0 — see [LICENSE](./LICENSE) or individual cog folders.

These cogs are not affiliated with any game developers or platforms. Use at your own risk.
