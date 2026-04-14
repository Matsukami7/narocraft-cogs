"""
CatbunGithub — Red Bot cog
Automatically creates GitHub Issues from Discord bug reports and feature requests.

Copyright (C) 2026 Lone Pixel Studios
Licensed under the GNU General Public License v3.0
https://www.gnu.org/licenses/gpl-3.0.en.html

All configuration (GitHub token, repo, channel IDs) is stored securely via
Red Bot's built-in Config system. Nothing sensitive is hardcoded here.

Sources handled:
  - #bug-reports / #feature-requests channels (free text → GitHub Issue)
  - !bug and !feature commands
  - #ingame-reports channel (webhook from in-game reporter → GitHub Issue, labeled source:in-game)

Setup commands (bot owner only):
  [p]cbgithub setrepo owner/repo
  [p]cbgithub settoken <github_token>    ← message is deleted immediately after
  [p]cbgithub addbugchannel #channel
  [p]cbgithub addfeaturechannel #channel
  [p]cbgithub addingamechannel #channel
  [p]cbgithub setlogchannel #channel
  [p]cbgithub settings
"""

import aiohttp
import discord
from datetime import datetime, timezone
from redbot.core import commands, Config
from redbot.core.bot import Red


class CatbunGithub(commands.Cog):
    """Creates GitHub Issues from Discord bug reports and feature requests."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=8675309420)
        self.config.register_global(
            github_token=None,
            github_repo=None,
            bug_channel_ids=[],
            feature_channel_ids=[],
            ingame_channel_ids=[],
            log_channel_id=None,
        )

    # -------------------------------------------------------------------------
    # Admin setup commands
    # -------------------------------------------------------------------------

    @commands.group(name="cbgithub")
    @commands.is_owner()
    async def cbgithub(self, ctx: commands.Context):
        """CatbunGithub configuration."""

    @cbgithub.command(name="settoken")
    async def set_token(self, ctx: commands.Context, token: str):
        """Set the GitHub fine-grained PAT. Message is deleted immediately."""
        await ctx.message.delete()
        await self.config.github_token.set(token)
        await ctx.send("✅ GitHub token saved. Message deleted for safety.", delete_after=10)

    @cbgithub.command(name="setrepo")
    async def set_repo(self, ctx: commands.Context, repo: str):
        """Set the GitHub repo in owner/repo format."""
        await self.config.github_repo.set(repo)
        await ctx.send(f"✅ GitHub repo set to `{repo}`.")

    @cbgithub.command(name="addbugchannel")
    async def add_bug_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Watch a channel for bug reports."""
        ids = await self.config.bug_channel_ids()
        if channel.id not in ids:
            ids.append(channel.id)
            await self.config.bug_channel_ids.set(ids)
        await ctx.send(f"✅ Watching {channel.mention} for bug reports.")

    @cbgithub.command(name="addfeaturechannel")
    async def add_feature_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Watch a channel for feature requests."""
        ids = await self.config.feature_channel_ids()
        if channel.id not in ids:
            ids.append(channel.id)
            await self.config.feature_channel_ids.set(ids)
        await ctx.send(f"✅ Watching {channel.mention} for feature requests.")

    @cbgithub.command(name="addingamechannel")
    async def add_ingame_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Watch a channel for in-game webhook reports (labeled source:in-game)."""
        ids = await self.config.ingame_channel_ids()
        if channel.id not in ids:
            ids.append(channel.id)
            await self.config.ingame_channel_ids.set(ids)
        await ctx.send(f"✅ Watching {channel.mention} for in-game reports.")

    @cbgithub.command(name="setlogchannel")
    async def set_log_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set a channel to receive a log entry every time an issue is created."""
        await self.config.log_channel_id.set(channel.id)
        await ctx.send(f"✅ Issue log channel set to {channel.mention}.")

    @cbgithub.command(name="settings")
    async def show_settings(self, ctx: commands.Context):
        """Show current configuration."""
        repo        = await self.config.github_repo()
        token       = await self.config.github_token()
        bug_ids     = await self.config.bug_channel_ids()
        feat_ids    = await self.config.feature_channel_ids()
        ingame_ids  = await self.config.ingame_channel_ids()
        log_id      = await self.config.log_channel_id()

        def fmt_channels(ids):
            return ", ".join(f"<#{i}>" for i in ids) if ids else "None"

        embed = discord.Embed(title="CatbunGithub Settings", color=0x2ecc71)
        embed.add_field(name="Repo",             value=repo or "Not set",          inline=False)
        embed.add_field(name="Token",            value="Set ✅" if token else "Not set ❌", inline=False)
        embed.add_field(name="Bug channels",     value=fmt_channels(bug_ids),       inline=False)
        embed.add_field(name="Feature channels", value=fmt_channels(feat_ids),      inline=False)
        embed.add_field(name="In-game channels", value=fmt_channels(ingame_ids),    inline=False)
        embed.add_field(name="Log channel",      value=f"<#{log_id}>" if log_id else "None", inline=False)
        await ctx.send(embed=embed)

    # -------------------------------------------------------------------------
    # User commands
    # -------------------------------------------------------------------------

    @commands.command(name="bug")
    async def bug_command(self, ctx: commands.Context, *, description: str):
        """Report a bug. Usage: !bug <description>"""
        await self._handle_command_report(ctx, description, "bug")

    @commands.command(name="feature")
    async def feature_command(self, ctx: commands.Context, *, description: str):
        """Suggest a feature. Usage: !feature <description>"""
        await self._handle_command_report(ctx, description, "feature-request")

    # -------------------------------------------------------------------------
    # Message listener — watches configured channels
    # -------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and empty messages with no attachments
        if message.author.bot:
            return
        if not message.content and not message.attachments:
            return

        bug_ids    = await self.config.bug_channel_ids()
        feat_ids   = await self.config.feature_channel_ids()
        ingame_ids = await self.config.ingame_channel_ids()

        if message.channel.id in bug_ids:
            await self._handle_message_report(message, "bug", "source:discord")
        elif message.channel.id in feat_ids:
            await self._handle_message_report(message, "feature-request", "source:discord")
        elif message.channel.id in ingame_ids:
            await self._handle_message_report(message, "bug", "source:in-game")

    # -------------------------------------------------------------------------
    # Core logic
    # -------------------------------------------------------------------------

    async def _handle_message_report(self, message: discord.Message,
                                     report_type: str, source_label: str):
        """Create a GitHub issue from a watched channel message."""
        content = message.content or ""
        title = (content[:77] + "...") if len(content) > 80 else content or "In-game report"

        attachment_section = ""
        if message.attachments:
            links = "\n".join(f"- [{a.filename}]({a.url})" for a in message.attachments)
            attachment_section = f"\n\n**Attachments:**\n{links}"

        body = self._build_body(
            report_type=report_type,
            author_name=str(message.author),
            author_id=message.author.id,
            channel_name=message.channel.name,
            timestamp=message.created_at,
            content=content,
            attachment_section=attachment_section,
            jump_url=message.jump_url,
        )

        labels = [report_type, source_label, "status:triage"]
        issue_url = await self._create_github_issue(title, body, labels)

        if issue_url:
            await message.add_reaction("✅")
            await message.reply(f"📋 Logged → {issue_url}", mention_author=False)
            await self._post_to_log(report_type, source_label, title, issue_url)
        else:
            await message.add_reaction("❌")
            await message.reply(
                "❌ Failed to create GitHub issue. Check bot configuration.",
                mention_author=False,
                delete_after=15,
            )

    async def _handle_command_report(self, ctx: commands.Context,
                                     description: str, report_type: str):
        """Create a GitHub issue from a !bug or !feature command."""
        title = (description[:77] + "...") if len(description) > 80 else description

        body = self._build_body(
            report_type=report_type,
            author_name=str(ctx.author),
            author_id=ctx.author.id,
            channel_name=ctx.channel.name,
            timestamp=datetime.now(timezone.utc),
            content=description,
            attachment_section="",
            jump_url=ctx.message.jump_url,
        )

        labels = [report_type, "source:discord", "status:triage"]
        issue_url = await self._create_github_issue(title, body, labels)

        if issue_url:
            await ctx.message.add_reaction("✅")
            await ctx.send(
                f"✅ Thanks {ctx.author.mention}! Logged → {issue_url}",
                delete_after=30,
            )
            await self._post_to_log(report_type, "source:discord", title, issue_url)
        else:
            await ctx.send(
                "❌ Failed to create GitHub issue. Check bot configuration.",
                delete_after=15,
            )

    def _build_body(self, report_type, author_name, author_id, channel_name,
                    timestamp, content, attachment_section, jump_url):
        readable_type = report_type.replace("-", " ").title()
        ts = timestamp.strftime("%Y-%m-%d %H:%M UTC") if hasattr(timestamp, "strftime") else str(timestamp)
        return (
            f"## {readable_type}\n\n"
            f"**Reported by:** {author_name} (ID: `{author_id}`)\n"
            f"**Channel:** #{channel_name}\n"
            f"**Submitted:** {ts}\n\n"
            f"---\n\n"
            f"{content}"
            f"{attachment_section}\n\n"
            f"---\n"
            f"[View original Discord message]({jump_url})\n"
            f"*Auto-created by CatBunBot*"
        )

    async def _create_github_issue(self, title: str, body: str,
                                   labels: list) -> str | None:
        """POST to GitHub Issues API. Returns issue URL or None on failure."""
        token = await self.config.github_token()
        repo  = await self.config.github_repo()

        if not token or not repo:
            return None

        url = f"https://api.github.com/repos/{repo}/issues"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {"title": title, "body": body, "labels": labels}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return data["html_url"]
                else:
                    text = await resp.text()
                    print(f"[CatbunGithub] GitHub API error {resp.status}: {text}")
                    return None

    async def _post_to_log(self, report_type: str, source: str,
                           title: str, issue_url: str):
        """Post a one-liner to the configured log channel."""
        log_id = await self.config.log_channel_id()
        if not log_id:
            return
        channel = self.bot.get_channel(log_id)
        if channel:
            emoji = "🐛" if report_type == "bug" else "💡"
            src   = source.replace("source:", "")
            await channel.send(f"{emoji} `[{src}]` **{title}** → {issue_url}")
