import discord
import datetime
import websockets
import json
import asyncio
from redbot.core import commands

class Trakteer(commands.Cog):
    # init method or constructor
    def __init__(self, bot):
        self.bot = bot
        self.socket_task = self.bot.loop.create_task(self.wsrun('wss://socket.trakteer.id/app/2ae25d102cc6cd41100a'))

        #loop = asyncio.get_event_loop()
        #loop.run_until_complete(self.wsrun('wss://socket.trakteer.id/app/2ae25d102cc6cd41100a'))

    async def wsrun(self, uri):
        async with websockets.connect(uri) as self.websocket:
            await self.websocket.send('{"event":"pusher:subscribe","data":{"channel":"creator-stream.n8rx3ldzx7o4wamg.trstream-t6ZPmsNYQM061wcg5slw"}}')
            await self.websocket.send('{"event":"pusher:subscribe","data":{"channel":"creator-stream-test.n8rx3ldzx7o4wamg.trstream-t6ZPmsNYQM061wcg5slw"}}')
            while True:
                try:
                    resp = json.loads(await self.websocket.recv())
                    if resp['event'] == "Illuminate\\Notifications\\Events\\BroadcastNotificationCreated":
                        donator = json.loads(resp['data'])

                        embed = discord.Embed(color=0xEE2222, title='%s mentraktir %s %s' % (donator['supporter_name'], donator['quantity'], donator['unit']), timestamp=datetime.datetime.utcnow())
                        embed.url = 'https://trakteer.id/overwatch-idn/'
                        embed.description = 'Baru saja memberikan **%s**' % donator['price']
                        embed.set_thumbnail(url=donator['unit_icon'])
                        embed.add_field(name='Klik disini untuk ikut mentraktir',value='https://trakteer.id/overwatch-idn/')

                        '''
                        embed = discord.Embed(color=0xEE2222, title='%s baru saja mengirimkan %s' % (donator['supporter_name'], donator['price']), timestamp=datetime.datetime.utcnow())
                        embed.description = '👉 https://trakteer.id/overwatch-idn/'
                        embed.set_thumbnail(url=donator['unit_icon'])
                        embed.set_author(name='Donation Box', icon_url='https://i.imgur.com/kgrkybF.png')'''

                        if 'supporter_message' in donator and len(donator['supporter_message']) > 0:
                            embed.set_footer(text= donator['supporter_message'], icon_url=donator['supporter_avatar'])

                        await self.bot.get_channel(803626623596363786).send(embed=embed)
                except websockets.exceptions.ConnectionClosed:
                    #await asyncio.sleep(5)
                    await self.wsrun(uri)
                    break

    def cog_unload(self):
        self.socket_task.cancel()
        self.bot.loop.create_task(self.websocket.close())

#Trakteer(None)