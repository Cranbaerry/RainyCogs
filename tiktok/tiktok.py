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
        self.proxy = None

        if __name__ != "__main__":
            self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
            self.config.register_guild(subscriptions=[], cache=[])
            self.config.register_global(interval=300, cache_size=500, proxy=[])
            self.background_get_new_videos.start()

        self.api = TikTokApi.get_instance(use_test_endpoints=False, use_selenium=True,
                                          custom_verifyFp="verify_kox6wops_bqKwq1Wc_OhSG_4O03_9CG2_t8CvbVmI3gZn",
                                          logging_level=logging.DEBUG, executablePath=ChromeDriverManager().install(),
                                          proxy=self.proxy)

    async def init_proxy(self):
        try:
            self.proxy = await self.config.proxy()
        except:
            self.proxy = None
            pass

        self.log.debug(f"Proxy: {self.config.proxy()}")

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
                self.log.debug("Fetching data from guild: " + sub["channel"]["name"])
                channel = self.bot.get_channel(int(sub["channel"]["id"]))
                tiktok = self.get_tiktok_by_name(sub["id"], 3)
                self.log.debug("Response: " + str(tiktok))
                if not channel:
                    self.log.debug("Channel not found: " + sub["channel"]["name"])
                    continue
                self.log.debug("Items: " + cache())
                if not tiktok["id"] in cache.keys():
                    self.log.debug("Sending data to channel: " + sub["channel"]["name"])
                    # TODO: Send embed and post in channel
                    # Add id to published cache
                    cache.append(tiktok["id"])
                    await self.config.guild(guild).cache.set(cache)
                    self.log.debug("Saved cache data: " + cache)

    @background_get_new_videos.before_loop
    async def wait_for_red(self):
        await self.bot.wait_until_red_ready()
        interval = await self.config.interval()
        self.background_get_new_videos.change_interval(seconds=interval)

    def cog_unload(self):
        self.log.debug("Shutting down TikTok service..")
        # self.api.browser.browser.quit()
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

    @tiktok.command()
    @checks.is_owner()
    async def setinterval(self, ctx: commands.Context, interval: int):
        """Set the interval in seconds at which to check for updates

        Very low values will probably get you rate limited

        Default is 300 seconds (5 minutes)"""
        await self.config.interval.set(interval)
        self.background_get_new_videos.change_interval(seconds=interval)
        await ctx.send(f"Interval set to {await self.config.interval()}")

    @tiktok.command()
    @checks.is_owner()
    async def setproxy(self, ctx: commands.Context, proxy):
        self.api.proxy = proxy

        await self.config.proxy.set(proxy)
        await ctx.send(f"Proxy set to {await self.config.proxy()}")


if __name__ == "__main__":
    main = TikTok(None)
