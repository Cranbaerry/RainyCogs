from .tiktok import TikTok


async def setup(bot):
    n = TikTok(bot)
    await n.init_proxy()
    bot.add_cog(n)
