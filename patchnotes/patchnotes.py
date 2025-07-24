import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import box, pagify


class PatchCog(commands.Cog):
    """A cog for fetching game patch notes"""

    def __init__(self, bot):
        self.bot = bot
        self.steam_api_base = (
            "http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
        )
        self.logger = logging.getLogger("red.PatchCog")
        self.check_task = None

        # Initialize config
        self.config = Config.get_conf(self, identifier=1234567890)
        default_guild = {
            "announcement_channel": None,  # Default channel for all games
            "subscribed_games": [],  # List of subscribed game keys
            "game_channels": {},  # Per-game channel overrides
            "auto_announce": False,  # Global announcement toggle
            "check_interval": 3600,  # Check every hour by default
            "last_patches": {},  # Store last seen patch timestamps per game
        }
        self.config.register_guild(**default_guild)

        # Start the background check task
        self.check_task = self.bot.loop.create_task(self.patch_check_loop())

        # Game database with Steam App IDs and display info
        self.games = {
            "factorio": {
                "appid": "427520",
                "name": "Factorio",
                "emoji": "🏭",
                "color": 0xFF6B35,  # Orange
                "aliases": ["factorio"],
            },
            "stellaris": {
                "appid": "281990",
                "name": "Stellaris",
                "emoji": "🌌",
                "color": 0x4A90E2,  # Blue
                "aliases": ["stellaris"],
            },
            "ffxiv": {
                "appid": "39210",
                "name": "Final Fantasy XIV",
                "emoji": "⚔️",
                "color": 0x8B4513,  # Brown/Bronze
                "aliases": ["ffxiv", "ff14", "finalfantasy14", "finalfantasyxiv"],
            },
            "nms": {
                "appid": "275850",
                "name": "No Man's Sky",
                "emoji": "🚀",
                "color": 0xFF1493,  # Deep Pink
                "aliases": ["nms", "nomanssky", "no-mans-sky"],
            },
        }

    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        if self.check_task and not self.check_task.done():
            self.check_task.cancel()

    async def patch_check_loop(self):
        """Background task to check for new patches periodically"""
        await self.bot.wait_until_red_ready()

        while True:
            try:
                await self.check_for_new_patches()
                await asyncio.sleep(300)  # Wait 5 minutes between checks
            except asyncio.CancelledError:
                self.logger.info("Patch check loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in patch check loop: {e}")
                await asyncio.sleep(300)  # Wait before retrying

    async def check_for_new_patches(self):
        """Check all guilds for new patches and announce them"""
        for guild in self.bot.guilds:
            try:
                guild_config = await self.config.guild(guild).all()

                if (
                    not guild_config["auto_announce"]
                    or not guild_config["subscribed_games"]
                ):
                    continue

                channel_id = guild_config["announcement_channel"]
                if not channel_id:
                    continue

                channel = guild.get_channel(channel_id)
                if not channel:
                    continue

                # Check permissions
                permissions = channel.permissions_for(guild.me)
                if not permissions.send_messages or not permissions.embed_links:
                    continue

                for game_key in guild_config["subscribed_games"]:
                    if game_key not in self.games:
                        continue

                    await self.check_game_for_updates(
                        guild, channel, game_key, guild_config
                    )

            except Exception as e:
                self.logger.error(f"Error checking patches for guild {guild.id}: {e}")

    async def check_game_for_updates(self, guild, default_channel, game_key, guild_config):
        """Check a specific game for updates and announce if found"""
        if game_key not in self.games:
            return

        # Get the last seen timestamp for this game
        last_seen = guild_config["last_patches"].get(game_key, 0)
        
        # Fetch latest patches
        success, result = await self.get_patch_notes(game_key, 5)  # Get last 5 patches
        
        if not success:
            self.logger.warning(f"Failed to fetch patches for {game_key} in guild {guild.id}")
            return

        # Filter for new patches
        new_patches = [
            item for item in result["news_items"]
            if item["date"] > last_seen
        ]

        if not new_patches:
            return  # No new patches

        # Sort by date (oldest first)
        new_patches.sort(key=lambda x: x["date"])
        
        # Update last seen timestamp
        last_seen = new_patches[-1]["date"]
        last_patches = guild_config["last_patches"]
        last_patches[game_key] = last_seen
        await self.config.guild(guild).last_patches.set(last_patches)

        # Create announcement embed
        game_info = self.games[game_key]
        embed = self.create_announcement_embed(game_info, new_patches)
        
        # Get the target channel (per-game or default)
        game_channels = await self.config.guild(guild).game_channels()
        channel_id = game_channels.get(game_key) or default_channel.id
        
        # Get the channel object
        target_channel = guild.get_channel(channel_id)
        if not target_channel:
            self.logger.warning(
                f"Could not find channel {channel_id} for game {game_key} in guild {guild.id}"
            )
            return
            
        # Check permissions
        if not target_channel.permissions_for(guild.me).send_messages:
            self.logger.warning(
                f"No permission to send messages in channel {target_channel.id} for guild {guild.id}"
            )
            return

        # Send the announcement
        try:
            await target_channel.send(embed=embed)
            self.logger.info(
                f"Announced {len(new_patches)} new patches for {game_key} "
                f"in channel {target_channel.id} (guild {guild.id})"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to send announcement for {game_key} in guild {guild.id}: {e}"
            )

        except Exception as e:
            self.logger.error(
                f"Error checking {game_key} for updates in guild {guild.id}: {e}"
            )

    def create_announcement_embed(self, game_info: dict, news_items: list):
        """Create a Discord embed for patch note announcements"""
        embed = discord.Embed(
            title=f"🆕 {game_info['emoji']} {game_info['name']} - New Patch Notes!",
            color=game_info["color"],
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="Auto-announcement • Powered by Steam API")

        # Limit to 3 most recent patches in announcements
        items_to_show = news_items[:3]

        for item in items_to_show:
            # Convert timestamp to readable date
            date = datetime.fromtimestamp(item["date"]).strftime("%Y-%m-%d %H:%M")

            # Clean up the content
            content = item["contents"]
            if len(content) > 300:  # Shorter for announcements
                content = content[:300] + "..."

            # Remove HTML tags if present
            content = re.sub(r"<[^>]+>", "", content)

            embed.add_field(
                name=f"📅 {item['title']} ({date})",
                value=f"{content}\n[Read More]({item['url']})",
                inline=False,
            )

        if len(news_items) > 3:
            embed.add_field(
                name="📋 More Updates",
                value=f"+ {len(news_items) - 3} more patch notes available",
                inline=False,
            )

        return embed

    async def get_patch_notes(self, game_key: str, count: int = 3):
        """Fetch patch notes for a specific game

        Parameters:
        game_key: The game identifier from self.games
        count: Number of news items to fetch

        Returns:
        tuple: (success: bool, data: dict or str)
        """
        if game_key not in self.games:
            return False, f"Game '{game_key}' not supported."

        game_info = self.games[game_key]

        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "appid": game_info["appid"],
                    "count": count,
                    "maxlength": 500,
                    "format": "json",
                }

                async with session.get(self.steam_api_base, params=params) as response:
                    if response.status != 200:
                        return (
                            False,
                            f"Failed to fetch patch notes. Status: {response.status}",
                        )

                    data = await response.json()

                    if "appnews" not in data or "newsitems" not in data["appnews"]:
                        return False, f"No news data found for {game_info['name']}."

                    news_items = data["appnews"]["newsitems"]

                    if not news_items:
                        return (
                            False,
                            f"No recent patch notes found for {game_info['name']}.",
                        )

                    return True, {
                        "game_info": game_info,
                        "news_items": news_items[:count],
                    }

        except aiohttp.ClientError as e:
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, f"An error occurred: {str(e)}"

    def create_patch_embed(self, game_info: dict, news_items: list):
        """Create a Discord embed for patch notes"""
        embed = discord.Embed(
            title=f"{game_info['emoji']} {game_info['name']} Patch Notes",
            color=game_info["color"],
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="Powered by Steam API")

        for item in news_items:
            # Convert timestamp to readable date
            date = datetime.fromtimestamp(item["date"]).strftime("%Y-%m-%d")

            # Clean up the content
            content = item["contents"]
            if len(content) > 400:
                content = content[:400] + "..."

            # Remove HTML tags if present
            content = re.sub(r"<[^>]+>", "", content)

            embed.add_field(
                name=f"📅 {item['title']} ({date})",
                value=f"{content}\n[Read More]({item['url']})",
                inline=False,
            )

        return embed

    @commands.command(name="patchnotes", aliases=["patch", "patches"])
    async def patch_notes_unified(
        self, ctx, game: Optional[str] = None, count: int = 3
    ):
        """Get the latest patch notes for a supported game

        Parameters:
        game: The game name (e.g., factorio)
        count: Number of news items to fetch (default: 3, max: 10)

        Usage:
        ^patchnotes factorio
        ^patchnotes factorio 5
        """
        if game is None:
            # Show available games
            prefix = await self.get_prefix(ctx)

            embed = discord.Embed(
                title="🎮 Available Games",
                description=f"Use `{prefix}patchnotes <game>` to get patch notes",
                color=0x00FF00,
            )

            games_list = "\n".join(
                [
                    f"{info['emoji']} **{info['name']}** - `{key}`"
                    for key, info in self.games.items()
                ]
            )

            embed.add_field(name="Supported Games", value=games_list, inline=False)

            embed.add_field(
                name="Examples",
                value=f"`{prefix}patchnotes factorio` - Get 3 latest Factorio patch notes\n`{prefix}patchnotes factorio 5` - Get 5 latest patch notes",
                inline=False,
            )

            await ctx.send(embed=embed)
            return

        # Normalize game name and check aliases
        game = game.lower()
        game_key = None

        for key, info in self.games.items():
            if game == key or game in info.get("aliases", []):
                game_key = key
                break

        if game_key is None:
            available_games = ", ".join(self.games.keys())
            await ctx.send(
                f"❌ Game '{game}' not supported. Available games: {available_games}"
            )
            return

        # Validate count
        if count > 10:
            count = 10
        elif count < 1:
            count = 1

        await ctx.typing()

        success, result = await self.get_patch_notes(game_key, count)

        if not success:
            await ctx.send(f"❌ {result}")
            return

        embed = self.create_patch_embed(result["game_info"], result["news_items"])
        await ctx.send(embed=embed)

    @commands.command(name="factorio")
    async def factorio_patch(self, ctx, count: int = 3):
        """Get the latest Factorio patch notes (alias for patchnotes factorio)"""
        await self.patch_notes_unified(ctx, "factorio", count)

    @commands.command(name="patchhelp")
    async def patch_help(self, ctx):
        """Show detailed help for patch note commands and configuration"""
        prefix = await self.get_prefix(ctx)

        embed = discord.Embed(
            title="🔧 Patch Notes Cog - Complete Guide",
            description=(
                "A comprehensive guide to using the Patch Notes cog. "
                "This cog allows you to fetch and automatically post game patch notes."
            ),
            color=0x00AAFF,
        )

        # Basic Commands
        embed.add_field(
            name="📜 Basic Commands",
            value=(
                f"`{prefix}patchnotes [game] [count]`\n"
                "• Fetch patch notes for any supported game\n"
                "• `game`: The game name (e.g., factorio)\n"
                "• `count`: Number of patch notes to fetch (1-10, default: 3)\n\n"
                f"`{prefix}factorio [count]`\n"
                "• Shortcut for Factorio patch notes\n"
                "• `count`: Number of patch notes to fetch (1-10, default: 3)"
            ),
            inline=False,
        )

        # Auto-Announcement Commands
        embed.add_field(
            name="🔔 Auto-Announcement Commands (Admin Only)",
            value=(
                f"`{prefix}patchconfig channel [#channel]`\n"
                "• Set the default announcement channel\n"
                "• Omit channel to use current channel\n\n"
                f"`{prefix}patchconfig subscribe <game> [#channel]`\n"
                "• Subscribe to automatic patch notes for a game\n"
                "• Optionally specify a channel for this game\n\n"
                f"`{prefix}patchconfig unsubscribe <game>`\n"
                "• Unsubscribe from a game's automatic updates\n\n"
                f"`{prefix}patchconfig toggle`\n"
                "• Toggle auto-announcements on/off\n\n"
                f"`{prefix}patchconfig status`\n"
                "• Show current configuration"
            ),
            inline=False,
        )

        # Available Games
        games_list = []
        for key, info in self.games.items():
            aliases = ", ".join([f"`{a}`" for a in info.get("aliases", [])])
            games_list.append(f"{info['emoji']} **{info['name']}** - `{key}` {aliases}")

        embed.add_field(
            name="🎮 Available Games",
            value="\n".join(games_list),
            inline=False,
        )

        # Examples
        examples = [
            f"`{prefix}patchnotes` - Show available games",
            f"`{prefix}patchnotes factorio` - Get Factorio patch notes",
            f"`{prefix}patchconfig #patch-notes` - Set announcement channel",
            f"`{prefix}patchconfig subscribe factorio #factorio-news` - Subscribe to Factorio updates",
            f"`{prefix}patchconfig unsubscribe stellaris` - Stop Stellaris updates",
            f"`{prefix}patchconfig status` - View current settings"
        ]

        embed.add_field(
            name="💡 Examples",
            value="\n".join(examples),
            inline=False,
        )

        # Auto-Announcement Info
        embed.add_field(
            name="ℹ️ Auto-Announcement Features",
            value=(
                "• Checks for new patches every 5 minutes\n"
                "• Posts only new patches since last check\n"
                "• Supports per-game announcement channels\n"
                "• Beautiful, game-themed embeds\n"
                "• Configurable per server"
            ),
            inline=False,
        )

        embed.set_footer(
            text=f"Use {prefix}patchhelp for this help menu • Bot prefix: {prefix}"
        )

        await ctx.send(embed=embed)

    @commands.group(name="patchconfig", aliases=["pconfig", "patchnotesconfig"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def patch_config(self, ctx):
        """Configure patch notes settings for this server"""
        if ctx.invoked_subcommand is None:
            await self.show_config(ctx)

    @patch_config.command(name="channel")
    async def set_channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Set the channel for patch note announcements

        Parameters:
        channel: The text channel to post announcements (leave empty to use current channel)
        """
        if channel is None:
            channel = ctx.channel

        # Check if bot has permissions to send messages in the channel
        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.send_messages or not permissions.embed_links:
            await ctx.send(
                f"❌ I don't have permission to send messages or embed links in {channel.mention}. "
                "Please ensure I have 'Send Messages' and 'Embed Links' permissions."
            )
            return

        await self.config.guild(ctx.guild).announcement_channel.set(channel.id)

        embed = discord.Embed(
            title="✅ Channel Set",
            description=f"Patch note announcements will be posted to {channel.mention}",
            color=0x00FF00,
        )
        await ctx.send(embed=embed)

    @patch_config.command(name="remove")
    async def remove_channel(self, ctx):
        """Remove the announcement channel (disable announcements)"""
        await self.config.guild(ctx.guild).announcement_channel.set(None)

        embed = discord.Embed(
            title="✅ Channel Removed",
            description="Patch note announcements have been disabled for this server.",
            color=0x00FF00,
        )
        await ctx.send(embed=embed)

    @patch_config.command(name="subscribe")
    async def subscribe_game(self, ctx, game: Optional[str] = None, channel: Optional[discord.TextChannel] = None):
        """Subscribe to patch notes for a specific game

        Parameters:
        game: The game to subscribe to (e.g., factorio)
        channel: (Optional) Specific channel for this game's announcements
        """
        if game is None:
            # Show available games
            embed = discord.Embed(
                title="🎮 Subscribe to Game Patch Notes",
                description=(
                    "Subscribe to automatic patch notes for supported games.\n"
                    "You can specify a channel for each game's announcements."
                ),
                color=0x0099FF,
            )

            games_list = []
            for key, info in self.games.items():
                alias_text = f" (aliases: {', '.join(info['aliases'])})" if info.get('aliases') else ""
                games_list.append(f"{info['emoji']} **{info['name']}** - `{key}`{alias_text}")

            embed.add_field(
                name="Available Games",
                value="\n".join(games_list),
                inline=False
            )

            prefix = await self.get_prefix(ctx)
            embed.add_field(
                name="Usage",
                value=(
                    f"`{prefix}patchconfig subscribe <game> [#channel]`\n"
                    f"• Subscribe to a game's patch notes\n"
                    f"• Optionally specify a channel for this game's announcements\n\n"
                    f"Example: `{prefix}patchconfig subscribe factorio #factorio-news`\n"
                    f"Example: `{prefix}patchconfig subscribe stellaris` (uses default channel)"
                ),
                inline=False,
            )
            await ctx.send(embed=embed)
            return

        # Normalize game name and check aliases
        game = game.lower()
        game_key = None

        for key, info in self.games.items():
            if game == key or game in info.get("aliases", []):
                game_key = key
                break

        if game_key is None:
            available_games = ", ".join(self.games.keys())
            await ctx.send(
                f"❌ Game '{game}' not supported. Available games: {available_games}"
            )
            return

        # Get current configuration
        guild_config = self.config.guild(ctx.guild)
        subscribed_games = await guild_config.subscribed_games()
        game_channels = await guild_config.game_channels()

        if game_key in subscribed_games:
            game_info = self.games[game_key]
            current_channel = game_channels.get(game_key)
            channel_mention = f" in {ctx.guild.get_channel(current_channel).mention}" if current_channel else ""
            await ctx.send(
                f"⚠️ This server is already subscribed to **{game_info['name']}** patch notes{channel_mention}."
            )
            return

        # Add the subscription
        subscribed_games.append(game_key)
        await guild_config.subscribed_games.set(subscribed_games)

        # Store channel override if provided
        if channel:
            game_channels[game_key] = channel.id
            await guild_config.game_channels.set(game_channels)

        game_info = self.games[game_key]
        channel_mention = f" in {channel.mention}" if channel else ""
        
        embed = discord.Embed(
            title="✅ Subscription Added",
            description=(
                f"This server is now subscribed to **{game_info['emoji']} {game_info['name']}** "
                f"patch notes{channel_mention}!"
            ),
            color=0x00FF00,
        )

        # Initialize last seen timestamp with current latest patch
        success, result = await self.get_patch_notes(game_key, 1)
        if success and result["news_items"]:
            last_patches = await guild_config.last_patches()
            last_patches[game_key] = result["news_items"][0]["date"]
            await guild_config.last_patches.set(last_patches)
            
            if not channel:
                default_channel = await guild_config.announcement_channel()
                if not default_channel:
                    embed.add_field(
                        name="⚠️ Note",
                        value=(
                            "No default announcement channel is set! "
                            f"Use `{await self.get_prefix(ctx)}patchconfig channel #channel` to set one."
                        ),
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="ℹ️ Note",
                        value=(
                            f"Using the default announcement channel. "
                            f"To set a specific channel for {game_info['name']}, use: "
                            f"`{await self.get_prefix(ctx)}patchconfig subscribe {game_key} #channel`"
                        ),
                        inline=False,
                    )
            else:
                embed.add_field(
                    name="📋 Note",
                    value=(
                        f"{game_info['name']} patch notes will be posted to {channel.mention}. "
                        f"You'll receive announcements for patches released after this subscription."
                    ),
                    inline=False,
                )

        await ctx.send(embed=embed)

    @patch_config.command(name="unsubscribe")
    async def unsubscribe_game(self, ctx, game: Optional[str] = None):
        """Unsubscribe from patch notes for a specific game

        Parameters:
        game: The game to unsubscribe from (e.g., factorio)
        """
        if game is None:
            # Show current subscriptions
            subscribed_games = await self.config.guild(ctx.guild).subscribed_games()

            if not subscribed_games:
                await ctx.send("❌ This server is not subscribed to any games.")
                return

            embed = discord.Embed(
                title="📋 Current Subscriptions",
                description="Games this server is subscribed to:",
                color=0x0099FF,
            )

            games_list = "\n".join(
                [
                    f"{self.games[key]['emoji']} **{self.games[key]['name']}** - `{key}`"
                    for key in subscribed_games
                    if key in self.games
                ]
            )

            embed.add_field(name="Subscribed Games", value=games_list, inline=False)

            prefix = await self.get_prefix(ctx)
            embed.add_field(
                name="Usage",
                value=f"`{prefix}patchconfig unsubscribe <game>`\nExample: `{prefix}patchconfig unsubscribe factorio`",
                inline=False,
            )

            await ctx.send(embed=embed)
            return

        # Normalize game name and check aliases
        game = game.lower()
        game_key = None

        for key, info in self.games.items():
            if game == key or game in info.get("aliases", []):
                game_key = key
                break

        if game_key is None:
            available_games = ", ".join(self.games.keys())
            await ctx.send(
                f"❌ Game '{game}' not supported. Available games: {available_games}"
            )
            return

        # Get current subscriptions
        subscribed_games = await self.config.guild(ctx.guild).subscribed_games()

        if game_key not in subscribed_games:
            game_info = self.games[game_key]
            await ctx.send(
                f"⚠️ This server is not subscribed to **{game_info['name']}** patch notes."
            )
            return

        # Remove the subscription
        subscribed_games.remove(game_key)
        await self.config.guild(ctx.guild).subscribed_games.set(subscribed_games)

        # Clean up last seen timestamp
        last_patches = await self.config.guild(ctx.guild).last_patches()
        if game_key in last_patches:
            del last_patches[game_key]
            await self.config.guild(ctx.guild).last_patches.set(last_patches)

        game_info = self.games[game_key]
        embed = discord.Embed(
            title="✅ Subscription Removed",
            description=f"This server is no longer subscribed to **{game_info['emoji']} {game_info['name']}** patch notes.",
            color=0x00FF00,
        )

        await ctx.send(embed=embed)

    @patch_config.command(name="toggle")
    async def toggle_announcements(self, ctx):
        """Toggle automatic patch note announcements on/off"""
        current_status = await self.config.guild(ctx.guild).auto_announce()
        new_status = not current_status

        await self.config.guild(ctx.guild).auto_announce.set(new_status)

        status_text = "enabled" if new_status else "disabled"
        status_emoji = "✅" if new_status else "❌"

        embed = discord.Embed(
            title=f"{status_emoji} Auto-Announcements {status_text.title()}",
            description=f"Automatic patch note announcements have been **{status_text}** for this server.",
            color=0x00FF00 if new_status else 0xFF0000,
        )

        if new_status:
            # Check if they have subscriptions and a channel set
            subscribed_games = await self.config.guild(ctx.guild).subscribed_games()
            announcement_channel = await self.config.guild(
                ctx.guild
            ).announcement_channel()

            warnings = []
            if not subscribed_games:
                warnings.append("⚠️ No games subscribed")
            if not announcement_channel:
                warnings.append("⚠️ No announcement channel set")

            if warnings:
                prefix = await self.get_prefix(ctx)
                embed.add_field(
                    name="Setup Required",
                    value="\n".join(warnings)
                    + f"\n\nUse `{prefix}patchconfig` to complete setup.",
                    inline=False,
                )

        await ctx.send(embed=embed)

    @patch_config.command(name="status")
    async def show_config(self, ctx):
        """Show current patch notes configuration"""
        guild_config = await self.config.guild(ctx.guild).all()

        embed = discord.Embed(title="🔧 Patch Notes Configuration", color=0x0099FF)

        # Announcement channel
        channel_id = guild_config["announcement_channel"]
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                embed.add_field(
                    name="📢 Announcement Channel", value=channel.mention, inline=False
                )
            else:
                embed.add_field(
                    name="📢 Announcement Channel",
                    value="⚠️ Channel not found (may have been deleted)",
                    inline=False,
                )
        else:
            embed.add_field(
                name="📢 Announcement Channel", value="❌ Not set", inline=False
            )

        # Auto announce status
        embed.add_field(
            name="🤖 Auto Announcements",
            value="✅ Enabled" if guild_config["auto_announce"] else "❌ Disabled",
            inline=False,
        )

        # Subscribed games
        subscribed_games = guild_config["subscribed_games"]
        if subscribed_games:
            games_list = "\n".join(
                [
                    f"{self.games[key]['emoji']} {self.games[key]['name']}"
                    for key in subscribed_games
                    if key in self.games
                ]
            )
        else:
            games_list = "None"

        embed.add_field(name="🎮 Subscribed Games", value=games_list, inline=False)

        prefix = await self.get_prefix(ctx)

        embed.add_field(
            name="⚙️ Configuration Commands",
            value=f"`{prefix}patchconfig channel #channel` - Set announcement channel\n"
            f"`{prefix}patchconfig remove` - Remove announcement channel\n"
            f"`{prefix}patchconfig subscribe <game>` - Subscribe to a game\n"
            f"`{prefix}patchconfig unsubscribe <game>` - Unsubscribe from a game\n"
            f"`{prefix}patchconfig toggle` - Toggle auto-announcements\n"
            f"`{prefix}patchconfig status` - Show this status",
            inline=False,
        )

        await ctx.send(embed=embed)

    async def get_announcement_channel(self, guild):
        """Get the configured announcement channel for a guild"""
        channel_id = await self.config.guild(guild).announcement_channel()
        if channel_id:
            return guild.get_channel(channel_id)
        return None

    async def get_prefix(self, ctx):
        """Get the bot prefix for the current context"""
        prefixes = await self.bot.get_valid_prefixes(ctx.guild)
        # Return the first prefix (usually the primary one)
        return prefixes[0] if prefixes else "!"
