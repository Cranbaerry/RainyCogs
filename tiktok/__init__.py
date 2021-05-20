from .tiktok import TikTok

def setup(bot):
    n = TikTok(bot)
    bot.add_cog(n)
