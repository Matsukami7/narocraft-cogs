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
            "announcement_channel": None,
            "subscribed_games": [],
            "auto_announce": False,
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

    async def check_game_for_updates(self, guild, channel, game_key, guild_config):
        """Check a specific game for updates and announce if found"""
        try:
            success, result = await self.get_patch_notes(game_key, 5)

            if not success:
                return

            news_items = result["news_items"]
            if not news_items:
                return

            last_patches = guild_config.get("last_patches", {})
            last_seen_timestamp = last_patches.get(game_key, 0)

            # Find new patches (those with timestamps newer than last seen)
            new_patches = [
                item for item in news_items if item["date"] > last_seen_timestamp
            ]

            if not new_patches:
                return

            # Update the last seen timestamp
            newest_timestamp = max(item["date"] for item in new_patches)
            last_patches[game_key] = newest_timestamp
            await self.config.guild(guild).last_patches.set(last_patches)

            # Create and send announcement
            game_info = result["game_info"]
            embed = self.create_announcement_embed(game_info, new_patches)

            try:
                await channel.send(
                    f"🔔 **New {game_info['name']} patch notes are available!**",
                    embed=embed,
                )
                self.logger.info(
                    f"Announced {len(new_patches)} new patches for {game_key} in guild {guild.id}"
                )
            except discord.HTTPException as e:
                self.logger.error(
                    f"Failed to send announcement in guild {guild.id}: {e}"
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
        """Show help for patch note commands"""
        prefix = await self.get_prefix(ctx)

        embed = discord.Embed(
            title="🔧 Patch Notes Cog Help",
            description="Commands for fetching game patch notes",
            color=0x00FF00,
        )

        embed.add_field(
            name=f"{prefix}patchnotes [game] [count]",
            value="Get latest patch notes for any supported game\n`game`: Game name (e.g., factorio)\n`count`: Number of items (1-10, default: 3)",
            inline=False,
        )

        embed.add_field(
            name=f"{prefix}factorio [count]",
            value="Get latest Factorio patch notes (shortcut)\n`count`: Number of items (1-10, default: 3)",
            inline=False,
        )

        embed.add_field(
            name="Available Games",
            value="\n".join(
                [
                    f"{info['emoji']} **{info['name']}** - `{key}`"
                    for key, info in self.games.items()
                ]
            ),
            inline=False,
        )

        embed.add_field(
            name="Examples",
            value=f"`{prefix}patchnotes` - Show available games\n`{prefix}patchnotes factorio` - Get 3 latest Factorio patch notes\n`{prefix}patchnotes factorio 5` - Get 5 latest patch notes\n`{prefix}factorio` - Shortcut for Factorio",
            inline=False,
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
    async def subscribe_game(self, ctx, game: Optional[str] = None):
        """Subscribe to patch notes for a specific game

        Parameters:
        game: The game to subscribe to (e.g., factorio)
        """
        if game is None:
            # Show available games
            embed = discord.Embed(
                title="🎮 Subscribe to Game Patch Notes",
                description="Choose a game to subscribe to for automatic announcements",
                color=0x0099FF,
            )

            games_list = "\n".join(
                [
                    f"{info['emoji']} **{info['name']}** - `{key}`"
                    for key, info in self.games.items()
                ]
            )

            embed.add_field(name="Available Games", value=games_list, inline=False)

            prefix = await self.get_prefix(ctx)
            embed.add_field(
                name="Usage",
                value=f"`{prefix}patchconfig subscribe <game>`\nExample: `{prefix}patchconfig subscribe factorio`",
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

        if game_key in subscribed_games:
            game_info = self.games[game_key]
            await ctx.send(
                f"⚠️ This server is already subscribed to **{game_info['name']}** patch notes."
            )
            return

        # Add the subscription
        subscribed_games.append(game_key)
        await self.config.guild(ctx.guild).subscribed_games.set(subscribed_games)

        game_info = self.games[game_key]
        embed = discord.Embed(
            title="✅ Subscription Added",
            description=f"This server is now subscribed to **{game_info['emoji']} {game_info['name']}** patch notes!",
            color=0x00FF00,
        )

        # Initialize last seen timestamp with current latest patch
        success, result = await self.get_patch_notes(game_key, 1)
        if success and result["news_items"]:
            last_patches = await self.config.guild(ctx.guild).last_patches()
            last_patches[game_key] = result["news_items"][0]["date"]
            await self.config.guild(ctx.guild).last_patches.set(last_patches)
            embed.add_field(
                name="📋 Note",
                value="You'll receive announcements for patches released after this subscription.",
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
