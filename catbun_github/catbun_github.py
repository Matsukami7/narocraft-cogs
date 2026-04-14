"""
CatbunGithub — Red Bot cog
Automatically creates GitHub Issues from Discord bug reports and feature requests.

Copyright (C) 2026 Lone Pixel Studios
Licensed under the GNU General Public License v3.0
https://www.gnu.org/licenses/gpl-3.0.en.html

All configuration (GitHub token, repo, channel IDs) is stored securely via
Red Bot's built-in Config system. Nothing sensitive is hardcoded here.

Sources handled:
  - #bug-reports / #feature-requests channels (auto → GitHub Issue on every message)
  - ^bug and ^feature commands (auto → GitHub Issue)
  - #ingame-reports channel (triage mode — Developer reacts ✅ to create issue, ❌ to dismiss)

Setup commands (bot owner only):
  ^cbgithub setrepo owner/repo
  ^cbgithub settoken <github_token>    ← message is deleted immediately after
  ^cbgithub addbugchannel #channel
  ^cbgithub addfeaturechannel #channel
  ^cbgithub addtriagechannel #channel  ← in-game reports, requires Developer reaction
  ^cbgithub setdevrolename <role name> ← name of role allowed to triage (default: Developer)
  ^cbgithub setlogchannel #channel
  ^cbgithub settings
"""

import asyncio
import aiohttp
import discord
from datetime import datetime, timezone
from redbot.core import commands, Config
from redbot.core.bot import Red

