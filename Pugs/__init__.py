from .pugs import Pugs

def setup(bot):
    n = Pugs(bot)
    bot.add_cog(n)
