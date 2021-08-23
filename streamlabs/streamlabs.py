# Imports #
import socketio
import asyncio
import discord
import logging
from redbot.core import commands

class Namespace(socketio.ClientNamespace):
    async def on_connect(self):
        print("Connected to Streamlabs for: " + socketio.ClientNamespace)

    async def on_message(self, data):
        print((data))
        # data.get('message')[0].get('name')
        if (data.get('type') == 'follow'):
            print(data.get('message')[0].get('name') + " is now following!")

    # elif (data.get('type') == 'follow'):

    async def on_disconnect(self):
        print("Disconnected.....")

class Streamlabs(commands.Cog):
    # init method or constructor
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.log = logging.getLogger("red")
        self.tasks = []
        self.keys = [{'channelId': 803626623596363786,
                      'socketToken': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbiI6IjlBQUY1OUFENDRFOTY5RkZEMkUwIiwi'
                                     'cmVhZF9vbmx5Ijp0cnVlLCJwcmV2ZW50X21hc3RlciI6dHJ1ZSwidHdpdGNoX2lkIjoiMjAzNDc5NTIxI'
                                     'iwieW91dHViZV9pZCI6IlVDWWdiOUFDbUZoeE1tb3hyOFYzSW5ZZyJ9.erMWarNRW2mhc8s1TXrLY-Rxg'
                                     '8cpNP9sN3IYt0dlXLg',
                      'channelUrl': 'https://trakteer.id/overwatch-idn',
                      'debug': True},]

        for key in self.keys:
            task = self.bot.loop.create_task(self.socket_thread(key))
            self.tasks.append(task)

    async def socket_thread(self, key):
        sio = socketio.AsyncClient()
        sio.register_namespace(Namespace('/' + key.get('channelId')))
        await sio.connect('https://sockets.streamlabs.com?token=' + key.get('socketToken'))
        await sio.wait()

