from .Together import Together

def setup(bot):
    n = Together(bot)
    bot.add_cog(n)
