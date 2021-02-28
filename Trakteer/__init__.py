from .trakteer import Trakteer

def setup(bot):
    n = Trakteer(bot)
    bot.add_cog(n)
