# CatbunGithub — Discord → GitHub Issues

A Red Bot cog that automatically creates GitHub Issues from Discord bug reports
and feature requests. Built for indie game studios who want community feedback
funneled into their GitHub repo without third-party tools like Zapier or Make.

## Features

- **Channel watching** — any message in a watched channel becomes a GitHub Issue
- **Commands** — `!bug` and `!feature` work from any channel
- **Source tagging** — labels issues as `source:discord` or `source:in-game`
- **Screenshot support** — Discord CDN attachment links are embedded in the issue body
- **Confirmation** — reacts ✅ and replies with the GitHub issue URL
- **Log channel** — optional channel that receives a one-liner for every issue created
- **Secure** — token stored in Red Bot's encrypted Config system, never in code

## Installation

```
^repo add narocraft-cogs <repo_url>
^cog install narocraft-cogs catbun_github
^load catbun_github
```

## Setup

All commands are bot-owner only:

```
^cbgithub setrepo owner/repo-name
^cbgithub settoken YOUR_GITHUB_TOKEN
^cbgithub addbugchannel #bug-reports
^cbgithub addfeaturechannel #feature-requests
^cbgithub addingamechannel #ingame-reports
^cbgithub setlogchannel #issue-log
^cbgithub settings
```

The token message is deleted immediately after saving.

## GitHub Token

Create a fine-grained token at GitHub → Settings → Developer Settings → Fine-grained tokens:
- Repository access: your target repo only
- Permissions: **Issues → Read and Write** (nothing else needed)

## Labels Applied

Every issue gets three labels automatically:

| Label | Values |
|---|---|
| Type | `bug` or `feature-request` |
| Source | `source:discord` or `source:in-game` |
| Status | `status:triage` |

Make sure these labels exist in your GitHub repo before using the cog.

## Commands

| Command | Who | What |
|---|---|---|
| `!bug <description>` | Anyone | Creates a bug report Issue |
| `!feature <description>` | Anyone | Creates a feature request Issue |
| `^cbgithub setrepo owner/repo` | Owner | Set GitHub repo |
| `^cbgithub settoken TOKEN` | Owner | Set GitHub token (deleted after save) |
| `^cbgithub addbugchannel #channel` | Owner | Watch channel for bug reports |
| `^cbgithub addfeaturechannel #channel` | Owner | Watch channel for feature requests |
| `^cbgithub addingamechannel #channel` | Owner | Watch channel for in-game reports |
| `^cbgithub setlogchannel #channel` | Owner | Set issue log channel |
| `^cbgithub settings` | Owner | Show current config |

## In-Game Reporter

The `addingamechannel` command is designed for a private channel that receives
webhook POSTs from an in-game bug reporter. Messages in that channel are labeled
`source:in-game` instead of `source:discord`.

## License

GPL-3.0 — Copyright (C) 2026 Lone Pixel Studios
