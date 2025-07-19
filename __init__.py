from .patchcog import PatchCog


async def setup(bot):
    await bot.add_cog(PatchCog(bot))