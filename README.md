# narocraft-cogs

A collection of custom Red Bot cogs by Lone Pixel Studios.

---

## Cogs

### 🎮 [patchnotes](./patchnotes) — Game Patch Notes

Fetches and announces game patch notes from the Steam API. Built as a replacement for paid patch note announcement bots.

**Supported games:** Factorio, Stellaris, Final Fantasy XIV, No Man's Sky, Path of Exile 1 & 2

### 🐛 [catbun_github](./catbun_github) — Discord → GitHub Issues

Automatically creates GitHub Issues from Discord bug reports and feature requests. Watches designated channels and responds to `!bug` / `!feature` commands. Designed for indie game studios who want to funnel community feedback directly into their GitHub repo without third-party tools.

---

## Installation

Add this repo to your Red Bot instance:
```
^repo add narocraft-cogs <repo_url>
```

Install a cog:
```
^cog install narocraft-cogs patchnotes
^cog install narocraft-cogs catbun_github
```

---

## License

GPL-3.0 — see individual cog folders for details.

## Disclaimer

These cogs are not affiliated with any game developers or platforms. Use at your own risk.

---

# patchnotes — Game Patch Notes Cog

A custom Redbot cog for fetching and announcing game patch notes from Steam API. Built as a replacement for paid patch note announcement bots.

## Features

- **Multi-Game Support**: Currently supports Factorio, Stellaris, Final Fantasy XIV, and No Man's Sky
- **Unified Commands**: Single command structure for all games
- **Automatic Announcements**: Background monitoring and auto-posting of new patch notes
- **Game Subscriptions**: Subscribe to specific games for targeted announcements
- **Channel Configuration**: Set custom announcement channels per server
- **Rich Embeds**: Beautiful Discord embeds with game-specific themes
- **Permission Management**: Admin-only configuration with proper permission checks
- **Error Handling**: Robust error handling for API failures and missing permissions

## Installation

1. Add this repository to your Redbot:
   ```
   ^repo add narocraft-cogs <repo_url>
   ```

2. Install the cog:
   ```
   ^cog install narocraft-cogs patchnotes
   ```

3. Load the cog:
   ```
   ^load patchnotes
   ```

## Commands

### Patch Notes Commands

- **`^patchnotes`** - Show all available games
- **`^patchnotes <game> [count]`** - Get patch notes for a specific game
  - `game`: Game name (factorio, stellaris, ffxiv, ff14, pathofexile, poe, pathofexile2, poe2)
  - `count`: Number of patch notes to fetch (1-10, default: 3)
- **`^factorio [count]`** - Direct shortcut for Factorio patch notes
- **`^patchhelp`** - Show detailed help for all commands

### Configuration Commands (Admin Only)

- **`^patchconfig`** or **`^pconfig`** or **`^patchnotesconfig`** - Show current configuration
- **`^patchconfig channel [#channel]`** - Set default announcement channel
  - If no channel specified, uses current channel
- **`^patchconfig remove`** - Remove announcement channel
- **`^patchconfig status`** - Show detailed configuration status

### Auto-Announcement Commands (Admin Only)

- **`^patchconfig subscribe <game> [#channel]`** - Subscribe to automatic announcements for a game
  - `game`: The game to subscribe to (e.g., factorio, stellaris)
  - `channel`: (Optional) Specific channel for this game's announcements
  - Example: `^patchconfig subscribe factorio #factorio-news`
- **`^patchconfig unsubscribe <game>`** - Unsubscribe from automatic announcements for a game
- **`^patchconfig toggle`** - Toggle automatic patch note announcements on/off

### Per-Game Channel Configuration

You can specify different announcement channels for each game:

1. **Default Channel**: Set with `^patchconfig channel #general`
   - Used when no per-game channel is specified
   - Fallback if a game's specific channel is deleted

2. **Game-Specific Channels**: Set when subscribing to a game
   - Example: `^patchconfig subscribe factorio #factorio-updates`
   - Overrides the default channel for that specific game
   - To change a game's channel, simply resubscribe with the new channel

