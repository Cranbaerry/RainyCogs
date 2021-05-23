import io
import time
import discord
import logging
import asyncio
import functools
import re
import requests
from TikTokApi.exceptions import TikTokCaptchaError
from redbot.core import commands, Config, checks
from TikTokApi import TikTokApi
from requests.exceptions import ConnectionError
from asyncio.exceptions import TimeoutError
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
from PIL import Image
from colorhash import ColorHash

UNIQUE_ID = 0x696969669


class MaximumProxyRequests(Exception):
    pass


class ProxyDatabaseEmpty(Exception):
    pass


class TikTok(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.log = logging.getLogger("tiktok")
        self.log.setLevel(logging.DEBUG)
        self.proxy = None
        self.api = None
        self.driver = None

        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.config.register_guild(subscriptions=[], cache=[])
        self.config.register_global(interval=300, cache_size=500, proxy=[], proxies=[], verifyFp=[])
        self.main_task = self.bot.loop.create_task(self.initialize())

    async def initialize(self):
        await self.bot.wait_until_red_ready()
        try:
            self.proxy = await self.config.proxy()
        except:
            self.proxy = None
            pass

        self.driver = ChromeDriverManager().install()
        verifyFp = await self.config.verifyFp()

        try:
            task = self.bot.loop.run_in_executor(None, self.get_tiktok_cookie)
            verifyFp = await asyncio.wait_for(task, timeout=30)
            await self.config.verifyFp.set(verifyFp)
        except TimeoutError:
            self.log.error("Could not fetch new verifyFP cookie")

        self.log.info(f"VerifyFp: {verifyFp}")
        self.api = TikTokApi.get_instance(use_test_endpoints=False, use_selenium=True,
                                          custom_verifyFp=verifyFp,
                                          logging_level=logging.DEBUG, executablePath=self.driver,
                                          proxy=self.proxy)

        self.log.info(f"Proxy: {self.proxy}")
        self.bot.loop.create_task(self.background_get_new_videos())

    def get_tiktok_by_name(self, username, count):
        try:
            data = self.api.byUsername(username, count=count)
        except TikTokCaptchaError:
            data = TikTokCaptchaError

        return data

    def get_tiktok_dynamic_cover(self, post):
        image_data = self.api.getBytes(url=post['video']['dynamicCover'], proxy=None)

        im = Image.open(io.BytesIO(image_data))
        im.info.pop('background', None)

        with io.BytesIO() as image_binary:
            im.save(image_binary, 'gif', save_all=True)
            # im.save(f"{post['id']}.gif", 'gif', save_all=True)
            image_binary.seek(0)
            file = discord.File(fp=image_binary, filename=f"{post['id']}.gif")
            self.log.info(f"Saved {post['id']}.gif")
            return file

    def get_tiktok_cookie(self):
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import TimeoutException

        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--test-type")
        options.add_argument("--headless")
        options.add_argument("--test-type")
        options.add_argument("--no-sandbox")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36")

        driver = webdriver.Chrome(executable_path=self.driver, options=options)
        url = 'https://www.tiktok.com/'
        driver.get(url)

        while True:
            try:
                cookie = driver.get_cookie('s_v_web_id').get('value')
            except AttributeError:
                time.sleep(1)
                continue
            else:
                break

        driver.quit()
        return cookie

    async def get_new_proxy(self, proxies, truncate=False):
        url = 'http://pubproxy.com/api/proxy?limit=5&format=txt&type=http'
        self.log.debug("Attempting to get new proxy..")

        if len(proxies) > 0:
            self.log.info(f"Cached proxies: {len(proxies['list'])}")
            self.log.info(f"Last update: {proxies['last-updated']}")
            self.log.info(f"Cached: {proxies['list']}")

        # More than 24 hours or empty
        if len(proxies) == 0 or \
                ('list' in proxies and len(proxies['list']) == 0) or \
                (datetime.now() - datetime.strptime(proxies['last-updated'], '%Y-%m-%d %H:%M:%S.%f')) > timedelta(1):
            self.log.debug("Updating proxy database..")
            proxies_list = []
            r = requests.get(url=url)
            res = r.text

            if 'We have to temporarily stop you.' in res:
                self.log.warning("Too fast, something went wrong..")
                asyncio.sleep(10)

            if 'You reached the maximum 50 requests for today.' in res:
                url = 'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt'
                self.log.info(f'Switched proxy database to {url}')

                r = requests.get(url=url)
                res = r.text

            for lines in res.split('\n'):
                proxy = ''.join(lines)
                proxies_list.append(proxy)

            proxies = {'last-updated': str(datetime.now()), 'list': proxies_list}

            await self.config.proxies.set(proxies)
            self.log.info(f"Proxies list updated: {proxies_list}")
        else:
            self.log.debug("Skipped proxy database update")

        if truncate:
            try:
                self.log.debug(f"Removing {self.api.proxy} from database")
                proxies['list'].remove(self.api.proxy)
                await self.config.proxies.set(proxies)
            except ValueError:
                pass

        if 'list' in proxies and len(proxies['list']) == 0:
            self.log.warning("Proxy database is empty..")
            return

        self.api.proxy = next(iter(proxies['list']))
        self.log.info(f"New proxy acquired: {self.api.proxy}")
        await self.config.proxy.set(self.api.proxy)

    async def get_new_videos(self):
        tiktoks = cover_file = None
        for guild in self.bot.guilds:
            try:
                subs = await self.config.guild(guild).subscriptions()
                cache = await self.config.guild(guild).cache()
            except:
                self.log.warning("Unable to fetch data, config is empty..")
                return
            for i, sub in enumerate(subs):
                # self.log.debug(f"Retrieving data of {sub['id']} from guild channel: {sub['channel']['name']}")
                channel = self.bot.get_channel(int(sub["channel"]["id"]))
                while True:
                    try:
                        task = functools.partial(self.get_tiktok_by_name, sub["id"], 3)
                        task = self.bot.loop.run_in_executor(None, task)
                        tiktoks = await asyncio.wait_for(task, timeout=30)

                        if tiktoks is TikTokCaptchaError:
                            raise TikTokCaptchaError()
                    except TimeoutError:
                        self.log.warning("Takes too long, retrying..")
                        # await self.get_new_proxy(await self.config.proxies(), True)
                        continue
                    except TikTokCaptchaError:
                        self.log.warning("Captcha error, retrying..")
                        await self.get_new_proxy(await self.config.proxies(), True)
                        continue
                    except ConnectionError as e:
                        self.log.warning(f"Connection error, retrying: {str(e)}")
                        await self.get_new_proxy(await self.config.proxies(), True)
                        continue
                    else:
                        break

                if not channel:
                    self.log.warning("Guild channel not found: " + sub["channel"]['name'])
                    continue

                if tiktoks is None or len(tiktoks) == 0:
                    self.log.warning("TikTok channel not found: " + sub["id"])
                    continue

                self.log.debug(f"Retrieved {len([post for post in tiktoks if not post['id'] in cache])} new video posts "
                               f"from {sub['id']} for {sub['channel']['name']} ({sub['channel']['id']})")

                for post in tiktoks:
                    if not post["id"] in cache:
                        self.log.debug(f"Posting {post['id']} to the channel")
                        color = int(hex(int(ColorHash(post['author']['uniqueId']).hex.replace("#", ""), 16)), 0)

                        # Send embed and post in channel
                        embed = discord.Embed(color=color,
                                              url=f"https://www.tiktok.com/@{post['author']['uniqueId']}/video/{post['id']}")
                        embed.timestamp = datetime.utcfromtimestamp(post['createTime'])
                        embed.description = re.sub(r'#(\w+)', r'[#\1](https://www.tiktok.com/tag/\1)',
                                                   f"{post['desc']}")
                        embed.add_field(
                            name=f"<:music:845585013327265822> {post['music']['title']} - {post['music']['authorName']}",
                            value=f"[Click to see full video!](https://www.tiktok.com/@{post['author']['uniqueId']}/video/{post['id']})",
                            inline=False)
                        embed.set_author(name=post['author']['nickname'],
                                         url=f"https://www.tiktok.com/@{post['author']['uniqueId']}",
                                         icon_url=post['author']['avatarMedium'])

                        # embed.set_thumbnail(url='https://i.imgur.com/xtvjGGD.png')
                        embed.set_thumbnail(url='https://i.imgur.com/ivShgrg.png')
                        # embed.set_footer(text='\u200b', icon_url='https://i.imgur.com/xtvjGGD.png')

                        try:
                            self.log.debug("Converting webp thumbnail to GIF..")
                            task = functools.partial(self.get_tiktok_dynamic_cover, post)
                            task = self.bot.loop.run_in_executor(None, task)
                            cover_file = await asyncio.wait_for(task, timeout=60)
                            embed.set_image(url=f"attachment://{post['id']}.gif")
                        except TimeoutError:
                            embed.set_image(url=post['video']['cover'])
                            self.log.warning("GIF processing too long..")
                        finally:
                            await self.bot.get_channel(sub["channel"]["id"]).send(embed=embed, file=cover_file)

                            # Add id to published cache
                            cache.append(post["id"])
                            await self.config.guild(guild).cache.set(cache)

    async def background_get_new_videos(self):
        await self.bot.wait_until_red_ready()
        while True:
            await self.get_new_videos()
            interval = await self.config.interval()
            await asyncio.sleep(interval)

    def cog_unload(self):
        self.log.debug("Shutting down TikTok service..")
        self.main_task.cancel()

    @commands.group()
    @commands.guild_only()
    async def tiktok(self: commands.Cog, ctx: commands.Context) -> None:
        """
        Role tools commands
        """
        pass

    @tiktok.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def add(self, ctx, tiktokId, channelDiscord: discord.TextChannel = None):
        """Subscribe a Discord channel to a TikTok Channel

        If no discord channel is specified, the current channel will be subscribed
        """
        if not channelDiscord:
            channelDiscord = ctx.channel

        color = int(hex(int(ColorHash(tiktokId).hex.replace("#", ""), 16)), 0)
        embed = discord.Embed(color=color)

        subs = await self.config.guild(ctx.guild).subscriptions()

        for i, sub in enumerate(subs):
            if sub['id'] == tiktokId:
                embed.description = f"[{tiktokId}](https://www.tiktok.com/@{tiktokId}) has already been subscribed to <#{sub['channel']['id']}>."
                await ctx.send(embed=embed)
                return

        newSub = {'id': tiktokId,
                  'channel': {"name": channelDiscord.name,
                              "id": channelDiscord.id}}

        subs.append(newSub)
        await self.config.guild(ctx.guild).subscriptions.set(subs)
        embed.description = f'TikTok feeds of user [{tiktokId}](https://www.tiktok.com/@{tiktokId}) added to <#{channelDiscord.id}>.'
        await ctx.send(embed=embed)

    @tiktok.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def remove(self, ctx: commands.Context, tiktokId, channelDiscord: discord.TextChannel = None):
        """Unsubscribe a Discord channel from a TikTok channel

        If no Discord channel is specified, the subscription will be removed from all channels"""
        subs = await self.config.guild(ctx.guild).subscriptions()
        unsubbed = []
        if channelDiscord:
            newSub = {'id': tiktokId,
                      'channel': {"name": channelDiscord.name,
                                  "id": channelDiscord.id}}

            for i, sub in enumerate(subs):
                if sub['id'] == newSub['id']:
                    unsubbed.append(subs.pop(i))
                    break
            else:
                await ctx.send("Subscription not found")
                return
        else:
            for i, sub in enumerate(subs):
                if sub['id'] == tiktokId:
                    unsubbed.append(subs.pop(i))
            if not len(unsubbed):
                await ctx.send("Subscription not found")
                return
        await self.config.guild(ctx.guild).subscriptions.set(subs)

        channels = f'<#{channelDiscord.id}>' if channelDiscord else 'all channels'
        color = int(hex(int(ColorHash(tiktokId).hex.replace("#", ""), 16)), 0)
        embed = discord.Embed(color=color)
        embed.description = f'TikTok feeds of user [{tiktokId}](https://www.tiktok.com/@{tiktokId}) no longer be ' \
                            f'subscriped to {channels} '
        await ctx.send(embed=embed)

    @tiktok.command()
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def clear(self, ctx):
        """Clear cached tiktok posts"""
        await self.config.guild(ctx.guild).cache.set([])

    @tiktok.command()
    @checks.is_owner()
    async def resetproxy(self, ctx):
        """Clear proxies database"""
        await self.config.proxies.set([])
        await ctx.send("Proxy database cleared!")

    @tiktok.command()
    @checks.is_owner()
    async def update(self, ctx):
        """Manually force feed update"""
        async with ctx.typing():
            await self.get_new_videos()

    @tiktok.command()
    @checks.is_owner()
    async def setinterval(self, ctx: commands.Context, interval: int):
        """Set the interval in seconds at which to check for updates

        Very low values will probably get you rate limited"""
        await self.config.interval.set(interval)
        await ctx.send(f"Interval set to {await self.config.interval()}")

    @commands.guild_only()
    @tiktok.command()
    async def list(self, ctx: commands.Context):
        """List current subscriptions"""
        await self._showsubs(ctx, ctx.guild)

    async def _showsubs(self, ctx: commands.Context, guild: discord.Guild):
        subs = await self.config.guild(guild).subscriptions()
        if not len(subs):
            await ctx.send("No subscriptions yet - try adding some!")
            return
        subs_by_channel = {}
        for sub in subs:
            channel = f'{sub["channel"]["name"]}'
            subs_by_channel[channel] = [
                f"<:PinkDot:838164789741617182> [{sub.get('name', sub['id'])}](https://www.tiktok.com/@{sub.get('name', sub['id'])})",
                *subs_by_channel.get(channel, [])
            ]

        for channel, sub_ids in subs_by_channel.items():
            page_count = (len(sub_ids) // 9) + 1
            page = 1
            while len(sub_ids) > 0:
                # Generate embed with max 1024 chars
                embed = discord.Embed(color=0xEE2222)
                title = f"Subscriptions for {channel}"
                embed.description = "\n".join(sub_ids[0:9])
                if page_count > 1:
                    title += f" ({page}/{page_count})"
                    page += 1
                embed.title = title
                await ctx.send(embed=embed)
                del (sub_ids[0:9])

    @tiktok.command()
    @checks.is_owner()
    async def setproxy(self, ctx: commands.Context, proxy):
        """Manually set HTTP proxy address"""
        self.api.proxy = proxy

        await self.config.proxy.set(proxy)
        await ctx.send(f"Proxy set to {await self.config.proxy()}")
        self.log.info(f"Proxy set to {await self.config.proxy()}")

    @tiktok.command()
    @checks.is_owner()
    async def setverify(self, ctx: commands.Context, txt):
        """Manually set verifyFp cookie value"""
        self.api.custom_verifyFp = txt

        await self.config.verifyFp.set(txt)
        await ctx.send(f"VerifyFp set to {await self.config.verifyFp()}")
        self.log.info(f"VerifyFp set to {await self.config.verifyFp()}")


#test = TikTok(None)
#test.get_tiktok_cookie()