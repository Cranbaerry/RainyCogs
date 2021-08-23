import datetime

import socketio
import asyncio
import discord
import logging
from redbot.core import commands


class client():
    def __init__(self, key, bot, log):
        self.bot = bot
        self.key = key
        self.log = log

        self.log.info("[streamlabs] socket thread: /" + str(key.get("channelId")))
        self.log.info("[streamlabs] socket token: " + key.get("socketToken"))

        self.sio = socketio.AsyncClient(logger=True, engineio_logger=True)
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('event', self.on_message)

    async def initialize(self):
        await self.sio.connect('https://sockets.streamlabs.com?token=' + self.key.get('socketToken'))
        await self.sio.wait()

    async def on_connect(self):
        self.log.info("[streamlabs] Connected!")

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
        # name = f"[{data.get('message')[0].get('name')}](https://www.twitch.tv/{data.get('message')[0].get('name')})"
        name = data.get('message')[0].get('name')
        embed = discord.Embed(color=0xCF83FF, title=f'{name} {message}')
        embed.timestamp = datetime.datetime.utcnow()
        # embed.set_thumbnail(url='https://i.imgur.com/XE1xwlZ.png')
        if 'message' in data.get('message')[0]:
            embed.description = data.get('message')[0].get('message')

        #name = f"[{data.get('message')[0].get('name')}](https://www.twitch.tv/{data.get('message')[0].get('name')})"
        #name = f"[{data.get('message')[0].get('name')}](https://www.twitch.tv/{data.get('message')[0].get('name')})"
        self.log.info(f"{data.get('message')[0].get('name')} {message}")

        embed.set_author(name=f"twitch.tv/{self.key.get('channelName')}",
                         url=f"http://twitch.tv/{self.key.get('channelName')}",
                         icon_url=self.key.get('channelIcon'))

        await self.bot.get_channel(self.key['channelId']).send(embed=embed)

    async def on_disconnect(self):
        self.log.info("[streamlabs] Disconnected")


class Streamlabs(commands.Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.log = logging.getLogger("red")
        self.sockets = []
        self.tasks = []
        self.keys = [{'channelId': 879290657078927450,
                      'channelName': 'nefiliapurin',
                      'channelIcon': 'https://cdn.discordapp.com/emojis/848913149494689792.png',
                      'socketToken': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbiI6IjlBQUY1OUFENDRFOTY5RkZEMkUwIiwi'
                                     'cmVhZF9vbmx5Ijp0cnVlLCJwcmV2ZW50X21hc3RlciI6dHJ1ZSwidHdpdGNoX2lkIjoiMjAzNDc5NTIxI'
                                     'iwieW91dHViZV9pZCI6IlVDWWdiOUFDbUZoeE1tb3hyOFYzSW5ZZyJ9.erMWarNRW2mhc8s1TXrLY-Rxg'
                                     '8cpNP9sN3IYt0dlXLg',
                      'debug': True},]

        self.log.info("[streamlabs] Initializing..")

        for key in self.keys:
            conn = client(key, bot, self.log)
            task = self.bot.loop.create_task(conn.initialize())
            self.tasks.append(task)
            self.sockets.append(conn.sio)

    def cog_unload(self):
        for task in self.tasks:
            task.cancel()
        for socket in self.sockets:
            self.bot.loop.create_task(socket.disconnect())
