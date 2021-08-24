import datetime
import re

import socketio
import asyncio
import discord
import logging
from redbot.core import commands, Config, checks

UNIQUE_ID = 0x696969667
EMBED_COLOR = 0xCF83FF

class client():
    def __init__(self, sub, bot, log):
        self.bot = bot
        self.sub = sub
        self.log = log

        self.log.info("[streamlabs] Initializing socket client: " + self.sub.get("id"))

        self.sio = socketio.AsyncClient(reconnection=True, logger=True, engineio_logger=True)
        self.sio.on('connect', self.on_connect)
        self.sio.on('connect_error', self.connect_error)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('event', self.on_message)

    async def initialize(self):
        await self.sio.connect('https://sockets.streamlabs.com?token=' + self.sub.get('socketToken'))
        await self.sio.wait()

    async def on_connect(self):
        self.log.info(f"[streamlabs] {self.sub.get('id')} connected!")

    async def connect_error(self, data):
        self.log.info(f"[streamlabs] {self.sub.get('id')} encountered connection error!")

    async def on_disconnect(self):
        self.log.info(f"[streamlabs] {self.sub.get('id')} Disconnected!")

    async def on_message(self, data):
        if data.get('type') == 'follow':
            message = f"is now following!"
        elif data.get('type') == 'donation':
            message = f"donated {data.get('message')[0].get('formatted_amount')}."
        elif data.get('type') == 'subscription':
            message = f"subscribed for {str(data.get('message')[0].get('months'))} months."
        elif data.get('type') == 'resub':
            message = f"subscribed for {str(data.get('message')[0].get('months'))} months, currently " \
                      f"{str(data.get('message')[0].get('streak_months'))} on streak!"
        elif data.get('type') == 'host':
            message = f"hosting with {str(data.get('message')[0].get('viewers'))} viewers."
        elif data.get('type') == 'bits':
            message = f"cheered! x{data.get('message')[0].get('amount')}"
        elif data.get('type') == 'raid':
            message = f"is raiding with a party of {str(data.get('message')[0].get('raiders'))}."
        else:
            return

        # https://streamlabs.readme.io/docs/socket-api
        name = data.get('message')[0].get('name')
        embed = discord.Embed(color=EMBED_COLOR, title=f'{name} {message}')
        embed.timestamp = datetime.datetime.utcnow()
        # embed.set_thumbnail(url='https://i.imgur.com/XE1xwlZ.png')
        if 'message' in data.get('message')[0]:
            embed.description = data.get('message')[0].get('message')

        self.log.info(f"{data.get('message')[0].get('name')} {message}")

        embed.set_author(name=f"twitch.tv/{self.sub.get('id')}",
                         url=f"http://twitch.tv/{self.sub.get('id')}",
                         icon_url=self.sub.get('icon'))

        await self.bot.get_channel(self.sub.get['channel'].get('id')).send(embed=embed)


