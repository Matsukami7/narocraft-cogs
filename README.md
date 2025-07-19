# Patch Notes Cog

A custom Redbot cog for fetching and announcing game patch notes from Steam API. Built as a replacement for paid patch note announcement bots.

## Features

- **Multi-Game Support**: Currently supports Factorio, Stellaris, and Final Fantasy XIV
- **Unified Commands**: Single command structure for all games
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
  - `game`: Game name (factorio, stellaris, ffxiv, ff14)
  - `count`: Number of patch notes to fetch (1-10, default: 3)
- **`^factorio [count]`** - Direct shortcut for Factorio patch notes
- **`^patchhelp`** - Show detailed help for all commands

### Configuration Commands (Admin Only)

- **`^patchconfig`** or **`^pconfig`** - Show current configuration
- **`^patchconfig channel [#channel]`** - Set announcement channel
  - If no channel specified, uses current channel
- **`^patchconfig remove`** - Remove announcement channel
- **`^patchconfig status`** - Show detailed configuration status

## Supported Games

| Game | Command | Aliases | Steam App ID |
|------|---------|---------|-------------|
| 🏭 Factorio | `factorio` | factorio | 427520 |
| 🌌 Stellaris | `stellaris` | stellaris | 281990 |
| ⚔️ Final Fantasy XIV | `ffxiv` | ffxiv, ff14, finalfantasy14, finalfantasyxiv | 39210 |

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

# Configuration (Admin only)
^patchconfig channel #patch-notes
^patchconfig status
^patchconfig remove
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
- `subscribed_games`: List of games to monitor (future feature)
- `auto_announce`: Auto-announcement toggle (future feature)

## Future Features

- Automatic patch note announcements
- Game subscription management
- Scheduled checking for new patches
- Support for additional games and RSS feeds

## Support

If you encounter any issues or have feature requests, please create an issue in the repository.