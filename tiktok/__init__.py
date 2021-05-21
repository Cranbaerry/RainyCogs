from .tiktok import TikTok


async def setup(bot):
    n = TikTok(bot)
    await n.initialize()
    bot.add_cog(n)
