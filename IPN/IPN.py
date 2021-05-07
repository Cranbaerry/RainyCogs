import json
import logging
import discord
import websockets
import asyncio
import threading
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
                data = json.loads(msg)

                self.log.debug(f"[IPN] < {msg}")
                embed = discord.Embed(color=0xEE2222, title='Payment from %s $s' % (data['first_name'], data['last_name']))
                embed.description = msg
                embed.add_field(name='Payment Received', value='%s %s' % (data['mc_gross'], data['mc_currency']))
                embed.add_field(name='Fee', value=data['mc_fee'])
                embed.add_field(name='Transaction ID', value=data['txn_id'])
                embed.add_field(name='Status', value=data['payment_status'])

                #for key, value in data.items():
                #    embed.add_field(name=key, value=value)

                embed.set_thumbnail(url='https://i.imgur.com/Mz2rAzF.png')
                await self.bot.get_channel(830267832889114644).send(embed=embed)

                await websocket.send("Hello")
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosed):
            self.log.debug("[IPN] Client connection closed")

    async def wsrun(self):
        try:
            async with websockets.serve(self.listen, "localhost", 8887):
                self.stop_event = threading.Event()
                asyncio.get_event_loop().run_in_executor(None, self.stop_event.wait)
            self.log.debug("[IPN] PayPal IPN websocket server started on port 8887")
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
        self.stop_event.set()
        self.socket_task.cancel()


#IPN(None)
