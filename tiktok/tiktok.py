import sys
from datetime import datetime

import discord
import logging
import asyncio
import websockets
import platform

from TikTokApi.exceptions import TikTokCaptchaError
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
            self.bot.loop.create_task(self.initialize())

    async def initialize(self):
        await self.bot.wait_until_red_ready()
        try:
            self.proxy = await self.config.proxy()
        except:
            self.proxy = None
            pass

        self.api = TikTokApi.get_instance(use_test_endpoints=False, use_selenium=True,
                                          custom_verifyFp="verify_kox6wops_bqKwq1Wc_OhSG_4O03_9CG2_t8CvbVmI3gZn",
                                          logging_level=logging.DEBUG, executablePath=ChromeDriverManager().install(),
                                          proxy=self.proxy)

        self.log.debug(f"Proxy: {await self.config.proxy()}")

    async def get_tiktok_by_name(self, username, count):
        return self.api.byUsername(username, count=count)

    @tasks.loop(seconds=300)
    async def background_get_new_videos(self):
        for guild in self.bot.guilds:
            try:
                subs = await self.config.guild(guild).subscriptions()
                cache = await self.config.guild(guild).cache()
            except:
                self.log.debug("Unable to fetch data, config is empty..")
                return
            #self.log.debug(f"Iterating in: {guild.name}")
            for i, sub in enumerate(subs):
                self.log.debug(f"Fetching data of {sub['id']} from guild channel: {sub['channel']['name']}")
                channel = self.bot.get_channel(int(sub["channel"]["id"]))
                try:
                    tiktoks = await self.get_tiktok_by_name(sub["id"], 3)
                except TikTokCaptchaError:
                    self.log.error("Asking captcha, need proxy")
                    continue
                #self.log.debug("Response: " + str(tiktoks))
                if not channel:
                    self.log.debug("Channel not found: " + sub["channel"]["name"])
                    continue
                self.log.debug("Items: " + str(cache))
                for post in tiktoks:
                    self.log.debug("Post ID: " + post["id"])
                    self.log.debug("Post Content: " + str(post))
                    if not post["id"] in cache:
                        self.log.debug("Sending data to channel: " + sub["channel"]["name"])
                        # TODO: Send embed and post in channel
                        # Add id to published cache
                        cache.append(post["id"])
                        await self.config.guild(guild).cache.set(cache)
                        self.log.debug("Saved cache data: " + str(cache))
                    else:
                        self.log.debug("Skipping: " + post["id"])

                self.log.debug("Sleeping 5 seconds..")
                await asyncio.sleep(5)


    @background_get_new_videos.before_loop
    async def wait_for_red(self):
        await self.bot.wait_until_red_ready()
        interval = await self.config.interval()
        self.log.debug(f"Background process interval is set to {interval}")
        self.background_get_new_videos.change_interval(seconds=interval)

    def cog_unload(self):
        self.log.debug("Shutting down TikTok service..")
        self.background_get_new_videos.cancel()
        # self.api.browser.browser.quit()

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

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @tiktok.command()
    async def remove(self, ctx: commands.Context, channelYouTube, channelDiscord: discord.TextChannel = None):
        """Unsubscribe a Discord channel from a TikTok channel

        If no Discord channel is specified, the subscription will be removed from all channels"""
        subs = await self.config.guild(ctx.guild).subscriptions()
        unsubbed = []
        if channelDiscord:
            newSub = {'id': channelYouTube,
                      'channel': {"name": channelDiscord.name,
                                  "id": channelDiscord.id}}
            newSub['uid'] = self.sub_uid(newSub)
            for i, sub in enumerate(subs):
                if sub['uid'] == newSub['uid']:
                    unsubbed.append(subs.pop(i))
                    break
            else:
                await ctx.send("Subscription not found")
                return
        else:
            for i, sub in enumerate(subs):
                if sub['id'] == channelYouTube:
                    unsubbed.append(subs.pop(i))
            if not len(unsubbed):
                await ctx.send("Subscription not found")
                return
        await self.config.guild(ctx.guild).subscriptions.set(subs)
        await ctx.send(f"Subscription(s) removed: {unsubbed}")

    @tiktok.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def update(self, ctx):
        """Manually force update"""
        self.background_get_new_videos()

    @tiktok.command()
    @checks.is_owner()
    async def stop(self, ctx):
        """Manually stop background process to check videos"""
        self.background_get_new_videos().cancel()

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
        """Set HTTP proxy address"""
        self.api.proxy = proxy

        await self.config.proxy.set(proxy)
        await ctx.send(f"Proxy set to {await self.config.proxy()}")


if __name__ == "__main__":
    main = TikTok(None)
