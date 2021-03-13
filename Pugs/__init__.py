from .pugs import Pugs

async def setup(bot):
    n = Pugs(bot)
    bot.add_cog(n)
    await n.initialize()
