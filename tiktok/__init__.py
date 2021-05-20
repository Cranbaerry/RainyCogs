from .tiktok import tiktok

def setup(bot):
    n = tiktok(bot)
    bot.add_cog(n)
