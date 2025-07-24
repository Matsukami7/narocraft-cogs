# GamePatch Notes Cog

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
   [p]repo add narocraft-cogs <repo_url>
   ```

2. Install the cog:
   ```
   [p]cog install narocraft-cogs patchnotes
   ```

3. Load the cog:
   ```
   [p]load patchnotes
   ```

## Commands

### Patch Notes Commands

- **`[p]patchnotes`** - Show all available games
- **`[p]patchnotes <game> [count]`** - Get patch notes for a specific game
  - `game`: Game name (factorio, stellaris, ffxiv, ff14)
  - `count`: Number of patch notes to fetch (1-10, default: 3)
- **`[p]factorio [count]`** - Direct shortcut for Factorio patch notes
- **`[p]patchhelp`** - Show detailed help for all commands

### Configuration Commands (Admin Only)

- **`[p]patchconfig`** or **`[p]pconfig`** or **`[p]patchnotesconfig`** - Show current configuration
- **`[p]patchconfig channel [#channel]`** - Set default announcement channel
  - If no channel specified, uses current channel
- **`[p]patchconfig remove`** - Remove announcement channel
- **`[p]patchconfig status`** - Show detailed configuration status

### Auto-Announcement Commands (Admin Only)

- **`[p]patchconfig subscribe <game> [#channel]`** - Subscribe to automatic announcements for a game
  - `game`: The game to subscribe to (e.g., factorio, stellaris)
  - `channel`: (Optional) Specific channel for this game's announcements
  - Example: `[p]patchconfig subscribe factorio #factorio-news`
- **`[p]patchconfig unsubscribe <game>`** - Unsubscribe from automatic announcements for a game
- **`[p]patchconfig toggle`** - Toggle automatic patch note announcements on/off

### Per-Game Channel Configuration

You can specify different announcement channels for each game:

1. **Default Channel**: Set with `[p]patchconfig channel #general`
   - Used when no per-game channel is specified
   - Fallback if a game's specific channel is deleted

2. **Game-Specific Channels**: Set when subscribing to a game
   - Example: `[p]patchconfig subscribe factorio #factorio-updates`
   - Overrides the default channel for that specific game
   - To change a game's channel, simply resubscribe with the new channel

3. **Mixed Configuration**: Use default for some games, specific channels for others
   - Example:
     ```
     [p]patchconfig channel #gaming
     [p]patchconfig subscribe stellaris
     [p]patchconfig subscribe factorio #factorio-news
     ```
   - Stellaris announcements go to #gaming
   - Factorio announcements go to #factorio-news

## Supported Games

| Game | Command | Aliases | Steam App ID |
|------|---------|---------|-------------|
| 🏭 Factorio | `factorio` | factorio | 427520 |
| 🌌 Stellaris | `stellaris` | stellaris | 281990 |
| ⚔️ Final Fantasy XIV | `ffxiv` | ffxiv, ff14, finalfantasy14, finalfantasyxiv | 39210 |
| 🚀 No Man's Sky | `nms` | nms, nomanssky, no-mans-sky | 275850 |

## Usage Examples

```
# Get available games
[p]patchnotes

# Get 3 latest Factorio patch notes
[p]patchnotes factorio
[p]factorio

# Get 5 latest Stellaris patch notes
[p]patchnotes stellaris 5

# Get Final Fantasy XIV patch notes
[p]patchnotes ffxiv
[p]patchnotes ff14

# Get No Man's Sky patch notes
[p]patchnotes nms
[p]patchnotes nomanssky
[p]patchnotes no-mans-sky

# Configuration (Admin only)
[p]patchconfig channel #patch-notes
[p]patchconfig status
[p]patchconfig remove

# Auto-Announcement Setup (Admin only)
[p]patchconfig subscribe factorio
[p]patchconfig subscribe stellaris
[p]patchconfig toggle
[p]patchconfig unsubscribe nms
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
[p]patchhelp
```

This will show you:
- Complete command reference
- Available game shortcuts
- Configuration examples
- Auto-announcement settings
- Per-game channel configuration

## Future Features

- Configurable check intervals
- Support for additional games and RSS feeds
- Webhook integration for external notifications
- Advanced filtering options

## Support

If you encounter any issues or have feature requests, please create an issue in the repository.