class Streamlabs(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.log = logging.getLogger("red")
        self.connections = []
        self.tasks = []
        self.log.info("[streamlabs] Initializing..")
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        self.config.register_guild(subscriptions=[])
        self.bot.loop.create_task(self.initialize())

    async def initialize(self):
        await self.bot.wait_until_red_ready()
        for guild in self.bot.guilds:
            subs = await self.config.guild(guild).subscriptions()
            for sub in subs:
                conn = client(sub, self.bot, self.log)
                task = self.bot.loop.create_task(conn.initialize())
                self.tasks.append(task)
                self.connections.append(conn)

    def clear_connections(self):
        for conn in self.connections:
            self.bot.loop.create_task(conn.sio.disconnect())
            self.log.info(f"[streamlabs] Disconnecting socket client: {conn.sub.get('id')}")

        for task in self.tasks:
            task.cancel()

    def cog_unload(self):
        self.clear_connections()

    @commands.guild_only()
    @commands.group()
    async def streamlabs(self: commands.Cog, ctx: commands.Context) -> None:
        """
        Streamlabs commands
        """
        pass

    @streamlabs.group()
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def clear(self, ctx):
        """Remove all subscriptions in the server"""
        self.clear_connections()
        await self.config.guild(ctx.guild).subscriptions.set([])
        await ctx.send("Subscriptions cleared!")

    @streamlabs.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def add(self, ctx, twitchChannel, channelDiscord: discord.TextChannel = None):
        """Subscribe a Discord Channel to a Twitch Channel

        If no discord channel is specified, the current channel will be subscribed
        """
        profileLink = re.search(r'https://www.twitch.tv/([^/?]+)', twitchChannel)
        if profileLink is not None:
            twitchChannel = profileLink.group(1)

        if not channelDiscord:
            channelDiscord = ctx.channel

        embed = discord.Embed(color=EMBED_COLOR)
        subs = await self.config.guild(ctx.guild).subscriptions()

        for i, sub in enumerate(subs):
            if sub['id'] == twitchChannel:
                embed.description = f"[{twitchChannel}](https://www.twitch.tv/{twitchChannel}) " \
                                    f"has already been subscribed to <#{sub['channel']['id']}>"
                await ctx.send(embed=embed)
                return

        message = await ctx.send("%s The bot needs additional sensitive information. "
                                 "Please check your DM." % ctx.message.author.mention)

        try:
            try:
                await ctx.author.send("Please enter your secret token "
                                      "which can be found in streamlabs.com API Settings.")
                token = await ctx.bot.wait_for(
                    "message", check=lambda m: m.author == ctx.message.author, timeout=120
                )
            except asyncio.TimeoutError:
                await ctx.author.send("Your response has timed out, please try again.")
                return

            try:
                await ctx.author.send("Please enter your channel icon URL.")
                iconUrl = await ctx.bot.wait_for(
                    "message", check=lambda m: m.author == ctx.message.author, timeout=120
                )
            except asyncio.TimeoutError:
                await ctx.author.send("Your response has timed out, please try again.")
                return

            await ctx.author.send("Your response has been recorded.")
        except discord.errors.Forbidden:
            await ctx.send("Unable to proceed.\nPlease make sure this bot is allowed to DM you in this server.")
            return

        try:
            await message.delete()
        except:
            pass

        newSub = {'id': twitchChannel,
                  'channel': {"name": channelDiscord.name,
                              "id": channelDiscord.id},
                  'icon': iconUrl.content,
                  'socketToken': token.content}

        subs.append(newSub)
        await self.config.guild(ctx.guild).subscriptions.set(subs)
        embed.description = f'Twitch events of channel [{twitchChannel}](https://www.twitch.tv/{twitchChannel}) ' \
                            f'added to <#{channelDiscord.id}>'

        conn = client(newSub, self.bot, self.log)
        task = self.bot.loop.create_task(conn.initialize())
        self.tasks.append(task)
        self.connections.append(conn)
        await ctx.send(embed=embed)

    @streamlabs.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def remove(self, ctx: commands.Context, twitchChannel, channelDiscord: discord.TextChannel = None):
        """Unsubscribe a Discord Channel from a Twitch Channel

        If no Discord channel is specified, the subscription will be removed from all channels"""
        profileLink = re.search(r'https://www.twitch.tv/([^/?]+)', twitchChannel)
        if profileLink is not None:
            twitchChannel = profileLink.group(1)

        subs = await self.config.guild(ctx.guild).subscriptions()
        unsubbed = []
        if channelDiscord:
            newSub = {'id': twitchChannel,
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
                if sub['id'] == twitchChannel:
                    unsubbed.append(subs.pop(i))
            if not len(unsubbed):
                await ctx.send("Subscription not found")
                return
        await self.config.guild(ctx.guild).subscriptions.set(subs)

        channels = f'<#{channelDiscord.id}>' if channelDiscord else 'all channels'
        embed = discord.Embed(color=EMBED_COLOR)
        embed.description = f'Twitch events of channel [{twitchChannel}](https://www.twitch.tv/{twitchChannel}) no longer be ' \
                            f'subscribed to {channels}'
        await ctx.send(embed=embed)

        for conn in self.connections:
            if conn.sub.get("id") == twitchChannel:
                self.bot.loop.create_task(conn.sio.disconnect())
                self.log.info(f"[streamlabs] Disconnecting socket client: {conn.sub.get('id')}")
                break

    @commands.guild_only()
    @streamlabs.command()
    async def list(self, ctx: commands.Context):
        """List active subscriptions in the server"""
        subs = await self.config.guild(ctx.guild).subscriptions()
        if not len(subs):
            await ctx.send("No subscriptions yet - try adding some!")
            return
        subs_by_channel = {}
        for sub in subs:
            channel = f'{sub["channel"]["name"]}'
            subs_by_channel[channel] = [
                f"○ [{sub.get('name', sub['id'])}](https://www.twitch.tv/{sub.get('name', sub['id'])})",
                *subs_by_channel.get(channel, [])
            ]

        for channel, sub_ids in subs_by_channel.items():
            page_count = (len(sub_ids) // 9) + 1
            page = 1
            while len(sub_ids) > 0:
                # Generate embed with max 1024 chars
                embed = discord.Embed(color=0xEE2222)
                title = f"Subscriptions on {channel}"
                embed.description = "\n".join(sub_ids[0:9])
                if page_count > 1:
                    title += f" ({page}/{page_count})"
                    page += 1
                embed.title = title
                await ctx.send(embed=embed)
                del (sub_ids[0:9])

