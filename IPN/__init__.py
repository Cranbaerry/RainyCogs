from .IPN import IPN

def setup(bot):
    n = IPN(bot)
    bot.add_cog(n)
