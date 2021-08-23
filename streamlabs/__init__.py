from .streamlabs import Streamlabs

async def setup(bot):
    n = Streamlabs(bot)
    bot.add_cog(n)
