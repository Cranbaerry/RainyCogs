import sys

import aiohttp
import discord
import logging
import asyncio
import functools
import re

from TikTokApi.exceptions import TikTokCaptchaError
from redbot.core import commands, Config, checks
from TikTokApi import TikTokApi
from urllib3.exceptions import NewConnectionError, ProxyError, MaxRetryError
from requests.exceptions import ConnectionError
from asyncio.exceptions import TimeoutError
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from PIL import Image

UNIQUE_ID = 0x696969669


class TikTok(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.log = logging.getLogger("tiktok")
        self.log.setLevel(logging.DEBUG)
        self.proxy = None
        self.api = None

        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.config.register_guild(subscriptions=[], cache=[])
        self.config.register_global(interval=300, cache_size=500, proxy=[])
        self.main_task = self.bot.loop.create_task(self.initialize())
        self.background_task = self.bot.loop.create_task(self.background_get_new_videos())

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

    def get_tiktok_by_name(self, username, count):
        return self.api.byUsername(username, count=count)

    def get_tikok_dynamic_cover(self, tiktok):
        self.log.debug(f"Writing the video: {tiktok['video']['dynamicCover']}")
        bytes = self.api.getBytes(url=tiktok['video']['dynamicCover'])
        self.log.debug("Bytes getto!")
        with open("{}.webp".format(tiktok['id']), "wb") as output:
            output.write(bytes)

        self.log.debug(f"Processing  {tiktok['id']}.gif")

        im = Image.open(f"{tiktok['id']}.webp")
        im.info.pop('background', None)
        im.save(f"{tiktok['id']}.gif", 'gif', save_all=True)
        self.log.debug(f"Saved {tiktok['id']}.gif")

        return f"{tiktok['id']}.gif"

    async def get_new_proxy(self):
        url = 'http://pubproxy.com/api/proxy?limit=1&format=txt&type=http'
        hdr = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=hdr) as resp:
                self.api.proxy = await resp.text()
                await self.config.proxy.set(self.api.proxy)
                self.log.debug(f"New proxy acquired: {self.api.proxy}")

    async def background_get_new_videos(self):
        await self.bot.wait_until_red_ready()
        self.log.debug("Running background..")
        while True:
            for guild in self.bot.guilds:
                try:
                    subs = await self.config.guild(guild).subscriptions()
                    cache = await self.config.guild(guild).cache()
                except:
                    self.log.debug("Unable to fetch data, config is empty..")
                    return
                for i, sub in enumerate(subs):
                    self.log.debug(f"Fetching data of {sub['id']} from guild channel: {sub['channel']['name']}")
                    channel = self.bot.get_channel(int(sub["channel"]["id"]))

                    try:
                        task = functools.partial(self.get_tiktok_by_name, sub["id"], 3)
                        task = self.bot.loop.run_in_executor(None, task)
                        tiktoks = await asyncio.wait_for(task, timeout=60)
                    except TikTokCaptchaError:
                        self.log.error("Asking captcha, need proxy")
                        await self.get_new_proxy()
                        continue
                    except ConnectionError as e:
                        self.log.error("Proxy failed: " + str(e))
                        await self.get_new_proxy()
                        continue
                    except TimeoutError:
                        self.log.error("Takes too long")
                        continue

                    self.log.debug("Response: " + str(tiktoks))
                    if not channel:
                        self.log.debug("Channel not found: " + sub["channel"]["name"])
                        continue
                    self.log.debug("Items: " + str(cache))
                    for post in tiktoks:
                        self.log.debug("Post ID: " + post["id"])
                        self.log.debug("Post Content: " + str(post))
                        if not post["id"] in cache:
                            self.log.debug("Sending data to channel: " + sub["channel"]["name"])
                            #task = functools.partial(self.get_tikok_dynamic_cover, tiktoks)
                            #task = self.bot.loop.run_in_executor(None, task)
                            #cover = await asyncio.wait_for(task, timeout=60)

                            cover = self.get_tikok_dynamic_cover(tiktoks)

                            # Send embed and post in channel
                            embed = discord.Embed(color=0xEE2222, title=post['author']['nickname'], url=f"https://www.tiktok.com/@{post['author']['uniqueId']}/video/{post['id']}")
                            embed.timestamp = datetime.utcfromtimestamp(post['createTime'])
                            embed.description = re.sub(r'#(\w+)', r'[#\1](https://www.tiktok.com/tag/\1)', post['desc'])
                            #embed.set_image(url=post['video']['dynamicCover'])
                            embed.set_footer(text=f"{post['music']['title']} - {post['music']['authorName']}", icon_url='https://i.imgur.com/RziGM2t.png')
                            embed.set_thumbnail(url=post['author']['avatarMedium'])

                            file = discord.File(cover)
                            embed.set_image(url=f"attachment://{cover}")

                            await self.bot.get_channel(sub["channel"]["id"]).send(embed=embed, file=file)
                            # Add id to published cache
                            cache.append(post["id"])
                            await self.config.guild(guild).cache.set(cache)
                            self.log.debug("Saved cache data: " + str(cache))
                        else:
                            self.log.debug("Skipping: " + post["id"])

                    self.log.debug("Sleeping 5 seconds..")
                    await asyncio.sleep(5)

            interval = await self.config.interval()
            self.log.debug(f"Sleeping {interval} seconds..")
            await asyncio.sleep(interval)

    def cog_unload(self):
        self.log.debug("Shutting down TikTok service..")
        self.background_task.cancel()
        self.main_task.cancel()

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
    async def clear(self, ctx):
        """Clear cache"""
        await self.config.guild(ctx.guild).cache.set([])
        await ctx.send("Cache cleared!")

    @tiktok.command()
    @checks.is_owner()
    async def setinterval(self, ctx: commands.Context, interval: int):
        """Set the interval in seconds at which to check for updates

        Very low values will probably get you rate limited

        Default is 300 seconds (5 minutes)"""
        await self.config.interval.set(interval)
        await ctx.send(f"Interval set to {await self.config.interval()}")

    @tiktok.command()
    @checks.is_owner()
    async def setproxy(self, ctx: commands.Context, proxy):
        """Set HTTP proxy address"""
        self.api.proxy = proxy

        await self.config.proxy.set(proxy)
        await ctx.send(f"Proxy set to {await self.config.proxy()}")
        self.log.debug(f"Proxy set to {await self.config.proxy()}")