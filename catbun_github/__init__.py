from .catbun_github import CatbunGithub


async def setup(bot):
    await bot.add_cog(CatbunGithub(bot))
