import datetime
import websockets
import json
import discord
from redbot.core import commands

class Trakteer(commands.Cog):
    # init method or constructor
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.wsrun('wss://socket.trakteer.id/app/2ae25d102cc6cd41100a'))

    async def wsrun(self, uri):
        async with websockets.connect(uri) as self.websocket:
            await self.websocket.send('{"event":"pusher:subscribe","data":{"channel":"creator-stream.n8rx3ldzx7o4wamg.trstream-t6ZPmsNYQM061wcg5slw"}}')
            await self.websocket.send('{"event":"pusher:subscribe","data":{"channel":"creator-stream-test.n8rx3ldzx7o4wamg.trstream-t6ZPmsNYQM061wcg5slw"}}')
            while True:
                resp = json.loads(await self.websocket.recv())
                if resp['event'] == "Illuminate\\Notifications\\Events\\BroadcastNotificationCreated":
                    #print(resp['data'])
                    donator = json.loads(resp['data'])

                    embed = discord.Embed(color=0xEE2222, title='%s mentraktir %s %s' % (donator['supporter_name'], donator['quantity'], donator['unit']), timestamp=datetime.datetime.utcnow())
                    embed.description = donator['supporter_message']
                    embed.set_thumbnail(url=donator['unit_icon'])
                    embed.set_footer(text=donator['price'], icon_url='https://i.imgur.com/0b4L7uL.png')
                    await self.bot.get_channel(803626623596363786).send(embed=embed)

    def cog_unload(self):
        self.bot.loop.create_task(self.websocket.close())
