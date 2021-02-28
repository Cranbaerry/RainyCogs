import asyncio
from datetime import datetime

import websockets
import json
import discord

class Trakteer:
    # init method or constructor
    def __init__(self, bot):
        self.bot = bot
        #await self.wsrun('wss://socket.trakteer.id/app/2ae25d102cc6cd41100a')
        asyncio.get_event_loop().run_until_complete(self.wsrun('wss://socket.trakteer.id/app/2ae25d102cc6cd41100a'))

    async def wsrun(self, uri):
        async with websockets.connect(uri) as self.websocket:
            await self.websocket.send('{"event":"pusher:subscribe","data":{"channel":"creator-stream.n8rx3ldzx7o4wamg.trstream-t6ZPmsNYQM061wcg5slw"}}')
            await self.websocket.send('{"event":"pusher:subscribe","data":{"channel":"creator-stream-test.n8rx3ldzx7o4wamg.trstream-t6ZPmsNYQM061wcg5slw"}}')
            while True:
                resp = json.loads(await self.websocket.recv())
                # print(resp)
                if resp['event'] == "Illuminate\\Notifications\\Events\\BroadcastNotificationCreated":
                    donator = resp['data']
                    embed = discord.Embed(color=0xEE2222, title='%s mentraktir %s %s' % (donator['supporter_name'], donator['quantity'], donator['supporter_message']), timestamp=datetime.datetime.utcnow())
                    embed.description = donator['supporter_message']
                    embed.set_thumbnail(url=donator['unit_icon'])
                    embed.set_author(name='Pick-Up Games Registration', icon_url='https://i.imgur.com/kgrkybF.png')
                    embed.set_footer(text=donator['price'], icon_url='https://www.flaticon.com/svg/vstatic/svg/715/715709.svg?token=exp=1614506121~hmac=3f881af053c9eb64afbd8f666b5b60fb')
                    await self.bot.get_channel(653090156961857539).send(embed=embed)

    def cog_unload(self):
        self.bot.loop.create_task(self.websocket.close())
