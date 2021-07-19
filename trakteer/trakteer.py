import functools
import logging
import threading

import discord
import datetime
import websockets
import json
import asyncio
from redbot.core import commands

log = logging.getLogger("red")

class Trakteer(commands.Cog):
    # init method or constructor
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.keys = ['creator-stream.n8rx3ldzx7o4wamg.trstream-t6ZPmsNYQM061wcg5slw',
                     'creator-stream.6am740y9vaj5z0vp.trstream-6Oml9NSUZMm4yuQK5Z7H']
        self.tasks = []
        self.websockets = []
        self.log = log
        for key in self.keys:
            event = threading.Event()
            self.log.debug("[trakteer] Adding thread %s" % key)
            task = functools.partial(self.websocket_thread, key, event, self.log)
            task = self.bot.loop.run_in_executor(None, task)
            self.tasks.append([task, event])

        self.log.debug("[trakteer] Trakteer threads initialized!")

        # loop = asyncio.get_event_loop()
        # loop.run_until_complete(self.websocket_thread())

    async def connect(self, key):
        uri = 'wss://socket.trakteer.id/app/2ae25d102cc6cd41100a'
        self.log.debug("[trakteer] Attempting to connect for key %s" % key)
        websocket = await websockets.connect(uri)
        while True:
            response = json.loads(await websocket.recv())
            # print(response)
            if response['event'] == 'pusher:connection_established':
                self.log.debug("[trakteer] Connected to %s" % uri)
                await websocket.send(json.dumps({
                    "event": "pusher:subscribe",
                    "data": {"channel": key}
                }))
                await websocket.send(json.dumps({
                    "event": "pusher:subscribe",
                    "data": {"channel": key.replace('creator-stream', 'creator-stream-test')}
                }))
                return websocket

    async def websocket_thread(self, key, event, logu):
        try:
            self.log = logging.getLogger("red")
            log.debug("[trakteer] Web socket test ")
            websocket = await asyncio.wait_for(self.connect(key), 30)
            self.websockets.append(websocket)
            while True:
                if event.is_set():
                    self.log.info("[trakteer] Websocket stopped gracefully for %s" % key)
                    return

                response = json.loads(await websocket.recv())
                # print(response)
                if response['event'] != 'pusher:pong':
                    self.log.debug('[trakteer] %s' % response)

                if response['event'] == 'Illuminate\\Notifications\\Events\\BroadcastNotificationCreated':
                    donator = json.loads(response['data'])

                    embed = discord.Embed(color=0xEE2222, title='%s mentraktir %s %s' % (
                        donator['supporter_name'], donator['quantity'], donator['unit']),
                                          timestamp=datetime.datetime.utcnow())
                    embed.url = 'https://trakteer.id/overwatch-idn/'
                    embed.description = 'Baru saja memberikan **%s**' % donator['price']
                    embed.set_thumbnail(url=donator['unit_icon'])
                    embed.add_field(name='Klik disini untuk ikut mentraktir',
                                    value='https://trakteer.id/overwatch-idn/')
                    if 'supporter_message' in donator:
                        embed.set_footer(text=donator['supporter_message'], icon_url=donator['supporter_avatar'])

                    await self.bot.get_channel(803626623596363786).send(embed=embed)
                else:
                    await websocket.send(json.dumps({"event": "pusher:ping", "data": {}}))
                    await asyncio.sleep(1)
        except asyncio.exceptions.TimeoutError:
            self.log.warning("[trakteer] Attempting to reconnect due to connection timeout")
            await self.websocket_thread(key)
        except websockets.exceptions.ConnectionClosed:
            self.log.warning("[trakteer] Attempting to reconnect due to connection closed")
            await self.websocket_thread(key)
        except Exception as e:
            self.log.warning("[trakteer] Attempting to reconnect due to: " + str(e))
            await self.websocket_thread(key)

    def cog_unload(self):
        for task in self.tasks:
            task[0].cancel()
            task[1].set()
        for socket in self.websockets:
            self.bot.loop.create_task(socket.close())