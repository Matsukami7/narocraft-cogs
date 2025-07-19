import aiohttp
import discord
import re
from redbot.core import commands, Config
from datetime import datetime

class PatchCog(commands.Cog):
    """A cog for fetching game patch notes"""

    def __init__(self, bot):
        self.bot = bot
        self.steam_api_base = "http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
        
        # Initialize config
        self.config = Config.get_conf(self, identifier=1234567890)
        default_guild = {
            "announcement_channel": None,
            "subscribed_games": [],
            "auto_announce": False
        }
        self.config.register_guild(**default_guild)
        
        # Game database with Steam App IDs and display info
        self.games = {
            "factorio": {
                "appid": "427520",
                "name": "Factorio",
                "emoji": "🏭",
                "color": 0xFF6B35,  # Orange
                "aliases": ["factorio"]
            },
            "stellaris": {
                "appid": "281990",
                "name": "Stellaris",
                "emoji": "🌌",
                "color": 0x4A90E2,  # Blue
                "aliases": ["stellaris"]
            },
            "ffxiv": {
                "appid": "39210",
                "name": "Final Fantasy XIV",
                "emoji": "⚔️",
                "color": 0x8B4513,  # Brown/Bronze
                "aliases": ["ffxiv", "ff14", "finalfantasy14", "finalfantasyxiv"]
            }
        }

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
                    'appid': game_info['appid'],
                    'count': count,
                    'maxlength': 500,
                    'format': 'json'
                }
                
                async with session.get(self.steam_api_base, params=params) as response:
                    if response.status != 200:
                        return False, f"Failed to fetch patch notes. Status: {response.status}"
                    
                    data = await response.json()
                    
                    if 'appnews' not in data or 'newsitems' not in data['appnews']:
                        return False, f"No news data found for {game_info['name']}."
                    
                    news_items = data['appnews']['newsitems']
                    
                    if not news_items:
                        return False, f"No recent patch notes found for {game_info['name']}."
                    
                    return True, {
                        'game_info': game_info,
                        'news_items': news_items[:count]
                    }
                    
        except aiohttp.ClientError as e:
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, f"An error occurred: {str(e)}"
    
    def create_patch_embed(self, game_info: dict, news_items: list):
        """Create a Discord embed for patch notes"""
        embed = discord.Embed(
            title=f"{game_info['emoji']} {game_info['name']} Patch Notes",
            color=game_info['color'],
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Powered by Steam API")
        
        for item in news_items:
            # Convert timestamp to readable date
            date = datetime.fromtimestamp(item['date']).strftime('%Y-%m-%d')
            
            # Clean up the content
            content = item['contents']
            if len(content) > 400:
                content = content[:400] + "..."
            
            # Remove HTML tags if present
            content = re.sub(r'<[^>]+>', '', content)
            
            embed.add_field(
                name=f"📅 {item['title']} ({date})",
                value=f"{content}\n[Read More]({item['url']})",
                inline=False
            )
        
        return embed
    
    @commands.command(name="patchnotes", aliases=["patch", "patches"])
    async def patch_notes_unified(self, ctx, game: str = None, count: int = 3):
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
            embed = discord.Embed(
                title="🎮 Available Games",
                description="Use `^patchnotes <game>` to get patch notes",
                color=0x00FF00
            )
            
            games_list = "\n".join([
                f"{info['emoji']} **{info['name']}** - `{key}`"
                for key, info in self.games.items()
            ])
            
            embed.add_field(
                name="Supported Games",
                value=games_list,
                inline=False
            )
            
            embed.add_field(
                name="Examples",
                value="`^patchnotes factorio` - Get 3 latest Factorio patch notes\n`^patchnotes factorio 5` - Get 5 latest patch notes",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # Normalize game name and check aliases
        game = game.lower()
        game_key = None
        
        for key, info in self.games.items():
            if game == key or game in info.get('aliases', []):
                game_key = key
                break
        
        if game_key is None:
            available_games = ", ".join(self.games.keys())
            await ctx.send(f"❌ Game '{game}' not supported. Available games: {available_games}")
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
        
        embed = self.create_patch_embed(result['game_info'], result['news_items'])
        await ctx.send(embed=embed)
    
    @commands.command(name="factorio")
    async def factorio_patch(self, ctx, count: int = 3):
        """Get the latest Factorio patch notes (alias for patchnotes factorio)"""
        await self.patch_notes_unified(ctx, "factorio", count)

    @commands.command(name="patchhelp")
    async def patch_help(self, ctx):
        """Show help for patch note commands"""
        embed = discord.Embed(
            title="🔧 Patch Notes Cog Help",
            description="Commands for fetching game patch notes",
            color=0x00FF00
        )
        
        embed.add_field(
            name="^patchnotes [game] [count]",
            value="Get latest patch notes for any supported game\n`game`: Game name (e.g., factorio)\n`count`: Number of items (1-10, default: 3)",
            inline=False
        )
        
        embed.add_field(
            name="^factorio [count]",
            value="Get latest Factorio patch notes (shortcut)\n`count`: Number of items (1-10, default: 3)",
            inline=False
        )
        
        embed.add_field(
            name="Available Games",
            value="\n".join([
                f"{info['emoji']} **{info['name']}** - `{key}`"
                for key, info in self.games.items()
            ]),
            inline=False
        )
        
        embed.add_field(
            name="Examples",
            value="`^patchnotes` - Show available games\n`^patchnotes factorio` - Get 3 latest Factorio patch notes\n`^patchnotes factorio 5` - Get 5 latest patch notes\n`^factorio` - Shortcut for Factorio",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.group(name="patchconfig", aliases=["pconfig"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def patch_config(self, ctx):
        """Configure patch notes settings for this server"""
        if ctx.invoked_subcommand is None:
            await self.show_config(ctx)
    
    @patch_config.command(name="channel")
    async def set_channel(self, ctx, channel: discord.TextChannel = None):
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
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    
    @patch_config.command(name="remove")
    async def remove_channel(self, ctx):
        """Remove the announcement channel (disable announcements)"""
        await self.config.guild(ctx.guild).announcement_channel.set(None)
        
        embed = discord.Embed(
            title="✅ Channel Removed",
            description="Patch note announcements have been disabled for this server.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    
    @patch_config.command(name="status")
    async def show_config(self, ctx):
        """Show current patch notes configuration"""
        guild_config = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="🔧 Patch Notes Configuration",
            color=0x0099FF
        )
        
        # Announcement channel
        channel_id = guild_config["announcement_channel"]
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                embed.add_field(
                    name="📢 Announcement Channel",
                    value=channel.mention,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📢 Announcement Channel",
                    value="⚠️ Channel not found (may have been deleted)",
                    inline=False
                )
        else:
            embed.add_field(
                name="📢 Announcement Channel",
                value="❌ Not set",
                inline=False
            )
        
        # Auto announce status
        embed.add_field(
            name="🤖 Auto Announcements",
            value="✅ Enabled" if guild_config["auto_announce"] else "❌ Disabled",
            inline=False
        )
        
        # Subscribed games
        subscribed_games = guild_config["subscribed_games"]
        if subscribed_games:
            games_list = ", ".join(subscribed_games)
        else:
            games_list = "None"
        
        embed.add_field(
            name="🎮 Subscribed Games",
            value=games_list,
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Configuration Commands",
            value="`^patchconfig channel #channel` - Set announcement channel\n"
                  "`^patchconfig remove` - Remove announcement channel\n"
                  "`^patchconfig status` - Show this status",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def get_announcement_channel(self, guild):
        """Get the configured announcement channel for a guild"""
        channel_id = await self.config.guild(guild).announcement_channel()
        if channel_id:
            return guild.get_channel(channel_id)
        return None