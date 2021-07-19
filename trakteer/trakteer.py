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
        self.keys = [{'channelId': 803626623596363786,
                      'channelKey': 'creator-stream.n8rx3ldzx7o4wamg.trstream-t6ZPmsNYQM061wcg5slw',
                      'channelUrl': 'https://trakteer.id/overwatch-idn',
                      'debug': True},
                     {'channelId': 842043854294220840,
                      'channelKey': 'creator-stream.6am740y9vaj5z0vp.trstream-6Oml9NSUZMm4yuQK5Z7H',
                      'channelUrl': 'https://trakteer.id/itspurinch',
                      'debug': True}]
        self.tasks = []
        self.websockets = []
        self.log = log
        for key in self.keys:
            task = self.bot.loop.create_task(self.websocket_thread(key))
            self.tasks.append(task)

        self.log.debug("[trakteer] Trakteer threads initialized!")

        # loop = asyncio.get_event_loop()
        # loop.run_until_complete(self.websocket_thread())

    async def connect(self, key):
        uri = 'wss://socket.trakteer.id/app/2ae25d102cc6cd41100a'
        self.log.debug("[trakteer] Attempting to connect for key %s" % key['channelKey'])
        websocket = await websockets.connect(uri)
        while True:
            response = json.loads(await websocket.recv())
            # print(response)
            if response['event'] == 'pusher:connection_established':
                # self.log.debug("[trakteer] Connected to %s" % uri)
                await websocket.send(json.dumps({
                    "event": "pusher:subscribe",
                    "data": {"channel": key['channelKey']}
                }))

                if key['debug']:
                    await websocket.send(json.dumps({
                        "event": "pusher:subscribe",
                        "data": {"channel": key['channelKey'].replace('creator-stream', 'creator-stream-test')}
                    }))
                return websocket

    async def websocket_thread(self, key):
        try:
            websocket = await asyncio.wait_for(self.connect(key), 30)
            self.websockets.append(websocket)
            while True:
                response = json.loads(await websocket.recv())
                if response['event'] == 'pusher_internal:subscription_succeeded':
                    self.log.debug('[trakteer] Successfully subscribed to %s' % response['channel'])
                # print(response)
                elif response['event'] != 'pusher:pong':
                    self.log.debug('[trakteer] %s' % response)

                if response['event'] == 'Illuminate\\Notifications\\Events\\BroadcastNotificationCreated':
                    donator = json.loads(response['data'])

                    click_here = f"[Klik disini untuk ikut mentraktir!]({key.get('channelUrl')})"
                    donate_info = f"🎁 Baru saja memberikan {donator['price']}"

                    embed = discord.Embed(color=0xEE2222, url=key.get('channelUrl'))
                    embed.timestamp = datetime.datetime.utcnow()
                    if 'supporter_message' in donator:
                        embed.description = donator['supporter_message']
                    embed.add_field(name=donate_info, value=click_here, inline=False)
                    embed.set_author(name=donator['supporter_name'], url=key.get('channelUrl'),
                                     icon_url=donator['supporter_avatar'])
                    embed.set_thumbnail(url=donator['unit_icon'])

                    await self.bot.get_channel(key['channelId']).send(embed=embed)
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
            task.cancel()
        for socket in self.websockets:
            self.bot.loop.create_task(socket.close())