3. **Mixed Configuration**: Use default for some games, specific channels for others
   - Example:
     ```
     ^patchconfig channel #gaming
     ^patchconfig subscribe stellaris
     ^patchconfig subscribe factorio #factorio-news
     ```
   - Stellaris announcements go to #gaming
   - Factorio announcements go to #factorio-news

## Supported Games

| Game | Command | Aliases | Steam App ID |
|------|---------|---------|-------------|
| 🏭 Factorio | `^factorio` | factorio | 427520 |
| 🌌 Stellaris | `^stellaris` | stellaris | 281990 |
| ⚔️ Final Fantasy XIV | `^ffxiv` | ffxiv, ff14, finalfantasy14, finalfantasyxiv | 39210 |
| 🚀 No Man's Sky | `^nms` | nms, nomanssky, no-mans-sky | 275850 |
| Path of Exile | `^pathofexile` | poe, poe1 | 238960 |
| Path of Exile 2 | `^pathofexile2` | poe2 | 238960 |

## Usage Examples

```
# Get available games
^patchnotes

# Get 3 latest Factorio patch notes
^patchnotes factorio
^factorio

# Get 5 latest Stellaris patch notes
^patchnotes stellaris 5

# Get Final Fantasy XIV patch notes
^patchnotes ffxiv
^patchnotes ff14

# Get No Man's Sky patch notes
^patchnotes nms
^patchnotes nomanssky
^patchnotes no-mans-sky

# Configuration (Admin only)
^patchconfig channel #patch-notes
^patchconfig status
^patchconfig remove

# Auto-Announcement Setup (Admin only)
^patchconfig subscribe factorio
^patchconfig subscribe stellaris
^patchconfig toggle
^patchconfig unsubscribe nms
```

## Permissions Required

### For Bot:
- Send Messages
- Embed Links
- Read Message History

### For Configuration:
- Manage Server permission or Admin role

## Technical Details

- **Data Source**: Steam Web API (no API key required)
- **Storage**: Redbot's built-in config system
- **Dependencies**: aiohttp, discord.py
- **Framework**: Redbot v3

## Configuration Storage

Per-server settings stored:
- `announcement_channel`: Channel ID for announcements
- `subscribed_games`: List of games to monitor for auto-announcements
- `auto_announce`: Auto-announcement toggle (enabled/disabled)
- `check_interval`: Frequency of patch checking (default: 3600 seconds)
- `last_patches`: Tracking of last seen patches to prevent duplicates

## Auto-Announcement System

The cog includes a background task that:
- Checks for new patches every 5 minutes
- Only announces patches newer than previously seen ones
- Respects per-server subscription settings
- Supports per-game announcement channels
- Requires proper channel permissions to post
- Automatically creates rich embeds for announcements
- Provides detailed logging for troubleshooting

## Getting Help

For detailed command help and examples, use:
```
^patchhelp
```

This will show you:
- Complete command reference
- Available game shortcuts
- Configuration examples
- Auto-announcement settings
- Per-game channel configuration

## Future Features

- Configurable check intervals
- Support for additional games. (would like to add this ability to the cog itself, and it not be hard coded)
- Webhook integration for external notifications
- Advanced filtering options

## Support

If you encounter any issues or have feature requests, please create an issue on this repo.


##Disclaimer

This cog is not affiliated with any game developers, and is not endorsed by them. It is a community-driven project.
By using this cog/software you accept the risk of using it, and the cog author is not responsible for any issues that may arise from using it.
By using this cog/software you agree that you have read and understand the license and disclaimer, and that running foreign code found on the internet is at your own risk.


## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). This means:

- You are free to use, modify, and distribute this software
- You must disclose the source code of any modified versions
- Modified versions must also be licensed under the GPL-3.0
- All original copyright notices and disclaimers must be preserved

```
GamePatch Notes Cog - A custom Redbot cog for fetching and announcing game patch notes
Copyright (C) 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