APPROVE_EMOJI = "✅"
DISMISS_EMOJI = "❌"


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
            triage_channel_ids=[],   # in-game reports — held for Developer reaction
            log_channel_id=None,
            dev_role_name="Developer",
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
        """Watch a channel for bug reports (auto-creates issue on every message)."""
        ids = await self.config.bug_channel_ids()
        if channel.id not in ids:
            ids.append(channel.id)
            await self.config.bug_channel_ids.set(ids)
        await ctx.send(f"✅ Watching {channel.mention} for bug reports (auto mode).")

    @cbgithub.command(name="addfeaturechannel")
    async def add_feature_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Watch a channel for feature requests (auto-creates issue on every message)."""
        ids = await self.config.feature_channel_ids()
        if channel.id not in ids:
            ids.append(channel.id)
            await self.config.feature_channel_ids.set(ids)
        await ctx.send(f"✅ Watching {channel.mention} for feature requests (auto mode).")

    @cbgithub.command(name="addtriagechannel")
    async def add_triage_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Watch a channel in triage mode (in-game reports).
        Developer must react ✅ to create a GitHub Issue, ❌ to dismiss.
        """
        ids = await self.config.triage_channel_ids()
        if channel.id not in ids:
            ids.append(channel.id)
            await self.config.triage_channel_ids.set(ids)
        await ctx.send(
            f"✅ Watching {channel.mention} in **triage mode**.\n"
            f"React {APPROVE_EMOJI} to create a GitHub Issue, {DISMISS_EMOJI} to dismiss."
        )

    @cbgithub.command(name="setdevrolename")
    async def set_dev_role_name(self, ctx: commands.Context, *, role_name: str):
        """Set the role name allowed to triage in-game reports (default: Developer)."""
        await self.config.dev_role_name.set(role_name)
        await ctx.send(f"✅ Triage role set to `{role_name}`.")

    @cbgithub.command(name="setlogchannel")
    async def set_log_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set a channel to receive a log entry every time an issue is created."""
        await self.config.log_channel_id.set(channel.id)
        await ctx.send(f"✅ Issue log channel set to {channel.mention}.")

    @cbgithub.command(name="settings")
    async def show_settings(self, ctx: commands.Context):
        """Show current configuration."""
        repo          = await self.config.github_repo()
        token         = await self.config.github_token()
        bug_ids       = await self.config.bug_channel_ids()
        feat_ids      = await self.config.feature_channel_ids()
        triage_ids    = await self.config.triage_channel_ids()
        log_id        = await self.config.log_channel_id()
        dev_role_name = await self.config.dev_role_name()

        def fmt_channels(ids):
            return ", ".join(f"<#{i}>" for i in ids) if ids else "None"

        embed = discord.Embed(title="CatbunGithub Settings", color=0x2ecc71)
        embed.add_field(name="Repo",                    value=repo or "Not set",                      inline=False)
        embed.add_field(name="Token",                   value="Set ✅" if token else "Not set ❌",    inline=False)
        embed.add_field(name="Bug channels (auto)",     value=fmt_channels(bug_ids),                  inline=False)
        embed.add_field(name="Feature channels (auto)", value=fmt_channels(feat_ids),                 inline=False)
        embed.add_field(name="Triage channels",         value=fmt_channels(triage_ids),               inline=False)
        embed.add_field(name="Triage role",             value=dev_role_name,                          inline=False)
        embed.add_field(name="Log channel",             value=f"<#{log_id}>" if log_id else "None",   inline=False)
        await ctx.send(embed=embed)

    # -------------------------------------------------------------------------
    # User commands
    # -------------------------------------------------------------------------

    @commands.command(name="bug")
    async def bug_command(self, ctx: commands.Context, *, description: str):
        """Report a bug. Usage: ^bug <description>"""
        await self._handle_command_report(ctx, description, "bug")

    @commands.command(name="feature")
    async def feature_command(self, ctx: commands.Context, *, description: str):
        """Suggest a feature. Usage: ^feature <description>"""
        await self._handle_command_report(ctx, description, "feature-request")

    # -------------------------------------------------------------------------
    # Forum listener — fires when a new post is created in a forum channel
    # -------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        # Only handle forum posts (parent is a forum channel, type 15)
        if not thread.parent or thread.parent.type != discord.ChannelType.forum:
            return
        if thread.owner and thread.owner.bot:
            return

        bug_ids  = await self.config.bug_channel_ids()
        feat_ids = await self.config.feature_channel_ids()

        if thread.parent_id not in bug_ids and thread.parent_id not in feat_ids:
            return

        report_type = "bug" if thread.parent_id in bug_ids else "feature-request"

        # Starter message may not be cached yet — wait briefly then fetch
        await asyncio.sleep(1)
        try:
            starter = await thread.fetch_message(thread.id)
        except discord.NotFound:
            starter = None

        content = starter.content if starter else ""
        attachments = starter.attachments if starter else []

        title = (thread.name[:77] + "...") if len(thread.name) > 80 else thread.name

        attachment_section = ""
        if attachments:
            links = "\n".join(f"- [{a.filename}]({a.url})" for a in attachments)
            attachment_section = f"\n\n**Attachments:**\n{links}"

        body = self._build_body(
            report_type=report_type,
            author_name=str(thread.owner) if thread.owner else "Unknown",
            author_id=thread.owner_id,
            channel_name=thread.parent.name,
            timestamp=thread.created_at or datetime.now(timezone.utc),
            content=content,
            attachment_section=attachment_section,
            jump_url=thread.jump_url,
        )

        labels = [report_type, "source:discord", "status:triage"]
        issue_url = await self._create_github_issue(title, body, labels)

        if issue_url:
            await thread.send(f"📋 Logged → {issue_url}")
            await self._post_to_log(report_type, "source:discord", title, issue_url)
        else:
            await thread.send(
                "❌ Failed to create GitHub issue. Check bot configuration.",
            )

    # -------------------------------------------------------------------------
    # Message listener — triage channels only (in-game reports)
    # -------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.content and not message.attachments:
            return

        triage_ids = await self.config.triage_channel_ids()

        if message.channel.id in triage_ids:
            # Triage mode — add reaction prompts for Developer to act on
            await message.add_reaction(APPROVE_EMOJI)
            await message.add_reaction(DISMISS_EMOJI)

    # -------------------------------------------------------------------------
    # Reaction listener — triage mode
    # -------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return

        triage_ids    = await self.config.triage_channel_ids()
        dev_role_name = await self.config.dev_role_name()

        if payload.channel_id not in triage_ids:
            return

        # Fetch guild member to check role
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return

        # Only Developer role can triage
        has_dev_role = any(r.name == dev_role_name for r in member.roles)
        if not has_dev_role:
            return

        emoji = str(payload.emoji)
        if emoji not in (APPROVE_EMOJI, DISMISS_EMOJI):
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Ignore reactions on bot's own messages
        if message.author.id == self.bot.user.id:
            return

        if emoji == APPROVE_EMOJI:
            await self._triage_approve(message, member)
        elif emoji == DISMISS_EMOJI:
            await self._triage_dismiss(message, member)

    async def _triage_approve(self, message: discord.Message, reviewer: discord.Member):
        """Developer approved — create GitHub Issue from the in-game report."""
        content = message.content or ""
        title = (content[:77] + "...") if len(content) > 80 else content or "In-game report"

        attachment_section = ""
        if message.attachments:
            links = "\n".join(f"- [{a.filename}]({a.url})" for a in message.attachments)
            attachment_section = f"\n\n**Attachments:**\n{links}"

        body = self._build_body(
            report_type="bug",
            author_name=str(message.author),
            author_id=message.author.id,
            channel_name=message.channel.name,
            timestamp=message.created_at,
            content=content,
            attachment_section=attachment_section,
            jump_url=message.jump_url,
            extra=f"**Triaged by:** {reviewer.display_name}",
        )

        labels = ["bug", "source:in-game", "status:triage"]
        issue_url = await self._create_github_issue(title, body, labels)

        if issue_url:
            await message.reply(
                f"📋 Logged by {reviewer.mention} → {issue_url}",
                mention_author=False,
            )
            await self._post_to_log("bug", "source:in-game", title, issue_url)
        else:
            await message.reply(
                "❌ Failed to create GitHub issue. Check bot configuration.",
                mention_author=False,
                delete_after=15,
            )

    async def _triage_dismiss(self, message: discord.Message, reviewer: discord.Member):
        """Developer dismissed — mark and move on."""
        await message.reply(
            f"🗑️ Dismissed by {reviewer.mention}.",
            mention_author=False,
            delete_after=30,
        )

    # -------------------------------------------------------------------------
    # Core logic
    # -------------------------------------------------------------------------

    async def _handle_message_report(self, message: discord.Message,
                                     report_type: str, source_label: str):
        """Auto-create a GitHub issue from a watched channel message."""
        content = message.content or ""
        title = (content[:77] + "...") if len(content) > 80 else content or "Report"

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
        """Auto-create a GitHub issue from a ^bug or ^feature command."""
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
                    timestamp, content, attachment_section, jump_url, extra=""):
        readable_type = report_type.replace("-", " ").title()
        ts = timestamp.strftime("%Y-%m-%d %H:%M UTC") if hasattr(timestamp, "strftime") else str(timestamp)
        extra_section = f"\n{extra}" if extra else ""
        return (
            f"## {readable_type}\n\n"
            f"**Reported by:** {author_name} (ID: `{author_id}`)\n"
            f"**Channel:** #{channel_name}\n"
            f"**Submitted:** {ts}"
            f"{extra_section}\n\n"
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
