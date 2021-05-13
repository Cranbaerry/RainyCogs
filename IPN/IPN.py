import json
import logging
import discord
import websockets
import asyncio
import threading
import pycountry
from redbot.core import commands


class IPN(commands.Cog):
    # init method or constructor
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.socket_task = self.bot.loop.create_task(self.wsrun())
        self.log = logging.getLogger("red")
        self.stop_event = threading.Event()
        self.stop = self.bot.loop.run_in_executor(None, self.stop_event.wait)

        #loop = asyncio.get_event_loop()
        #loop.run_until_complete(self.wsrun())

    async def listen(self, websocket, path):
        try:
            self.log.debug("[IPN] Client connection established")
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)

                self.log.debug(f"[IPN] < {msg}")
                embed = discord.Embed(color=0xCBC3E3, title='Payment from %s %s' % (data['first_name'], data['last_name']))
                # embed.set_author(name='%s %s' % (data['first_name'], data['last_name']), icon_url='https://cdn.discordapp.com/embed/avatars/0.png')
                embed.add_field(name='Payment Received', value='%s %s' % (data['mc_gross'], data['mc_currency']), inline=True)

                if 'mc_fee' in data:
                    embed.add_field(name='Fee', value='%s %s' % (data['mc_fee'], data['mc_currency']), inline=True)

                embed.add_field(name='E-mail Address', value=data['payer_email'], inline=False)
                embed.add_field(name='Country', value='%s (%s)' % (pycountry.countries.get(alpha_2=data['residence_country']).name, data['residence_country']), inline=False)
                embed.add_field(name='Transaction ID', value=data['txn_id'], inline=False)
                embed.add_field(name='Date', value=data['payment_status'], inline=False)
                embed.add_field(name='Status', value=data['payment_date'], inline=False)
                embed.set_image(url="https://i.pinimg.com/originals/f3/e0/5e/f3e05e008d8d5e0eda6c0fa8f559ab28.gif")
                embed.set_thumbnail(url='https://i.imgur.com/Mz2rAzF.png')
                embed.set_footer(text='Track ID: %s | %s' % (data['ipn_track_id'].upper(), data['payment_date']))
                embed.url = 'https://www.paypal.com/activity/payment/%s' % data['txn_id']
                await self.bot.get_channel(830267832889114644).send(embed=embed)

                await websocket.send("Hello")
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosed):
            self.log.debug("[IPN] Client connection closed")

    async def wsrun(self):
        try:
            self.log.debug("[IPN] Serving websocket on port 8887")
            async with websockets.serve(self.listen, "localhost", 8887):
                await self.stop
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
        self.log.debug("[IPN] Shutting down websocket server..")
        self.stop_event.set()
        self.socket_task.cancel()


#IPN(None)
