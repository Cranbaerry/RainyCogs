import logging
import discord
import websockets
import asyncio
import datetime
from redbot.core import commands


class IPN(commands.Cog):
    # init method or constructor
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.socket_task = self.bot.loop.create_task(self.wsrun())
        self.log = logging.getLogger("red")

        #loop = asyncio.get_event_loop()
        #loop.run_until_complete(self.wsrun())

    async def listen(self, websocket, path):
        try:
            self.log.debug("[IPN] Client connection established")
            while True:
                msg = await websocket.recv()
                self.log.debug(f"[IPN] < {msg}")

                embed = discord.Embed(color=0xEE2222, title='%s mentraktir %s %s' % (
                    'silly', 'test', 'gay'),
                                      timestamp=datetime.datetime.utcnow())
                embed.url = 'https://trakteer.id/overwatch-idn/'
                embed.description = msg
                #embed.set_thumbnail(url=donator['unit_icon'])
                embed.add_field(name='Klik disini untuk ikut mentraktir',
                                value='https://trakteer.id/overwatch-idn/')


                await self.bot.get_channel(830267832889114644).send(embed=embed)

                #await websocket.send(greeting)
                #print(f"> {greeting}")
        except websockets.exceptions.ConnectionClosedError:
            self.log.debug("[IPN] Client connection closed")

    async def wsrun(self):
        try:
            await websockets.serve(self.listen, "localhost", 8887)
            self.log.warning("[IPN] PayPal IPN websocket server started on port 8887")
            while True:
                await asyncio.sleep(1)
        except asyncio.exceptions.TimeoutError:
            self.log.warning("[IPN] Attempting to reconnect due to connection timeout")
            await self.wsrun()
        except websockets.exceptions.ConnectionClosed:
            self.log.warning("[IPN] Attempting to reconnect due to connection closed")
            await self.wsrun()
        except Exception as e:
            self.log.warning("[IPN] Attempting to reconnect due to: " + str(e))
            await self.wsrun()

    def cog_unload(self):
        self.socket_task.cancel()
        self.bot.loop.create_task(self.websocket.close())


#IPN(None)
