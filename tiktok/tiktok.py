import sys
from datetime import datetime

import discord
import logging
import asyncio
import websockets
import platform

from discord.ext import tasks
from redbot.core import commands, Config, checks
from TikTokApi import TikTokApi
from webdriver_manager.chrome import ChromeDriverManager

UNIQUE_ID = 0x696969669


class TikTok(commands.Cog):
    # init method or constructor
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.log = logging.getLogger("tiktok")
        self.log.setLevel(logging.DEBUG)
        self.api = TikTokApi.get_instance(use_test_endpoints=False, use_selenium=False, custom_verifyFp="verify_kox6wops_bqKwq1Wc_OhSG_4O03_9CG2_t8CvbVmI3gZn",
                                          logging_level=logging.ERROR, executablePath=ChromeDriverManager().install())

        self.log.debug("Verify: verify_kox68gzm_z2N190FQ_dmGv_4YgN_9eQo_YUNXoHldT8T6")

        if platform.system() == 'Windows':
            import threading

            stop_event = threading.Event()
            self.stop = asyncio.get_event_loop().run_in_executor(None, stop_event.wait) if __name__ == "__main__" else self.bot.loop.run_in_executor(None, stop_event.wait)
            # stop_event.set()
        elif platform.system() == "Linux":
            # The stop condition is set when receiving SIGTERM.
            # https://stackoverflow.com/questions/56663152/how-to-stop-websocket-server-created-with-websockets-serve
            import signal

            self.stop = asyncio.get_event_loop().create_future() if __name__ == "__main__" else self.bot.loop.create_future()
            self.bot.loop.add_signal_handler(signal.SIGTERM, self.stop.set_result, None)
            # loop.close()

        if __name__ != "__main__":
            self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
            self.config.register_guild(subscriptions=[], cache=[])
            self.config.register_global(interval=300, cache_size=500)
            self.background_get_new_videos.start()

    def get_tiktok_by_name(self, username, count):
        return self.api.byUsername(username, count=count)

    @tasks.loop(seconds=1)
    async def background_get_new_videos(self):
        for guild in self.bot.guilds:
            try:
                subs = await self.config.guild(guild).subscriptions()
                cache = await self.config.guild(guild).cache()
            except:
                self.log.debug("Unable to fetch data, config is empty..")
                return

            for i, sub in enumerate(subs):
                channel = self.bot.get_channel(int(sub["channel"]["id"]))
                tiktok = self.get_tiktok_by_name(sub["id"], 3)
                if not channel:
                    continue
                if not tiktok["id"] in cache.keys():
                    self.log.debug("Sending data to channel: " + sub["channel"]["name"])
                    # TODO: Send embed and post in channel
                    # Add id to published cache
                    cache.append(tiktok["id"])
                    await self.config.guild(guild).cache.set(cache)

    @background_get_new_videos.before_loop
    async def wait_for_red(self):
        await self.bot.wait_until_red_ready()
        interval = await self.config.interval()
        self.background_get_new_videos.change_interval(seconds=interval)

    def cog_unload(self):
        self.log.debug("Shutting down TikTok service..")
        #self.api.browser.browser.quit()
        if sys.platform.system() == 'Windows':
            self.stop_event.set()
        elif sys.platform.system() == "Linux":
            self.loop.close()
        self.background_get_new_videos.cancel()

    @commands.group()
    @commands.guild_only()
    async def tiktok(self: commands.Cog, ctx: commands.Context) -> None:
        """
        Role tools commands
        """
        pass

    @tiktok.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def add(self, ctx, tiktokId, channelDiscord: discord.TextChannel = None):
        """Subscribe a Discord channel to a TikTok Channel

        If no discord channel is specified, the current channel will be subscribed
        """
        if not channelDiscord:
            channelDiscord = ctx.channel

        subs = await self.config.guild(ctx.guild).subscriptions()
        newSub = {'id': tiktokId,
                  'channel': {"name": channelDiscord.name,
                              "id": channelDiscord.id}}

        subs.append(newSub)
        await self.config.guild(ctx.guild).subscriptions.set(subs)
        await ctx.send(f"Subscription added: {newSub}")

    @checks.is_owner()
    @tiktok.command(name="setinterval", hidden=True)
    async def set_interval(self, ctx: commands.Context, interval: int):
        """Set the interval in seconds at which to check for updates

        Very low values will probably get you rate limited

        Default is 300 seconds (5 minutes)"""
        await self.config.interval.set(interval)
        self.background_get_new_videos.change_interval(seconds=interval)
        await ctx.send(f"Interval set to {await self.config.interval()}")


if __name__ == "__main__":
    main = TikTok(None)