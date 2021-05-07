import json
import logging
import discord
import websockets
import asyncio
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
                embed = discord.Embed(color=0xCBC3E3, title='Payment from %s %s' % (data['first_name'], data['last_name']))
                embed.add_field(name='Payment Received', value='%s %s' % (data['mc_gross'], data['mc_currency']), inline=True)
                embed.add_field(name='Fee', value='%s %s' % (data['mc_fee'], data['mc_currency']), inline=True)
                embed.add_field(name='E-mail Address', value=data['payer_email'], inline=False)
                embed.add_field(name='Country', value=data['address_country'], inline=False)
                embed.add_field(name='Transaction ID', value=data['txn_id'], inline=False)
                embed.add_field(name='Status', value=data['payment_status'], inline=False)
                embed.set_image(url="https://i.pinimg.com/originals/f3/e0/5e/f3e05e008d8d5e0eda6c0fa8f559ab28.gif")
                embed.set_thumbnail(url='https://i.imgur.com/Mz2rAzF.png')
                embed.set_footer(text=data['payment_date'])
                embed.url = 'https://www.paypal.com/activity/payment/%s' % data['txn_id']
                await self.bot.get_channel(830267832889114644).send(embed=embed)

                await websocket.send("Hello")
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosed):
            self.log.debug("[IPN] Client connection closed")

    async def wsrun(self):
        try:
            await websockets.serve(self.listen, "localhost", 8887)
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
        #self.stop_event.set()
        self.socket_task.cancel()


#IPN(None)
