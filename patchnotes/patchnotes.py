import aiohttp
import discord
from redbot.core import commands
from datetime import datetime

class PatchCog(commands.Cog):
    """A cog for fetching game patch notes"""

    def __init__(self, bot):
        self.bot = bot
        self.steam_api_base = "http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
        # Factorio's Steam App ID
        self.factorio_appid = "427520"

    @commands.command(name="factorio")
    async def factorio_patch(self, ctx, count: int = 3):
        """Get the latest Factorio patch notes from Steam
        
        Parameters:
        count: Number of news items to fetch (default: 3, max: 10)
        """
        if count > 10:
            count = 10
        elif count < 1:
            count = 1
            
        await ctx.typing()
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'appid': self.factorio_appid,
                    'count': count,
                    'maxlength': 500,
                    'format': 'json'
                }
                
                async with session.get(self.steam_api_base, params=params) as response:
                    if response.status != 200:
                        await ctx.send(f"❌ Failed to fetch patch notes. Status: {response.status}")
                        return
                    
                    data = await response.json()
                    
                    if 'appnews' not in data or 'newsitems' not in data['appnews']:
                        await ctx.send("❌ No news data found for Factorio.")
                        return
                    
                    news_items = data['appnews']['newsitems']
                    
                    if not news_items:
                        await ctx.send("📰 No recent patch notes found for Factorio.")
                        return
                    
                    # Create embed for the response
                    embed = discord.Embed(
                        title="🏭 Factorio Patch Notes",
                        color=0xFF6B35,  # Factorio orange color
                        timestamp=datetime.utcnow()
                    )
                    embed.set_footer(text="Powered by Steam API")
                    
                    for i, item in enumerate(news_items[:count]):
                        # Convert timestamp to readable date
                        date = datetime.fromtimestamp(item['date']).strftime('%Y-%m-%d')
                        
                        # Clean up the content
                        content = item['contents']
                        if len(content) > 400:
                            content = content[:400] + "..."
                        
                        # Remove HTML tags if present
                        import re
                        content = re.sub(r'<[^>]+>', '', content)
                        
                        embed.add_field(
                            name=f"📅 {item['title']} ({date})",
                            value=f"{content}\n[Read More]({item['url']})",
                            inline=False
                        )
                    
                    await ctx.send(embed=embed)
                    
        except aiohttp.ClientError as e:
            await ctx.send(f"❌ Network error: {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.command(name="patchhelp")
    async def patch_help(self, ctx):
        """Show help for patch note commands"""
        embed = discord.Embed(
            title="🔧 Patch Notes Cog Help",
            description="Commands for fetching game patch notes",
            color=0x00FF00
        )
        
        embed.add_field(
            name="^factorio [count]",
            value="Get latest Factorio patch notes\n`count`: Number of items (1-10, default: 3)",
            inline=False
        )
        
        embed.add_field(
            name="Examples",
            value="`^factorio` - Get 3 latest patch notes\n`^factorio 5` - Get 5 latest patch notes",
            inline=False
        )
        
        await ctx.send(embed=embed)